/**
  ******************************************************************************
  * @file    iwdg.c
  * @brief   Independent watchdog configuration
  ******************************************************************************
  */
#include "iwdg.h"

IWDG_HandleTypeDef hiwdg;

void MX_IWDG_Init(void)
{
    /*
     * Nominal timeout: (2499 + 1) * 64 / 40000 Hz = 4.0 s.
     * The STM32F1 LSI tolerance means the physical timeout is approximate.
     */
    __HAL_DBGMCU_FREEZE_IWDG();

    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Reload = 2499U;
    if (HAL_IWDG_Init(&hiwdg) != HAL_OK)
    {
        Error_Handler();
    }
}
