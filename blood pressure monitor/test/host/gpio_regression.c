/* Exercise production GPIO init/macros: PB8 and PC8 must stay independent. */
#include "gpio.h"
#include <assert.h>
#include <stdio.h>
static uint32_t levels[3], configured[3], valve_init_count;

void HAL_GPIO_WritePin(int port, uint32_t pin, GPIO_PinState state)
{
    assert(port >= GPIOA && port <= GPIOC);
    if (state == GPIO_PIN_SET) levels[port] |= pin;
    else levels[port] &= ~pin;
}

void HAL_GPIO_Init(int port, GPIO_InitTypeDef *config)
{
    configured[port] |= config->Pin;
    if (port == GPIOB && (config->Pin & GPIO_PIN_8))
    {
        /* The first output transition must release, never energize the relay. */
        assert(levels[GPIOB] & GPIO_PIN_8);
        assert(config->Pin == GPIO_PIN_8);
        assert(config->Mode == GPIO_MODE_OUTPUT_OD);
        assert(config->Pull == GPIO_NOPULL);
        valve_init_count++;
    }
    if (port == GPIOC)
    {
        assert(!(config->Pin & GPIO_PIN_0));
        assert(config->Mode == GPIO_MODE_OUTPUT_PP);
    }
}
void HAL_NVIC_SetPriority(int irq, int preempt, int sub)
{ (void)irq; (void)preempt; (void)sub; }
void HAL_NVIC_EnableIRQ(int irq) { (void)irq; }

int main(void)
{
    MX_GPIO_Init();
    assert(VALVE1_CTRL_Port == GPIOB && VALVE1_CTRL_Pin == GPIO_PIN_8);
    assert(valve_init_count == 1U);
    assert(!(configured[GPIOC] & GPIO_PIN_0));
    assert(!(levels[GPIOC] & GPIO_PIN_1));
    assert(levels[GPIOC] & GPIO_PIN_8);
    VALVE1_OPEN();
    assert(!(levels[GPIOB] & GPIO_PIN_8));
    assert(levels[GPIOC] & GPIO_PIN_8); /* opening the valve cannot start pump */
    VALVE1_CLOSE();
    assert(levels[GPIOB] & GPIO_PIN_8);
    VALVE2_OPEN();
    assert(levels[GPIOC] & GPIO_PIN_1);
    assert(levels[GPIOB] & GPIO_PIN_8);
    VALVE2_CLOSE();
    assert(!(levels[GPIOC] & GPIO_PIN_1));
    puts("PASS actual PB8 open-drain init and valve macros");
    return 0;
}
