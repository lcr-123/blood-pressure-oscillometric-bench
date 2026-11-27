/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    stm32f1xx_it.c
  * @brief   Interrupt Service Routines
  ******************************************************************************
  */
/* USER CODE END Header */
#include "main.h"
#include "stm32f1xx_it.h"

/* USER CODE BEGIN Includes */
#include "usart.h"
#include "i2c.h"
/* USER CODE END Includes */

/* External HAL handles */
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart3;
extern I2C_HandleTypeDef  hi2c1;
extern TIM_HandleTypeDef  htim3;

/******************************************************************************/
/*           Cortex-M3 Core Exception Handlers                                */
/******************************************************************************/

void NMI_Handler(void)
{
    while (1) {}
}

void HardFault_Handler(void)
{
    while (1) {}
}

void MemManage_Handler(void)
{
    while (1) {}
}

void BusFault_Handler(void)
{
    while (1) {}
}

void UsageFault_Handler(void)
{
    while (1) {}
}

void SVC_Handler(void) {}

void DebugMon_Handler(void) {}

void PendSV_Handler(void) {}

void SysTick_Handler(void)
{
    HAL_IncTick();
    HAL_SYSTICK_IRQHandler();
}

/******************************************************************************/
/*           Peripheral Interrupt Handlers                                    */
/******************************************************************************/

/**
  * @brief  EXTI9_5 — PB5 / ADS1115 ALRT
  */
void EXTI9_5_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(ADS_ALRT_Pin);
}

/**
  * @brief  I2C1 Event
  */
void I2C1_EV_IRQHandler(void)
{
    HAL_I2C_EV_IRQHandler(&hi2c1);
}

/**
  * @brief  I2C1 Error
  */
void I2C1_ER_IRQHandler(void)
{
    HAL_I2C_ER_IRQHandler(&hi2c1);
}

/**
  * @brief  USART1 — ESP8266
  */
void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

/**
  * @brief  USART2 — RS232 / MAX3232
  */
void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

/**
  * @brief  USART3 — CH340 Debug
  *
  *  RX 实时接收：主循环 PressureStream 每 50ms 才轮询一次，整串命令
  *  （字节间隔 ~87µs@115200）会在轮询间隙 RX 溢出（ORE）丢失。
  *  采用 HAL_UART_Receive_IT 单字节中断链（main.c 启动），字节到达即回调。
  */
void USART3_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart3);
}

/**
  * @brief  TIM3 — stepper motor STEP pulse generation (motor.c)
  */
void TIM3_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim3);
}
