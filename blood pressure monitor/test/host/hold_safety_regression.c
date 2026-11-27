/* Real main.c hold/sampling/cancellation and bp_control.c emergency functions.
 * Only the ADS device, clock, UART, algorithm and HAL boundary are simulated. */
#include "ads1115.h"
#include "bp_control.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define MANUAL_PRESSURE_SAMPLE_INTERVAL_MS BP_SAMPLE_INTERVAL_MS
#define MANUAL_PUMP_TIMEOUT_MS 60000U
#define DEFLATE_HOLD_MS 1000U
#define DEFLATE_PWM_BASE_ON_MS 1U
#define PRESSURE_STREAM_INTERVAL_MS 50U
#define ADS1115_OFFLINE_RETRY_MS 1000U
#define ZERO_PULSE_ACTIVE 2U
#define LOADED_PULSE_ACTIVE 3U
static uint8_t s_manual_pump_active, s_hold_open_active, s_deflate_pwm_enabled;
static uint8_t s_deflate_test_active, s_calculation_pending, s_ads1115_ready;
static uint8_t s_last_pressure_sample_valid, s_pressure_stream_enabled;
static struct { uint8_t active; } s_read_test;
static uint32_t s_manual_pressure_last_ms, s_ads1115_last_attempt_ms;
static uint32_t s_last_pressure_sample_ms, s_manual_pump_start_ms;
static uint32_t s_deflate_hold_until_ms, s_deflate_pulse_remaining_ms;
static uint32_t s_pressure_stream_last_ms, s_deflate_next_pulse_ms;
static uint32_t s_deflate_pwm_on_ms, s_deflate_last_time_ms, s_algo_sample_last_ms;
static float g_last_pressure_mmhg, s_inflate_target_mmhg, s_deflate_last_pressure;
static float s_deflate_speed_prev;
static ADS1115_Sample_t s_last_pressure_sample;
static BP_Result_t g_bp_result, s_result;
static BP_Fault_t s_fault;
static BP_State_t s_state;
static uint32_t s_fault_time_ms, ticks;
static HAL_StatusTypeDef read_status;
static float next_pressure;
static unsigned reads, inits, logs, records, writes, resets, cancels;
static uint8_t initialized, expect_vent_before_output, check_cancel_before_gpio;
static uint8_t pins[9];
static I2C_HandleTypeDef hi2c1;

uint32_t HAL_GetTick(void) { return ticks; }
static uint32_t __get_PRIMASK(void) { return 0U; }
static void __disable_irq(void) { }
static void __enable_irq(void) { }
static void BP_Algorithm_CancelCalculate(void) { cancels++; }
static void BP_Algorithm_RecordValveClose(uint32_t tick) { (void)tick; }
static void BP_Algorithm_Reset(void) { resets++; }
static void BP_Algorithm_SetCaptureContext(unsigned m, unsigned v, float s, float i)
{ (void)m; (void)v; (void)s; (void)i; }
static uint8_t BP_Cal_IsValid(void) { return 1U; }
static float BP_Cal_GetSlope(void) { return 82.326f; }
static float BP_Cal_GetIntercept(void) { return -19.887f; }
void host_actuator(uint8_t pin, uint8_t level)
{
    if (check_cancel_before_gpio)
    {
        assert(!s_deflate_hold_until_ms && !s_deflate_pwm_enabled);
        assert(!s_deflate_pulse_remaining_ms && !s_calculation_pending);
    }
    if (pin == 1U && level == 1U) assert(pins[8] && pins[0]);
    pins[pin] = level;
    writes++;
}
static void assert_vented(void)
{
    assert(pins[8] && pins[0] && pins[1]);
    assert(!s_deflate_hold_until_ms && !s_deflate_pwm_enabled);
    assert(!s_deflate_pulse_remaining_ms && !s_calculation_pending);
    assert(!s_manual_pump_active && !s_hold_open_active);
}
static void Debug_UART_Write(const char *text)
{
    if (expect_vent_before_output) assert_vented();
    if (strstr(text, "target reached") != NULL)
        assert(pins[8] && pins[0] && !s_manual_pump_active);
    logs++;
}
static void Debug_PrintADS1115Diagnostics(void)
{
    if (expect_vent_before_output) assert_vented();
}
static void Debug_PrintADS1115InitResult(uint8_t ready) { (void)ready; }
static void Debug_PrintPressureRecord(const ADS1115_Sample_t *sample)
{ assert(sample->pressure_mmhg == g_last_pressure_mmhg); records++; }
uint8_t ADS1115_IsInitialized(void) { return initialized; }
HAL_StatusTypeDef ADS1115_Init(I2C_HandleTypeDef *bus)
{
    (void)bus;
    if (expect_vent_before_output) assert_vented();
    inits++;
    initialized = 1U;
    return HAL_OK;
}
HAL_StatusTypeDef ADS1115_ReadSample(ADS1115_Sample_t *sample)
{
    reads++;
    if (read_status != HAL_OK) { initialized = 0U; return read_status; }
    memset(sample, 0, sizeof(*sample));
    sample->pressure_mmhg = next_pressure;
    return HAL_OK;
}
#include "hold_safety_under_test.h"

