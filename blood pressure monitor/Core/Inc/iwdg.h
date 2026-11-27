/**
  ******************************************************************************
  * @file    iwdg.h
  * @brief   Independent watchdog configuration
  ******************************************************************************
  */
#ifndef __IWDG_H
#define __IWDG_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

extern IWDG_HandleTypeDef hiwdg;
void MX_IWDG_Init(void);

#ifdef __cplusplus
}
#endif
#endif /* __IWDG_H */
