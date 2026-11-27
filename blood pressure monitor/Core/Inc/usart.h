/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    usart.h
  * @brief   USART1/2/3 initialization
  ******************************************************************************
  */
/* USER CODE END Header */
#ifndef __USART_H__
#define __USART_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

extern UART_HandleTypeDef huart1;  /* ESP8266  */
extern UART_HandleTypeDef huart2;  /* MAX3232/RS232 */
extern UART_HandleTypeDef huart3;  /* CH340 Debug  */

void MX_USART1_UART_Init(void);
void MX_USART2_UART_Init(void);
void MX_USART3_UART_Init(void);

#ifdef __cplusplus
}
#endif
#endif /* __USART_H__ */