static void reset_hold(void)
{
    s_manual_pump_active = s_hold_open_active = s_deflate_pwm_enabled = 0U;
    s_deflate_test_active = s_calculation_pending = 0U;
    s_ads1115_ready = initialized = s_last_pressure_sample_valid = 1U;
    s_pressure_stream_enabled = 0U;
    s_deflate_pulse_remaining_ms = 0U;
    ticks = 1500U;
    s_manual_pressure_last_ms = ticks - BP_SAMPLE_INTERVAL_MS;
    s_ads1115_last_attempt_ms = s_last_pressure_sample_ms = ticks;
    s_pressure_stream_last_ms = ticks - PRESSURE_STREAM_INTERVAL_MS;
    s_deflate_hold_until_ms = 2000U;
    g_last_pressure_mmhg = next_pressure = 50.0f;
    s_last_pressure_sample.pressure_mmhg = 50.0f;
    s_inflate_target_mmhg = 50.0f;
    read_status = HAL_OK;
    s_fault = BP_FAULT_NONE;
    s_state = BP_STATE_IDLE;
    reads = inits = logs = records = writes = resets = cancels = 0U;
    expect_vent_before_output = check_cancel_before_gpio = 0U;
    pins[8] = pins[0] = 1U; pins[1] = 0U;
}

int main(void)
{
    /* Every HAL failure, stream on/off, before and exactly at the deadline. */
    for (unsigned status = HAL_ERROR; status <= HAL_TIMEOUT; status++)
    for (unsigned stream = 0; stream < 2; stream++)
    for (unsigned at_deadline = 0; at_deadline < 2; at_deadline++)
    {
        reset_hold();
        if (at_deadline) ticks = s_deflate_hold_until_ms;
        s_pressure_stream_enabled = (uint8_t)stream;
        read_status = (HAL_StatusTypeDef)status;
        s_deflate_pulse_remaining_ms = 2U;
        s_calculation_pending = 1U;
        expect_vent_before_output = check_cancel_before_gpio = 1U;
        ManualPump_TimeoutTask();
        assert_vented();
        assert(s_fault == BP_FAULT_SENSOR_READ && !s_last_pressure_sample_valid);
        PressureStream_Task();
        hold_transition();
        assert_vented();
        assert(reads == 1U && inits == 0U && resets == 0U);
    }
    /* Healthy hold samples with no stream; streaming uses only the cache.
       Pressure at target must never re-arm or extend the hold deadline. */
    for (unsigned stream = 0; stream < 2; stream++)
    {
        reset_hold();
        s_pressure_stream_enabled = (uint8_t)stream;
        for (ticks = 1500U; ticks <= 2000U; ticks += 25U)
        {
            ManualPump_TimeoutTask();
            PressureStream_Task();
            assert(s_deflate_hold_until_ms == 2000U);
            hold_transition();
            if (ticks < 2000U) assert(!s_deflate_pwm_enabled);
        }
        assert(reads == 21U && records == (stream ? 11U : 0U) && inits == 0U);
        assert(s_deflate_pwm_enabled && !s_deflate_hold_until_ms && resets == 1U);
    }
    /* Below cadence: no extra conversion. */
    reset_hold();
    s_manual_pressure_last_ms = ticks;
    ManualPump_TimeoutTask();
    assert(!reads && s_deflate_hold_until_ms == 2000U);

    /* Explicit pressure query failure and already-offline query both vent
       before output, and the latter must not reinitialize while hold owns it. */
    for (unsigned offline = 0; offline < 2; offline++)
    {
        reset_hold();
        initialized = (uint8_t)!offline;
        read_status = HAL_BUSY;
        expect_vent_before_output = check_cancel_before_gpio = 1U;
        assert(!Debug_PrintPressureSample());
        assert_vented();
        assert(s_fault == BP_FAULT_SENSOR_READ && !inits);
        hold_transition();
        assert(!s_deflate_pwm_enabled);
    }
    /* Explicit seal's cancellation releases automatic safety ownership:
       a subsequent idle query error records a fault with no actuator writes. */
    reset_hold();
    DeflateControl_Cancel();
    VALVE2_CLOSE();
    writes = 0U;
    read_status = HAL_TIMEOUT;
    assert(!Debug_PrintPressureSample());
    assert(!writes && !pins[1] && s_fault == BP_FAULT_SENSOR_READ);
    ManualPump_TimeoutTask();
    hold_transition();
    assert(!writes && !s_deflate_pwm_enabled);

    reset_hold();
    next_pressure = (float)BP_MAX_PRESSURE_MMHG;
    expect_vent_before_output = check_cancel_before_gpio = 1U;
    ManualPump_TimeoutTask();
    assert_vented();
    assert(s_fault == BP_FAULT_OVERPRESSURE);

    /* Existing target transition still stops the pump and arms exactly once. */
    reset_hold();
    s_deflate_hold_until_ms = 0U;
    s_manual_pump_active = 1U;
    pins[8] = pins[0] = 0U;
    ManualPump_TimeoutTask();
    assert(!s_manual_pump_active && pins[8] && pins[0] && !pins[1]);
    assert(s_deflate_hold_until_ms == ticks + DEFLATE_HOLD_MS);
    puts("PASS actual hold safety: failures, stream, deadline, query, seal, overpressure, target");
    return 0;
}
