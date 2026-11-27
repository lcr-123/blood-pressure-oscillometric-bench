/**
  ******************************************************************************
  * @file    ads1115.c
  * @brief   ADS1115 AIN0 pressure acquisition driver implementation
  ******************************************************************************
  */
#include "ads1115.h"
#include "bp_cal.h"

static I2C_HandleTypeDef *s_hi2c = NULL;
static volatile uint8_t s_drdy = 0U;
static uint8_t s_initialized = 0U;
static uint16_t s_config = 0U;
static uint8_t s_recovery_pending = 0U;
static ADS1115_Diagnostics_t s_diag = {0};

static HAL_StatusTypeDef ADS1115_Fail(ADS1115_ErrorStage_t stage,
                                     HAL_StatusTypeDef status, uint8_t reg)
{
    /* An offline API call is not a new bus transaction. Keep the evidence
     * from the transaction that made us offline until a real retry fails. */
    if ((stage == ADS1115_STAGE_ARGUMENT) && (s_recovery_pending != 0U))
        return status;
    s_diag.stage = stage;
    s_diag.status = status;
    s_diag.reg = reg;
    s_diag.hal_error = (s_hi2c != NULL) ? HAL_I2C_GetError(s_hi2c) : 0U;
    s_diag.hal_state = (s_hi2c != NULL) ? (uint32_t)HAL_I2C_GetState(s_hi2c) : 0U;
    s_diag.sr1 = (s_hi2c != NULL) ? s_hi2c->Instance->SR1 : 0U;
    s_diag.sr2 = (s_hi2c != NULL) ? s_hi2c->Instance->SR2 : 0U;
    s_diag.cr1 = (s_hi2c != NULL) ? (uint16_t)s_hi2c->Instance->CR1 : 0U;
    /* Read only: never reconfigure/pulse pins or reset before the caller vents.
     * This sequential failure snapshot is not an electrical edge recording. */
    s_diag.gpio_b_idr = (s_hi2c != NULL && s_hi2c->Instance == I2C1) ?
                        (uint16_t)GPIOB->IDR : 0U;
    s_diag.error_count++;
    s_initialized = 0U;
    s_recovery_pending = 1U;
    /* Return immediately: active callers must stop/vent BEFORE any recovery. */
    return status;
}

static HAL_StatusTypeDef ADS1115_I2C_Recover(void)
{
    HAL_StatusTypeDef status;
    if ((s_hi2c == NULL) || (s_hi2c->Instance != I2C1)) return HAL_ERROR;
    s_diag.recovery_count++;
    status = HAL_I2C_DeInit(s_hi2c);
    if (status != HAL_OK) return status;
    __HAL_RCC_I2C1_FORCE_RESET();
    __HAL_RCC_I2C1_RELEASE_RESET();
    /* Rebuild both the peripheral and HAL handle state. No GPIO clock pulsing;
     * this cannot repair a slave physically holding the bus low. */
    return HAL_I2C_Init(s_hi2c);
}

static HAL_StatusTypeDef ADS1115_ReadRegister16(uint8_t reg, uint16_t *value)
{
    uint8_t data[2];
    HAL_StatusTypeDef status;

    if ((s_hi2c == NULL) || (value == NULL))
    {
        return ADS1115_Fail(ADS1115_STAGE_ARGUMENT, HAL_ERROR, reg);
    }

    status = HAL_I2C_Master_Transmit(s_hi2c, ADS1115_I2C_ADDR, &reg, 1U, ADS1115_I2C_TIMEOUT_MS);
    if (status != HAL_OK)
    {
        return ADS1115_Fail(ADS1115_STAGE_REGISTER_SELECT, status, reg);
    }
    status = HAL_I2C_Master_Receive(s_hi2c, ADS1115_I2C_ADDR, data, 2U, ADS1115_I2C_TIMEOUT_MS);
    if (status != HAL_OK)
    {
        return ADS1115_Fail(ADS1115_STAGE_REGISTER_READ, status, reg);
    }

    *value = (uint16_t)(((uint16_t)data[0] << 8) | data[1]);
    return HAL_OK;
}

HAL_StatusTypeDef ADS1115_Init(I2C_HandleTypeDef *hi2c)
{
    uint16_t config = 0U;
    HAL_StatusTypeDef status;

    s_hi2c = hi2c;
    s_drdy = 0U;
    s_initialized = 0U;
    s_config = 0U;

    if (s_hi2c == NULL)
    {
        return ADS1115_Fail(ADS1115_STAGE_ARGUMENT, HAL_ERROR, ADS1115_REG_CONFIG);
    }
    if (s_recovery_pending != 0U)
    {
        status = ADS1115_I2C_Recover();
        if (status != HAL_OK)
            return ADS1115_Fail(ADS1115_STAGE_RECOVERY, status, ADS1115_REG_CONFIG);
        s_recovery_pending = 0U;
    }
    status = HAL_I2C_IsDeviceReady(s_hi2c, ADS1115_I2C_ADDR, 1U, ADS1115_I2C_TIMEOUT_MS);
    if (status != HAL_OK)
        return ADS1115_Fail(ADS1115_STAGE_PROBE, status, ADS1115_REG_CONFIG);
    status = ADS1115_ReadRegister16(ADS1115_REG_CONFIG, &config);
    if (status != HAL_OK) return status;

    s_config = config;
    s_initialized = 1U;
    return HAL_OK;
}

