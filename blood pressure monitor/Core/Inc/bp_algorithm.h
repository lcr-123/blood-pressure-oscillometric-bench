/**
  ******************************************************************************
  * @file    bp_algorithm.h
  * @brief   Oscillometric blood pressure algorithm
  *
  *  原理：振荡法（Oscillometric method）
  *    - 在缓慢放气过程中，袖带压力振荡幅度先增大后减小
  *    - 最大振荡幅度对应 MAP（平均动脉压）
  *    - 收缩压 ≈ MAP 处振荡幅度上升到 50% 对应的袖带压
  *    - 舒张压 ≈ MAP 处振荡幅度下降到 60% 对应的袖带压
  ******************************************************************************
  */
#ifndef __BP_ALGORITHM_H
#define __BP_ALGORITHM_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "bp_control.h"

/* 40 Hz nominal: 105 seconds. Private inputs, exact tick deltas and one
 * envelope plus a 32-float ring use 13 * 4200 + 128 bytes. Keep the 64 KiB linker RAM and stack budget checked.
 * Overflow invalidates the entire capture; this is not a circular buffer. */
#define BP_ALGO_MAX_SAMPLES     4200U
#define BP_FIRMWARE_ID "PEAK_WINDOW_20261105"

/* Cooperative work per main-loop iteration; final feature/FFT step is timed
 * separately and is not covered by the envelope batch's 5 ms yield budget. */
#define BP_ALGO_CALC_BATCH_SAMPLES 8U
#define BP_ALGO_CALC_YIELD_MS      5U

/* 振荡幅度比例系数（经验值，可校准） */
#define BP_ALGO_SBP_RATIO       0.50f   /* 收缩压阈值系数：保持0.50，固定补偿修正全量程误差 */
#define BP_ALGO_DBP_RATIO       0.60f   /* 舒张压阈值系数：2026-10-25 0.70→0.60，External Cuff 低压段包络下降慢，70% 交叉点偏早（DBP=105 vs 目标 80，偏高 25）；降低阈值让交叉点往低压端移 */

/* 脉率计算窗口（ms） */
#define BP_ALGO_PULSE_WINDOW_MS 5000U

typedef struct {
    float   cuff_pressure;    /* 袖带压力 mmHg */
    float   oscillation;      /* 算法输入电压 V；来源由 capture context 标识 */
    uint32_t timestamp_ms;    /* HAL_GetTick() */
} BP_Sample_t;

/* 调试诊断：最近一次 BP_Algorithm_Calculate 的中间量，供主循环打印 */
typedef struct {
    uint16_t sample_count;      /* s_count */
    uint32_t dropped_samples;   /* nonzero invalidates capture until Reset */
    uint32_t duration_ms;       /* actual last timestamp - first timestamp */
    uint16_t map_idx;           /* 包络最大点下标 */
    float    map_pressure_mmhg; /* MAP 读数 */
    uint8_t  sbp_found;         /* 是否找到 SBP 特征点 */
    float    sbp_pressure_mmhg;
    uint8_t  dbp_found;
    float    dbp_pressure_mmhg;
    uint8_t  fft_pass;          /* FFT 是否通过 3x 噪声门槛 */
    float    fft_peak_hz;
    float    fft_peak_bpm;
    float    fft_max_mag;
    float    fft_noise;
    float    fft_threshold;
    uint8_t  pulse_fft;         /* FFT 返回脉率 */
    uint8_t  pulse_peak;        /* 峰值计数返回脉率 */
    uint32_t calc_work_ms;      /* sum of Step execution ticks, not host time */
    uint32_t calc_wall_ms;      /* Begin to terminal Step, including loop work */
    uint32_t calc_max_step_ms;
    uint32_t calc_extract_ms;
    uint32_t calc_smooth_ms;
    uint32_t calc_finish_ms;
    uint32_t calc_steps;
} BP_AlgoDebug_t;

extern BP_AlgoDebug_t g_bp_debug;

typedef enum {
    BP_CALC_IDLE = 0,
    BP_CALC_BUSY,
    BP_CALC_DONE,
    BP_CALC_FAILED
} BP_CalcStatus_t;

