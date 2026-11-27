#ifndef BP_HOST_CAL_H
#define BP_HOST_CAL_H
#include "main.h"
float BP_Cal_GetPressure_mmHg(float voltage);
uint8_t BP_Cal_IsValid(void);
float BP_Cal_GetSlope(void);
float BP_Cal_GetIntercept(void);
#endif
