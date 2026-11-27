#include "bp_capture_export.h"
#include <stdio.h>
#include <string.h>

static uint32_t s_revision, s_hash;
static uint16_t s_cursor;
static uint8_t s_active, s_header_sent, s_valve_sent, s_features_sent;
static uint8_t s_trace_cursor;
static uint8_t s_timing_sent;
static uint16_t s_pulse_cursor;

static uint32_t float_bits(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}

uint8_t BP_CaptureExport_IsActive(void) { return s_active; }
void BP_CaptureExport_Cancel(void) { s_active = 0U; }
uint8_t BP_CaptureExport_Begin(void)
{
    if ((s_active != 0U) || (g_bp_debug.sample_count == 0U) ||
        (g_bp_debug.dropped_samples != 0U) ||
        (BP_Algorithm_CaptureState() == 1U) ||
        (BP_Algorithm_GetValveTiming()->pending != 0U) ||
        (BP_Algorithm_GetCaptureContext()->raw_kind == 0U)) return 0U;
    s_revision = BP_Algorithm_CaptureRevision();
    s_hash = 2166136261UL;
    s_cursor = 0U;
    s_header_sent = 0U;
    s_valve_sent = 0U;
    s_trace_cursor = 0U;
    s_features_sent = 0U;
    s_timing_sent = 0U;
    s_pulse_cursor = 0U;
    s_active = 1U;
    return 1U;
}

