/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    gpio.c
  * @brief   GPIO initialization
  *
  *  Output pin (open-drain, no pull):
  *    PB8  - VALVE1_CTRL  (inflation relay, low = open, released = closed)
  *  Output pins (push-pull, no pull):
  *    PC1  - VALVE2_CTRL  (deflation valve, high = open)
  *    PC3  - ESP_RST      (ESP8266 reset, active low)
  *    PC8  - PUMP_RELAY   (pump relay, low = on)
  *
  *  Input pins (pull-up):
  *    PA0  - BTN_START
  *    PA1  - BTN_STOP
  *    PA4  - BTN_FUNC
  *
  *  EXTI input (pull-up, rising+falling):
  *    PB5  - ADS_ALRT     (ADS1115 alert/ready)
  ******************************************************************************
  */
/* USER CODE END Header */
#include "gpio.h"

void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable clocks for GPIOA, GPIOB, GPIOC */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_AFIO_CLK_ENABLE();

    /* Preload released PB8 before enabling output; PC1 low, PC8 high. */
    HAL_GPIO_WritePin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOC, VALVE2_CTRL_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(PUMP_RELAY_Port, PUMP_RELAY_Pin, GPIO_PIN_SET);
    /* ESP_RST high: normal operation. */
    HAL_GPIO_WritePin(ESP_RST_GPIO_Port, ESP_RST_Pin, GPIO_PIN_SET);

    /* USER CODE BEGIN valve1_init */
    /* FT PB8: never enable an internal pull when relay IN exceeds VDD. */
    GPIO_InitStruct.Pin   = VALVE1_CTRL_Pin;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(VALVE1_CTRL_Port, &GPIO_InitStruct);
    /* USER CODE END valve1_init */

    /* PC1, PC3, PC8: output push-pull. PB8 must not enter this port mask. */
    GPIO_InitStruct.Pin   = VALVE2_CTRL_Pin | ESP_RST_Pin | PUMP_RELAY_Pin;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* PA0, PA1, PA4: input pull-up buttons. */
    GPIO_InitStruct.Pin  = BTN_START_Pin | BTN_STOP_Pin | BTN_FUNC_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* PB5: ADS1115 alert/ready, EXTI on both edges. */
    GPIO_InitStruct.Pin  = ADS_ALRT_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING_FALLING;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ADS_ALRT_GPIO_Port, &GPIO_InitStruct);

    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
}
