/**
  ******************************************************************************
  * @file    ads1115.h
  * @brief   ADS1115 AIN0 pressure acquisition driver
  ******************************************************************************
  */
#ifndef __ADS1115_H
#define __ADS1115_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* ADDR tied to GND: 7-bit address 0x48; STM32 HAL expects left-shifted form. */
#define ADS1115_I2C_ADDR             (0x48U << 1)

#define ADS1115_REG_CONVERSION       0x00U
#define ADS1115_REG_CONFIG           0x01U
#define ADS1115_REG_LO_THRESH        0x02U
#define ADS1115_REG_HI_THRESH        0x03U

#define ADS1115_OS_START             0x8000U
#define ADS1115_OS_READY             0x8000U
#define ADS1115_MUX_AIN0_GND         0x4000U
#define ADS1115_MUX_AIN1_GND         0x5000U
#define ADS1115_MUX_AIN2_GND         0x6000U
#define ADS1115_MUX_AIN3_GND         0x7000U
#define ADS1115_PGA_4096             0x0200U
#define ADS1115_MODE_SINGLE          0x0100U
#define ADS1115_MODE_CONTINUOUS      0x0000U
#define ADS1115_DR_128SPS            0x0080U
#define ADS1115_DR_250SPS            0x00A0U
#define ADS1115_COMP_QUE_DISABLE     0x0003U
#define ADS1115_CONVERSION_TIMEOUT_MS 25U
#define ADS1115_I2C_TIMEOUT_MS        10U

/* Divider values measured on hardware; pressure constants remain provisional
 * defaults until a real calibration is stored via bp_cal (BP_Cal_*).
 *
 * MPXV5050GP datasheet (NXP Rev 6): transfer function
 *   Vout = VS * (0.018 * P + 0.04),  VS = 5.0 V
 * so sensitivity = 90 mV/kPa = 0.09 V/kPa and zero output = 0.2 V typ
 * (full scale 50 kPa = 4.7 V = 0-375 mmHg gauge). */
#define ADS1115_LSB_V                       0.000125f
#define ADS1115_DIVIDER_TOP_KOHM            6.823f
#define ADS1115_DIVIDER_BOTTOM_KOHM        17.96f
#define ADS1115_DIVIDER_SCALE               ((ADS1115_DIVIDER_TOP_KOHM + ADS1115_DIVIDER_BOTTOM_KOHM) / ADS1115_DIVIDER_BOTTOM_KOHM)
#define MPXV5050_ZERO_VOLTAGE               0.20f
#define MPXV5050_SENSITIVITY_V_PER_KPA      0.09f
#define VOLTAGE_TO_KPA(v)                   (((v) - MPXV5050_ZERO_VOLTAGE) / MPXV5050_SENSITIVITY_V_PER_KPA)
#define KPA_TO_MMHG(kpa)                    ((kpa) * 7.5f)

typedef struct {
    int16_t raw;
    float ads_voltage_v;
    float sensor_voltage_v;
    float pressure_mmhg;
} ADS1115_Sample_t;

typedef enum {
    ADS1115_STAGE_NONE = 0,
    ADS1115_STAGE_ARGUMENT,
    ADS1115_STAGE_PROBE,
    ADS1115_STAGE_REGISTER_SELECT,
    ADS1115_STAGE_REGISTER_READ,
    ADS1115_STAGE_CONVERSION_START,
    ADS1115_STAGE_CONVERSION_WAIT,
    ADS1115_STAGE_RECOVERY
} ADS1115_ErrorStage_t;

/* Last failure is retained across successful re-init; counters are boot-lifetime.
 * No printing or actuator control occurs in the driver. */
typedef struct {
    ADS1115_ErrorStage_t stage;
    HAL_StatusTypeDef status;
    uint32_t hal_error;
    uint32_t hal_state;
    uint32_t sr1;
    uint32_t sr2;
    uint32_t error_count;
    uint32_t recovery_count;
    uint8_t reg;
    uint16_t cr1;
    uint16_t gpio_b_idr;
} ADS1115_Diagnostics_t;

HAL_StatusTypeDef ADS1115_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef ADS1115_StartSingleConversion(uint16_t mux_channel);
HAL_StatusTypeDef ADS1115_ReadRaw(int16_t *raw_value);
HAL_StatusTypeDef ADS1115_ReadSample(ADS1115_Sample_t *sample);
float ADS1115_RawToVoltage(int16_t raw);
float ADS1115_GetPressure_mmHg(void);
uint8_t ADS1115_IsInitialized(void);
uint16_t ADS1115_GetConfig(void);
const ADS1115_Diagnostics_t *ADS1115_GetDiagnostics(void);
void ADS1115_DataReadyCallback(void);
uint8_t ADS1115_IsDataReady(void);

#ifdef __cplusplus
}
#endif
#endif /* __ADS1115_H */