void BP_CaptureExport_Task(BP_CaptureWriter_t writer)
{
    char line[512];
    int length;
    uint8_t state = BP_Algorithm_CaptureState();
    const BP_CaptureContext_t *context = BP_Algorithm_GetCaptureContext();
    if (s_active == 0U) return;
    if ((writer == NULL) || (s_revision != BP_Algorithm_CaptureRevision()))
    {
        BP_CaptureExport_Cancel();
        return;
    }
    if (s_header_sent == 0U)
    {
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"begin\",\"firmware\":\"%s\",\"n\":%u,\"dropped\":%lu,\"interval_ms\":%u,\"raw_kind\":%u,\"cal_valid\":%u,\"slope\":%lu,\"intercept\":%lu,\"calc\":%u}\r\n",
            BP_FIRMWARE_ID, (unsigned)g_bp_debug.sample_count,
            (unsigned long)g_bp_debug.dropped_samples, (unsigned)BP_SAMPLE_INTERVAL_MS,
            (unsigned)context->raw_kind, (unsigned)context->cal_valid,
            (unsigned long)float_bits(context->slope), (unsigned long)float_bits(context->intercept),
            (unsigned)state);
        s_header_sent = 1U;
    }
    else if (s_cursor < g_bp_debug.sample_count)
    {
        BP_Sample_t sample;
        float envelope, smooth;
        if (BP_Algorithm_GetCapturePoint(s_cursor, &sample, &envelope, &smooth) == 0U)
        {
            BP_CaptureExport_Cancel();
            return;
        }
        if ((state == 2U) || (state == 3U))
            length = snprintf(line, sizeof(line),
                "{\"schema\":\"bp.capture/4\",\"type\":\"point\",\"i\":%u,\"t\":%lu,\"p\":%lu,\"v\":%lu,\"e\":%lu,\"s\":%lu}\r\n",
                (unsigned)s_cursor, (unsigned long)sample.timestamp_ms,
                (unsigned long)float_bits(sample.cuff_pressure), (unsigned long)float_bits(sample.oscillation),
                (unsigned long)float_bits(envelope), (unsigned long)float_bits(smooth));
        else
            length = snprintf(line, sizeof(line),
                "{\"schema\":\"bp.capture/4\",\"type\":\"point\",\"i\":%u,\"t\":%lu,\"p\":%lu,\"v\":%lu,\"e\":null,\"s\":null}\r\n",
                (unsigned)s_cursor, (unsigned long)sample.timestamp_ms,
                (unsigned long)float_bits(sample.cuff_pressure), (unsigned long)float_bits(sample.oscillation));
        s_cursor++;
    }
    else if (s_valve_sent == 0U)
    {
        const BP_ValveDiagnostics_t *valve = BP_Algorithm_GetValveDiagnostics();
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"valve\",\"pulses\":%lu,\"period_min\":%lu,\"period_max\":%lu,\"on_min\":%u,\"on_max\":%u,\"threshold\":%lu,\"steps\":%u,\"phase\":[%u,%u,%u,%u,%u,%u,%u,%u,%u],\"rise_found\":%u,\"rise_i\":%u,\"rise_d\":%lu,\"rise_phase\":%lu,\"rise_on\":%u,\"fall_found\":%u,\"fall_i\":%u,\"fall_d\":%lu,\"fall_phase\":%lu,\"fall_on\":%u,\"trace_n\":%u}\r\n",
            (unsigned long)valve->pulse_count,
            (unsigned long)valve->period_min_ms, (unsigned long)valve->period_max_ms,
            (unsigned)valve->on_min_ms, (unsigned)valve->on_max_ms,
            (unsigned long)float_bits(BP_VALVE_DIAG_STEP_THRESHOLD_MMHG),
            (unsigned)valve->step_count,
            (unsigned)valve->phase_bins[0], (unsigned)valve->phase_bins[1],
            (unsigned)valve->phase_bins[2], (unsigned)valve->phase_bins[3],
            (unsigned)valve->phase_bins[4], (unsigned)valve->phase_bins[5],
            (unsigned)valve->phase_bins[6], (unsigned)valve->phase_bins[7],
            (unsigned)valve->phase_bins[8],
            (unsigned)valve->rise_found, (unsigned)valve->rise_index,
            (unsigned long)float_bits(valve->rise_delta_mmhg),
            (unsigned long)valve->rise_phase_ms, (unsigned)valve->rise_on_ms,
            (unsigned)valve->fall_found, (unsigned)valve->fall_index,
            (unsigned long)float_bits(valve->fall_delta_mmhg),
            (unsigned long)valve->fall_phase_ms, (unsigned)valve->fall_on_ms,
            (unsigned)valve->trace_count);
        s_valve_sent = 1U;
    }
    else if (s_trace_cursor < BP_Algorithm_GetValveDiagnostics()->trace_count)
    {
        const BP_ValveStepTrace_t *trace =
            &BP_Algorithm_GetValveDiagnostics()->trace[s_trace_cursor++];
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"step\",\"i\":%u,\"phase\":%u,\"on\":%u}\r\n",
            (unsigned)trace->sample_index, (unsigned)trace->phase_ms,
            (unsigned)trace->on_ms);
    }
    else if (s_timing_sent == 0U)
    {
        const BP_ValveTiming_t *timing = BP_Algorithm_GetValveTiming();
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"timing\",\"n\":%u,\"errors\":%u,\"complete\":%u}\r\n",
            (unsigned)timing->count, (unsigned)timing->errors,
            (unsigned)((timing->errors == 0U) && (timing->pending == 0U) &&
                       (timing->count == BP_Algorithm_GetValveDiagnostics()->pulse_count)));
        s_timing_sent = 1U;
    }
    else if (s_pulse_cursor < BP_Algorithm_GetValveTiming()->count)
    {
        uint32_t open_ms, close_ms;
        if (BP_Algorithm_GetValvePulse(s_pulse_cursor, &open_ms, &close_ms) == 0U)
        {
            BP_CaptureExport_Cancel();
            return;
        }
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"pulse\",\"i\":%u,\"open\":%lu,\"close\":%lu}\r\n",
            (unsigned)s_pulse_cursor++, (unsigned long)open_ms, (unsigned long)close_ms);
    }
    else if (s_features_sent == 0U)
    {
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"features\",\"map_i\":%u,\"map_p\":%lu,\"sbp_found\":%u,\"sbp_p\":%lu,\"dbp_found\":%u,\"dbp_p\":%lu}\r\n",
            (unsigned)g_bp_debug.map_idx,
            (unsigned long)float_bits(g_bp_debug.map_pressure_mmhg), (unsigned)g_bp_debug.sbp_found,
            (unsigned long)float_bits(g_bp_debug.sbp_pressure_mmhg), (unsigned)g_bp_debug.dbp_found,
            (unsigned long)float_bits(g_bp_debug.dbp_pressure_mmhg));
        s_features_sent = 1U;
    }
    else
    {
        length = snprintf(line, sizeof(line),
            "{\"schema\":\"bp.capture/4\",\"type\":\"end\",\"n\":%u,\"hash\":%lu}\r\n",
            (unsigned)s_cursor, (unsigned long)s_hash);
        s_active = 0U;
    }
    if ((length <= 2) || ((size_t)length >= sizeof(line)) || (writer(line) == 0U))
    {
        BP_CaptureExport_Cancel();
        return;
    }
    if (s_active != 0U)
        for (int i = 0; i < length - 2; i++) s_hash = (s_hash ^ (uint8_t)line[i]) * 16777619UL;
}
