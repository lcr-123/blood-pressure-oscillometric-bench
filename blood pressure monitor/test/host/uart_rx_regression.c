/* Actual vendor RX/error code + production parser/callbacks, no device I/O. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef enum { HAL_OK, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;
typedef struct { uint32_t SR, DR, CR1, CR3; } USART_TypeDef;
typedef struct DMA_Handle DMA_HandleTypeDef;
struct DMA_Handle { void (*XferAbortCallback)(DMA_HandleTypeDef *); };
typedef struct {
    USART_TypeDef *Instance;
    struct { uint32_t WordLength, Parity; } Init;
    uint8_t *pRxBuffPtr;
    uint16_t RxXferSize, RxXferCount;
    uint32_t ErrorCode, RxState, RxEventType, ReceptionType;
    DMA_HandleTypeDef *hdmarx;
} UART_HandleTypeDef;
#define RESET 0U
#define USART_SR_PE 1U
#define USART_SR_FE 2U
#define USART_SR_NE 4U
#define USART_SR_ORE 8U
#define USART_SR_RXNE 32U
#define USART_SR_IDLE 16U
#define USART_CR1_RXNEIE 32U
#define USART_CR1_PEIE 256U
#define USART_CR1_IDLEIE 16U
#define USART_CR3_EIE 1U
#define USART_CR3_DMAR 64U
#define HAL_UART_ERROR_NONE 0U
#define HAL_UART_ERROR_PE 1U
#define HAL_UART_ERROR_NE 2U
#define HAL_UART_ERROR_FE 4U
#define HAL_UART_ERROR_ORE 8U
#define HAL_UART_STATE_READY 0U
#define HAL_UART_STATE_BUSY_RX 1U
#define UART_WORDLENGTH_9B 9U
#define UART_WORDLENGTH_8B 8U
#define UART_PARITY_NONE 0U
#define HAL_UART_RXEVENT_TC 0U
#define HAL_UART_RECEPTION_STANDARD 0U
#define HAL_UART_RECEPTION_TOIDLE 1U
#define UART_FLAG_IDLE USART_SR_IDLE
#define UART_IT_RXNE USART_CR1_RXNEIE
#define UART_IT_PE USART_CR1_PEIE
#define UART_IT_ERR 0x10000U
#define READ_REG(v) (v)
#define HAL_IS_BIT_SET(v,b) (((v) & (b)) != 0U)
#define ATOMIC_CLEAR_BIT(v,b) ((v) &= ~(b))
#define __HAL_UART_DISABLE_IT(h,b) uart_it((h),(b),0)
#define __HAL_UART_ENABLE_IT(h,b) uart_it((h),(b),1)
#define __HAL_UART_CLEAR_OREFLAG(h) clear_flags(h)
#define __HAL_UART_CLEAR_IDLEFLAG(h) clear_flags(h)
#define __HAL_UART_GET_FLAG(h,b) ((h)->Instance->SR & (b))

static USART_TypeDef uart1, uart2, uart3;
#define USART1 (&uart1)
#define USART2 (&uart2)
#define USART3 (&uart3)
static UART_HandleTypeDef huart3;
static uint32_t primask, esp_calls, flag_clears;
static void __disable_irq(void) { primask = 1U; }
static uint32_t __get_PRIMASK(void) { return primask; }
static void __set_PRIMASK(uint32_t value) { primask = value; }
static void uart_it(UART_HandleTypeDef *h, uint32_t bit, int enable)
{
    uint32_t *reg = bit == UART_IT_ERR ? &h->Instance->CR3 : &h->Instance->CR1;
    bit = bit == UART_IT_ERR ? USART_CR3_EIE : bit;
    if (enable) *reg |= bit; else *reg &= ~bit;
}
static void clear_flags(UART_HandleTypeDef *h)
{
    /* Model the F1 SR then DR read side effect; plain host RAM cannot do it. */
    h->Instance->SR = 0U;
    flag_clears++;
}
static void ESP8266_RxCallback(void) { esp_calls++; }
static HAL_StatusTypeDef HAL_DMA_Abort_IT(DMA_HandleTypeDef *h)
{ (void)h; assert(0); return HAL_ERROR; }
static void UART_DMAAbortOnError(DMA_HandleTypeDef *h) { (void)h; assert(0); }
static void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *h, uint16_t n)
{ (void)h; (void)n; assert(0); }
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *h);
void HAL_UART_ErrorCallback(UART_HandleTypeDef *h);
static HAL_StatusTypeDef UART_Receive_IT(UART_HandleTypeDef *h);
#include "uart_vendor_under_test.h"
#include "uart_main_under_test.h"

