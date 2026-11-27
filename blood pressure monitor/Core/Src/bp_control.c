/**
  ******************************************************************************
  * @file    bp_control.c
  * @brief   Blood pressure measurement state machine and safety fault handling
  ******************************************************************************
  */
#include "bp_control.h"
#include "bp_cal.h"
#include "ads1115.h"
#include "bp_algorithm.h"
#include <string.h>
#include <stdio.h>

static BP_State_t  s_state = BP_STATE_IDLE;
static BP_Result_t s_result = {0};
static BP_Fault_t  s_fault = BP_FAULT_NONE;
static uint32_t    s_fault_time_ms = 0U;
static uint32_t    s_inflate_start_ms = 0U;
static uint32_t    s_last_sample_ms = 0U;
static uint32_t    s_deflate_period_start_ms = 0U;
static uint8_t     s_calculation_pending = 0U;

static void BP_Control_SetSealedIdle(void);

static void BP_Control_SetSealedIdle(void)
{
    PUMP_STOP();
    PUMP_SET_DUTY(PUMP_DUTY_OFF);
    VALVE1_CLOSE();
    VALVE2_CLOSE();
}

void BP_Control_Init(void)
{
    BP_Algorithm_CancelCalculate();
    s_calculation_pending = 0U;
    s_state = BP_STATE_IDLE;
    s_fault = BP_FAULT_NONE;
    s_fault_time_ms = 0U;
    memset(&s_result, 0, sizeof(s_result));
    BP_Control_SetSealedIdle();
}

void BP_Control_RecordFault(BP_Fault_t fault)
{
    if (fault != BP_FAULT_NONE)
    {
        s_fault = fault;
        s_fault_time_ms = HAL_GetTick();
    }
}

void BP_Control_EmergencyStop(BP_Fault_t fault)
{
    /* Safe order: pump off, inflation path closed, then vent open. */
    PUMP_STOP();
    PUMP_SET_DUTY(PUMP_DUTY_OFF);
    VALVE1_CLOSE();
    VALVE2_OPEN();

    BP_Algorithm_CancelCalculate();
    s_calculation_pending = 0U;
    memset(&s_result, 0, sizeof(s_result));
    BP_Control_RecordFault(fault);
    s_state = BP_STATE_EMERGENCY;
}

void BP_Control_Reset(void)
{
    BP_Algorithm_CancelCalculate();
    s_calculation_pending = 0U;
    BP_Control_SetSealedIdle();
    memset(&s_result, 0, sizeof(s_result));
    s_inflate_start_ms = 0U;
    s_last_sample_ms = 0U;
    s_fault = BP_FAULT_NONE;
    s_fault_time_ms = 0U;
    s_state = BP_STATE_IDLE;
}

void BP_Control_Start(void)
{
    if (s_state != BP_STATE_IDLE)
    {
        return;
    }

    if (BP_Control_IsCalibrationValid() == 0U)
    {
        BP_Control_RecordFault(BP_FAULT_UNCALIBRATED);
        printf("[BP_Control] START blocked: pressure sensor UNCAL\r\n");
        return;
    }

    if (ADS1115_IsInitialized() == 0U)
    {
        BP_Control_EmergencyStop(BP_FAULT_SENSOR_INIT);
        printf("[BP_Control] START blocked: ADS1115 offline\r\n");
        return;
    }

    BP_Algorithm_Reset();
    BP_Algorithm_SetCaptureContext(1U, BP_Cal_IsValid(), BP_Cal_GetSlope(), BP_Cal_GetIntercept());
    memset(&s_result, 0, sizeof(s_result));
    s_fault = BP_FAULT_NONE;
    s_fault_time_ms = 0U;

    VALVE2_CLOSE();
    VALVE1_OPEN();
    PUMP_SET_DUTY(PUMP_DUTY_FULL);
    PUMP_START();

    s_inflate_start_ms = HAL_GetTick();
    s_state = BP_STATE_INFLATE;
    printf("[BP_Control] Inflate started, target=%d mmHg\r\n",
           BP_INFLATE_TARGET_MMHG);
}

void BP_Control_Stop(void)
{
    BP_Control_EmergencyStop(BP_FAULT_USER_STOP);
    printf("[BP_Control] User stop: vent remains open\r\n");
}

