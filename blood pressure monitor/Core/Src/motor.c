/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    motor.c
  * @brief   Stepper motor control (TMC2209 STEP/DIR) via TIM3_CH1 PWM stepping
  *
  *  原理：TMC2209 为 STEP/DIR 接口，无需相序表。
  *        TIM3_CH1 输出 50% 占空比 STEP 脉冲（微步 1/8 → 每整步 8 个脉冲），
  *        TIM3 更新中断计数 STEP 脉冲，到达目标自动停止（保持锁定位置）。
  *
  *  STEP 频率 = 整步频率 × 8（微步）。整步频 50-2000Hz → STEP 400-16000Hz。
  *
  *  安全：上电默认禁用（EN 拉高，电机自由）；Motor_StepN 参数校验；
  *        到步自停后保持相序锁定，由命令层 motor stop 释放。
  ******************************************************************************
  */
/* USER CODE END Header */
#include "motor.h"

TIM_HandleTypeDef htim3;

static volatile uint32_t s_motor_pulses_sent = 0U;
static volatile uint32_t s_motor_pulses_target = 0U;
static volatile uint8_t  s_motor_busy = 0U;
static volatile uint8_t  s_motor_dir_fwd = 1U;

/* 诊断：TIM3 更新中断进入次数（busy 期间），用于定位"电机不停"问题 */
volatile uint32_t g_motor_irq_count = 0U;

static void Motor_Tim3Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    TIM_OC_InitTypeDef sConfigOC = {0};

    __HAL_RCC_TIM3_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_AFIO_CLK_ENABLE();

    /* STEP = PA6：TIM3_CH1 复用推挽输出（AF），初始无脉冲（低） */
    GPIO_InitStruct.Pin   = MOTOR_STEP_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(MOTOR_STEP_PORT, &GPIO_InitStruct);

    /* DIR = PA7：GPIO 推挽输出，初始前进 */
    GPIO_InitStruct.Pin   = MOTOR_DIR_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(MOTOR_DIR_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(MOTOR_DIR_PORT, MOTOR_DIR_PIN, GPIO_PIN_SET);

    /* EN = PB0：GPIO 推挽输出，初始拉高（TMC2209 ENN 低=使能，高=禁用） */
    GPIO_InitStruct.Pin   = MOTOR_EN_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(MOTOR_EN_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(MOTOR_EN_PORT, MOTOR_EN_PIN, GPIO_PIN_SET);   /* 默认禁用 */

    /* TIM3：1MHz 计数时钟，ARR 由 Motor_StepN 按频率设置；PWM1 50% 占空比 */
    htim3.Instance               = TIM3;
    htim3.Init.Prescaler         = MOTOR_TIM_PRESCALER;
    htim3.Init.CounterMode       = TIM_COUNTERMODE_UP;
    htim3.Init.Period            = 0xFFFFU;   /* 占位，StepN 覆盖 */
    htim3.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
    {
        Error_Handler();
    }

    sConfigOC.OCMode     = TIM_OCMODE_PWM1;
    sConfigOC.Pulse      = 0U;   /* 占位，StepN 设为 ARR/2（50%） */
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
    {
        Error_Handler();
    }

    HAL_NVIC_SetPriority(TIM3_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(TIM3_IRQn);
}

void Motor_Init(void)
{
    Motor_Tim3Init();
    Motor_Enable(0U);          /* 上电禁用，防意外转动 */
    Motor_SetDir(MOTOR_DIR_FWD);
    s_motor_busy = 0U;
    s_motor_pulses_sent = 0U;
    s_motor_pulses_target = 0U;
}

void Motor_SetDir(uint8_t fwd)
{
    s_motor_dir_fwd = (fwd != 0U) ? 1U : 0U;
    HAL_GPIO_WritePin(MOTOR_DIR_PORT, MOTOR_DIR_PIN,
                      s_motor_dir_fwd ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

void Motor_Enable(uint8_t en)
{
    /* TMC2209 ENN：低=使能，高=禁用（释放电机） */
    HAL_GPIO_WritePin(MOTOR_EN_PORT, MOTOR_EN_PIN,
                      (en != 0U) ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

uint8_t Motor_IsBusy(void)
{
    return s_motor_busy;
}

uint8_t Motor_StepN(uint8_t dir, uint32_t steps, uint32_t freq_hz)
{
    uint32_t step_freq;      /* STEP 脉冲频率 = 整步频 × 微步 */
    uint32_t arr;
    TIM_OC_InitTypeDef sConfigOC = {0};

    if (s_motor_busy != 0U) { return 1U; }                       /* busy */
    if ((steps == 0U) || (steps > 1000000U)) { return 2U; }     /* bad steps */
    if ((freq_hz < MOTOR_FREQ_HZ_MIN) || (freq_hz > MOTOR_FREQ_HZ_MAX)) { return 3U; }

    step_freq = freq_hz * MOTOR_MICROSTEPS;
    if (step_freq > (MOTOR_TIM_CNT_HZ / 2U)) { return 3U; }     /* 超过 500kHz 限制 */

    arr = (MOTOR_TIM_CNT_HZ / step_freq) - 1U;
    __HAL_TIM_SET_AUTORELOAD(&htim3, arr);

    /* PWM 50% 占空比：CCR = ARR/2 */
    sConfigOC.OCMode     = TIM_OCMODE_PWM1;
    sConfigOC.Pulse      = arr / 2U;
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1);

    Motor_SetDir(dir);
    Motor_Enable(1U);

    s_motor_pulses_sent = 0U;
    s_motor_pulses_target = steps * MOTOR_MICROSTEPS;
    s_motor_busy = 1U;

    if (HAL_TIM_PWM_Start_IT(&htim3, TIM_CHANNEL_1) != HAL_OK)
    {
        s_motor_busy = 0U;
        Motor_Enable(0U);
        return 4U;                                               /* hw start fail */
    }
    /* 修复：某些 HAL 库版本的 HAL_TIM_PWM_Start_IT 只使能 CC1IE、
     * 不使能更新中断（DIER 实测 0x0002），导致自停计数中断永不触发。
     * 显式使能更新中断（UIE），SR.UIF 已证明更新事件在持续发生。 */
    __HAL_TIM_ENABLE_IT(&htim3, TIM_IT_UPDATE);
    return 0U;
}

void Motor_Stop(void)
{
    if (s_motor_busy != 0U)
    {
        HAL_TIM_PWM_Stop_IT(&htim3, TIM_CHANNEL_1);
        s_motor_busy = 0U;
    }
    Motor_Enable(0U);          /* 禁用电机（EN 拉高） */
    HAL_GPIO_WritePin(MOTOR_STEP_PORT, MOTOR_STEP_PIN, GPIO_PIN_RESET);  /* STEP 回低 */
}

/**
  * @brief  TIM3 更新中断回调：每 1 个 STEP 脉冲计数一次，到达目标自停
  *         （到步后保持当前相序锁定，不释放；由命令层 motor stop 释放）
  */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance != TIM3) { return; }
    if (s_motor_busy == 0U) { return; }

    g_motor_irq_count++;
    s_motor_pulses_sent++;
    if (s_motor_pulses_sent >= s_motor_pulses_target)
    {
        HAL_TIM_PWM_Stop_IT(&htim3, TIM_CHANNEL_1);   /* 停 PWM，保持锁定 */
        s_motor_busy = 0U;
        HAL_GPIO_WritePin(MOTOR_STEP_PORT, MOTOR_STEP_PIN, GPIO_PIN_RESET);
    }
}
