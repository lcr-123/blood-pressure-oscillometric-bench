/* Minimal HAL for compiling the actual gpio.c and main.h without hardware. */
#ifndef GPIO_HAL_STUB_H
#define GPIO_HAL_STUB_H
#include <stdint.h>
typedef struct { uint32_t Pin, Mode, Pull, Speed; } GPIO_InitTypeDef;
typedef enum { GPIO_PIN_RESET, GPIO_PIN_SET } GPIO_PinState;
#define GPIOA 0
#define GPIOB 1
#define GPIOC 2
#define GPIO_PIN_0 (1U << 0)
#define GPIO_PIN_1 (1U << 1)
#define GPIO_PIN_3 (1U << 3)
#define GPIO_PIN_4 (1U << 4)
#define GPIO_PIN_5 (1U << 5)
#define GPIO_PIN_8 (1U << 8)
#define GPIO_MODE_OUTPUT_OD 1U
#define GPIO_MODE_OUTPUT_PP 2U
#define GPIO_MODE_INPUT 3U
#define GPIO_MODE_IT_RISING_FALLING 4U
#define GPIO_NOPULL 0U
#define GPIO_PULLUP 1U
#define GPIO_SPEED_FREQ_LOW 0U
#define EXTI9_5_IRQn 23
#define __HAL_RCC_GPIOA_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOB_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOC_CLK_ENABLE() ((void)0)
#define __HAL_RCC_AFIO_CLK_ENABLE() ((void)0)
void HAL_GPIO_WritePin(int port, uint32_t pin, GPIO_PinState state);
void HAL_GPIO_Init(int port, GPIO_InitTypeDef *config);
void HAL_NVIC_SetPriority(int irq, int preempt, int sub);
void HAL_NVIC_EnableIRQ(int irq);
#endif
