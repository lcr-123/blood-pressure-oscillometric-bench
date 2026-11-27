/* Host-only executable: production driver/control + white-box algorithm tests.
 * Never include this file or test/host headers in the Keil firmware target. */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stddef.h>
#include "ads1115.h"
#include "bp_control.h"
#include "bp_algorithm.c"

static uint8_t s_calculation_pending;
static BP_Result_t g_bp_result;
static char calculation_log[4096];
static void Debug_UART_Write(const char *message)
{
    assert(strlen(calculation_log) + strlen(message) < sizeof(calculation_log));
    strcat(calculation_log, message);
}
#include "main_calculation_under_test.h"

I2C_TypeDef host_i2c1 = {0x0400U, 0x0002U, 0x0401U};
GPIO_TypeDef host_gpiob = {0x01C0U};
static I2C_HandleTypeDef bus = {I2C1, 0x20U, 0x22U};
static uint32_t ticks, tx_count, rx_count, deinit_count, init_count, reset_count;
static uint32_t fail_tx, fail_rx;
static uint32_t tick_increment;
static uint8_t selected_reg, never_ready, fail_probe, fail_recovery;
static uint8_t pb8, pc1, pc8;
static uint16_t conversion_raw = 10000U;
static HAL_StatusTypeDef injected_status = HAL_TIMEOUT;

uint32_t HAL_GetTick(void) { uint32_t now = ticks; ticks += tick_increment; return now; }
void HAL_Delay(uint32_t delay) { ticks += delay; }
uint32_t HAL_I2C_GetError(I2C_HandleTypeDef *handle) { return handle->ErrorCode; }
uint32_t HAL_I2C_GetState(I2C_HandleTypeDef *handle) { return handle->State; }
HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *handle, uint16_t addr,
                                        uint8_t *data, uint16_t length, uint32_t timeout)
{
    (void)handle;
    assert(addr == ADS1115_I2C_ADDR && timeout == ADS1115_I2C_TIMEOUT_MS);
    assert(length == 1U || length == 3U);
    tx_count++;
    if (tx_count == fail_tx) return injected_status;
    selected_reg = data[0];
    return HAL_OK;
}
HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *handle, uint16_t addr,
                                       uint8_t *data, uint16_t length, uint32_t timeout)
{
    uint16_t value;
    (void)handle;
    assert(addr == ADS1115_I2C_ADDR && length == 2U && timeout == ADS1115_I2C_TIMEOUT_MS);
    rx_count++;
    if (rx_count == fail_rx) return injected_status;
    value = (selected_reg == ADS1115_REG_CONFIG) ?
            (never_ready ? 0x4383U : 0xC383U) : conversion_raw;
    data[0] = (uint8_t)(value >> 8);
    data[1] = (uint8_t)value;
    return HAL_OK;
}
HAL_StatusTypeDef HAL_I2C_IsDeviceReady(I2C_HandleTypeDef *handle, uint16_t addr,
                                      uint32_t trials, uint32_t timeout)
{
    (void)handle;
    assert(addr == ADS1115_I2C_ADDR && trials == 1U && timeout == ADS1115_I2C_TIMEOUT_MS);
    return fail_probe ? injected_status : HAL_OK;
}
HAL_StatusTypeDef HAL_I2C_DeInit(I2C_HandleTypeDef *handle)
{
    (void)handle; deinit_count++; return HAL_OK;
}
HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *handle)
{
    init_count++;
    if (fail_recovery) return HAL_BUSY;
    handle->State = 0x20U;
    handle->ErrorCode = 0U;
    return HAL_OK;
}
void host_reset_bus(uint8_t asserted) { (void)asserted; reset_count++; }
void host_actuator(uint8_t pin, uint8_t level)
{
    if (pin == 0U) pb8 = level;
    else if (pin == 1U) pc1 = level;
    else if (pin == 8U) pc8 = level;
    else assert(0);
}
float BP_Cal_GetPressure_mmHg(float voltage) { return 82.326f * voltage - 19.887f; }
uint8_t BP_Cal_IsValid(void) { return 1U; }
float BP_Cal_GetSlope(void) { return 82.326f; }
float BP_Cal_GetIntercept(void) { return -19.887f; }

