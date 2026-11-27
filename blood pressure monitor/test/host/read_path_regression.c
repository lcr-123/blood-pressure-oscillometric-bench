/* Host only. Actual ADS1115 driver + actual main inflate/hold/readtest code.
 * A register-level fake validates every transmitted byte and models 8 ms
 * conversion latency. This is a software test, never a hardware diagnosis. */
#include "ads1115.h"
#include "bp_control.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#define MANUAL_PRESSURE_SAMPLE_INTERVAL_MS BP_SAMPLE_INTERVAL_MS
#define MANUAL_PUMP_TIMEOUT_MS 60000U
#define DEFLATE_HOLD_MS 1000U
#define ZERO_PULSE_ACTIVE 2U
#define LOADED_PULSE_ACTIVE 3U
#define READ_TEST_DURATION_MS 10000U
#define READ_TEST_MIN_SAMPLES 380U
#define GPIO_PIN_SET 1U
#define GPIO_PIN_RESET 0U
#define VALVE1_CTRL_Port 0U
#define VALVE1_CTRL_Pin 0U
#define VALVE2_CTRL_Port 1U
#define VALVE2_CTRL_Pin 0U
#define PUMP_RELAY_Port 8U
#define PUMP_RELAY_Pin 0U

I2C_TypeDef host_i2c1;
GPIO_TypeDef host_gpiob = {0xC0U};
static I2C_HandleTypeDef hi2c1 = {I2C1, 0U, 0x20U};
static struct { uint32_t start_ms; uint16_t samples; uint8_t active; } s_read_test;
static uint8_t s_manual_pump_active, s_hold_open_active, s_deflate_pwm_enabled;
static uint8_t s_deflate_test_active, s_calculation_pending, s_ads1115_ready;
static uint8_t s_last_pressure_sample_valid, calibrated = 1U;
static uint32_t s_manual_pressure_last_ms, s_ads1115_last_attempt_ms;
static uint32_t s_last_pressure_sample_ms, s_manual_pump_start_ms;
static uint32_t s_deflate_hold_until_ms, s_deflate_pulse_remaining_ms;
static float g_last_pressure_mmhg, s_inflate_target_mmhg;
static ADS1115_Sample_t s_last_pressure_sample;
static BP_Result_t g_bp_result, s_result;
static BP_Fault_t s_fault;
static BP_State_t s_state;
static uint32_t s_fault_time_ms, ticks, conversion_started;
static unsigned conversions, deinit_count, writes, failures;
static uint8_t pins[9], selected_reg, never_ready, expect_vent;
static int16_t raw_code;
/* 1=start, 2=config select, 3=config receive, 4=raw select, 5=raw receive */
static unsigned fail_at;
static HAL_StatusTypeDef fail_status;
static char output[4096];

