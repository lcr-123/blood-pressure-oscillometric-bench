#ifndef BP_HOST_MAIN_H
#define BP_HOST_MAIN_H
#include <stdint.h>
#include <stddef.h>
typedef enum { HAL_OK, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;
typedef struct { uint32_t SR1, SR2, CR1; } I2C_TypeDef;
typedef struct { uint32_t IDR; } GPIO_TypeDef;
extern GPIO_TypeDef host_gpiob;
#define GPIOB (&host_gpiob)
typedef struct { I2C_TypeDef *Instance; uint32_t ErrorCode, State; } I2C_HandleTypeDef;
extern I2C_TypeDef host_i2c1;
#define I2C1 (&host_i2c1)
uint32_t HAL_GetTick(void);
void HAL_Delay(uint32_t delay);
HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *, uint16_t, uint8_t *, uint16_t, uint32_t);
HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *, uint16_t, uint8_t *, uint16_t, uint32_t);
HAL_StatusTypeDef HAL_I2C_IsDeviceReady(I2C_HandleTypeDef *, uint16_t, uint32_t, uint32_t);
HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *);
HAL_StatusTypeDef HAL_I2C_DeInit(I2C_HandleTypeDef *);
uint32_t HAL_I2C_GetError(I2C_HandleTypeDef *);
uint32_t HAL_I2C_GetState(I2C_HandleTypeDef *);
void host_reset_bus(uint8_t asserted);
#define __HAL_RCC_I2C1_FORCE_RESET() host_reset_bus(1U)
#define __HAL_RCC_I2C1_RELEASE_RESET() host_reset_bus(0U)
void host_actuator(uint8_t pin, uint8_t level);
#define PUMP_STOP() host_actuator(8U, 1U)
#define PUMP_START() host_actuator(8U, 0U)
#define PUMP_SET_DUTY(duty) ((void)(duty))
#define VALVE1_CLOSE() host_actuator(0U, 1U)
#define VALVE1_OPEN() host_actuator(0U, 0U)
#define VALVE2_CLOSE() host_actuator(1U, 0U)
#define VALVE2_OPEN() host_actuator(1U, 1U)
#endif