static void check_vent(BP_Fault_t fault)
{
    assert(BP_Control_GetFault() == fault);
    assert(BP_Control_GetState() == BP_STATE_EMERGENCY);
    assert(pc8 == 1U && pb8 == 1U && pc1 == 1U);
}

static void test_capacity(void)
{
    BP_Result_t result = {120U, 80U, 80U, 1U};
    BP_Sample_t captured;
    float envelope, smooth;
    BP_Algorithm_Reset();
    ticks = UINT32_MAX - 50U;
    for (uint16_t i = 0; i < BP_ALGO_MAX_SAMPLES; i++)
    {
        assert(BP_Algorithm_AddSample(100.0f, 1.0f) == 1U);
        ticks += BP_SAMPLE_INTERVAL_MS;
    }
    assert(g_bp_debug.sample_count == BP_ALGO_MAX_SAMPLES);
    assert(g_bp_debug.duration_ms == (BP_ALGO_MAX_SAMPLES - 1U) * BP_SAMPLE_INTERVAL_MS);
    assert(BP_Algorithm_GetCapturePoint(BP_ALGO_MAX_SAMPLES - 1U,
                                        &captured, &envelope, &smooth) == 1U);
    assert(captured.timestamp_ms == ticks - BP_SAMPLE_INTERVAL_MS);
    assert(captured.cuff_pressure == 100.0f && captured.oscillation == 1.0f);
    ticks += BP_SAMPLE_INTERVAL_MS;
    assert(BP_Algorithm_AddSample(1.0f, 2.0f) == 0U);
    assert(BP_Algorithm_AddSample(1.0f, 2.0f) == 0U);
    assert(g_bp_debug.dropped_samples == 2U);
    assert(s_samples[BP_ALGO_MAX_SAMPLES - 1U].cuff_pressure == 100.0f);
    assert(BP_Algorithm_Calculate(&result) == 0U && result.valid == 0U);
    assert(BP_Algorithm_Calculate(NULL) == 0U);
    BP_Algorithm_Reset();
    assert(g_bp_debug.sample_count == 0U && g_bp_debug.dropped_samples == 0U);
    assert(g_bp_debug.duration_ms == 0U && g_bp_debug.map_pressure_mmhg == 0.0f);
    result.valid = 1U;
    assert(BP_Algorithm_Calculate(&result) == 0U && result.valid == 0U);
    for (uint16_t i = 0; i < BP_ALGO_MAX_SAMPLES; i++)
    {
        ticks += BP_SAMPLE_INTERVAL_MS;
        assert(BP_Algorithm_AddSample(100.0f, 1.0f) == 1U);
    }
    assert(BP_Algorithm_Calculate(&result) == 0U && result.valid == 0U);
    assert(g_bp_debug.sample_count == BP_ALGO_MAX_SAMPLES);

    BP_Algorithm_Reset();
    ticks = UINT32_MAX - 10U;
    assert(BP_Algorithm_AddSample(90.0f, 1.25f) == 1U);
    assert(BP_Algorithm_GetCapturePoint(0U, &captured, &envelope, &smooth) == 1U);
    assert(captured.timestamp_ms == UINT32_MAX - 10U);
    ticks += 25U;
    assert(BP_Algorithm_AddSample(89.0f, 1.5f) == 1U);
    assert(BP_Algorithm_GetCapturePoint(1U, &captured, &envelope, &smooth) == 1U);
    assert(captured.timestamp_ms == 14U && captured.oscillation == 1.5f);
    ticks += 255U;
    assert(BP_Algorithm_AddSample(88.0f, 1.75f) == 1U);
    assert(BP_Algorithm_GetCapturePoint(2U, &captured, &envelope, &smooth) == 1U);
    assert(captured.timestamp_ms == ticks && g_bp_debug.duration_ms == 280U);
    ticks += 256U;
    assert(BP_Algorithm_AddSample(87.0f, 2.0f) == 0U);
    assert(s_count == 3U && g_bp_debug.dropped_samples == 1U);
    BP_Algorithm_Reset();
    assert(BP_Algorithm_AddSample(90.0f, 1.0f) == 1U);
    assert(BP_Algorithm_AddSample(89.0f, 1.1f) == 0U);
    assert(s_count == 1U && g_bp_debug.dropped_samples == 1U);
}

