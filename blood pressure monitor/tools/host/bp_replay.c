/* Host-only runner. Compile the production algorithm/exporter; no device I/O. */
#include "bp_capture_export.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <fcntl.h>
#include <io.h>

static uint32_t ticks;
static unsigned lines, ends;
uint32_t HAL_GetTick(void) { return ticks; }
static uint32_t bits(float value) { uint32_t b; memcpy(&b, &value, 4); return b; }
static float value(uint32_t b) { float v; memcpy(&v, &b, 4); return v; }
static uint8_t emit(const char *line) { return fputs(line, stdout) >= 0; }
static uint8_t inspect(const char *line)
{
    assert(strlen(line) < 512U);
    lines++;
    if (strstr(line, "\"type\":\"end\"")) ends++;
    return 1U;
}
static uint8_t fail(const char *line) { (void)line; return 0U; }

static void fixture(unsigned n, unsigned pattern)
{
    uint32_t tick = UINT32_MAX - 400U;
    BP_Algorithm_Reset();
    BP_Algorithm_SetCaptureContext(2U, 1U, 82.326f, -19.887f);
    for (unsigned i = 0; i < n; i++)
    {
        float p = 150.0f - 135.0f * (float)i / (float)(n - 1U);
        if ((pattern == 5U && (i == 17U || i == 33U || i == 49U)) ||
            (pattern == 6U && i >= 17U && i <= 121U && ((i - 17U) % 8U) == 0U))
            p -= 6.0f;
        float amp = 0.04f * expf(-powf((p - 95.0f) / 25.0f, 2.0f));
        float voltage = (p + 19.887f) / 82.326f;
        if (pattern == 0U) voltage += amp * sinf((float)i * 0.20943951f);
        if (i != 0U) tick += (pattern == 4U && i == 10U) ? 255U :
                             (pattern == 4U && i == 11U) ? 1U : 25U;
        ticks = tick;
        assert(BP_Algorithm_AddSample(p, voltage));
        if ((i % 8U) == 0U)
        {
            BP_Algorithm_RecordValvePulse(ticks, (uint8_t)(1U + ((i / 8U) % 3U)));
            BP_Algorithm_RecordValveClose(ticks + 1U + ((i / 8U) % 3U));
        }
    }
}

static void self_test(void)
{
    BP_Result_t result;
    const BP_ValveDiagnostics_t *valve;
    BP_Algorithm_Reset();
    assert(!BP_CaptureExport_Begin());
    ticks = 1000U;
    assert(BP_Algorithm_AddSample(100.0f, 1.0f));
    BP_Algorithm_RecordValvePulse(ticks, 5U);
    ticks = 1025U;
    assert(BP_Algorithm_AddSample(93.0f, 1.0f));
    ticks = 1050U;
    assert(BP_Algorithm_AddSample(101.0f, 1.0f));
    valve = BP_Algorithm_GetValveDiagnostics();
    assert(valve->pulse_count == 1U && valve->step_count == 2U);
    assert(valve->phase_bins[1] == 1U && valve->phase_bins[2] == 1U);
    assert(valve->fall_found && valve->fall_index == 1U && valve->fall_delta_mmhg == -7.0f);
    assert(valve->rise_found && valve->rise_index == 2U && valve->rise_delta_mmhg == 8.0f);
    assert(valve->trace_count == 2U);
    assert(valve->trace[0].sample_index == 1U && valve->trace[0].phase_ms == 25U && valve->trace[0].on_ms == 5U);
    assert(valve->trace[1].sample_index == 2U && valve->trace[1].phase_ms == 50U && valve->trace[1].on_ms == 5U);
    fixture(200U, 0U);
    assert(BP_Algorithm_BeginCalculate());
    assert(!BP_CaptureExport_Begin());
    BP_Algorithm_CalculateStep(&result);
    BP_Algorithm_CancelCalculate();
    assert(BP_Algorithm_CaptureState() == 4U);
    assert(BP_CaptureExport_Begin());
    assert(!BP_CaptureExport_Begin());
    BP_CaptureExport_Task(inspect);
    assert(lines == 1U);
    BP_CaptureExport_Cancel();
    BP_CaptureExport_Task(inspect);
    assert(lines == 1U && ends == 0U);
    assert(BP_CaptureExport_Begin());
    BP_CaptureExport_Task(inspect);
    ticks += 25U;
    assert(BP_Algorithm_AddSample(10.0f, 0.3f));
    BP_CaptureExport_Task(inspect);
    assert(!BP_CaptureExport_IsActive() && ends == 0U);
    assert(BP_CaptureExport_Begin());
    BP_CaptureExport_Task(fail);
    assert(!BP_CaptureExport_IsActive());
    assert(BP_CaptureExport_Begin());
    BP_Algorithm_Reset();
    BP_CaptureExport_Task(inspect);
    assert(!BP_CaptureExport_IsActive());
    fixture(BP_ALGO_MAX_SAMPLES, 0U);
    BP_Algorithm_Calculate(&result);
    assert(BP_Algorithm_CaptureState() == 2U || BP_Algorithm_CaptureState() == 3U);
    assert(BP_CaptureExport_Begin());
    unsigned before = lines;
    while (BP_CaptureExport_IsActive())
    {
        unsigned previous = lines;
        BP_CaptureExport_Task(inspect);
        assert(lines == previous + 1U);
    }
    assert(lines - before == BP_ALGO_MAX_SAMPLES + 5U + BP_Algorithm_GetValveTiming()->count && ends == 1U);
    /* Completed envelopes survive stop/vent/seal's idle cancellation. */
    uint8_t state = BP_Algorithm_CaptureState();
    BP_Algorithm_CancelCalculate();
    assert(BP_Algorithm_CaptureState() == state);
    BP_Algorithm_Reset();
    BP_Algorithm_SetCaptureContext(2U, 1U, 82.326f, -19.887f);
    ticks = 1000U;
    assert(BP_Algorithm_AddSample(100.0f, 1.0f));
    assert(!BP_Algorithm_AddSample(99.0f, 1.0f)); /* duplicate MCU tick */
    assert(g_bp_debug.dropped_samples == 1U);
    assert(!BP_CaptureExport_Begin());
    puts("PASS export lifecycle");
}

