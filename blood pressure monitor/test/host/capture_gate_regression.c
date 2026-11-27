/* Test the real main.c safe-export predicates against all actuator states. */
#include "ads1115.h"
#include "bp_control.h"
#include <assert.h>
#include <stdio.h>
#include <math.h>

#define GPIOC 0
#define GPIOB 1
#define GPIO_PIN_1 2U
#define GPIO_PIN_8 256U
#define GPIO_PIN_RESET 0U
#define GPIO_PIN_SET 1U
#define VALVE1_CTRL_Port GPIOB
#define VALVE1_CTRL_Pin GPIO_PIN_8
#define VALVE2_CTRL_Port GPIOC
#define VALVE2_CTRL_Pin GPIO_PIN_1
#define PUMP_RELAY_Port GPIOC
#define PUMP_RELAY_Pin GPIO_PIN_8
#define LOADED_PULSE_START_MIN_MMHG 40.0f
#define LOADED_PULSE_START_MAX_MMHG 80.0f
static uint8_t s_manual_pump_active, s_hold_open_active, s_deflate_pwm_enabled;
static uint8_t s_calculation_pending, s_last_pressure_sample_valid, s_ads1115_ready;
static uint8_t s_pressure_stream_enabled, calibration_valid;
static struct { uint8_t active; } s_read_test;
static uint32_t s_deflate_hold_until_ms, s_last_pressure_sample_ms, ticks;
static ADS1115_Sample_t s_last_pressure_sample;
static BP_State_t state;
static uint16_t gpio_levels[2];
static uint8_t s_peak_profile_enabled, export_active;
static uint8_t BP_CaptureExport_IsActive(void) { return export_active; }
uint32_t HAL_GetTick(void) { return ticks; }
BP_State_t BP_Control_GetState(void) { return state; }
uint8_t BP_Cal_IsValid(void) { return calibration_valid; }
BP_Fault_t BP_Control_GetFault(void) { return BP_FAULT_NONE; }
static uint8_t HAL_GPIO_ReadPin(int port, uint16_t mask)
{
    assert(port == GPIOB || port == GPIOC);
    return (gpio_levels[port] & mask) ? GPIO_PIN_SET : GPIO_PIN_RESET;
}
#include "capture_gate_under_test.h"

int main(void)
{
    ticks = 20U;
    s_last_pressure_sample_ms = UINT32_MAX - 29U; /* wrap:50ms old */
    s_pressure_stream_enabled = s_last_pressure_sample_valid = s_ads1115_ready = calibration_valid = 1U;
    gpio_levels[GPIOB] = gpio_levels[GPIOC] = GPIO_PIN_8;
    state = BP_STATE_IDLE;
    assert(CaptureExport_IsSafe());
    assert(!s_peak_profile_enabled);
    assert(DeflateProfile_Set(1U) && s_peak_profile_enabled);
    assert(DeflateProfile_Set(0U) && !s_peak_profile_enabled);
    assert(!DeflateProfile_Set(2U) && !s_peak_profile_enabled);
    export_active=1U;
    assert(!DeflateProfile_Set(1U) && !s_peak_profile_enabled);
    export_active=0U;
    s_read_test.active = 1U;
    assert(!CaptureExport_IsSafe() && CaptureAcquisition_IsActive());
    s_read_test.active = 0U;
    uint8_t *flags[] = {&s_manual_pump_active, &s_hold_open_active, &s_deflate_pwm_enabled, &s_calculation_pending};
    for (unsigned i = 0; i < sizeof(flags) / sizeof(flags[0]); i++)
    {
        *flags[i] = 1U;
        assert(!CaptureExport_IsSafe());
        assert(!DeflateProfile_Set(1U) && !s_peak_profile_enabled);
        if (i < 3U) assert(CaptureAcquisition_IsActive());
        *flags[i] = 0U;
    }
    s_deflate_hold_until_ms = 1U;
    assert(!CaptureExport_IsSafe() && CaptureAcquisition_IsActive());
    s_deflate_hold_until_ms = 0U;
    for (unsigned i = BP_STATE_INFLATE; i <= BP_STATE_DEFLATE; i++)
    {
        state = (BP_State_t)i;
        assert(!CaptureExport_IsSafe() && CaptureAcquisition_IsActive());
    }
    state = BP_STATE_COMPLETE;
    assert(CaptureExport_IsSafe());
    for (unsigned bits = 0; bits < 8; bits++)
    {
        gpio_levels[GPIOB] = (bits & 1U) ? GPIO_PIN_8 : 0U;
        gpio_levels[GPIOC] = (uint16_t)((bits & 2U) | ((bits & 4U) ? GPIO_PIN_8 : 0U));
        assert(CaptureExport_IsSafe() == (bits == 5U));
        assert(DeflateProfile_Set(1U) == (bits == 5U));
        assert(s_peak_profile_enabled == (bits == 5U));
        s_peak_profile_enabled = 0U;
        state = BP_STATE_IDLE;
        s_last_pressure_sample.pressure_mmhg = 60.0f;
        assert(LoadedPulse_IsSafe() == (bits == 5U));
        s_last_pressure_sample.pressure_mmhg = 0.0f;
        state = BP_STATE_COMPLETE;
    }
    gpio_levels[GPIOB] = gpio_levels[GPIOC] = GPIO_PIN_8;
    uint8_t *required[] = {&s_last_pressure_sample_valid, &s_ads1115_ready, &calibration_valid, &s_pressure_stream_enabled};
    for (unsigned i = 0; i < sizeof(required) / sizeof(required[0]); i++)
    {
        *required[i] = 0U;
        assert(!CaptureExport_IsSafe() && !DeflateProfile_Set(1U));
        *required[i] = 1U;
    }
    s_last_pressure_sample_ms = ticks - 251U;
    assert(!CaptureExport_IsSafe());
    assert(!DeflateProfile_Set(1U));
    s_last_pressure_sample_ms = ticks;
    float invalid[] = {5.01f, -5.01f, NAN, INFINITY};
    for (unsigned i = 0; i < 4; i++)
    {
        s_last_pressure_sample.pressure_mmhg = invalid[i];
        assert(!CaptureExport_IsSafe());
        assert(!DeflateProfile_Set(1U));
    }
    s_last_pressure_sample.pressure_mmhg=1.01f;
    assert(!DeflateProfile_Set(1U));
    s_last_pressure_sample.pressure_mmhg=-1.01f;
    assert(!DeflateProfile_Set(1U));
    s_last_pressure_sample.pressure_mmhg=1.0f;
    assert(DeflateProfile_Set(1U) && s_peak_profile_enabled);
    s_last_pressure_sample.pressure_mmhg=-1.0f;
    assert(DeflateProfile_Set(0U) && !s_peak_profile_enabled);
    puts("PASS actual main export gate");
    return 0;
}