static int compare_float(const void *left, const void *right)
{
    float a = *(const float *)left, b = *(const float *)right;
    return (a > b) - (a < b);
}

static void test_gate(void)
{
    static float reference[BP_ALGO_MAX_SAMPLES]; /* test memory, not firmware stack */
    uint32_t seed = 123456U;
    BP_Algorithm_Reset();
    assert(envelope_has_signal(80U, 15U) == 0U);
    for (uint16_t n = 1U; n <= BP_ALGO_MAX_SAMPLES; n++)
    {
        s_count = n;
        for (uint16_t i = 0; i < n; i++)
        {
            seed = seed * 1664525U + 1013904223U;
            reference[i] = (float)(seed % 101U) * 0.000001f;
            s_env_smooth[i] = reference[i];
            s_samples[i].cuff_pressure = 90.0f;
        }
        qsort(reference, n, sizeof(float), compare_float);
        uint16_t idx = (uint16_t)(n * 0.95f);
        assert(envelope_has_signal(0U, 0U) == (reference[idx] >= 0.0001f));
        /* Exactly at threshold and either side of the percentile boundary. */
        for (uint16_t i = 0U; i < n; i++) s_env_smooth[i] = (i < idx) ? 0.0f : 0.0001f;
        assert(envelope_has_signal(0U, 0U) == 1U);
        s_env_smooth[idx] = 0.0f;
        assert(envelope_has_signal(0U, 0U) == 0U);
    }
    s_count = 100U;
    for (uint16_t i = 0; i < s_count; i++) s_env_smooth[i] = 1.0f;
    s_samples[80].cuff_pressure = 11.0f;
    assert(envelope_has_signal(80U, 15U) == 0U);
    assert(envelope_has_signal(90U, 15U) == 0U);
}

static void test_ads_failure(unsigned scenario)
{
    ADS1115_Sample_t sample, sentinel;
    ADS1115_Diagnostics_t saved;
    ADS1115_ErrorStage_t expected_stage;
    memset(&sample, 0xA5, sizeof(sample));
    sentinel = sample;
    assert(ADS1115_Init(&bus) == HAL_OK);
    assert(deinit_count == 0U);
    if (scenario == 0U) { fail_tx = tx_count + 1U; expected_stage = ADS1115_STAGE_CONVERSION_START; }
    else if (scenario == 1U) { fail_tx = tx_count + 2U; expected_stage = ADS1115_STAGE_REGISTER_SELECT; }
    else if (scenario == 2U) { fail_rx = rx_count + 1U; expected_stage = ADS1115_STAGE_REGISTER_READ; }
    else if (scenario == 3U) { never_ready = 1U; expected_stage = ADS1115_STAGE_CONVERSION_WAIT; }
    else { fail_rx = rx_count + 2U; expected_stage = ADS1115_STAGE_REGISTER_READ; }
    if (scenario == 1U) injected_status = HAL_BUSY;
    assert(ADS1115_ReadSample(&sample) == injected_status);
    assert(memcmp(&sample, &sentinel, sizeof(sample)) == 0);
    assert(ADS1115_IsInitialized() == 0U);
    assert(deinit_count == 0U && reset_count == 0U);
    saved = *ADS1115_GetDiagnostics();
    assert(saved.stage == expected_stage && saved.status == injected_status);
    assert(saved.error_count == 1U && saved.hal_error == 0x20U && saved.hal_state == 0x22U);
    assert(saved.sr1 == 0x0400U && saved.sr2 == 0x0002U);
    assert(saved.cr1 == 0x0401U && saved.gpio_b_idr == 0x01C0U);
    if (scenario == 3U) assert(ticks == ADS1115_CONVERSION_TIMEOUT_MS);
    /* Offline reads cannot erase the first bus fault or change the sample. */
    assert(ADS1115_ReadSample(&sample) == HAL_ERROR);
    assert(ADS1115_ReadRaw(NULL) == HAL_ERROR);
    assert(ADS1115_StartSingleConversion(ADS1115_MUX_AIN0_GND) == HAL_ERROR);
    assert(memcmp(ADS1115_GetDiagnostics(), &saved, sizeof(saved)) == 0);
    assert(memcmp(&sample, &sentinel, sizeof(sample)) == 0);
    assert(deinit_count == 0U && reset_count == 0U);
    never_ready = 0U;
    host_i2c1.CR1 = 0U;
    host_gpiob.IDR = 0U;
    assert(ADS1115_Init(&bus) == HAL_OK);
    assert(deinit_count == 1U && init_count == 1U && reset_count == 2U);
    assert(ADS1115_GetDiagnostics()->stage == saved.stage);
    assert(ADS1115_GetDiagnostics()->hal_error == saved.hal_error);
    assert(ADS1115_GetDiagnostics()->cr1 == saved.cr1);
    assert(ADS1115_GetDiagnostics()->gpio_b_idr == saved.gpio_b_idr);
    assert(ADS1115_GetDiagnostics()->recovery_count == 1U);
    assert(ADS1115_ReadSample(&sample) == HAL_OK);
    assert(sample.raw == 10000 && sample.ads_voltage_v == 1.25f);
}

