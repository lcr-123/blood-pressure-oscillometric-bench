/**
  ******************************************************************************
  * @file    bp_control.h
  * @brief   Blood pressure measurement state machine
  *          Controls pump (PC8 relay output) and valves (PB8 active low, PC1)
  ******************************************************************************
  */
#ifndef __BP_CONTROL_H
#define __BP_CONTROL_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "tim.h"

/* 充气目标压力 (mmHg) — 高于预估收缩压 30mmHg */
#define BP_INFLATE_TARGET_MMHG   150U

/* 放气速率控制（每次 tick 降低的目标）*/
#define BP_DEFLATE_STEP_MMHG    2U    /* ~2mmHg/step，约 2~3mmHg/s */

/* 慢放气 PWM：高频驱动开关阀，气容滤波后实现连续匀速放体感 */
#define BP_DEFLATE_PERIOD_MS    20U   /* 50Hz高频PWM，消除人耳可闻的断续放气感 */
#define BP_DEFLATE_ON_MS        1U    /* 保持占空比5%，放气速率与原参数一致 */

/* 超压保护上限 */
#define BP_MAX_PRESSURE_MMHG    280U
/* 目标值保留 5 mmHg 的超压保护裕量，避免传感器/泵惯性越过硬上限。 */
#define BP_MAX_TARGET_MMHG      (BP_MAX_PRESSURE_MMHG - 5U)
#define BP_SENSOR_CALIBRATION_VALID   0U
#define BP_INFLATE_TIMEOUT_MS     30000U
#define BP_SAMPLE_INTERVAL_MS        25U


/* 气泵 PWM 占空比 (0~999) */
#define PUMP_DUTY_FULL          800U  /* 80% 全速充气 */
#define PUMP_DUTY_SLOW          300U  /* 慢速补气 */
#define PUMP_DUTY_OFF           0U

typedef enum {
    BP_STATE_IDLE = 0,    /* 等待开始 */
    BP_STATE_INFLATE,     /* 充气阶段 */
    BP_STATE_DEFLATE,     /* 缓慢放气+采样 */
    BP_STATE_COMPLETE,    /* 测量完成 */
    BP_STATE_EMERGENCY    /* 紧急放气（超压/超时） */
} BP_State_t;
typedef enum {
    BP_FAULT_NONE = 0,
    BP_FAULT_USER_STOP,
    BP_FAULT_UNCALIBRATED,
    BP_FAULT_SENSOR_INIT,
    BP_FAULT_SENSOR_READ,
    BP_FAULT_INFLATE_TIMEOUT,
    BP_FAULT_OVERPRESSURE,
    BP_FAULT_MANUAL_TIMEOUT,
    BP_FAULT_RESIDUAL_PRESSURE,
    BP_FAULT_SAMPLE_OVERFLOW,
    BP_FAULT_PRESSURE_RANGE
} BP_Fault_t;


typedef struct {
    uint8_t  systolic;    /* 收缩压 mmHg */
    uint8_t  diastolic;   /* 舒张压 mmHg */
    uint8_t  pulse;       /* 脉率 bpm */
    uint8_t  valid;       /* 结果是否有效 */
} BP_Result_t;

/* Public API */
void         BP_Control_Init(void);
void         BP_Control_Task(void);        /* 主循环调用 */
void         BP_Control_Start(void);       /* BTN_START 触发 */
void         BP_Control_Stop(void);        /* Non-blocking user stop / vent */
BP_State_t   BP_Control_GetState(void);
BP_Result_t  BP_Control_GetResult(void);
void         BP_Control_PressureTick(float pressure_mmhg);  /* 来自 ADS1115 采样 */
void         BP_Control_EmergencyStop(BP_Fault_t fault);
void         BP_Control_RecordFault(BP_Fault_t fault);
void         BP_Control_Reset(void);
BP_Fault_t   BP_Control_GetFault(void);
uint32_t     BP_Control_GetFaultTimeMs(void);
const char  *BP_Control_StateName(BP_State_t state);
const char  *BP_Control_FaultName(BP_Fault_t fault);
uint8_t      BP_Control_IsCalibrationValid(void);


#ifdef __cplusplus
}
#endif
#endif /* __BP_CONTROL_H */
