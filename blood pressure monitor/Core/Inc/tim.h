/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    tim.h
  * @brief   Pump output initialization (PC8, low-level relay trigger)
  ******************************************************************************
  */
/* USER CODE END Header */
#ifndef __TIM_H__
#define __TIM_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

extern TIM_HandleTypeDef htim8;

void MX_TIM8_Init(void);
void Pump_SetDuty(uint16_t duty);
void Pump_Start(void);
void Pump_Stop(void);
uint8_t Pump_IsOn(void);

/* Low-level relay module: PC8 high = pump off, PC8 low = pump on. */
#define PUMP_SET_DUTY(duty)  Pump_SetDuty((duty))
#define PUMP_START()         Pump_Start()
#define PUMP_STOP()          Pump_Stop()

#ifdef __cplusplus
}
#endif
#endif /* __TIM_H__ */