static void test_probe_recovery(void)
{
    fail_probe = 1U;
    assert(ADS1115_Init(&bus) == HAL_TIMEOUT);
    assert(ADS1115_GetDiagnostics()->stage == ADS1115_STAGE_PROBE);
    fail_probe = 0U; fail_recovery = 1U;
    assert(ADS1115_Init(&bus) == HAL_BUSY);
    assert(ADS1115_GetDiagnostics()->stage == ADS1115_STAGE_RECOVERY);
    assert(ADS1115_IsInitialized() == 0U);
    fail_recovery = 0U;
    assert(ADS1115_Init(&bus) == HAL_OK);
    assert(ADS1115_GetDiagnostics()->recovery_count == 2U);
}

static void test_control(unsigned scenario)
{
    BP_Control_Init();
    BP_Algorithm_Reset();
    assert(ADS1115_Init(&bus) == HAL_OK);
    if (scenario == 0U)
    {
        BP_Control_Start();
        fail_tx = tx_count + 1U;
        BP_Control_Task();
        check_vent(BP_FAULT_SENSOR_READ);
        assert(deinit_count == 0U);
        return;
    }
    if (scenario >= 2U)
    {
        BP_Control_Start();
        conversion_raw = 14000U; /* calibrated pressure above inflate target */
        BP_Control_Task();
        assert(BP_Control_GetState() == BP_STATE_DEFLATE);
        ticks += BP_SAMPLE_INTERVAL_MS;
        if (scenario == 3U)
        {
            fail_tx = tx_count + 1U;
            BP_Control_Task();
            check_vent(BP_FAULT_SENSOR_READ);
            assert(deinit_count == 0U);
            return;
        }
    }
    for (uint16_t i = g_bp_debug.sample_count; i < BP_ALGO_MAX_SAMPLES; i++)
    {
        ticks += BP_SAMPLE_INTERVAL_MS;
        assert(BP_Algorithm_AddSample(100.0f, 1.0f) == 1U);
    }
    ticks += BP_SAMPLE_INTERVAL_MS;
    if (scenario == 2U) BP_Control_Task();
    else BP_Control_PressureTick(100.0f);
    check_vent(BP_FAULT_SAMPLE_OVERFLOW);
    assert(g_bp_debug.dropped_samples == 1U);
    assert(strcmp(BP_Control_FaultName(BP_FAULT_SAMPLE_OVERFLOW), "SAMPLE_OVERFLOW") == 0);
}

static void test_gap_vent(void)
{
    BP_Control_Init();
    BP_Algorithm_Reset();
    assert(ADS1115_Init(&bus) == HAL_OK);
    BP_Control_Start();
    conversion_raw = 14000U;
    BP_Control_Task();
    assert(BP_Control_GetState() == BP_STATE_DEFLATE);
    ticks += BP_SAMPLE_INTERVAL_MS;
    BP_Control_Task();
    assert(g_bp_debug.sample_count == 1U);
    ticks += 256U;
    BP_Control_Task();
    check_vent(BP_FAULT_SAMPLE_OVERFLOW);
    assert(g_bp_debug.sample_count == 1U && g_bp_debug.dropped_samples == 1U);
}

