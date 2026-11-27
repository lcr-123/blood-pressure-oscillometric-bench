/**
  ******************************************************************************
  * @file    bp_cal.h
  * @brief   Calibration parameter persistence for the pressure chain.
  *
  * Stores the linear pressure model
  *     pressure_mmhg = slope_mmhg_per_unit * sensor_voltage_v + intercept_mmhg
  * in the last internal-Flash page of the STM32F103ZE (512 KB, 2 KB pages),
  * with a magic word and CRC16 integrity check.
  *
  * The stored model is sensor-agnostic: replacing the pressure sensor only
  * requires writing a new calibration with the same protocol. When no valid
  * calibration is stored, default MPXV5050GP constants (0.09 V/kPa) are used
  * and the pressure estimate stays explicitly uncalibrated.
  ******************************************************************************
  */
#ifndef __BP_CAL_H
#define __BP_CAL_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* F103ZE = 512 KB flash, 2 KB pages; last page is dedicated to calibration. */
#define BP_CAL_MAGIC            0x43414C31UL  /* "CAL1" */
#define BP_CAL_VERSION          1U
#define BP_CAL_FLASH_ADDR       0x0807F800UL

/* Historical fallback constants, used only while no valid calibration is
 * stored; they are not the current Flash restore record. 本板实测
 *（2026-09-23，MPXV5050GP 新传感器）：
 *  - 零点：大气 sensor=0.290V（传感器个体零点偏移，datasheet 典型 0.20V）
 *  - 灵敏度：STATIC 两点标定 slope=88.3 mmHg/V → 0.0849 V/kPa
 *    （BP Pump 2 加压 110 mmHg 峰值 sensor=1.584V；datasheet 典型 0.09 V/kPa）
 * 当前 Flash 恢复记录为 82.326/-19.887（2026-10-25）；全片擦除后不得从
 * 这些历史 fallback 宏推导 cal write 参数。 */
#define BP_CAL_DEFAULT_ZERO_V            0.29f
#define BP_CAL_DEFAULT_SENS_V_PER_KPA    0.0849f
#define BP_CAL_DEFAULT_MMHG_PER_KPA      7.50062f

typedef struct {
    uint32_t magic;              /* BP_CAL_MAGIC */
    uint8_t  version;            /* BP_CAL_VERSION */
    uint8_t  reserved[3];
    float    slope_mmhg_per_unit;   /* mmHg per sensor volt */
    float    intercept_mmhg;        /* mmHg at 0 V */
    uint16_t crc;                   /* CRC16 over all preceding bytes */
    uint16_t reserved2;
} BP_Cal_t;

HAL_StatusTypeDef BP_Cal_Load(void);
HAL_StatusTypeDef BP_Cal_Write(float slope_mmhg_per_unit, float intercept_mmhg);
HAL_StatusTypeDef BP_Cal_Clear(void);
uint8_t  BP_Cal_IsValid(void);
float    BP_Cal_GetSlope(void);
float    BP_Cal_GetIntercept(void);
float    BP_Cal_GetZeroVoltageV(void);       /* -intercept/slope */
float    BP_Cal_GetSensitivityVPerKPa(void); /* 7.50062/slope */
float    BP_Cal_GetPressure_mmHg(float sensor_voltage_v);

#ifdef __cplusplus
}
#endif
#endif /* __BP_CAL_H */