int main(int argc, char **argv)
{
    _setmode(_fileno(stdout), _O_BINARY); /* preserve firmware CRLF exactly */
    BP_Result_t result;
    if (argc > 1 && strcmp(argv[1], "--self-test") == 0) { self_test(); return 0; }
    if (argc > 1 && strcmp(argv[1], "--fixture") == 0)
    {
        unsigned n = argc > 2 ? (unsigned)strtoul(argv[2], NULL, 10) : 2000U;
        unsigned pattern = argc > 3 ? (unsigned)strtoul(argv[3], NULL, 10) : 0U;
        if (n < 2U || n > BP_ALGO_MAX_SAMPLES) return 2;
        fixture(n, pattern);
        if (pattern != 2U) BP_Algorithm_Calculate(&result);
        if (pattern == 3U) { BP_Algorithm_BeginCalculate(); BP_Algorithm_CalculateStep(&result); BP_Algorithm_CancelCalculate(); }
        assert(BP_CaptureExport_Begin());
        while (BP_CaptureExport_IsActive()) BP_CaptureExport_Task(emit);
        return 0;
    }
    BP_Algorithm_Reset();
    unsigned long p, v, t;
    int scanned;
    while ((scanned = scanf("%lu %lu %lu", &p, &v, &t)) == 3)
    {
        ticks = (uint32_t)t;
        if (!isfinite(value((uint32_t)p)) || !isfinite(value((uint32_t)v)) ||
            !BP_Algorithm_AddSample(value((uint32_t)p), value((uint32_t)v))) return 2;
    }
    if (scanned != EOF) return 2;
    uint8_t ok = BP_Algorithm_Calculate(&result);
    printf("{\"type\":\"replay\",\"firmware\":\"%s\",\"valid\":%u,\"sbp\":%u,\"dbp\":%u,\"pulse\":%u,\"map_i\":%u,\"map_p\":%lu,\"sbp_found\":%u,\"sbp_p\":%lu,\"dbp_found\":%u,\"dbp_p\":%lu,\"sbp_ratio\":%.2f,\"dbp_ratio\":%.2f}\n",
           BP_FIRMWARE_ID, (unsigned)ok, (unsigned)result.systolic, (unsigned)result.diastolic,
           (unsigned)result.pulse, (unsigned)g_bp_debug.map_idx, (unsigned long)bits(g_bp_debug.map_pressure_mmhg),
           (unsigned)g_bp_debug.sbp_found, (unsigned long)bits(g_bp_debug.sbp_pressure_mmhg),
           (unsigned)g_bp_debug.dbp_found, (unsigned long)bits(g_bp_debug.dbp_pressure_mmhg),
           (double)BP_ALGO_SBP_RATIO, (double)BP_ALGO_DBP_RATIO);
    for (uint16_t i = 0; i < g_bp_debug.sample_count; i++)
    {
        BP_Sample_t sample;
        float e, s;
        BP_Algorithm_GetCapturePoint(i, &sample, &e, &s);
        printf("{\"i\":%u,\"e\":%lu,\"s\":%lu}\n", (unsigned)i,
               (unsigned long)bits(e), (unsigned long)bits(s));
    }
    return 0;
}
