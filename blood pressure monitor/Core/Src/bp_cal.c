/**
  ******************************************************************************
  * @file    bp_cal.c
  * @brief   Calibration parameter persistence (internal Flash) implementation.
  *
  * Storage layout: last 2 KB page of internal flash at BP_CAL_FLASH_ADDR.
  * A valid calibration is one whose magic matches and whose CRC16 over the
  * preceding bytes matches. The write path erases the page, programs the
  * record, locks flash, then re-loads and compares against the requested
  * values so a corrupted write is reported instead of silently accepted.
  ******************************************************************************
  */
#include "bp_cal.h"
#include <string.h>
#include <stddef.h>
#include <math.h>

static BP_Cal_t s_cal;
static uint8_t  s_valid = 0U;

static uint16_t BP_Cal_Crc16(const uint8_t *data, uint32_t len)
{
    uint16_t crc = 0xFFFFU;
    uint32_t i;

    for (i = 0U; i < len; i++)
    {
        uint8_t bit;
        crc ^= (uint16_t)data[i];
        for (bit = 0U; bit < 8U; bit++)
        {
            if ((crc & 0x0001U) != 0U)
            {
                crc = (uint16_t)((crc >> 1) ^ 0xA001U);
            }
            else
            {
                crc >>= 1;
            }
        }
    }
    return crc;
}

static uint32_t BP_Cal_PayloadLen(void)
{
    return (uint32_t)offsetof(BP_Cal_t, crc);
}

static HAL_StatusTypeDef BP_Cal_FlashErasePage(void)
{
    FLASH_EraseInitTypeDef erase = {0};
    uint32_t page_error = 0U;

    erase.TypeErase = FLASH_TYPEERASE_PAGES;
    erase.PageAddress = BP_CAL_FLASH_ADDR;
    erase.NbPages = 1U;

    if (HAL_FLASH_Unlock() != HAL_OK)
    {
        return HAL_ERROR;
    }
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_PGERR | FLASH_FLAG_WRPERR);
    if (HAL_FLASHEx_Erase(&erase, &page_error) != HAL_OK)
    {
        HAL_FLASH_Lock();
        return HAL_ERROR;
    }
    HAL_FLASH_Lock();
    return HAL_OK;
}

static HAL_StatusTypeDef BP_Cal_FlashProgram(const BP_Cal_t *cal)
{
    const uint32_t *src = (const uint32_t *)cal;
    uint32_t *dst = (uint32_t *)BP_CAL_FLASH_ADDR;
    uint32_t words = (uint32_t)sizeof(BP_Cal_t) / 4U;
    uint32_t i;

    if (HAL_FLASH_Unlock() != HAL_OK)
    {
        return HAL_ERROR;
    }
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_PGERR | FLASH_FLAG_WRPERR);
    for (i = 0U; i < words; i++)
    {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, (uint32_t)(dst + i), src[i]) != HAL_OK)
        {
            HAL_FLASH_Lock();
            return HAL_ERROR;
        }
    }
    HAL_FLASH_Lock();
    return HAL_OK;
}

HAL_StatusTypeDef BP_Cal_Load(void)
{
    const BP_Cal_t *stored = (const BP_Cal_t *)BP_CAL_FLASH_ADDR;

    if (stored->magic != BP_CAL_MAGIC)
    {
        s_valid = 0U;
        return HAL_ERROR;
    }

    if (BP_Cal_Crc16((const uint8_t *)stored, BP_Cal_PayloadLen()) != stored->crc)
    {
        s_valid = 0U;
        return HAL_ERROR;
    }

    s_cal = *stored;
    s_valid = 1U;
    return HAL_OK;
}

HAL_StatusTypeDef BP_Cal_Write(float slope_mmhg_per_unit, float intercept_mmhg)
{
    BP_Cal_t cal;

    if ((!isfinite(slope_mmhg_per_unit)) ||
        (!isfinite(intercept_mmhg)) ||
        (fabsf(slope_mmhg_per_unit) < 1.0e-6f))
    {
        return HAL_ERROR;
    }

    cal.magic = BP_CAL_MAGIC;
    cal.version = BP_CAL_VERSION;
    memset(cal.reserved, 0, sizeof(cal.reserved));
    cal.slope_mmhg_per_unit = slope_mmhg_per_unit;
    cal.intercept_mmhg = intercept_mmhg;
    cal.reserved2 = 0U;
    cal.crc = BP_Cal_Crc16((const uint8_t *)&cal, BP_Cal_PayloadLen());

    if (BP_Cal_FlashProgram(&cal) != HAL_OK)
    {
        return HAL_ERROR;
    }

    /* Read back and verify integrity + requested values. */
    if (BP_Cal_Load() != HAL_OK)
    {
        return HAL_ERROR;
    }
    if ((s_cal.slope_mmhg_per_unit != slope_mmhg_per_unit) ||
        (s_cal.intercept_mmhg != intercept_mmhg))
    {
        s_valid = 0U;
        return HAL_ERROR;
    }
    return HAL_OK;
}

HAL_StatusTypeDef BP_Cal_Clear(void)
{
    if (BP_Cal_FlashErasePage() != HAL_OK)
    {
        return HAL_ERROR;
    }
    s_valid = 0U;
    return HAL_OK;
}

uint8_t BP_Cal_IsValid(void)
{
    return s_valid;
}

float BP_Cal_GetSlope(void)
{
    return s_cal.slope_mmhg_per_unit;
}

float BP_Cal_GetIntercept(void)
{
    return s_cal.intercept_mmhg;
}

float BP_Cal_GetZeroVoltageV(void)
{
    return -s_cal.intercept_mmhg / s_cal.slope_mmhg_per_unit;
}

float BP_Cal_GetSensitivityVPerKPa(void)
{
    return BP_CAL_DEFAULT_MMHG_PER_KPA / s_cal.slope_mmhg_per_unit;
}

float BP_Cal_GetPressure_mmHg(float sensor_voltage_v)
{
    if (s_valid != 0U)
    {
        return s_cal.slope_mmhg_per_unit * sensor_voltage_v + s_cal.intercept_mmhg;
    }
    return ((sensor_voltage_v - BP_CAL_DEFAULT_ZERO_V) /
            BP_CAL_DEFAULT_SENS_V_PER_KPA) * BP_CAL_DEFAULT_MMHG_PER_KPA;
}