/* Frozen pre-cooperative loops: do not call the new per-sample helpers here. */
static void reference_extract(float *envelope, float *smooth)
{
    for (uint16_t i = 0U; i < s_count; i++)
    {
        uint16_t lo = (i >= 32U) ? (i - 32U) : 0U;
        uint16_t hi = (i + 32U < s_count) ? (i + 32U) : (uint16_t)(s_count - 1U);
        uint16_t n = hi - lo + 1U;
        float mt = 0.0f, my = 0.0f;
        for (uint16_t j = lo; j <= hi; j++) { mt += (float)j; my += s_samples[j].oscillation; }
        mt /= (float)n; my /= (float)n;
        float cov = 0.0f, var = 0.0f;
        for (uint16_t j = lo; j <= hi; j++)
        {
            float dt = (float)j - mt;
            cov += dt * (s_samples[j].oscillation - my);
            var += dt * dt;
        }
        float a = (var > 1e-9f) ? (cov / var) : 0.0f;
        float b = my - a * mt;
        float fit = a * (float)i + b;
        envelope[i] = fabsf(s_samples[i].oscillation - fit);
    }
    for (uint16_t i = 0U; i < s_count; i++)
    {
        uint16_t start = (i >= 31U) ? (i - 31U) : 0U;
        float esum = 0.0f;
        uint16_t cnt = i - start + 1;
        for (uint16_t j = start; j <= i; j++) esum += envelope[j];
        smooth[i] = esum / (float)cnt;
    }
}

static float reference_env[BP_ALGO_MAX_SAMPLES];
static float reference_smooth[BP_ALGO_MAX_SAMPLES];
#include "legacy_result_3300.h"

static void fill_wave(uint16_t n, unsigned kind)
{
    BP_Algorithm_Reset();
    for (uint16_t i = 0; i < n; i++)
    {
        float p = 150.0f - 135.0f * (float)i / (float)(n - 1U);
        float v = 0.2f + p / 80.0f;
        if (kind == 0U) v = 1.0f;
        if (kind >= 2U)
        {
            float d = (p - 93.0f) / 24.0f;
            v += 0.02f * expf(-0.5f * d * d) * sinf((float)i * 0.19634954f);
        }
        if (kind == 4U && i < 256U) v = 1.0f; /* FFT flat; later pulses need fallback. */
        if (kind == 3U) v += (float)((i * 13U) % 17U) * 0.00001f;
        assert(BP_Algorithm_AddSample(p, v));
        ticks += 25U;
    }
}

