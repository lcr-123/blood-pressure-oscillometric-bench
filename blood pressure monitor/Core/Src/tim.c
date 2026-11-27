/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    tim.c
  * @brief   Pump control output on PC8
  *
  *  Temporary bring-up mode:
  *  PC8 drives a low-level trigger relay module.
  *  PC8 high = relay released = pump off.
  *  PC8 low  = relay active   = pump on.
  ******************************************************************************
  */
/* USER CODE END Header */
#include "tim.h"

TIM_HandleTypeDef htim8;
static uint16_t s_pump_duty = 0U;

void MX_TIM8_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOC_CLK_ENABLE();

    HAL_GPIO_WritePin(PUMP_RELAY_Port, PUMP_RELAY_Pin, GPIO_PIN_SET);

    GPIO_InitStruct.Pin   = PUMP_RELAY_Pin;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(PUMP_RELAY_Port, &GPIO_InitStruct);

    s_pump_duty = 0U;
}

void Pump_SetDuty(uint16_t duty)
{
    s_pump_duty = duty;
}

void Pump_Start(void)
{
    if (s_pump_duty > 0U)
    {
        HAL_GPIO_WritePin(PUMP_RELAY_Port, PUMP_RELAY_Pin, GPIO_PIN_RESET);
    }
}

void Pump_Stop(void)
{
    s_pump_duty = 0U;
    HAL_GPIO_WritePin(PUMP_RELAY_Port, PUMP_RELAY_Pin, GPIO_PIN_SET);
}

uint8_t Pump_IsOn(void)
{
    return (HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin) == GPIO_PIN_RESET) ? 1U : 0U;
}
