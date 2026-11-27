/* Production algorithm plus extracted main.c pulse functions. No device I/O. */
#include "bp_algorithm.h"
#include "bp_capture_export.h"
#include <assert.h>
#include <stdio.h>

static uint32_t ticks, irq_mask;
static volatile uint32_t s_deflate_pulse_remaining_ms;
static unsigned close_commands, open_commands;
static uint8_t valve_open;
uint32_t HAL_GetTick(void) { return ticks; }
static uint32_t __get_PRIMASK(void) { return irq_mask; }
static void __disable_irq(void) { irq_mask = 1U; }
static void __enable_irq(void) { irq_mask = 0U; }
void host_actuator(uint8_t pin, uint8_t level)
{
    assert(pin == 1U);
    valve_open = level;
    if (level) open_commands++; else close_commands++;
}
#include "valve_pulse_under_test.h"

static void reset(void)
{
    DeflatePulse_Cancel();
    BP_Algorithm_Reset();
    BP_Algorithm_SetCaptureContext(2U, 1U, 82.326f, -19.887f);
    assert(!BP_Algorithm_GetValveTiming()->pending);
    assert(!BP_Algorithm_GetValveTiming()->count);
    assert(!BP_Algorithm_GetValveTiming()->errors);
}

int main(void)
{
    uint32_t opened, closed;
    reset();
    ticks = UINT32_MAX - 2U;
    assert(BP_Algorithm_AddSample(100.0f, 1.0f));
    DeflatePulse_Start(5U);
    assert(valve_open && BP_Algorithm_GetValveTiming()->pending);
    assert(!BP_CaptureExport_Begin());
    for (unsigned i = 0; i < 5U; i++) { ticks++; HAL_SYSTICK_Callback(); }
    assert(!valve_open && !BP_Algorithm_GetValveTiming()->pending);
    assert(BP_Algorithm_GetValvePulse(0U, &opened, &closed));
    assert(opened == UINT32_MAX - 2U && closed == 2U);
    assert(BP_CaptureExport_Begin());
    BP_CaptureExport_Cancel();
    ticks = opened + 201U;
    DeflatePulse_Start(10U);
    ticks += 2U;
    irq_mask = 1U;
    DeflatePulse_Cancel();
    assert(irq_mask == 1U); /* preserve caller's mask */
    irq_mask = 0U;
    assert(BP_Algorithm_GetValvePulse(1U, &opened, &closed));
    assert(closed - opened == 2U); /* actual cancel, not planned 10 */
    assert(!s_deflate_pulse_remaining_ms && !valve_open);
    unsigned before = close_commands;
    VALVE2_OPEN(); /* caller's final emergency vent */
    for (unsigned i = 0; i < 20U; i++) { ticks++; HAL_SYSTICK_Callback(); }
    assert(valve_open && close_commands == before); /* no stale reseal */
    VALVE2_CLOSE();
    DeflatePulse_Cancel();
    assert(!BP_Algorithm_GetValveTiming()->errors); /* idempotent */
    reset();
    ticks = 100U;
    for (unsigned i = 0; i < BP_VALVE_PULSE_TRACE_MAX; i++)
    {
        BP_Algorithm_RecordValvePulse(ticks, 1U);
        BP_Algorithm_RecordValveClose(ticks); /* same-tick early close is exact */
        ticks += 200U;
    }
    assert(BP_Algorithm_GetValveTiming()->count == BP_VALVE_PULSE_TRACE_MAX);
    assert(!BP_Algorithm_GetValveTiming()->errors);
    BP_Algorithm_RecordValvePulse(ticks, 1U);
    BP_Algorithm_RecordValveClose(ticks + 1U);
    assert(BP_Algorithm_GetValveTiming()->errors == 1U);
    assert(BP_Algorithm_GetValveTiming()->count == BP_VALVE_PULSE_TRACE_MAX);
    assert(!BP_Algorithm_GetValvePulse(BP_VALVE_PULSE_TRACE_MAX, &opened, &closed));
    reset();
    BP_Algorithm_RecordValvePulse(100U, 1U);
    BP_Algorithm_RecordValveClose(101U);
    BP_Algorithm_RecordValvePulse(356U, 1U);
    BP_Algorithm_RecordValveClose(357U);
    assert(BP_Algorithm_GetValveTiming()->errors == 2U);
    assert(BP_Algorithm_GetValveTiming()->count == 1U);
    reset();
    BP_Algorithm_RecordValvePulse(100U, 1U);
    BP_Algorithm_RecordValveClose(356U);
    assert(BP_Algorithm_GetValveTiming()->errors == 4U);
    assert(!BP_Algorithm_GetValveTiming()->count);
    reset();
    BP_Algorithm_RecordValveClose(100U);
    assert(BP_Algorithm_GetValveTiming()->errors == 8U);
    reset();
    BP_Algorithm_RecordValvePulse(100U, 1U);
    BP_Algorithm_RecordValvePulse(101U, 1U);
    BP_Algorithm_RecordValveClose(102U);
    assert(BP_Algorithm_GetValveTiming()->errors == 8U);
    reset();
    assert(open_commands > 0U);
    puts("PASS real valve command timing, cancel, wrap and explicit failures");
    return 0;
}