static void test_cooperative_equivalence(void)
{
    const uint16_t sizes[] = {20U, 31U, 32U, 33U, 64U, 65U, 256U, 2521U, 2800U, 3300U, 4200U};
    unsigned valid_count = 0U, fallback_count = 0U;
    for (unsigned k = 0; k < 5U; k++)
    for (unsigned z = 0; z < sizeof(sizes) / sizeof(sizes[0]); z++)
    {
        uint16_t n = sizes[z];
        BP_Result_t expected = {0}, actual = {0};
        fill_wave(n, k);
        reference_extract(reference_env, reference_smooth);
        memcpy(s_env_smooth, reference_smooth, n * sizeof(float));
        uint8_t expected_ok = reference_calculate_result(&expected);
        BP_AlgoDebug_t expected_debug = g_bp_debug;
        valid_count += expected_ok;
        memset(s_env_smooth, 0, sizeof(s_env_smooth));
        assert(BP_Algorithm_BeginCalculate());
        BP_CalcStatus_t status;
        unsigned steps = 0U;
        do
        {
            CalcPhase_t phase = s_calc_phase;
            uint16_t before = s_calc_index;
            status = BP_Algorithm_CalculateStep(&actual);
            if (phase == CALC_PULSE_FALLBACK) fallback_count++;
            if (phase == CALC_EXTRACT || phase == CALC_SMOOTH || phase == CALC_PULSE_FALLBACK)
            {
                uint16_t processed = (s_calc_index == 0U) ? n - before : s_calc_index - before;
                assert(processed > 0U && processed <= BP_ALGO_CALC_BATCH_SAMPLES);
                if (status == BP_CALC_BUSY) assert(actual.valid == 0U);
            }
            assert(++steps <= 3U * n + 1U);
            ticks += 3U; /* main-loop work between steps */
        } while (status == BP_CALC_BUSY);
        assert(status == (expected_ok ? BP_CALC_DONE : BP_CALC_FAILED));
        assert(memcmp(&actual, &expected, sizeof(actual)) == 0);
        for (uint16_t i = 0U; i < n; i++)
        {
            BP_Sample_t sample;
            float envelope, smooth;
            assert(BP_Algorithm_GetCapturePoint(i, &sample, &envelope, &smooth));
            assert(memcmp(&envelope, &reference_env[i], sizeof(float)) == 0);
            assert(memcmp(&smooth, &reference_smooth[i], sizeof(float)) == 0);
            assert(memcmp(&sample.cuff_pressure, &s_samples[i].cuff_pressure, sizeof(float)) == 0);
            assert(memcmp(&sample.oscillation, &s_samples[i].oscillation, sizeof(float)) == 0);
            assert(sample.timestamp_ms == s_first_sample_tick_ms + 25U * i);
        }
        assert(memcmp(s_env_smooth, reference_smooth, n * sizeof(float)) == 0);
        assert(memcmp(&g_bp_debug, &expected_debug, offsetof(BP_AlgoDebug_t, calc_work_ms)) == 0);
        assert(g_bp_debug.calc_steps == steps && g_bp_debug.calc_work_ms == 0U);
        assert(g_bp_debug.calc_wall_ms == (steps - 1U) * 3U);
        assert(BP_Algorithm_CalculateStep(&actual) == BP_CALC_IDLE && actual.valid == 0U);
    }
    assert(valid_count > 0U && fallback_count > 0U); /* Includes successful feature/FFT paths, not only failures. */
}

static void test_cooperative_lifecycle(void)
{
    BP_Result_t result = {0};
    for (unsigned phase = CALC_EXTRACT; phase <= CALC_PULSE_FALLBACK; phase++)
    {
        fill_wave(2521U, phase == CALC_PULSE_FALLBACK ? 4U : 2U);
        assert(BP_Algorithm_BeginCalculate());
        while ((unsigned)s_calc_phase != phase)
            assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_BUSY);
        if (phase != CALC_FINISH)
        {
            tick_increment = 2U;
            assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_BUSY);
            assert(s_calc_index == 3U); /* All linear-work phases yield. */
            tick_increment = 0U;
        }
        uint16_t before = s_calc_index;
        assert(BP_Algorithm_BeginCalculate() == 0U && s_calc_index == before);
        BP_Algorithm_CancelCalculate();
        result.valid = 1U;
        assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_IDLE && !result.valid);
        assert(BP_Algorithm_BeginCalculate());
        assert(BP_Algorithm_CalculateStep(NULL) == BP_CALC_FAILED);
        assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_IDLE);
        assert(BP_Algorithm_BeginCalculate());
        assert(BP_Algorithm_AddSample(90.0f, 1.0f) == 0U);
        assert(s_count == 2521U && g_bp_debug.dropped_samples == 1U);
        assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_IDLE);
        assert(!BP_Algorithm_BeginCalculate());
    }
    fill_wave(65U, 2U);
    ticks = UINT32_MAX - 2U;
    tick_increment = 2U;
    assert(BP_Algorithm_BeginCalculate());
    assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_BUSY);
    assert(s_calc_index == 3U); /* Yield at 6ms, before reaching the 8-sample cap. */
    assert(g_bp_debug.calc_extract_ms == 8U && g_bp_debug.calc_max_step_ms == 8U);
    assert(g_bp_debug.calc_wall_ms == 10U && g_bp_debug.calc_steps == 1U);
    tick_increment = 0U;
    BP_Algorithm_Reset();
    assert(BP_Algorithm_CalculateStep(&result) == BP_CALC_IDLE);
}