uint32_t HAL_GetTick(void) { return ticks; }
void HAL_Delay(uint32_t delay) { ticks += delay; }
uint32_t HAL_I2C_GetError(I2C_HandleTypeDef *bus) { return bus->ErrorCode; }
uint32_t HAL_I2C_GetState(I2C_HandleTypeDef *bus) { return bus->State; }
void host_reset_bus(uint8_t asserted) { (void)asserted; }
HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *bus)
{ bus->ErrorCode = 0U; return HAL_OK; }
HAL_StatusTypeDef HAL_I2C_DeInit(I2C_HandleTypeDef *bus)
{ (void)bus; deinit_count++; return HAL_OK; }
HAL_StatusTypeDef HAL_I2C_IsDeviceReady(I2C_HandleTypeDef *bus, uint16_t addr,
                                     uint32_t trials, uint32_t timeout)
{
    assert(bus == &hi2c1 && addr == 0x90U && trials == 1U && timeout == 10U);
    return HAL_OK;
}
static HAL_StatusTypeDef injected(I2C_HandleTypeDef *bus)
{
    bus->ErrorCode = fail_status == HAL_ERROR ? 0x200U : 0x20U;
    bus->Instance->SR1 = fail_status == HAL_ERROR ? 0x10U : 0U;
    bus->Instance->SR2 = fail_status == HAL_BUSY ? 2U : 0U;
    bus->Instance->CR1 = 0x101U;
    failures++;
    return fail_status;
}
HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *bus, uint16_t addr,
                                        uint8_t *data, uint16_t length, uint32_t timeout)
{
    unsigned stage;
    assert(bus == &hi2c1 && addr == 0x90U && timeout == 10U);
    assert(length == 1U || length == 3U);
    if (length == 3U)
    {
        /* Actual AIN0, +/-4.096 V, single-shot, 128 SPS, comparator disabled. */
        assert(data[0] == 1U && data[1] == 0xC3U && data[2] == 0x83U);
        stage = 1U;
    }
    else
    {
        assert(data[0] <= 1U);
        stage = data[0] == 1U ? 2U : 4U;
    }
    if (fail_at == stage) return injected(bus);
    selected_reg = data[0];
    if (length == 3U) { conversion_started = ticks; conversions++; }
    return HAL_OK;
}
HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *bus, uint16_t addr,
                                       uint8_t *data, uint16_t length, uint32_t timeout)
{
    uint16_t value;
    assert(bus == &hi2c1 && addr == 0x90U && length == 2U && timeout == 10U);
    if (fail_at == (selected_reg == 1U ? 3U : 5U)) return injected(bus);
    value = selected_reg == 1U ?
        (((ticks - conversion_started) >= 8U && !never_ready) ? 0xC383U : 0x4383U) :
        (uint16_t)raw_code;
    data[0] = (uint8_t)(value >> 8);
    data[1] = (uint8_t)value;
    return HAL_OK;
}
float BP_Cal_GetPressure_mmHg(float voltage) { return 82.326f * voltage - 19.887f; }
uint8_t BP_Cal_IsValid(void) { return calibrated; }
BP_State_t BP_Control_GetState(void) { return s_state; }
static uint32_t __get_PRIMASK(void) { return 0U; }
static void __disable_irq(void) { }
static void __enable_irq(void) { }
static void BP_Algorithm_CancelCalculate(void) { }
static void BP_Algorithm_RecordValveClose(uint32_t tick) { (void)tick; }
static unsigned HAL_GPIO_ReadPin(unsigned port, unsigned pin)
{ (void)pin; return pins[port]; }
void host_actuator(uint8_t pin, uint8_t level)
{
    if (pin == 1U && level == 1U) assert(pins[0] && pins[8]);
    pins[pin] = level;
    writes++;
}
static void assert_vented(void)
{
    assert(pins[0] && pins[1] && pins[8]);
    assert(!s_deflate_hold_until_ms && !s_deflate_pwm_enabled);
    assert(!s_deflate_pulse_remaining_ms && !s_calculation_pending);
    assert(!s_manual_pump_active && !s_hold_open_active);
}
static void Debug_UART_Write(const char *text)
{
    if (expect_vent) assert_vented();
    assert(strlen(output) + strlen(text) < sizeof(output));
    strcat(output, text);
}
static void Debug_PrintADS1115Diagnostics(void)
{ if (expect_vent) assert_vented(); }
#include "read_path_under_test.h"

static void reset_case(void)
{
    fail_at = never_ready = expect_vent = 0U;
    assert(ADS1115_Init(&hi2c1) == HAL_OK);
    ticks = 1000U;
    s_state = BP_STATE_IDLE;
    s_fault = BP_FAULT_NONE;
    s_manual_pump_active = s_hold_open_active = s_deflate_pwm_enabled = 0U;
    s_deflate_test_active = s_calculation_pending = 0U;
    s_deflate_hold_until_ms = s_deflate_pulse_remaining_ms = 0U;
    s_read_test.active = 0U;
    s_last_pressure_sample_valid = s_ads1115_ready = calibrated = 1U;
    s_last_pressure_sample_ms = ticks;
    memset(&s_last_pressure_sample, 0, sizeof(s_last_pressure_sample));
    pins[0] = pins[8] = 1U; pins[1] = 0U;
    raw_code = 1400;
    conversions = deinit_count = writes = failures = 0U;
    output[0] = '\0';
}

