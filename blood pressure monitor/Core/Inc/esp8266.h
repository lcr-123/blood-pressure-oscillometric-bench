/**
  ******************************************************************************
  * @file    esp8266.h
  * @brief   ESP8266 WiFi module driver (AT command over USART1)
  ******************************************************************************
  */
#ifndef __ESP8266_H
#define __ESP8266_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "usart.h"

#define ESP_RX_BUF_SIZE     256
#define ESP_TX_BUF_SIZE     256
#define ESP_CMD_TIMEOUT_MS  3000

typedef enum {
    ESP_STATE_IDLE = 0,
    ESP_STATE_CONNECTING,
    ESP_STATE_CONNECTED,
    ESP_STATE_SENDING,
    ESP_STATE_ERROR
} ESP8266_State_t;

/* Public API */
void ESP8266_Init(UART_HandleTypeDef *huart);
void ESP8266_Task(void);
void ESP8266_RxCallback(void);
HAL_StatusTypeDef ESP8266_SendAT(const char *cmd, const char *expected, uint32_t timeout_ms);
HAL_StatusTypeDef ESP8266_ConnectWiFi(const char *ssid, const char *password);
HAL_StatusTypeDef ESP8266_SendData(const char *server, uint16_t port,
                                    const char *payload);
ESP8266_State_t   ESP8266_GetState(void);
void ESP8266_UploadResult(uint8_t systolic, uint8_t diastolic, uint8_t pulse);

#ifdef __cplusplus
}
#endif
#endif /* __ESP8266_H */