static void test_control_calculation_cancel(void)
{
    BP_Result_t result;
    BP_Control_Init();
    assert(ADS1115_Init(&bus) == HAL_OK);
    BP_Control_Start();
    conversion_raw = 18000U;
    BP_Control_Task();
    assert(BP_Control_GetState() == BP_STATE_DEFLATE);
    fill_wave(256U, 2U);
    conversion_raw = 2000U;
    ticks += BP_SAMPLE_INTERVAL_MS;
    BP_Control_Task();
    assert(BP_Control_GetState() == BP_STATE_COMPLETE && s_calc_phase == CALC_EXTRACT);
    BP_Control_Task();
    assert(s_calc_index > 0U);
    BP_Control_Stop();
    check_vent(BP_FAULT_USER_STOP);
    result = BP_Control_GetResult();
    assert(!result.valid && s_calc_phase == CALC_IDLE);
    BP_Control_Task();
    result = BP_Control_GetResult();
    assert(!result.valid);
    fill_wave(256U, 2U);
    assert(BP_Algorithm_BeginCalculate());
    BP_Control_Reset();
    assert(s_calc_phase == CALC_IDLE);
    assert(BP_Algorithm_BeginCalculate());
    BP_Control_Init();
    assert(s_calc_phase == CALC_IDLE);
    BP_Control_Start();
    conversion_raw = 18000U;
    BP_Control_Task();
    assert(BP_Control_GetState() == BP_STATE_DEFLATE);
    fill_wave(2521U, 2U);
    conversion_raw = 2000U;
    ticks += BP_SAMPLE_INTERVAL_MS;
    BP_Control_Task();
    assert(BP_Control_GetState() == BP_STATE_COMPLETE && s_calc_phase == CALC_EXTRACT);
    unsigned guard = 0U;
    do
    {
        BP_Control_Task();
        result = BP_Control_GetResult();
        assert(++guard < 6000U);
    } while (s_calc_phase != CALC_IDLE);
    assert(result.valid);
    BP_Result_t saved = result;
    BP_Control_Task();
    result = BP_Control_GetResult();
    assert(memcmp(&saved, &result, sizeof(result)) == 0);
    BP_Control_Stop();
    result = BP_Control_GetResult();
    assert(!result.valid);
}

static void test_main_calculation(void)
{
    for (unsigned phase = CALC_EXTRACT; phase <= CALC_PULSE_FALLBACK; phase++)
    {
        fill_wave(2521U, phase == CALC_PULSE_FALLBACK ? 4U : 2U);
        s_calculation_pending = BP_Algorithm_BeginCalculate();
        while ((unsigned)s_calc_phase != phase) BP_CalculationTask();
        BP_CalculationCancel();
        BP_CalculationTask();
        assert(!s_calculation_pending && !g_bp_result.valid && !calculation_log[0]);
    }
    for (unsigned valid = 0; valid <= 1U; valid++)
    {
        fill_wave(2521U, valid ? 2U : 0U);
        s_calculation_pending = BP_Algorithm_BeginCalculate();
        unsigned guard = 0U;
        while (s_calculation_pending) { BP_CalculationTask(); assert(++guard < 6000U); }
        assert(g_bp_result.valid == valid);
        assert(strstr(calculation_log, valid ? "[BP] SBP=" : "[BP] calculation failed"));
        assert(strstr(calculation_log, "[Calc] work="));
        size_t length = strlen(calculation_log);
        BP_CalculationTask();
        assert(strlen(calculation_log) == length);
        calculation_log[0] = '\0';
    }
    fill_wave(2521U, 2U);
    s_calculation_pending = BP_Algorithm_BeginCalculate();
    BP_Algorithm_Reset();
    BP_CalculationTask();
    assert(!s_calculation_pending && !g_bp_result.valid && !calculation_log[0]);
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    unsigned scenario = (unsigned)strtoul(argv[1], NULL, 10);
    if (scenario == 0U) test_capacity();
    else if (scenario == 1U) test_gate();
    else if (scenario >= 2U && scenario <= 6U) test_ads_failure(scenario - 2U);
    else if (scenario == 7U) test_probe_recovery();
    else if (scenario == 12U) test_cooperative_equivalence();
    else if (scenario == 13U) test_cooperative_lifecycle();
    else if (scenario == 14U) test_control_calculation_cancel();
    else if (scenario == 15U) test_main_calculation();
    else if (scenario == 16U) test_gap_vent();
    else test_control(scenario - 8U);
    puts("PASS");
    return 0;
}
