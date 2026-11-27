#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define HAL_OK 0U
#define HAL_ERROR 1U
#define GPIO_PIN_RESET 0U
#define GPIO_PIN_SET 1U
#define PUMP_RELAY_Port 0U
#define PUMP_RELAY_Pin 0U
#define VALVE1_CTRL_Port 1U
#define VALVE1_CTRL_Pin 0U
#define VALVE2_CTRL_Port 2U
#define VALVE2_CTRL_Pin 0U
static uint8_t active, s_calculation_pending;
static unsigned pins[3], hi2c1, scans;
static char output[512];
static uint8_t CaptureAcquisition_IsActive(void) { return active; }
static unsigned HAL_GPIO_ReadPin(unsigned port, unsigned pin)
{ (void)pin; return pins[port]; }
static void Debug_UART_Write(const char *text) { strcat(output, text); }
static unsigned HAL_I2C_IsDeviceReady(unsigned *i2c, uint16_t address,
                                      uint32_t trials, uint32_t timeout)
{
    assert(i2c == &hi2c1);
    assert(address == (0x40U + scans) * 2U);
    assert(trials == 3U && timeout == 20U);
    scans++;
    return address == (0x48U << 1U) ? HAL_OK : HAL_ERROR;
}
#include "i2c_scan_under_test.h"
int main(void)
{
    unsigned gate;
    for (gate = 0U; gate < 6U; gate++)
    {
        pins[0] = pins[1] = GPIO_PIN_SET;
        pins[2] = GPIO_PIN_RESET;
        active = s_calculation_pending = 0U;
        scans = 0U;
        output[0] = '\0';
        if (gate == 1U) active = 1U;
        if (gate == 2U) s_calculation_pending = 1U;
        if (gate == 3U) pins[0] = GPIO_PIN_RESET;
        if (gate == 4U) pins[1] = GPIO_PIN_RESET;
        if (gate == 5U) pins[2] = GPIO_PIN_SET;
        Debug_I2CScan();
        if (gate == 0U)
        {
            assert(scans == 16U);
            assert(strstr(output, "found device at 0x48"));
            assert(strstr(output, "scan done"));
        }
        else
        {
            assert(scans == 0U);
            assert(strstr(output, "scan blocked"));
        }
    }
    puts("PASS actual I2C scan shifted address and inactive actuator gate");
    return 0;
}