void BP_Control_Task(void)
{
    uint32_t now = HAL_GetTick();
    ADS1115_Sample_t sample;

    switch (s_state)
    {
        case BP_STATE_INFLATE:
            if ((now - s_inflate_start_ms) > BP_INFLATE_TIMEOUT_MS)
            {
                BP_Control_EmergencyStop(BP_FAULT_INFLATE_TIMEOUT);
                printf("[BP_Control] Inflate TIMEOUT; emergency vent\r\n");
                break;
            }

            if (ADS1115_ReadSample(&sample) != HAL_OK)
            {
                BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
                printf("[BP_Control] Sensor read failed during inflate; emergency vent\r\n");
                break;
            }

            if (sample.pressure_mmhg > (float)BP_MAX_PRESSURE_MMHG)
            {
                BP_Control_EmergencyStop(BP_FAULT_OVERPRESSURE);
                printf("[BP_Control] Over-pressure %.1f mmHg; emergency vent\r\n",
                       sample.pressure_mmhg);
                break;
            }

            if (sample.pressure_mmhg >= (float)BP_INFLATE_TARGET_MMHG)
            {
                PUMP_STOP();
                PUMP_SET_DUTY(PUMP_DUTY_OFF);
                VALVE1_CLOSE();
                /* 充到160后完全松手：放气阀全程关闭，不启动任何自身放气逻辑，
                   整个放气过程由BP Pump 2控制，我们只做纯采样 */
                VALVE2_CLOSE();

                s_last_sample_ms = HAL_GetTick();
                s_deflate_period_start_ms = HAL_GetTick();
                s_state = BP_STATE_DEFLATE;
                printf("[BP_Control] Inflate to 160 done, BP Pump 2 controls deflate, we sample only\r\n");
            }
            break;

        case BP_STATE_DEFLATE:
            /* 纯采样模式：放气阀保持常开通路，BP Pump 2可以自由抽气控压，
               我们不做任何开关阀动作，只采样压力和脉搏波形 */
            {
                VALVE2_OPEN();
            }

            if ((now - s_last_sample_ms) >= BP_SAMPLE_INTERVAL_MS)
            {
                s_last_sample_ms = now;

                if (ADS1115_ReadSample(&sample) != HAL_OK)
                {
                    BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
                    printf("[BP_Control] Sensor read failed during deflate; emergency vent\r\n");
                    break;
                }

                if (BP_Algorithm_AddSample(sample.pressure_mmhg, sample.ads_voltage_v) == 0U)
                {
                    BP_Control_EmergencyStop(BP_FAULT_SAMPLE_OVERFLOW);
                    printf("[BP_Control] Sample overflow; emergency vent\r\n");
                    break;
                }

                if (sample.pressure_mmhg < 20.0f)
                {
                    VALVE2_CLOSE();
                    memset(&s_result, 0, sizeof(s_result));
                    s_calculation_pending = BP_Algorithm_BeginCalculate();
                    if (s_calculation_pending == 0U)
                    {
                        printf("[BP_Control] Algorithm failed, retry\r\n");
                    }
                    s_state = BP_STATE_COMPLETE;
                }
            }
            break;

        case BP_STATE_COMPLETE:
            if (s_calculation_pending != 0U)
            {
                BP_CalcStatus_t status = BP_Algorithm_CalculateStep(&s_result);
                if (status == BP_CALC_BUSY) break;
                s_calculation_pending = 0U;
                if (status == BP_CALC_DONE)
                {
                    printf("[BP_Control] Result: SBP=%d DBP=%d Pulse=%d\r\n",
                           s_result.systolic, s_result.diastolic, s_result.pulse);
                }
                else if (status == BP_CALC_FAILED)
                {
                    printf("[BP_Control] Algorithm failed, retry\r\n");
                }
            }
            break;
        case BP_STATE_IDLE:
        case BP_STATE_EMERGENCY:
        default:
            break;
    }
}

void BP_Control_PressureTick(float pressure_mmhg)
{
    int16_t raw = 0;

    if (ADS1115_ReadRaw(&raw) != HAL_OK)
    {
        BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
        return;
    }

    if (BP_Algorithm_AddSample(pressure_mmhg, ADS1115_RawToVoltage(raw)) == 0U)
    {
        BP_Control_EmergencyStop(BP_FAULT_SAMPLE_OVERFLOW);
    }
}

BP_State_t BP_Control_GetState(void)
{
    return s_state;
}

BP_Result_t BP_Control_GetResult(void)
{
    return s_result;
}

BP_Fault_t BP_Control_GetFault(void)
{
    return s_fault;
}

uint32_t BP_Control_GetFaultTimeMs(void)
{
    return s_fault_time_ms;
}

uint8_t BP_Control_IsCalibrationValid(void)
{
    /* Calibration validity is runtime state: a stored, CRC-valid record in
     * flash makes the sensor calibrated. BP_SENSOR_CALIBRATION_VALID remains
     * the compile-time default (0) used while no record is stored. */
    if (BP_Cal_IsValid() != 0U)
    {
        return 1U;
    }
    return (uint8_t)BP_SENSOR_CALIBRATION_VALID;
}

const char *BP_Control_StateName(BP_State_t state)
{
    switch (state)
    {
        case BP_STATE_IDLE:      return "IDLE";
        case BP_STATE_INFLATE:   return "INFLATE";
        case BP_STATE_DEFLATE:   return "DEFLATE";
        case BP_STATE_COMPLETE:  return "COMPLETE";
        case BP_STATE_EMERGENCY: return "EMERGENCY";
        default:                 return "UNKNOWN";
    }
}

const char *BP_Control_FaultName(BP_Fault_t fault)
{
    switch (fault)
    {
        case BP_FAULT_NONE:            return "NONE";
        case BP_FAULT_USER_STOP:       return "USER_STOP";
        case BP_FAULT_UNCALIBRATED:    return "UNCALIBRATED";
        case BP_FAULT_SENSOR_INIT:     return "SENSOR_INIT";
        case BP_FAULT_SENSOR_READ:     return "SENSOR_READ";
        case BP_FAULT_INFLATE_TIMEOUT: return "INFLATE_TIMEOUT";
        case BP_FAULT_OVERPRESSURE:    return "OVERPRESSURE";
        case BP_FAULT_MANUAL_TIMEOUT:  return "MANUAL_TIMEOUT";
        case BP_FAULT_RESIDUAL_PRESSURE: return "RESIDUAL_PRESSURE";
        case BP_FAULT_SAMPLE_OVERFLOW: return "SAMPLE_OVERFLOW";
        case BP_FAULT_PRESSURE_RANGE: return "PRESSURE_RANGE";
        default:                       return "UNKNOWN";
    }
}
