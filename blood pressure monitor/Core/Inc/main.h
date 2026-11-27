/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c — pin labels & includes
  ******************************************************************************
  */
/* USER CODE END Header */
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

/* ============================================================
   Pin label definitions (matches接线方案)
   ============================================================ */

/* --- Buttons (active LOW, internal pull-up) --- */
#define BTN_START_Pin        GPIO_PIN_0
#define BTN_START_GPIO_Port  GPIOA

#define BTN_STOP_Pin         GPIO_PIN_1
#define BTN_STOP_GPIO_Port   GPIOA

#define BTN_FUNC_Pin         GPIO_PIN_4
#define BTN_FUNC_GPIO_Port   GPIOA

/* --- ADS1115 alert/ready (EXTI5, PB5) --- */
#define ADS_ALRT_Pin         GPIO_PIN_5
#define ADS_ALRT_GPIO_Port   GPIOB

/* --- Valve & pump control --- */
#define VALVE1_CTRL_Pin      GPIO_PIN_8    /* PB8 FT, open-drain, active LOW */
#define VALVE1_CTRL_Port     GPIOB

#define VALVE2_CTRL_Pin      GPIO_PIN_1    /* 放气阀 PC1 */
#define VALVE2_CTRL_Port     GPIOC

#define PUMP_RELAY_Pin       GPIO_PIN_8    /* Pump relay PC8, active low */
#define PUMP_RELAY_Port      GPIOC

/* --- ESP8266 reset (PC3, active LOW) --- */
#define ESP_RST_Pin          GPIO_PIN_3
#define ESP_RST_GPIO_Port    GPIOC

/* Valve macros own only their valve pin. Pump control remains independent. */
/* SET releases PB8; the powered relay input supplies the external pull-up. */
#define VALVE1_OPEN()   HAL_GPIO_WritePin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin, GPIO_PIN_RESET)
#define VALVE1_CLOSE()  HAL_GPIO_WritePin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin, GPIO_PIN_SET)
#define VALVE2_OPEN()   HAL_GPIO_WritePin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin, GPIO_PIN_SET)
#define VALVE2_CLOSE()  HAL_GPIO_WritePin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin, GPIO_PIN_RESET)
#define ESP_RESET()     do { HAL_GPIO_WritePin(ESP_RST_GPIO_Port, ESP_RST_Pin, GPIO_PIN_RESET); \
                             HAL_Delay(100); \
                             HAL_GPIO_WritePin(ESP_RST_GPIO_Port, ESP_RST_Pin, GPIO_PIN_SET); \
                        } while(0)

/* Exported functions */
void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