HAL_StatusTypeDef ADS1115_StartSingleConversion(uint16_t mux_channel)
{
    uint16_t config;
    uint8_t data[3];
    HAL_StatusTypeDef status;

    if ((s_initialized == 0U) || (s_hi2c == NULL))
    {
        return ADS1115_Fail(ADS1115_STAGE_ARGUMENT, HAL_ERROR, ADS1115_REG_CONFIG);
    }

    config = ADS1115_OS_START |
             mux_channel |
             ADS1115_PGA_4096 |
             ADS1115_MODE_SINGLE |
             ADS1115_DR_128SPS |
             ADS1115_COMP_QUE_DISABLE;

    data[0] = ADS1115_REG_CONFIG;
    data[1] = (uint8_t)(config >> 8);
    data[2] = (uint8_t)(config & 0xFFU);
    s_drdy = 0U;

    status = HAL_I2C_Master_Transmit(s_hi2c, ADS1115_I2C_ADDR, data, 3U, ADS1115_I2C_TIMEOUT_MS);
    if (status != HAL_OK)
    {
        return ADS1115_Fail(ADS1115_STAGE_CONVERSION_START, status, ADS1115_REG_CONFIG);
    }
    return HAL_OK;
}

HAL_StatusTypeDef ADS1115_ReadRaw(int16_t *raw_value)
{
    uint16_t conversion = 0U;
    HAL_StatusTypeDef status;

    if ((raw_value == NULL) || (s_initialized == 0U))
    {
        return ADS1115_Fail(ADS1115_STAGE_ARGUMENT, HAL_ERROR, ADS1115_REG_CONVERSION);
    }
    status = ADS1115_ReadRegister16(ADS1115_REG_CONVERSION, &conversion);
    if (status != HAL_OK) return status;

    *raw_value = (int16_t)conversion;
    return HAL_OK;
}

float ADS1115_RawToVoltage(int16_t raw)
{
    return (float)raw * ADS1115_LSB_V;
}

HAL_StatusTypeDef ADS1115_ReadSample(ADS1115_Sample_t *sample)
{
    uint16_t config = 0U;
    uint32_t start_ms;
    HAL_StatusTypeDef status;
    ADS1115_Sample_t next;

    if ((sample == NULL) || (s_initialized == 0U))
    {
        return ADS1115_Fail(ADS1115_STAGE_ARGUMENT, HAL_ERROR, ADS1115_REG_CONFIG);
    }

    status = ADS1115_StartSingleConversion(ADS1115_MUX_AIN0_GND);
    if (status != HAL_OK)
    {
        return status;
    }

    start_ms = HAL_GetTick();
    do
    {
        status = ADS1115_ReadRegister16(ADS1115_REG_CONFIG, &config);
        if (status != HAL_OK)
        {
            return status;
        }
        if ((config & ADS1115_OS_READY) != 0U)
        {
            break;
        }
        if ((HAL_GetTick() - start_ms) >= ADS1115_CONVERSION_TIMEOUT_MS)
        {
            return ADS1115_Fail(ADS1115_STAGE_CONVERSION_WAIT, HAL_TIMEOUT, ADS1115_REG_CONFIG);
        }
        HAL_Delay(1U);
    } while (1);

    status = ADS1115_ReadRaw(&next.raw);
    if (status != HAL_OK)
    {
        return status;
    }

    next.ads_voltage_v = ADS1115_RawToVoltage(next.raw);
    next.sensor_voltage_v = next.ads_voltage_v * ADS1115_DIVIDER_SCALE;
    /* Pressure conversion routes through the calibration store: a valid flash
     * record uses slope/intercept; otherwise the default MPXV5050GP constants
     * are used and the result stays explicitly UNCAL. */
    next.pressure_mmhg = BP_Cal_GetPressure_mmHg(next.sensor_voltage_v);
    if (next.pressure_mmhg < 0.0f)
    {
        next.pressure_mmhg = 0.0f;
    }

    *sample = next;
    return HAL_OK;
}

const ADS1115_Diagnostics_t *ADS1115_GetDiagnostics(void)
{
    return &s_diag;
}

float ADS1115_GetPressure_mmHg(void)
{
    ADS1115_Sample_t sample;

    if (ADS1115_ReadSample(&sample) != HAL_OK)
    {
        return -1.0f;
    }
    return sample.pressure_mmhg;
}

uint8_t ADS1115_IsInitialized(void)
{
    return s_initialized;
}

uint16_t ADS1115_GetConfig(void)
{
    return s_config;
}

void ADS1115_DataReadyCallback(void)
{
    s_drdy = 1U;
}

uint8_t ADS1115_IsDataReady(void)
{
    return s_drdy;
}