/* Public API */
void BP_Algorithm_Init(void);
void BP_Algorithm_Reset(void);
uint8_t BP_Algorithm_AddSample(float cuff_pressure_mmhg, float raw_voltage); /* 0=full/frozen */
uint8_t BP_Algorithm_BeginCalculate(void); /* 0=busy/insufficient/overflow */
BP_CalcStatus_t BP_Algorithm_CalculateStep(BP_Result_t *result);
void BP_Algorithm_CancelCalculate(void); /* no GPIO/serial/watchdog side effects */
uint8_t BP_Algorithm_Calculate(BP_Result_t *result); /* synchronous host/legacy API */

/* Read-only forensic export; raw_kind: 0=unknown, 1=ADS V, 2=sensor V.
 * Set context immediately after Reset, before any samples are added. */
typedef struct {
    float slope;
    float intercept;
    uint8_t cal_valid;
    uint8_t raw_kind;
} BP_CaptureContext_t;

#define BP_VALVE_DIAG_PHASE_BIN_COUNT 9U
#define BP_VALVE_DIAG_STEP_THRESHOLD_MMHG 5.0f
#define BP_VALVE_STEP_TRACE_MAX 12U
#define BP_VALVE_PULSE_TRACE_MAX 600U

/* GPIO command timestamps, not mechanical edges or ADC conversion apertures.
 * Error bits: 1=capacity, 2=period, 4=width, 8=edge sequence. */
typedef struct {
    volatile uint16_t count;
    volatile uint8_t errors;
    volatile uint8_t pending;
} BP_ValveTiming_t;

const BP_ValveTiming_t *BP_Algorithm_GetValveTiming(void);
void BP_Algorithm_RecordValveClose(uint32_t timestamp_ms);
uint8_t BP_Algorithm_GetValvePulse(uint16_t index, uint32_t *open_ms,
                                  uint32_t *close_ms);

typedef struct {
    uint16_t sample_index;
    uint8_t phase_ms; /* 255 means the exact phase exceeded this compact field. */
    uint8_t on_ms;
} BP_ValveStepTrace_t;

/* Aggregate evidence only: eight 25 ms bins cover 0..199 ms after the latest
 * actual valve pulse; bin 8 contains phases >=200 ms. */
typedef struct {
    uint32_t pulse_count;
    uint32_t period_min_ms;
    uint32_t period_max_ms;
    uint16_t step_count;
    uint16_t phase_bins[BP_VALVE_DIAG_PHASE_BIN_COUNT];
    uint16_t rise_index;
    uint16_t fall_index;
    float rise_delta_mmhg;
    float fall_delta_mmhg;
    uint32_t rise_phase_ms;
    uint32_t fall_phase_ms;
    uint8_t on_min_ms;
    uint8_t on_max_ms;
    uint8_t rise_found;
    uint8_t fall_found;
    uint8_t rise_on_ms;
    uint8_t fall_on_ms;
    uint8_t trace_count;
    BP_ValveStepTrace_t trace[BP_VALVE_STEP_TRACE_MAX];
} BP_ValveDiagnostics_t;

void BP_Algorithm_SetCaptureContext(uint8_t raw_kind, uint8_t cal_valid,
                                    float slope, float intercept);
const BP_CaptureContext_t *BP_Algorithm_GetCaptureContext(void);
void BP_Algorithm_RecordValvePulse(uint32_t timestamp_ms, uint8_t on_ms);
const BP_ValveDiagnostics_t *BP_Algorithm_GetValveDiagnostics(void);
uint32_t BP_Algorithm_LastValvePulseTick(void);
uint32_t BP_Algorithm_CaptureRevision(void);
uint8_t BP_Algorithm_CaptureState(void); /* 0=uncomputed,1=busy,2=done,3=failed,4=cancelled */
uint8_t BP_Algorithm_GetCapturePoint(uint16_t index, BP_Sample_t *sample,
                                    float *envelope, float *smooth);

#ifdef __cplusplus
}
#endif
#endif /* __BP_ALGORITHM_H */