int main(void)
{
    static const int16_t codes[] = {-32768, -1, 0, 1400, 3513, 8430, 18900, 32767};
    ADS1115_Sample_t sample, before;
    /* Verify raw sign, big-endian assembly, exact scale and unchanged calibration. */
    reset_case();
    for (unsigned i = 0; i < sizeof(codes) / sizeof(codes[0]); i++)
    {
        float expected;
        uint32_t started = ticks;
        raw_code = codes[i];
        assert(ADS1115_ReadSample(&sample) == HAL_OK);
        assert(sample.raw == raw_code && ticks - started == 8U);
        assert(sample.ads_voltage_v == (float)raw_code * 0.000125f);
        expected = 82.326f * (sample.ads_voltage_v * ADS1115_DIVIDER_SCALE) - 19.887f;
        if (expected < 0.0f) expected = 0.0f;
        assert(fabsf(sample.pressure_mmhg - expected) < 0.0001f);
    }
    /* Software 0 -> 100 mmHg ramp through actual manual target-stop and hold. */
    reset_case();
    s_manual_pump_active = 1U;
    s_manual_pump_start_ms = ticks;
    s_inflate_target_mmhg = 100.0f;
    pins[0] = pins[8] = 0U;
    for (raw_code = 1400; raw_code <= 8500; raw_code += 100)
    {
        ticks += 25U;
        ManualPump_TimeoutTask();
    }
    assert(g_last_pressure_mmhg >= 100.0f && !s_manual_pump_active);
    assert(s_deflate_hold_until_ms && pins[0] && pins[8] && !pins[1]);
    for (unsigned i = 0; i < 40U; i++)
    {
        ticks += 25U;
        ManualPump_TimeoutTask();
        assert(s_fault == BP_FAULT_NONE && s_deflate_hold_until_ms);
    }
    assert(!deinit_count && !failures);
    /* Every real driver stage can fail at the first post-stop read. Preserve
       the destination and first error; vent before any log or bus recovery. */
    for (unsigned stage = 1U; stage <= 5U; stage++)
    for (unsigned status = HAL_ERROR; status <= HAL_TIMEOUT; status++)
    {
        uint32_t errors;
        reset_case();
        memset(&sample, 0x5A, sizeof(sample)); before = sample;
        fail_at = stage; fail_status = (HAL_StatusTypeDef)status;
        errors = ADS1115_GetDiagnostics()->error_count;
        assert(ADS1115_ReadSample(&sample) == fail_status);
        assert(memcmp(&sample, &before, sizeof(sample)) == 0);
        assert(ADS1115_GetDiagnostics()->error_count == errors + 1U && !deinit_count);
        reset_case();
        fail_at = stage; fail_status = (HAL_StatusTypeDef)status;
        s_deflate_hold_until_ms = ticks + 1000U;
        s_deflate_pwm_enabled = s_calculation_pending = 1U;
        s_deflate_pulse_remaining_ms = 2U;
        s_manual_pressure_last_ms = ticks - 25U;
        expect_vent = 1U;
        ManualPump_TimeoutTask();
        assert_vented();
        assert(s_fault == BP_FAULT_SENSOR_READ && failures == 1U && !deinit_count);
    }
    reset_case(); never_ready = 1U;
    assert(ADS1115_ReadSample(&sample) == HAL_TIMEOUT);
    assert(ADS1115_GetDiagnostics()->stage == ADS1115_STAGE_CONVERSION_WAIT);
    assert(!deinit_count);
    /* Real static diagnostic: 400 conversions with stream-independent cadence. */
    reset_case();
    ReadTest_Start();
    assert(s_read_test.active);
    uint32_t start = ticks;
    for (unsigned i = 0; i <= 400U; i++)
    {
        ticks = start + i * 25U;
        ReadTest_Task();
    }
    assert(!s_read_test.active && s_read_test.samples == 400U);
    assert(strstr(output, "PASS_READ_ONLY") && conversions == 400U);
    assert(!writes && !deinit_count && !failures);
    /* Wrap-safe timing, slow-loop failure, first error, bad pins/pressure,
       stale/calibration/active preflights and explicit cancellation. */
    reset_case(); ticks = UINT32_MAX - 100U; s_last_pressure_sample_ms = ticks;
    ReadTest_Start(); start = ticks;
    for (unsigned i = 0; i <= 400U; i++) { ticks = start + i * 25U; ReadTest_Task(); }
    assert(strstr(output, "PASS_READ_ONLY") && !writes);
    reset_case(); ReadTest_Start(); ticks += 10000U; ReadTest_Task();
    assert(strstr(output, "FAIL_CADENCE") && !writes);
    reset_case(); ReadTest_Start(); fail_at = 1U; fail_status = HAL_ERROR;
    ReadTest_Task();
    assert(strstr(output, "FAIL_ADS") && !s_read_test.active);
    assert(!s_last_pressure_sample_valid && !writes && !deinit_count);
    reset_case(); ReadTest_Start(); pins[0] = 0U; ReadTest_Task();
    assert(strstr(output, "FAIL_PINS") && !writes && !conversions);
    reset_case(); ReadTest_Start(); raw_code = 8500; ReadTest_Task();
    assert(strstr(output, "FAIL_PRESSURE") && !writes);
    for (unsigned gate = 0; gate < 8U; gate++)
    {
        reset_case();
        if (gate == 0U) pins[8] = 0U;
        if (gate == 1U) s_last_pressure_sample_ms -= 251U;
        if (gate == 2U) calibrated = 0U;
        if (gate == 3U) s_manual_pump_active = 1U;
        if (gate == 4U) s_calculation_pending = 1U;
        if (gate == 5U) s_last_pressure_sample.pressure_mmhg = 2.0f;
        if (gate == 6U) s_last_pressure_sample_valid = 0U;
        if (gate == 7U) s_last_pressure_sample.pressure_mmhg = NAN;
        ReadTest_Start();
        assert(strstr(output, "REJECTED") && !writes && !conversions);
    }
    reset_case(); ReadTest_Start(); DeflateControl_Cancel(); ReadTest_Task();
    assert(!s_read_test.active && !strstr(output, "PASS_READ_ONLY") && !writes);
    puts("PASS production ADS bytes/latency/scaling, 100mmHg ramp/hold, 15 fault cases, static readtest gates");
    return 0;
}
