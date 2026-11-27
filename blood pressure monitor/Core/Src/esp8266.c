/**
  ******************************************************************************
  * @file    esp8266.c
  * @brief   ESP8266 WiFi driver (AT command mode, USART1)
  ******************************************************************************
  */
#include "esp8266.h"
#include <string.h>
#include <stdio.h>

static UART_HandleTypeDef *s_huart = NULL;
static ESP8266_State_t     s_state = ESP_STATE_IDLE;

static uint8_t s_rx_byte;                      /* 单字节 DMA/IT 接收 */
static uint8_t s_rx_buf[ESP_RX_BUF_SIZE];
static uint16_t s_rx_idx = 0;

/* =========================================================================
   Init
   ========================================================================= */
void ESP8266_Init(UART_HandleTypeDef *huart)
{
    s_huart = huart;
    s_state = ESP_STATE_IDLE;
    s_rx_idx = 0;
    memset(s_rx_buf, 0, sizeof(s_rx_buf));

    /* 启动 UART 中断接收（单字节） */
    HAL_UART_Receive_IT(s_huart, &s_rx_byte, 1);

    /* 复位 ESP8266 */
    ESP_RESET();
    HAL_Delay(500);

    /* 基础 AT 测试 */
    if (ESP8266_SendAT("AT", "OK", ESP_CMD_TIMEOUT_MS) == HAL_OK)
    {
        printf("[ESP8266] AT OK\r\n");
        ESP8266_SendAT("ATE0", "OK", 1000);       /* 关闭回显 */
        ESP8266_SendAT("AT+CWMODE=1", "OK", 1000);/* Station mode */
    }
    else
    {
        printf("[ESP8266] Init FAILED - check USART1 wiring\r\n");
        s_state = ESP_STATE_ERROR;
    }
}

/* =========================================================================
   Main task (called in while(1))
   ========================================================================= */
void ESP8266_Task(void)
{
    /* 目前为轮询驱动，后续可扩展为状态机自动重连 */
}

/* =========================================================================
   UART RxCplt callback (byte-by-byte accumulation)
   ========================================================================= */
void ESP8266_RxCallback(void)
{
    if (s_rx_idx < ESP_RX_BUF_SIZE - 1)
    {
        s_rx_buf[s_rx_idx++] = s_rx_byte;
        s_rx_buf[s_rx_idx]   = '\0';
    }
    /* 继续接收下一字节 */
    HAL_UART_Receive_IT(s_huart, &s_rx_byte, 1);
}

/* =========================================================================
   Send AT command and wait for expected response
   ========================================================================= */
HAL_StatusTypeDef ESP8266_SendAT(const char *cmd, const char *expected, uint32_t timeout_ms)
{
    uint8_t tx_buf[ESP_TX_BUF_SIZE];
    uint16_t len = (uint16_t)snprintf((char *)tx_buf, sizeof(tx_buf), "%s\r\n", cmd);

    /* 清空接收缓冲 */
    s_rx_idx = 0;
    memset(s_rx_buf, 0, sizeof(s_rx_buf));

    HAL_UART_Transmit(s_huart, tx_buf, len, 500);

    uint32_t t_start = HAL_GetTick();
    while ((HAL_GetTick() - t_start) < timeout_ms)
    {
        if (strstr((char *)s_rx_buf, expected) != NULL)
            return HAL_OK;
        HAL_Delay(10);
    }
    return HAL_TIMEOUT;
}

/* =========================================================================
   Connect to WiFi AP
   ========================================================================= */
HAL_StatusTypeDef ESP8266_ConnectWiFi(const char *ssid, const char *password)
{
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "AT+CWJAP=\"%s\",\"%s\"", ssid, password);
    s_state = ESP_STATE_CONNECTING;

    HAL_StatusTypeDef ret = ESP8266_SendAT(cmd, "WIFI CONNECTED", 15000);
    if (ret == HAL_OK)
    {
        s_state = ESP_STATE_CONNECTED;
        printf("[ESP8266] WiFi connected to %s\r\n", ssid);
    }
    else
    {
        s_state = ESP_STATE_ERROR;
        printf("[ESP8266] WiFi connect FAILED\r\n");
    }
    return ret;
}

/* =========================================================================
   Upload BP result to server (HTTP GET, simple implementation)
   ========================================================================= */
void ESP8266_UploadResult(uint8_t systolic, uint8_t diastolic, uint8_t pulse)
{
    if (s_state != ESP_STATE_CONNECTED)
    {
        printf("[ESP8266] Not connected, skip upload\r\n");
        return;
    }
    char payload[128];
    snprintf(payload, sizeof(payload),
             "GET /bp?sbp=%d&dbp=%d&pulse=%d HTTP/1.0\r\nHost: server\r\n\r\n",
             systolic, diastolic, pulse);
    /* TODO: 填写实际服务器地址和端口 */
    printf("[ESP8266] Upload: SBP=%d DBP=%d Pulse=%d\r\n",
           systolic, diastolic, pulse);
}

ESP8266_State_t ESP8266_GetState(void)
{
    return s_state;
}
