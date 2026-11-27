/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    motor.h
  * @brief   Stepper motor control (TMC2209 STEP/DIR driver) for syringe pump
  *
  *  用途：注射器泵（42 步进电机丝杆滑台 + 20ml 针管）
  *    - 用途 B：体积法多点校准（注入已知 ΔV → 已知 ΔP）
  *    - 用途 A：示波法脉搏模拟器（运动曲线生成，后续扩展）
  *
  *  驱动：TMC2209 步进驱动模块（STEP/DIR 接口，国产紫板）
  *    微步 1/8（MS1=MS2=Low）：1 个 STEP 脉冲 = 1/8 整步 = 0.225°
  *    固件命令语义保持「整步」：内部每个整步发 8 个 STEP 脉冲
  *    STEP = TIM3_CH1 PWM 脉冲（PA6）；DIR = PA7（高=前进）；EN = PB0（低=使能）
  *
  *  引脚映射：
  *    STEP = PA6（TIM3_CH1）  DIR = PA7  EN = PB0
  *
  *  命令：motor <dir 0/1> <steps> <freq 50-2000Hz> | motor stop
  *    steps = 整步数（1 整步 = 1.8° = 丝杆 0.01mm）
  *    freq  = 整步频率（内部 STEP 脉冲 = 8×freq）
  ******************************************************************************
  */
/* USER CODE END Header */
#ifndef __MOTOR_H__
#define __MOTOR_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

#define MOTOR_STEP_PIN        GPIO_PIN_6
#define MOTOR_STEP_PORT       GPIOA
#define MOTOR_DIR_PIN         GPIO_PIN_7
#define MOTOR_DIR_PORT        GPIOA
#define MOTOR_EN_PIN          GPIO_PIN_0
#define MOTOR_EN_PORT         GPIOB

#define MOTOR_DIR_FWD         1U   /* 前进（针管活塞注入） */
#define MOTOR_DIR_REV         0U   /* 后退（回抽） */

#define MOTOR_FREQ_HZ_MIN     50U
#define MOTOR_FREQ_HZ_MAX     2000U

/* 微步 1/8：每整步 8 个 STEP 脉冲 */
#define MOTOR_MICROSTEPS      8U

/* TIM3 定时器时钟 = APB1 36MHz x 2 = 72MHz；预分频 72 → 计数时钟 1MHz
 * （ARR 16 位最大 65535 → 最低 STEP 频率 ≈15Hz；整步频 50-2000Hz
 *   ×8 微步 = STEP 400-16000Hz，50% 占空比 PWM 输出） */
#define MOTOR_TIM_CLK_HZ      72000000U
#define MOTOR_TIM_PRESCALER   71U   /* ÷72 → 1MHz */
#define MOTOR_TIM_CNT_HZ      (MOTOR_TIM_CLK_HZ / (MOTOR_TIM_PRESCALER + 1U))

extern TIM_HandleTypeDef htim3;
extern volatile uint32_t g_motor_irq_count;   /* 诊断：TIM3 更新中断进入次数 */

void  Motor_Init(void);
void  Motor_SetDir(uint8_t fwd);
void  Motor_Enable(uint8_t en);          /* 1=使能(EN拉低), 0=禁用(EN拉高, 电机自由) */
uint8_t Motor_IsBusy(void);
uint8_t Motor_StepN(uint8_t dir, uint32_t steps, uint32_t freq_hz);
void  Motor_Stop(void);

#ifdef __cplusplus
}
#endif
#endif /* __MOTOR_H__ */