static void reset(void)
{
    memset(&uart3, 0, sizeof(uart3));
    memset(&huart3, 0, sizeof(huart3));
    huart3.Instance = USART3;
    huart3.Init.WordLength = UART_WORDLENGTH_8B;
    memset(s_debug_cmd_buffer, 0, sizeof(s_debug_cmd_buffer));
    s_debug_cmd_len = 0U;
    s_pending_debug_cmd = DEBUG_CMD_NONE;
    s_debug_cmd_discard = 0U;
    s_debug_urgent_match = 0U;
    s_uart3_rx_errors = 0U;
    primask = esp_calls = flag_clears = 0U;
    Debug_UART_StartRxInterrupt();
}
static void byte(uint8_t value, uint32_t error, int rxne)
{
    uart3.DR = value;
    uart3.SR = error | (rxne ? USART_SR_RXNE : 0U);
    HAL_UART_IRQHandler(&huart3);
    /* Model flags cleared by the vendor SR/DR reads. */
    uart3.SR = 0U;
}
static void line(const char *text)
{
    while (*text) byte((uint8_t)*text++, 0U, 1);
}
static void ready(void)
{
    assert(huart3.RxState == HAL_UART_STATE_BUSY_RX);
    assert(uart3.CR1 & USART_CR1_RXNEIE);
    assert(uart3.CR3 & USART_CR3_EIE);
}
int main(void)
{
    uint32_t error;
    UART_HandleTypeDef other = {0};
    char snapshot[DEBUG_CMD_BUFFER_LEN];
    reset();
    byte(0U, USART_SR_ORE, 0);
    ready(); /* Old firmware fails: ORE without RXNE permanently ends RX. */
    assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
    line("\nstatus\n");
    assert(s_pending_debug_cmd == DEBUG_CMD_STATUS);

    for (error = USART_SR_PE; error <= USART_SR_ORE; error <<= 1U)
    {
        reset();
        /* Parity bit is enabled only here to exercise PE on a host. */
        line("start");
        uart3.CR1 |= USART_CR1_PEIE;
        byte('\n', error, 1);
        ready();
        assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
        line("open\n"); /* Unsynchronized tail must not start inflation. */
        assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
        line("stop\n");
        assert(s_pending_debug_cmd == DEBUG_CMD_STOP);
    }
    reset();
    line("target 30\ncal write 999 -999\n");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_TARGET);
    assert(strcmp(snapshot, "target 30") == 0);
    line("target 40\nstop\nstart\n");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_STOP);
    line("target 40\nvent\nseal\n");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_VALVE2_OPEN);
    /* A partial busy line cannot become a command after the mailbox is taken. */
    line("status\nst");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_STATUS);
    line("art\n");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_NONE);
    line("status\n");
    primask = 1U;
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_STATUS);
    assert(primask == 1U);
    primask = 0U;
    line("!start\n");
    assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
    line("target 30 00000000000000000000000000000000000000000000000000\n");
    assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
    line("status\n");
    assert(Debug_CommandTake(snapshot) == DEBUG_CMD_STATUS);
    /* Error without RXNE, pending command and repeated errors are bounded. */
    line("start\n");
    byte(0U, USART_SR_NE | USART_SR_FE | USART_SR_ORE, 0);
    assert(s_pending_debug_cmd == DEBUG_CMD_NONE);
    ready();
    s_uart3_rx_errors = UINT16_MAX;
    byte(0U, USART_SR_ORE, 0);
    assert(s_uart3_rx_errors == UINT16_MAX);
    line("\nstop\n");
    byte(0U, USART_SR_ORE, 0);
    assert(s_pending_debug_cmd == DEBUG_CMD_STOP);
    /* Simulate an unexpectedly ended RX, and retry once from the main loop. */
    UART_EndRxTransfer(&huart3);
    primask = 1U;
    Debug_UART_RxTask();
    assert(primask == 1U);
    primask = 0U;
    ready();
    Debug_UART_RxTask(); /* BUSY receive untouched. */
    ready();
    other.Instance = USART2;
    HAL_UART_ErrorCallback(&other);
    assert(other.RxState == HAL_UART_STATE_READY);
    other.Instance = USART1;
    HAL_UART_RxCpltCallback(&other);
    assert(esp_calls == 1U);
    puts("PASS actual UART error recovery, command integrity and routing");
    return 0;
}
