/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Blood Pressure Monitor — Main Program
  *
  *  外设初始化顺序:
  *    1. HAL_Init()
  *    2. SystemClock_Config()  72MHz HSE PLL
  *    3. MX_GPIO_Init()
  *    4. MX_I2C1_Init()        ADS1115
  *    5. MX_USART1_UART_Init() ESP8266
  *    6. MX_USART2_UART_Init() MAX3232/RS232
  *    7. MX_USART3_UART_Init() CH340 Debug
  *    8. MX_TIM8_Init()        气泵 PWM
  *    9. 应用层初始化
  ******************************************************************************
  */
/* USER CODE END Header */
#include "main.h"

/* USER CODE BEGIN Includes */
#include "gpio.h"
#include "usart.h"
#include "i2c.h"
#include "tim.h"
#include "ads1115.h"
#include "bp_cal.h"
#include "bp_algorithm.h"
#include "bp_capture_export.h"
#include "esp8266.h"
#include "bp_control.h"
#include "bp_algorithm.h"
#include "motor.h"
#include "stack_watermark.h"
#include <string.h>
#include "iwdg.h"
/* USER CODE END Includes */

/* Private function prototypes */
void SystemClock_Config(void);

/* USER CODE BEGIN PV */
/* Global measurement result */
static BP_Result_t g_bp_result = {0};
static uint8_t s_ads1115_ready = 0U;

#define BUTTON_DEBOUNCE_MS    40U

#define DEBUG_CMD_BUFFER_LEN  48U
#define MANUAL_PUMP_TIMEOUT_MS      60000U
#define MANUAL_PRESSURE_SAMPLE_INTERVAL_MS  BP_SAMPLE_INTERVAL_MS
#define HOLD_OPEN_TIMEOUT_MS                15000U
#define BOOT_RESIDUAL_PRESSURE_MMHG         15.0f

#define PRESSURE_STREAM_INTERVAL_MS   50U
#define ADS1115_OFFLINE_RETRY_MS      1000U
#define BP_BRINGUP_RELAY_ONLY     1U
#define BP_BRINGUP_ENABLE_BUTTONS 0U
#define BP_BRINGUP_ENABLE_ESP8266  0U

#if BP_BRINGUP_ENABLE_BUTTONS
typedef struct {
    GPIO_TypeDef *port;
    uint16_t pin;
    GPIO_PinState stable_level;
    GPIO_PinState last_sample;
    uint32_t last_change_ms;
} ButtonDebounce_t;

static ButtonDebounce_t s_start_button = {
    BTN_START_GPIO_Port,
    BTN_START_Pin,
    GPIO_PIN_SET,
    GPIO_PIN_SET,
    0U
};

static ButtonDebounce_t s_stop_button = {
    BTN_STOP_GPIO_Port,
    BTN_STOP_Pin,
    GPIO_PIN_SET,
    GPIO_PIN_SET,
    0U
};
#endif

typedef enum {
    DEBUG_CMD_NONE = 0,
    DEBUG_CMD_START,
    DEBUG_CMD_STOP,
    DEBUG_CMD_VALVE1_OPEN,
    DEBUG_CMD_VALVE1_CLOSE,
    DEBUG_CMD_VALVE2_OPEN,
    DEBUG_CMD_VALVE2_CLOSE,
    DEBUG_CMD_HOLD_OPEN,
    DEBUG_CMD_DEFLATE_PWM,
    DEBUG_CMD_DEFLATE_TEST,
    DEBUG_CMD_PRESSURE,
    DEBUG_CMD_HELP,
    DEBUG_CMD_VERSION,
    DEBUG_CMD_STATUS,
    DEBUG_CMD_PINS,
    DEBUG_CMD_FAULT,
    DEBUG_CMD_STREAM_START,
    DEBUG_CMD_STREAM_STOP,
    DEBUG_CMD_CAL,
    DEBUG_CMD_CAL_CLEAR,
    DEBUG_CMD_CAL_WRITE,
    DEBUG_CMD_PUMP_ON,
    DEBUG_CMD_TARGET,
    DEBUG_CMD_MOTOR,
    DEBUG_CMD_MOTOR_STOP,
    DEBUG_CMD_I2C_SCAN,
    DEBUG_CMD_CAPTURE_EXPORT,
    DEBUG_CMD_ZERO_PULSE,
    DEBUG_CMD_LOADED_PULSE,
    DEBUG_CMD_LOADED_PULSE_1,
    DEBUG_CMD_LOADED_PULSE_2,
    DEBUG_CMD_LOADED_PULSE_3,
    DEBUG_CMD_LOADED_PULSE_4,
    DEBUG_CMD_STACK,
    DEBUG_CMD_READ_TEST,
    DEBUG_CMD_PROFILE,
    DEBUG_CMD_PROFILE_NORMAL,
    DEBUG_CMD_PROFILE_PEAK,
    DEBUG_CMD_UNKNOWN
} DebugCommand_t;

static char s_debug_cmd_buffer[DEBUG_CMD_BUFFER_LEN];
static uint8_t s_debug_cmd_len = 0U;
static volatile DebugCommand_t s_pending_debug_cmd = DEBUG_CMD_NONE;
static uint8_t s_rx3_byte = 0U;   /* USART3 单字节中断接收缓冲（HAL_UART_Receive_IT 链） */
static uint8_t s_debug_cmd_discard = 0U;
static uint8_t s_debug_urgent_match = 0U;
static volatile uint16_t s_uart3_rx_errors = 0U;
static uint8_t s_manual_pump_active = 0U;
static uint32_t s_manual_pump_start_ms = 0U;
static uint32_t s_manual_pressure_last_ms = 0U;
static uint8_t s_hold_open_active = 0U;
static uint32_t s_hold_open_start_ms = 0U;
static uint8_t s_pressure_stream_enabled = 0U;
static uint8_t s_deflate_pwm_enabled = 0U;
static uint8_t s_deflate_test_active = 0U;
static uint32_t s_deflate_test_start_ms = 0U;
static uint8_t s_calculation_pending = 0U;
static float g_last_pressure_mmhg = 0.0f;
static ADS1115_Sample_t s_last_pressure_sample;
static uint8_t s_last_pressure_sample_valid = 0U;
static uint32_t s_last_pressure_sample_ms;
static uint32_t s_deflate_next_pulse_ms = 0U;
static volatile uint32_t s_deflate_pulse_remaining_ms = 0U;
/* Keep the 5 Hz valve fundamental above the pulse-analysis band.  SysTick owns
 * the short pulse end, so blocking ADS1115 reads cannot stretch a 2 ms pulse. */
#define DEFLATE_PWM_PERIOD_MS       200U
#define ZERO_PULSE_ON_MS              5U
#define ZERO_PULSE_DURATION_MS     5000U
#define ZERO_PULSE_ACTIVE             2U
#define LOADED_PULSE_ACTIVE           3U
#define LOADED_PULSE_BASELINE_MS   1000U
#define LOADED_PULSE_DURATION_MS   4000U
#define LOADED_PULSE_START_MIN_MMHG 40.0f
#define LOADED_PULSE_START_MAX_MMHG 80.0f
#define LOADED_PULSE_ABORT_MIN_MMHG 20.0f
#define LOADED_PULSE_ABORT_MAX_MMHG 85.0f
#define DEFLATE_TEST_DURATION_MS 10000U
#define DEFLATE_TEST_STOP_MMHG 45.0f
#define DEFLATE_TEST_MAX_ON_MS 4U
static uint8_t s_loaded_pulse_on_ms = ZERO_PULSE_ON_MS;
#define DEFLATE_PWM_BASE_ON_MS  1U   /* 真人手臂气阻小，2ms 放气太快(0.65s放完)；降到1ms */
#define DEFLATE_CONTROL_INTERVAL_MS 400U
#define DEFLATE_HIGH_TARGET_MMHG 200.0f
#define DEFLATE_NORMAL_SPEED_MMHG_S 2.0f
#define DEFLATE_HIGH_SPEED_MMHG_S 3.0f
#define DEFLATE_PEAK_LOW_MMHG 200.0f
#define DEFLATE_PEAK_HIGH_MMHG 245.0f
#define DEFLATE_PEAK_SPEED_MMHG_S 1.8f
static uint8_t s_peak_profile_enabled = 0U;
/* 放气开度上限 45→90ms（22.5%→45% 平均开度）：低压 bench 实测闭环只能到
 * 1.3-1.6 mmHg/s（MAX_ON=45 时），成人量程 160→5 @1.5 需 103s≈4100 样本，
 * 远超算法缓冲 2048（51.2s）→ 包络主体丢失。提升上限让闭环可达 3.0 mmHg/s
 * （160→5 ≈52s≈2080 样本，边缘可用；实际 160→70 即已覆盖 DBP 交叉）。 */
#define DEFLATE_PWM_MAX_ON_MS   90U
static uint32_t s_deflate_pwm_on_ms = DEFLATE_PWM_BASE_ON_MS;
static float s_deflate_last_pressure = 0.0f;
static uint32_t s_deflate_last_time_ms = 0U;
static uint32_t s_algo_sample_last_ms = 0U;
static uint32_t s_deflate_hold_until_ms = 0U;
#define DEFLATE_HOLD_MS  1000U
/* deflate 闭环速度平滑：单次 500ms 差含压力振荡，直接调节会导致 on_ms
 * 在稳态附近来回 ±1，阀开时间抖动激起振铃（2026-09-29 真人实测 deflate
 * 5-8s 第二波瞬态带通 11781-16151 vs 脉搏 2000-3000）。用一阶平滑估计。 */
static float s_deflate_speed_prev = 0.0f;
/* 充气目标压力（mmHg）。默认 50（低压 bench），用串口 target <mmHg> 可调，
 * 成人验证（120/80）设 160。超出 BP_MAX_PRESSURE_MMHG 触发超压保护。 */
static float s_inflate_target_mmhg = 50.0f;
static uint32_t s_pressure_stream_last_ms = 0U;
static uint32_t s_ads1115_last_attempt_ms = 0U;
/* Static, sealed-zero diagnostic: eight bytes, no capture-buffer ownership. */
#define READ_TEST_DURATION_MS 10000U
#define READ_TEST_MIN_SAMPLES 380U
static struct {
    uint32_t start_ms;
    uint16_t samples;
    uint8_t active;
} s_read_test;
/* Captured once at boot, before HAL_Init() can touch the flags: which reset
 * sources fired, and how long the previous session had been running. A mid-run
 * reset with no [Safety] line cannot be diagnosed afterwards otherwise, because
 * the firmware did not read RCC_CSR at all before this. */
static uint32_t s_reset_flags = 0U;
/* USER CODE END PV */

/* USER CODE BEGIN 0 */
/**
  * @brief  调试串口打印（重定向 printf 到 USART3/CH340）
  */
#include <stdio.h>
#ifdef __GNUC__
int __io_putchar(int ch)
{
    HAL_UART_Transmit(&huart3, (uint8_t *)&ch, 1, 100);
    return ch;
}
#else
/* Keil MDK: retarget fputc */
int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart3, (uint8_t *)&ch, 1, 100);
    return ch;
}
#endif

static void Debug_UART_Write(const char *text)
{
    HAL_UART_Transmit(&huart3, (uint8_t *)text, (uint16_t)strlen(text), 100);
}

static uint8_t Capture_UART_Write(const char *text)
{
    return (HAL_UART_Transmit(&huart3, (uint8_t *)text,
                             (uint16_t)strlen(text), 100U) == HAL_OK) ? 1U : 0U;
}

static uint8_t CaptureExport_IsSafe(void)
{
    BP_State_t state = BP_Control_GetState();
    return (s_read_test.active == 0U) &&
           (s_manual_pump_active == 0U) && (s_hold_open_active == 0U) &&
           (s_deflate_pwm_enabled == 0U) && (s_deflate_hold_until_ms == 0U) &&
           (s_calculation_pending == 0U) && (state != BP_STATE_INFLATE) &&
           (state != BP_STATE_DEFLATE) && (s_last_pressure_sample_valid != 0U) &&
           (BP_Cal_IsValid() != 0U) && (s_ads1115_ready != 0U) &&
           (s_pressure_stream_enabled != 0U) &&
           ((HAL_GetTick() - s_last_pressure_sample_ms) <= 250U) &&
           (s_last_pressure_sample.pressure_mmhg >= -5.0f) &&
           (s_last_pressure_sample.pressure_mmhg <= 5.0f) &&
           (HAL_GPIO_ReadPin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin) == GPIO_PIN_SET) &&
           (HAL_GPIO_ReadPin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin) == GPIO_PIN_RESET) &&
           (HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin) == GPIO_PIN_SET);
}

static uint8_t CaptureAcquisition_IsActive(void)
{
    BP_State_t state = BP_Control_GetState();
    return (s_read_test.active != 0U) ||
           (s_manual_pump_active != 0U) || (s_hold_open_active != 0U) ||
           (s_deflate_pwm_enabled != 0U) || (s_deflate_hold_until_ms != 0U) ||
           (state == BP_STATE_INFLATE) || (state == BP_STATE_DEFLATE);
}

static float DeflateTargetSpeed(void)
{
    if ((s_deflate_test_active == 0U) &&
        (s_inflate_target_mmhg >= DEFLATE_HIGH_TARGET_MMHG))
    {
        if ((s_peak_profile_enabled != 0U) &&
            (g_last_pressure_mmhg >= DEFLATE_PEAK_LOW_MMHG) &&
            (g_last_pressure_mmhg <= DEFLATE_PEAK_HIGH_MMHG))
            return DEFLATE_PEAK_SPEED_MMHG_S;
        return DEFLATE_HIGH_SPEED_MMHG_S;
    }
    return DEFLATE_NORMAL_SPEED_MMHG_S;
}

static uint8_t DeflateProfile_Set(uint8_t peak)
{
    if ((peak > 1U) || (CaptureExport_IsSafe() == 0U) ||
        (BP_CaptureExport_IsActive() != 0U) ||
        !(s_last_pressure_sample.pressure_mmhg >= -1.0f &&
          s_last_pressure_sample.pressure_mmhg <= 1.0f)) return 0U;
    s_peak_profile_enabled = peak;
    return 1U;
}

static void Debug_PrintDeflateProfile(void)
{
    char msg[144];
    snprintf(msg, sizeof(msg),
             "[Profile] mode=%s peak_window=%.0f-%.0fmmHg peak_speed=%.1fmmHg/s outside=%.1fmmHg/s high_target_only=1\r\n",
             (s_peak_profile_enabled != 0U) ? "peak" : "normal",
             (double)DEFLATE_PEAK_LOW_MMHG, (double)DEFLATE_PEAK_HIGH_MMHG,
             (double)DEFLATE_PEAK_SPEED_MMHG_S, (double)DEFLATE_HIGH_SPEED_MMHG_S);
    Debug_UART_Write(msg);
}

static uint8_t LoadedPulse_IsSafe(void)
{
    BP_State_t state = BP_Control_GetState();
    return (CaptureAcquisition_IsActive() == 0U) &&
           (s_calculation_pending == 0U) &&
           ((state == BP_STATE_IDLE) ||
            ((state == BP_STATE_EMERGENCY) &&
             (BP_Control_GetFault() == BP_FAULT_USER_STOP))) &&
           (s_last_pressure_sample_valid != 0U) &&
           (BP_Cal_IsValid() != 0U) && (s_ads1115_ready != 0U) &&
           (s_pressure_stream_enabled != 0U) &&
           ((HAL_GetTick() - s_last_pressure_sample_ms) <= 250U) &&
           (s_last_pressure_sample.pressure_mmhg >= LOADED_PULSE_START_MIN_MMHG) &&
           (s_last_pressure_sample.pressure_mmhg <= LOADED_PULSE_START_MAX_MMHG) &&
           (HAL_GPIO_ReadPin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin) == GPIO_PIN_SET) &&
           (HAL_GPIO_ReadPin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin) == GPIO_PIN_RESET) &&
           (HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin) == GPIO_PIN_SET);
}

static void DeflatePulse_Cancel(void)
{
    uint32_t primask = __get_PRIMASK();
    uint32_t remaining;

    __disable_irq();
    remaining = s_deflate_pulse_remaining_ms;
    s_deflate_pulse_remaining_ms = 0U;
    if (remaining != 0U)
    {
        VALVE2_CLOSE();
        BP_Algorithm_RecordValveClose(HAL_GetTick());
    }
    if (primask == 0U)
    {
        __enable_irq();
    }
}

static void DeflatePulse_Start(uint32_t on_ms)
{
    uint32_t primask;

    if (on_ms == 0U)
    {
        return;
    }

    primask = __get_PRIMASK();
    __disable_irq();
    VALVE2_OPEN();
    s_deflate_pulse_remaining_ms = on_ms;
    BP_Algorithm_RecordValvePulse(HAL_GetTick(), (uint8_t)on_ms);
    if (primask == 0U)
    {
        __enable_irq();
    }
}

static void BP_CalculationCancel(void)
{
    s_calculation_pending = 0U;
    BP_Algorithm_CancelCalculate();
    memset(&g_bp_result, 0, sizeof(g_bp_result));
}

static void DeflateControl_Cancel(void)
{
    s_read_test.active = 0U; /* cancellation has no success marker or UART delay */
    s_deflate_pwm_enabled = 0U;
    s_deflate_hold_until_ms = 0U;
    s_deflate_test_active = 0U;
    if ((s_hold_open_active == ZERO_PULSE_ACTIVE) ||
        (s_hold_open_active == LOADED_PULSE_ACTIVE)) s_hold_open_active = 0U;
    BP_CalculationCancel();
    DeflatePulse_Cancel();
}

void HAL_SYSTICK_Callback(void)
{
    if (s_deflate_pulse_remaining_ms > 0U)
    {
        s_deflate_pulse_remaining_ms--;
        if (s_deflate_pulse_remaining_ms == 0U)
        {
            VALVE2_CLOSE();
            BP_Algorithm_RecordValveClose(HAL_GetTick());
        }
    }
}

static void ManualPump_EmergencyStop(BP_Fault_t fault);

static void Debug_PrintADS1115Diagnostics(void)
{
    const ADS1115_Diagnostics_t *diag = ADS1115_GetDiagnostics();
    char msg[192];
    snprintf(msg, sizeof(msg),
             "[ADSdiag] stage=%u status=%u reg=0x%02X err=0x%08lX state=0x%lX sr1=0x%04lX sr2=0x%04lX errors=%lu recoveries=%lu\r\n",
             (unsigned)diag->stage, (unsigned)diag->status, (unsigned)diag->reg,
             (unsigned long)diag->hal_error, (unsigned long)diag->hal_state,
             (unsigned long)diag->sr1, (unsigned long)diag->sr2,
             (unsigned long)diag->error_count, (unsigned long)diag->recovery_count);
    Debug_UART_Write(msg);
    snprintf(msg, sizeof(msg),
             "[ADSbus] cr1=0x%04X pb=0x%04X scl=%u sda=%u\r\n",
             (unsigned)diag->cr1, (unsigned)diag->gpio_b_idr,
             (unsigned)((diag->gpio_b_idr >> 6) & 1U),
             (unsigned)((diag->gpio_b_idr >> 7) & 1U));
    Debug_UART_Write(msg);
}

static void Debug_PrintCapture(void)
{
    char msg[128];
    snprintf(msg, sizeof(msg), "[Capture] n=%u capacity=%u dropped=%lu duration=%lums interval=%ums\r\n",
             (unsigned)g_bp_debug.sample_count, (unsigned)BP_ALGO_MAX_SAMPLES,
             (unsigned long)g_bp_debug.dropped_samples,
             (unsigned long)g_bp_debug.duration_ms, (unsigned)BP_SAMPLE_INTERVAL_MS);
    Debug_UART_Write(msg);
}

static void Debug_PrintADS1115InitResult(uint8_t ready)
{
    char msg[64];

    if (ready != 0U)
    {
        snprintf(msg, sizeof(msg),
                 "[ADS1115] Init OK address=0x48 config=0x%04X\r\n",
                 ADS1115_GetConfig());
        Debug_UART_Write(msg);
    }
    else
    {
        Debug_UART_Write("[ADS1115] Init FAILED address=0x48\r\n");
        Debug_PrintADS1115Diagnostics();
    }
}

static void Debug_PrintPressureRecord(const ADS1115_Sample_t *sample)
{
    char msg[144];
    size_t length;
    int32_t ads_mv = (int32_t)(sample->ads_voltage_v * 1000.0f + 0.5f);
    int32_t sensor_mv = (int32_t)(sample->sensor_voltage_v * 1000.0f + 0.5f);
    int32_t pressure_x10 = (int32_t)(sample->pressure_mmhg * 10.0f + 0.5f);

    snprintf(msg, sizeof(msg),
             "[Pressure] raw=%d ads=%ldmV sensor=%ldmV est=%ld.%01ldmmHg %s\r\n",
             sample->raw,
             (long)ads_mv,
             (long)sensor_mv,
             (long)(pressure_x10 / 10L),
             (long)(pressure_x10 % 10L),
             BP_Control_IsCalibrationValid() ? "VALID" : "UNCAL");
    /* Avoid exact 64-byte USB-serial records; preserve fields and CRLF.
       This is a transport compatibility workaround, not a timing guarantee. */
    length = strlen(msg);
    if ((length >= 2U) && ((length % 64U) == 0U) &&
        ((length + 1U) < sizeof(msg)))
    {
        msg[length - 2U] = ' ';
        msg[length - 1U] = '\r';
        msg[length] = '\n';
        msg[length + 1U] = '\0';
    }
    Debug_UART_Write(msg);
}

static uint8_t Debug_PrintPressureSample(void)
{
    char msg[144];
    ADS1115_Sample_t sample;
    HAL_StatusTypeDef status;

    s_ads1115_last_attempt_ms = HAL_GetTick();
    if (ADS1115_IsInitialized() == 0U) s_ads1115_ready = 0U;
    /* A pending automatic deflation owns pressure safety even with the pump off.
       Cancel/vent before any diagnostic output or offline recovery. */
    if ((s_deflate_hold_until_ms != 0U) && (s_ads1115_ready == 0U))
    {
        s_last_pressure_sample_valid = 0U;
        ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
        Debug_UART_Write("[Safety] Pressure offline during hold; emergency vent\r\n");
        Debug_PrintADS1115Diagnostics();
        return 0U;
    }
    if (s_ads1115_ready == 0U)
    {
        Debug_UART_Write("[Pressure] ADS1115 retry init\r\n");
        if (ADS1115_Init(&hi2c1) != HAL_OK)
        {
            BP_CalculationCancel();
            Debug_PrintADS1115InitResult(0U);
            Debug_UART_Write("[Pressure] ADS1115 offline\r\n");
            BP_Control_RecordFault(BP_FAULT_SENSOR_INIT);
            return 0U;
        }
        s_ads1115_ready = 1U;
        Debug_PrintADS1115InitResult(1U);
    }

    status = ADS1115_ReadSample(&sample);
    if (status != HAL_OK)
    {
        if (s_deflate_hold_until_ms != 0U)
            ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
        BP_CalculationCancel();
        s_ads1115_ready = 0U;
        s_last_pressure_sample_valid = 0U;
        snprintf(msg, sizeof(msg),
                 "[Pressure] sample failed status=%d; will retry init\r\n",
                 (int)status);
        Debug_UART_Write(msg);
        BP_Control_RecordFault(BP_FAULT_SENSOR_READ);
        Debug_PrintADS1115Diagnostics();
        return 0U;
    }

    g_last_pressure_mmhg = sample.pressure_mmhg;
    s_last_pressure_sample = sample;
    s_last_pressure_sample_ms = HAL_GetTick();
    s_last_pressure_sample_valid = 1U;
    Debug_PrintPressureRecord(&sample);
    return 1U;
}

static const char *Debug_PinLevel(GPIO_PinState level)
{
    return (level == GPIO_PIN_SET) ? "HIGH" : "LOW";
}

static void Debug_PrintPins(void)
{
    char msg[96];

    snprintf(msg, sizeof(msg),
             "[Pins] PB8=%s PC1=%s PC8=%s pump=%s\r\n",
             Debug_PinLevel(HAL_GPIO_ReadPin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin)),
             Debug_PinLevel(HAL_GPIO_ReadPin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin)),
             Debug_PinLevel(HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin)),
             Pump_IsOn() ? "ON" : "OFF");
    Debug_UART_Write(msg);
}

static void Debug_PrintFault(void)
{
    char msg[96];
    BP_Fault_t fault = BP_Control_GetFault();
    uint32_t age_ms = 0U;

    if (fault != BP_FAULT_NONE)
    {
        age_ms = HAL_GetTick() - BP_Control_GetFaultTimeMs();
    }

    snprintf(msg, sizeof(msg),
             "[Fault] code=%d name=%s age=%lums\r\n",
             (int)fault,
             BP_Control_FaultName(fault),
             (unsigned long)age_ms);
    Debug_UART_Write(msg);
    Debug_PrintADS1115Diagnostics();
    Debug_PrintCapture();
}

static void Debug_PrintStatus(void)
{
    char msg[176];
    uint32_t remaining_ms = 0U;

    if (s_manual_pump_active != 0U)
    {
        uint32_t elapsed_ms = HAL_GetTick() - s_manual_pump_start_ms;
        if (elapsed_ms < MANUAL_PUMP_TIMEOUT_MS)
        {
            remaining_ms = MANUAL_PUMP_TIMEOUT_MS - elapsed_ms;
        }
    }

    snprintf(msg, sizeof(msg),
             "[Status] mode=RELAY_ONLY state=%s cal=%s ads=%s stream=%s manual=%s remaining=%lums\r\n",
             BP_Control_StateName(BP_Control_GetState()),
             BP_Control_IsCalibrationValid() ? "VALID" : "UNCAL",
             s_ads1115_ready ? "ONLINE" : "OFFLINE",
             s_pressure_stream_enabled ? "ON" : "OFF",
             s_manual_pump_active ? "ON" : "OFF",
             (unsigned long)remaining_ms);
    Debug_UART_Write(msg);
    snprintf(msg, sizeof(msg), "[UART3] rx_errors=%u rx_state=0x%02lX\r\n",
             (unsigned)s_uart3_rx_errors, (unsigned long)huart3.RxState);
    Debug_UART_Write(msg);
}

static void Debug_PrintCalStatus(void)
{
    char msg[128];

    if (BP_Cal_IsValid() != 0U)
    {
        snprintf(msg, sizeof(msg),
                 "[Cal] VALID slope=%.3fmmHg/V intercept=%.2fmmHg zero=%.3fV sens=%.4fV/kPa\r\n",
                 BP_Cal_GetSlope(),
                 BP_Cal_GetIntercept(),
                 BP_Cal_GetZeroVoltageV(),
                 BP_Cal_GetSensitivityVPerKPa());
    }
    else
    {
        snprintf(msg, sizeof(msg),
                 "[Cal] UNCAL (no stored record); defaults zero=%.2fV sens=%.3fV/kPa\r\n",
                 BP_CAL_DEFAULT_ZERO_V,
                 BP_CAL_DEFAULT_SENS_V_PER_KPA);
    }
    Debug_UART_Write(msg);
}

void Debug_PrintFirmwareVersion(void)
{
    char msg[128];
    snprintf(msg, sizeof(msg),
             "algo=PULSE_STEP_DEFLATE sw=" BP_FIRMWARE_ID " capacity=%u deflate=%lums_open%lums\r\n",
             (unsigned)BP_ALGO_MAX_SAMPLES,
             (unsigned long)DEFLATE_PWM_PERIOD_MS,
             (unsigned long)DEFLATE_PWM_BASE_ON_MS);
    Debug_UART_Write(msg);
}

static void Debug_PrintHelp(void)
{
    Debug_UART_Write("[Help] start stop open close vent seal pressure p\r\n");
    Debug_UART_Write("[Help] help version status pins fault stream start stream stop\r\n");
    Debug_UART_Write("[Help] holdopen (non-human sealed-path diagnostic, 15s timeout)\r\n");
    Debug_UART_Write("[Help] cal | cal clear | cal write <slope> <intercept>\r\n");
    Debug_UART_Write("[Help] target <20-275>  inflate target mmHg\r\n");
    Debug_UART_Write("[Help] profile | profile normal | profile peak (sealed fresh zero only)\r\n");
    Debug_UART_Write("[Help] motor <dir 0/1> <steps> <freq 50-2000Hz> | motor stop\r\n");
    Debug_UART_Write("[Help] capture export (stream on, sealed, fresh calibrated <=5mmHg)\r\n");
    Debug_UART_Write("[Help] zero pulse (non-human, sealed zero, pump off, 5s)\r\n");
    Debug_UART_Write("[Help] loaded pulse [1-4] (non-human, default 5ms, 40-80mmHg, auto vent)\r\n");
    Debug_UART_Write("[Help] deflate test (non-human, 1-4ms closed-loop rate probe, 10s/45mmHg limit)\r\n");
    Debug_UART_Write("[Help] stack (runtime stack high-water mark)\r\n");
    Debug_UART_Write("[Help] readtest (non-human, sealed zero, 10s at 25ms, no actuator writes)\r\n");
}

static void Debug_PrintStackWatermark(void)
{
    StackWatermark_Result_t result;
    char msg[112];

    if (StackWatermark_Get(&result) == 0U)
    {
        Debug_UART_Write("[Stack] INVALID linker range or reservation\r\n");
        return;
    }

    snprintf(msg, sizeof(msg),
             "[Stack] used=%lu free=%lu reserved=%lu saturated=%u pattern=0x%08lX\r\n",
             (unsigned long)result.used_bytes,
             (unsigned long)result.free_bytes,
             (unsigned long)result.reserved_bytes,
             (unsigned)result.saturated,
             (unsigned long)STACK_WATERMARK_PATTERN);
    Debug_UART_Write(msg);
}

static uint8_t ManualPump_Start(void)
{
    ADS1115_Sample_t sample;

    if (BP_Control_IsCalibrationValid() == 0U)
    {
        BP_Control_RecordFault(BP_FAULT_UNCALIBRATED);
        Debug_UART_Write("[Safety] START blocked: pressure sensor UNCAL\r\n");
        return 0U;
    }

    if ((s_ads1115_ready == 0U) || (ADS1115_ReadSample(&sample) != HAL_OK))
    {
        s_ads1115_ready = 0U;
        ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
        Debug_UART_Write("[Safety] START blocked: pressure sensor read failed; emergency vent\r\n");
        Debug_PrintADS1115Diagnostics();
        return 0U;
    }

    g_last_pressure_mmhg = sample.pressure_mmhg;
    s_last_pressure_sample = sample;
    s_last_pressure_sample_ms = HAL_GetTick();
    s_last_pressure_sample_valid = 1U;
    s_hold_open_active = 0U;
    DeflateControl_Cancel();
    BP_Control_Reset();
    VALVE2_CLOSE();
    VALVE1_OPEN();
    PUMP_SET_DUTY(PUMP_DUTY_FULL);
    PUMP_START();
    s_manual_pump_start_ms = HAL_GetTick();
    s_manual_pressure_last_ms = s_manual_pump_start_ms;
    s_manual_pump_active = 1U;
    return 1U;
}

static void ManualPump_Disarm(void)
{
    s_manual_pump_active = 0U;
}

static void ManualPump_EmergencyStop(BP_Fault_t fault)
{
    ManualPump_Disarm();
    s_hold_open_active = 0U;
    DeflateControl_Cancel();
    BP_Control_EmergencyStop(fault);
}

static void HoldOpen_TimeoutTask(void)
{
    if ((s_hold_open_active != 0U) &&
        ((HAL_GetTick() - s_hold_open_start_ms) >= HOLD_OPEN_TIMEOUT_MS))
    {
        s_hold_open_active = 0U;
        BP_Control_EmergencyStop(BP_FAULT_MANUAL_TIMEOUT);
        Debug_UART_Write("[Safety] HOLDOPEN timeout; emergency vent\r\n");
    }
}

static void Boot_PressureSafetyCheck(void)
{
    ADS1115_Sample_t sample;

    if ((s_ads1115_ready == 0U) || (BP_Control_IsCalibrationValid() == 0U))
    {
        return;
    }

    if (ADS1115_ReadSample(&sample) != HAL_OK)
    {
        s_ads1115_ready = 0U;
        BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
        Debug_UART_Write("[Safety] Boot pressure read failed; emergency vent\r\n");
        Debug_PrintADS1115Diagnostics();
        return;
    }

    g_last_pressure_mmhg = sample.pressure_mmhg;
    s_last_pressure_sample = sample;
    s_last_pressure_sample_ms = HAL_GetTick();
    s_last_pressure_sample_valid = 1U;
    if (sample.pressure_mmhg >= BOOT_RESIDUAL_PRESSURE_MMHG)
    {
        BP_Control_EmergencyStop(BP_FAULT_RESIDUAL_PRESSURE);
        Debug_UART_Write("[Safety] Residual pressure after reset; emergency vent\r\n");
    }
}

static void ManualPump_TimeoutTask(void)
{
    uint32_t now;
    ADS1115_Sample_t sample;

    if ((s_manual_pump_active == 0U) && (s_deflate_hold_until_ms == 0U)) return;

    now = HAL_GetTick();
    if ((now - s_manual_pressure_last_ms) >= MANUAL_PRESSURE_SAMPLE_INTERVAL_MS)
    {
        s_manual_pressure_last_ms = now;
        s_ads1115_last_attempt_ms = now;
        if (ADS1115_ReadSample(&sample) != HAL_OK)
        {
            uint8_t was_holding = (s_deflate_hold_until_ms != 0U) ? 1U : 0U;
            s_ads1115_ready = 0U;
            s_last_pressure_sample_valid = 0U;
            ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
            Debug_UART_Write((was_holding != 0U)
                ? "[Safety] Pressure read failed during hold; emergency vent\r\n"
                : "[Safety] Pressure read failed during inflate; emergency vent\r\n");
            Debug_PrintADS1115Diagnostics();
            return;
        }

        g_last_pressure_mmhg = sample.pressure_mmhg;
        s_last_pressure_sample = sample;
        s_last_pressure_sample_ms = HAL_GetTick();
        s_last_pressure_sample_valid = 1U;
    }

    if (g_last_pressure_mmhg >= (float)BP_MAX_PRESSURE_MMHG)
    {
        ManualPump_EmergencyStop(BP_FAULT_OVERPRESSURE);
        Debug_UART_Write("[Safety] Over-pressure; emergency vent\r\n");
        return;
    }

    /* Hold checks share the sampling/over-pressure path, but must not restart
       the one-second deadline when pressure remains above the inflate target. */
    if (s_manual_pump_active == 0U) return;

    if (g_last_pressure_mmhg >= s_inflate_target_mmhg)
    {
        char msg[64];
        snprintf(msg, sizeof(msg), "[Inflate] target reached %.1f mmHg; stopping pump\r\n", g_last_pressure_mmhg);
        ManualPump_Disarm();
        VALVE1_CLOSE();
        PUMP_STOP();
        s_deflate_hold_until_ms = HAL_GetTick() + DEFLATE_HOLD_MS;
        Debug_UART_Write(msg);
        Debug_UART_Write("[Inflate] holding before deflate...\r\n");
        return;
    }

    if ((now - s_manual_pump_start_ms) >= MANUAL_PUMP_TIMEOUT_MS)
    {
        ManualPump_EmergencyStop(BP_FAULT_MANUAL_TIMEOUT);
        Debug_UART_Write("[Safety] Manual pump timeout; emergency vent\r\n");
    }
}

/* Use the same production ADS conversion and 25 ms cadence as inflation/hold,
 * with sealed actuators throughout. No retries or GPIO writes in this test. */
static uint8_t ReadTest_PinsSafe(void)
{
    return (HAL_GPIO_ReadPin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin) == GPIO_PIN_SET) &&
           (HAL_GPIO_ReadPin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin) == GPIO_PIN_RESET) &&
           (HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin) == GPIO_PIN_SET);
}

static void ReadTest_Finish(const char *reason)
{
    char msg[112];
    s_read_test.active = 0U;
    snprintf(msg, sizeof(msg), "[ReadTest] %s n=%u elapsed=%lums last_raw=%d\r\n",
             reason, (unsigned)s_read_test.samples,
             (unsigned long)(HAL_GetTick() - s_read_test.start_ms),
             s_last_pressure_sample.raw);
    Debug_UART_Write(msg);
}

static void ReadTest_Start(void)
{
    if ((CaptureAcquisition_IsActive() != 0U) || (s_calculation_pending != 0U) ||
        (BP_Cal_IsValid() == 0U) || (s_ads1115_ready == 0U) ||
        (ADS1115_IsInitialized() == 0U) || (s_last_pressure_sample_valid == 0U) ||
        ((HAL_GetTick() - s_last_pressure_sample_ms) > 250U) ||
        !(s_last_pressure_sample.pressure_mmhg <= 1.0f) ||
        !(s_last_pressure_sample.pressure_mmhg >= 0.0f) ||
        (ReadTest_PinsSafe() == 0U))
    {
        Debug_UART_Write("[ReadTest] REJECTED: require inactive, fresh calibrated sealed zero\r\n");
        return;
    }
    Debug_PrintADS1115Diagnostics(); /* retain boot-lifetime baseline, never clear */
    s_read_test.start_ms = HAL_GetTick();
    s_read_test.samples = 0U;
    s_manual_pressure_last_ms = s_read_test.start_ms - BP_SAMPLE_INTERVAL_MS;
    s_read_test.active = 1U;
    Debug_UART_Write("[ReadTest] START 10000ms interval=25ms sealed-zero NONHUMAN\r\n");
}

static void ReadTest_Task(void)
{
    uint32_t now;
    ADS1115_Sample_t sample;
    if (s_read_test.active == 0U) return;
    now = HAL_GetTick();
    if (ReadTest_PinsSafe() == 0U)
    {
        ReadTest_Finish("FAIL_PINS");
        return;
    }
    if ((now - s_read_test.start_ms) >= READ_TEST_DURATION_MS)
    {
        ReadTest_Finish((s_read_test.samples >= READ_TEST_MIN_SAMPLES) ?
                        "PASS_READ_ONLY" : "FAIL_CADENCE");
        return;
    }
    if ((now - s_manual_pressure_last_ms) < BP_SAMPLE_INTERVAL_MS) return;
    s_manual_pressure_last_ms = now;
    s_ads1115_last_attempt_ms = now;
    if (ADS1115_ReadSample(&sample) != HAL_OK)
    {
        s_ads1115_ready = 0U;
        s_last_pressure_sample_valid = 0U;
        BP_Control_RecordFault(BP_FAULT_SENSOR_READ);
        ReadTest_Finish("FAIL_ADS");
        Debug_PrintADS1115Diagnostics();
        return;
    }
    s_last_pressure_sample = sample;
    s_last_pressure_sample_ms = HAL_GetTick();
    s_last_pressure_sample_valid = 1U;
    g_last_pressure_mmhg = sample.pressure_mmhg;
    s_read_test.samples++;
    if (!(sample.pressure_mmhg >= 0.0f) || !(sample.pressure_mmhg <= 5.0f))
        ReadTest_Finish("FAIL_PRESSURE");
}

static void PressureStream_Task(void)
{
    uint32_t now = HAL_GetTick();

    if ((s_pressure_stream_enabled != 0U) &&
        ((now - s_pressure_stream_last_ms) >= PRESSURE_STREAM_INTERVAL_MS))
    {
        s_pressure_stream_last_ms = now;
        if (((s_manual_pump_active != 0U) || (s_deflate_hold_until_ms != 0U) ||
             (s_deflate_pwm_enabled != 0U) ||
             (s_hold_open_active == ZERO_PULSE_ACTIVE) ||
             (s_hold_open_active == LOADED_PULSE_ACTIVE) ||
             (s_read_test.active != 0U)) &&
            (s_last_pressure_sample_valid != 0U))
        {
            Debug_PrintPressureRecord(&s_last_pressure_sample);
        }
        else if (((ADS1115_IsInitialized() != 0U) ||
                  ((now - s_ads1115_last_attempt_ms) >= ADS1115_OFFLINE_RETRY_MS)) &&
                 (Debug_PrintPressureSample() == 0U))
        {
            /* Keep stream alive, but do not flood Init failures at 20 Hz. */
            Debug_UART_Write("[Stream] read failed; offline retry interval=1000ms\r\n");
        }
    }
}

static void PulseDiagnostic_Task(void)
{
    uint32_t now;
    uint32_t elapsed;
    uint8_t loaded;
    ADS1115_Sample_t sample;

    if ((s_hold_open_active != ZERO_PULSE_ACTIVE) &&
        (s_hold_open_active != LOADED_PULSE_ACTIVE)) return;
    loaded = (s_hold_open_active == LOADED_PULSE_ACTIVE) ? 1U : 0U;
    now = HAL_GetTick();
    elapsed = now - s_hold_open_start_ms;
    if (elapsed >= ((loaded != 0U) ? LOADED_PULSE_DURATION_MS : ZERO_PULSE_DURATION_MS))
    {
        char msg[112];
        uint32_t last_tick = BP_Algorithm_LastValvePulseTick();
        DeflateControl_Cancel();
        PUMP_STOP();
        VALVE1_CLOSE();
        if (loaded != 0U)
        {
            VALVE2_OPEN();
            snprintf(msg, sizeof(msg),
                     "[LoadedPulse] done pulses=%lu last_tick=%lu; PC1=HIGH venting pump=OFF\r\n",
                     (unsigned long)BP_Algorithm_GetValveDiagnostics()->pulse_count,
                     (unsigned long)last_tick);
        }
        else
        {
            VALVE2_CLOSE();
            snprintf(msg, sizeof(msg),
                     "[ZeroPulse] done pulses=%lu last_tick=%lu; PC1=LOW pump=OFF\r\n",
                     (unsigned long)BP_Algorithm_GetValveDiagnostics()->pulse_count,
                     (unsigned long)last_tick);
        }
        Debug_UART_Write(msg);
        Debug_PrintCapture();
        return;
    }
    if ((now - s_algo_sample_last_ms) >= BP_SAMPLE_INTERVAL_MS)
    {
        s_algo_sample_last_ms = now;
        if (ADS1115_ReadSample(&sample) != HAL_OK)
        {
            s_ads1115_ready = 0U;
            ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
            s_last_pressure_sample_valid = 0U;
            Debug_UART_Write("[Safety] Pulse diagnostic ADS failure; emergency vent\r\n");
            return;
        }
        g_last_pressure_mmhg = sample.pressure_mmhg;
        s_last_pressure_sample = sample;
        s_last_pressure_sample_ms = HAL_GetTick();
        s_last_pressure_sample_valid = 1U;
        if ((loaded == 0U) && (sample.pressure_mmhg > 1.0f))
        {
            ManualPump_EmergencyStop(BP_FAULT_OVERPRESSURE);
            Debug_UART_Write("[Safety] Zero pulse pressure above 1mmHg; emergency vent\r\n");
            return;
        }
        if ((loaded != 0U) &&
            ((sample.pressure_mmhg < LOADED_PULSE_ABORT_MIN_MMHG) ||
             (sample.pressure_mmhg > LOADED_PULSE_ABORT_MAX_MMHG)))
        {
            ManualPump_EmergencyStop(BP_FAULT_PRESSURE_RANGE);
            Debug_UART_Write("[Safety] Loaded pulse pressure outside 20-85mmHg; emergency vent\r\n");
            return;
        }
        if (BP_Algorithm_AddSample(sample.pressure_mmhg,
                                   sample.sensor_voltage_v) == 0U)
        {
            ManualPump_EmergencyStop(BP_FAULT_SAMPLE_OVERFLOW);
            Debug_UART_Write("[Safety] Pulse diagnostic sample overflow; emergency vent\r\n");
            return;
        }
    }
    now = HAL_GetTick();
    if (((loaded == 0U) || (elapsed >= LOADED_PULSE_BASELINE_MS)) &&
        ((int32_t)(now - s_deflate_next_pulse_ms) >= 0))
    {
        DeflatePulse_Start((loaded != 0U) ? s_loaded_pulse_on_ms : ZERO_PULSE_ON_MS);
        s_deflate_next_pulse_ms = now + DEFLATE_PWM_PERIOD_MS;
    }
}

static void DeflateTest_Finish(const char *reason)
{
    char msg[120];
    uint32_t on_ms = s_deflate_pwm_on_ms;
    uint32_t last_tick = BP_Algorithm_LastValvePulseTick();
    uint32_t pulses = BP_Algorithm_GetValveDiagnostics()->pulse_count;
    DeflateControl_Cancel();
    PUMP_STOP();
    VALVE1_CLOSE();
    VALVE2_OPEN();
    snprintf(msg, sizeof(msg),
             "[DeflateTest] done reason=%s pulses=%lu last_tick=%lu on=%lums; PC1=HIGH venting\r\n",
             reason, (unsigned long)pulses, (unsigned long)last_tick,
             (unsigned long)on_ms);
    Debug_UART_Write(msg);
    Debug_PrintCapture();
}

static void BP_CalculationTask(void)
{
    if (s_calculation_pending == 0U) return;
    BP_CalcStatus_t status = BP_Algorithm_CalculateStep(&g_bp_result);
    if (status == BP_CALC_BUSY) return;
    s_calculation_pending = 0U;
    if (status == BP_CALC_IDLE) return; /* reset/cancel: never publish stale BP */

    char msg[256];
    if (status == BP_CALC_DONE)
    {
        snprintf(msg, sizeof(msg), "[BP] SBP=%d DBP=%d Pulse=%d bpm valid=%d\r\n",
                 g_bp_result.systolic, g_bp_result.diastolic,
                 g_bp_result.pulse, g_bp_result.valid);
        Debug_UART_Write(msg);
        snprintf(msg, sizeof(msg),
                 "[DBG] n=%u map=%u(%.1f) sbp=%u(%.1f) dbp=%u(%.1f) fft=%u(%.1fHz/%.0fbpm/m=%.1f/n=%.1f/t=%.1f) ff=%.0f pk=%.0f\r\n",
                 (unsigned)g_bp_debug.sample_count, (unsigned)g_bp_debug.map_idx,
                 (double)g_bp_debug.map_pressure_mmhg, (unsigned)g_bp_debug.sbp_found,
                 (double)g_bp_debug.sbp_pressure_mmhg, (unsigned)g_bp_debug.dbp_found,
                 (double)g_bp_debug.dbp_pressure_mmhg, (unsigned)g_bp_debug.fft_pass,
                 (double)g_bp_debug.fft_peak_hz, (double)g_bp_debug.fft_peak_bpm,
                 (double)g_bp_debug.fft_max_mag, (double)g_bp_debug.fft_noise,
                 (double)g_bp_debug.fft_threshold, (double)g_bp_debug.pulse_fft,
                 (double)g_bp_debug.pulse_peak);
        Debug_UART_Write(msg);
    }
    else
    {
        Debug_UART_Write("[BP] calculation failed\r\n");
        snprintf(msg, sizeof(msg),
                 "[DBGFAIL] n=%u map=%u(%.1f) sbp=%u(%.1f) dbp=%u(%.1f)\r\n",
                 (unsigned)g_bp_debug.sample_count, (unsigned)g_bp_debug.map_idx,
                 (double)g_bp_debug.map_pressure_mmhg, (unsigned)g_bp_debug.sbp_found,
                 (double)g_bp_debug.sbp_pressure_mmhg, (unsigned)g_bp_debug.dbp_found,
                 (double)g_bp_debug.dbp_pressure_mmhg);
        Debug_UART_Write(msg);
    }
    snprintf(msg, sizeof(msg),
             "[Calc] work=%lums wall=%lums max_step=%lums extract=%lums smooth=%lums finish=%lums steps=%lu\r\n",
             (unsigned long)g_bp_debug.calc_work_ms, (unsigned long)g_bp_debug.calc_wall_ms,
             (unsigned long)g_bp_debug.calc_max_step_ms, (unsigned long)g_bp_debug.calc_extract_ms,
             (unsigned long)g_bp_debug.calc_smooth_ms, (unsigned long)g_bp_debug.calc_finish_ms,
             (unsigned long)g_bp_debug.calc_steps);
    Debug_UART_Write(msg);
}

#if BP_BRINGUP_ENABLE_BUTTONS
static uint8_t Button_PressedEdge(ButtonDebounce_t *button, uint32_t now)
{
    GPIO_PinState sample = HAL_GPIO_ReadPin(button->port, button->pin);

    if (sample != button->last_sample)
    {
        button->last_sample = sample;
        button->last_change_ms = now;
    }

    if ((sample != button->stable_level) &&
        ((now - button->last_change_ms) >= BUTTON_DEBOUNCE_MS))
    {
        button->stable_level = sample;
        return (sample == GPIO_PIN_RESET) ? 1U : 0U;
    }

    return 0U;
}

static void Process_Buttons(void)
{
    uint32_t now = HAL_GetTick();

    if (Button_PressedEdge(&s_stop_button, now))
    {
        Debug_UART_Write("[Button] STOP pressed; emergency vent\r\n");
        ManualPump_EmergencyStop(BP_FAULT_USER_STOP);
        return;
    }

    if (Button_PressedEdge(&s_start_button, now))
    {
        Debug_UART_Write("[Button] START pressed\r\n");
        if (BP_Control_IsCalibrationValid() == 0U)
        {
            BP_Control_RecordFault(BP_FAULT_UNCALIBRATED);
            Debug_UART_Write("[Safety] START blocked: pressure sensor UNCAL\r\n");
            return;
        }

#if BP_BRINGUP_RELAY_ONLY
        Debug_UART_Write("[Safety] START blocked: relay-only mode; use serial start for bench test\r\n");
#else
        if (BP_Control_GetState() == BP_STATE_IDLE)
        {
            BP_Control_Start();
        }
#endif
    }
}
#endif

static void Debug_CommandRejectLine(void)
{
    s_debug_cmd_len = 0U;
    s_debug_urgent_match = 0U;
    s_debug_cmd_discard = 1U;
}

static DebugCommand_t Debug_CommandTake(char *snapshot)
{
    uint32_t saved_primask = __get_PRIMASK();
    DebugCommand_t command;

    __disable_irq();
    command = s_pending_debug_cmd;
    if (command != DEBUG_CMD_NONE)
    {
        /* The ISR freezes this buffer until this bounded copy completes. */
        memcpy(snapshot, s_debug_cmd_buffer, DEBUG_CMD_BUFFER_LEN);
        s_pending_debug_cmd = DEBUG_CMD_NONE;
        if (s_debug_cmd_len != 0U) Debug_CommandRejectLine();
        s_debug_urgent_match = 0U;
    }
    __set_PRIMASK(saved_primask);
    return command;
}

static void Debug_UART_RxTask(void)
{
    uint32_t saved_primask = __get_PRIMASK();

    __disable_irq();
    if (huart3.RxState == HAL_UART_STATE_READY)
    {
        /* One attempt per main-loop pass; never wait or abort an active RX. */
        Debug_CommandRejectLine();
        if ((s_pending_debug_cmd != DEBUG_CMD_STOP) &&
            (s_pending_debug_cmd != DEBUG_CMD_VALVE2_OPEN))
            s_pending_debug_cmd = DEBUG_CMD_NONE;
        __HAL_UART_CLEAR_OREFLAG(&huart3);
        (void)HAL_UART_Receive_IT(&huart3, &s_rx3_byte, 1U);
    }
    __set_PRIMASK(saved_primask);
}

void Debug_CommandAcceptByte(uint8_t byte)
{
    char ch = (char)byte;

    if (s_debug_cmd_discard != 0U)
    {
        if ((ch == '\r') || (ch == '\n')) s_debug_cmd_discard = 0U;
        return;
    }

    if (s_pending_debug_cmd != DEBUG_CMD_NONE)
    {
        /* Keep accepted parameters immutable, but let stop/vent replace them.
         * Other pipelined commands are dropped, never partly concatenated. */
        if ((ch == '\r') || (ch == '\n'))
        {
            if (s_debug_cmd_len == 4U)
            {
                if ((s_debug_urgent_match & 1U) != 0U)
                    s_pending_debug_cmd = DEBUG_CMD_STOP;
                else if ((s_debug_urgent_match & 2U) != 0U)
                    s_pending_debug_cmd = DEBUG_CMD_VALVE2_OPEN;
            }
            s_debug_cmd_len = 0U;
            s_debug_urgent_match = 0U;
            return;
        }
        if ((ch >= 'A') && (ch <= 'Z')) ch += ('a' - 'A');
        if (s_debug_cmd_len == 0U) s_debug_urgent_match = 3U;
        if (s_debug_cmd_len < 4U)
        {
            if (ch != "stop"[s_debug_cmd_len]) s_debug_urgent_match &= (uint8_t)~1U;
            if (ch != "vent"[s_debug_cmd_len]) s_debug_urgent_match &= (uint8_t)~2U;
        }
        else s_debug_urgent_match = 0U;
        if (s_debug_cmd_len < 5U) s_debug_cmd_len++;
        return;
    }

    if ((ch != '\r') && (ch != '\n') &&
        (s_debug_cmd_len >= (DEBUG_CMD_BUFFER_LEN - 1U)))
    {
        Debug_CommandRejectLine();
        return;
    }

    if ((ch == '\r') || (ch == '\n'))
    {
        if (s_debug_cmd_len > 0U)
        {
            s_debug_cmd_buffer[s_debug_cmd_len] = '\0';

            if (strcmp(s_debug_cmd_buffer, "start") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_START;
            }
            else if (strcmp(s_debug_cmd_buffer, "stop") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_STOP;
            }
            else if (strcmp(s_debug_cmd_buffer, "open") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_VALVE1_OPEN;
            }
            else if (strcmp(s_debug_cmd_buffer, "close") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_VALVE1_CLOSE;
            }
            else if (strcmp(s_debug_cmd_buffer, "vent") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_VALVE2_OPEN;
            }
            else if (strcmp(s_debug_cmd_buffer, "seal") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_VALVE2_CLOSE;
            }
            else if (strcmp(s_debug_cmd_buffer, "holdopen") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_HOLD_OPEN;
            }
            else if ((strcmp(s_debug_cmd_buffer, "pressure") == 0) ||
                     (strcmp(s_debug_cmd_buffer, "p") == 0))
            {
                s_pending_debug_cmd = DEBUG_CMD_PRESSURE;
            }
            else if (strcmp(s_debug_cmd_buffer, "help") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_HELP;
            }
            else if (strcmp(s_debug_cmd_buffer, "version") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_VERSION;
            }
            else if (strcmp(s_debug_cmd_buffer, "status") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_STATUS;
            }
            else if (strcmp(s_debug_cmd_buffer, "pins") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_PINS;
            }
            else if (strcmp(s_debug_cmd_buffer, "fault") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_FAULT;
            }
            else if (strcmp(s_debug_cmd_buffer, "stream start") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_STREAM_START;
            }
            else if (strcmp(s_debug_cmd_buffer, "stream stop") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_STREAM_STOP;
            }
            else if (strcmp(s_debug_cmd_buffer, "pump") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_PUMP_ON;
            }
            else if (strcmp(s_debug_cmd_buffer, "cal") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_CAL;
            }
            else if (strcmp(s_debug_cmd_buffer, "cal clear") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_CAL_CLEAR;
            }
            else if (strncmp(s_debug_cmd_buffer, "cal write ", 10U) == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_CAL_WRITE;
            }
            else if (strncmp(s_debug_cmd_buffer, "target ", 7U) == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_TARGET;
            }
            else if (strcmp(s_debug_cmd_buffer, "profile") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_PROFILE;
            }
            else if (strcmp(s_debug_cmd_buffer, "profile normal") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_PROFILE_NORMAL;
            }
            else if (strcmp(s_debug_cmd_buffer, "profile peak") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_PROFILE_PEAK;
            }
            else if (strcmp(s_debug_cmd_buffer, "motor stop") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_MOTOR_STOP;
            }
            else if (strncmp(s_debug_cmd_buffer, "motor ", 6U) == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_MOTOR;
            }
            else if (strcmp(s_debug_cmd_buffer, "i2cscan") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_I2C_SCAN;
            }
            else if (strcmp(s_debug_cmd_buffer, "capture export") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_CAPTURE_EXPORT;
            }
            else if (strcmp(s_debug_cmd_buffer, "zero pulse") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_ZERO_PULSE;
            }
            else if (strcmp(s_debug_cmd_buffer, "loaded pulse") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_LOADED_PULSE;
            }
            else if (strcmp(s_debug_cmd_buffer, "loaded pulse 1") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_LOADED_PULSE_1;
            }
            else if (strcmp(s_debug_cmd_buffer, "loaded pulse 2") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_LOADED_PULSE_2;
            }
            else if (strcmp(s_debug_cmd_buffer, "loaded pulse 3") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_LOADED_PULSE_3;
            }
            else if (strcmp(s_debug_cmd_buffer, "loaded pulse 4") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_LOADED_PULSE_4;
            }
            else if (strcmp(s_debug_cmd_buffer, "deflate test") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_DEFLATE_TEST;
            }
            else if (strcmp(s_debug_cmd_buffer, "stack") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_STACK;
            }
            else if (strcmp(s_debug_cmd_buffer, "readtest") == 0)
            {
                s_pending_debug_cmd = DEBUG_CMD_READ_TEST;
            }
            else
            {
                s_pending_debug_cmd = DEBUG_CMD_UNKNOWN;
            }

            s_debug_cmd_len = 0U;
        }
    }
    else if ((ch >= 'A') && (ch <= 'Z'))
    {
        if (s_debug_cmd_len < (DEBUG_CMD_BUFFER_LEN - 1U))
        {
            s_debug_cmd_buffer[s_debug_cmd_len++] = (char)(ch + ('a' - 'A'));
        }
    }
    else if ((ch >= 'a') && (ch <= 'z'))
    {
        if (s_debug_cmd_len < (DEBUG_CMD_BUFFER_LEN - 1U))
        {
            s_debug_cmd_buffer[s_debug_cmd_len++] = ch;
        }
    }
    else if (ch == ' ')
    {
        if ((s_debug_cmd_len > 0U) &&
            (s_debug_cmd_buffer[s_debug_cmd_len - 1U] != ' ') &&
            (s_debug_cmd_len < (DEBUG_CMD_BUFFER_LEN - 1U)))
        {
            s_debug_cmd_buffer[s_debug_cmd_len++] = ch;
        }
    }
    else if (((ch >= '0') && (ch <= '9')) || (ch == '.') || (ch == '-'))
    {
        if (s_debug_cmd_len < (DEBUG_CMD_BUFFER_LEN - 1U))
        {
            s_debug_cmd_buffer[s_debug_cmd_len++] = ch;
        }
    }
    else
    {
        Debug_CommandRejectLine();
    }
}

/* RX 由 USART3_IRQHandler 中断实时接收（见 stm32f1xx_it.c），
   此处不再轮询，避免双读竞争与错误帧清缓冲导致命令丢失。 */

static void Debug_I2CScan(void)
{
    uint8_t addr;
    char msg[64];

    if ((CaptureAcquisition_IsActive() != 0U) || (s_calculation_pending != 0U) ||
        (HAL_GPIO_ReadPin(PUMP_RELAY_Port, PUMP_RELAY_Pin) != GPIO_PIN_SET) ||
        (HAL_GPIO_ReadPin(VALVE1_CTRL_Port, VALVE1_CTRL_Pin) != GPIO_PIN_SET) ||
        (HAL_GPIO_ReadPin(VALVE2_CTRL_Port, VALVE2_CTRL_Pin) != GPIO_PIN_RESET))
    {
        Debug_UART_Write("[I2C] scan blocked: requires inactive sealed actuators\r\n");
        return;
    }
    Debug_UART_Write("[I2C] scanning 0x40-0x4F...\r\n");
    for (addr = 0x40U; addr <= 0x4FU; addr++)
    {
        if (HAL_I2C_IsDeviceReady(&hi2c1, (uint16_t)(addr << 1U), 3U, 20U) == HAL_OK)
        {
            snprintf(msg, sizeof(msg), "[I2C] found device at 0x%02X\r\n", addr);
            Debug_UART_Write(msg);
        }
    }
    Debug_UART_Write("[I2C] scan done\r\n");
}

static void Process_DebugCommand(void)
{
    char command_buffer[DEBUG_CMD_BUFFER_LEN];
    DebugCommand_t command = Debug_CommandTake(command_buffer);

    if (command == DEBUG_CMD_NONE)
    {
        return;
    }

    /* Commands always remain reachable. A cancelled transfer has no end row. */
    if (command != DEBUG_CMD_CAPTURE_EXPORT) BP_CaptureExport_Cancel();

    if (((s_hold_open_active == ZERO_PULSE_ACTIVE) ||
         (s_hold_open_active == LOADED_PULSE_ACTIVE) ||
         (s_deflate_test_active != 0U) || (s_read_test.active != 0U)) &&
        (command != DEBUG_CMD_STOP) && (command != DEBUG_CMD_VALVE2_OPEN) &&
        (command != DEBUG_CMD_VALVE2_CLOSE) &&
        (command != DEBUG_CMD_HELP) && (command != DEBUG_CMD_STATUS) &&
        (command != DEBUG_CMD_VERSION) &&
        (command != DEBUG_CMD_PINS) && (command != DEBUG_CMD_FAULT) &&
        (command != DEBUG_CMD_STACK) &&
        (command != DEBUG_CMD_STREAM_START) && (command != DEBUG_CMD_STREAM_STOP))
    {
        Debug_UART_Write("[Diagnostic] busy; use stop/vent or wait for completion\r\n");
        return;
    }
    if (((s_hold_open_active == LOADED_PULSE_ACTIVE) ||
         (s_deflate_test_active != 0U)) &&
        (command == DEBUG_CMD_VALVE2_CLOSE))
    {
        Debug_UART_Write("[LoadedPulse] seal blocked until vent reaches zero\r\n");
        return;
    }

    if (command == DEBUG_CMD_STOP)
    {
        Debug_UART_Write("[DebugCmd] STOP\r\n");
        ManualPump_EmergencyStop(BP_FAULT_USER_STOP);
        Debug_UART_Write("[Safety] STOP PB8=HIGH PC1=HIGH PC8=HIGH\r\n");
    }
    else if (command == DEBUG_CMD_START)
    {
#if BP_BRINGUP_RELAY_ONLY
        Debug_UART_Write("[DebugCmd] START\r\n");
        DeflateControl_Cancel();
        BP_Algorithm_Reset();  /* 启动测量前先清算法缓冲，防止上轮残留干扰 */
        BP_Algorithm_SetCaptureContext(2U, BP_Cal_IsValid(), BP_Cal_GetSlope(), BP_Cal_GetIntercept());
        if (ManualPump_Start() != 0U)
        {
            Debug_UART_Write("[Inflate] START PB8=LOW PC1=LOW PC8=LOW safety=pressure+timeout\r\n");
        }
#else
        if (BP_Control_GetState() == BP_STATE_IDLE)
        {
            Debug_UART_Write("[DebugCmd] START\r\n");
            BP_Control_Start();
        }
        else
        {
            Debug_UART_Write("[DebugCmd] START ignored: state is not IDLE\r\n");
        }
#endif
    }
    else if (command == DEBUG_CMD_VALVE1_OPEN)
    {
        if (ManualPump_Start() != 0U)
        {
            Debug_UART_Write("[Inflate] OPEN PB8=LOW PC1=LOW PC8=LOW safety=pressure+timeout\r\n");
        }
    }
    else if (command == DEBUG_CMD_PUMP_ON)
    {
        Debug_UART_Write("[Pump] continuous mode blocked; use target + start\r\n");
    }
    else if (command == DEBUG_CMD_VALVE1_CLOSE)
    {
        BP_CalculationCancel();
        ManualPump_Disarm();
        s_hold_open_active = 0U;
        PUMP_STOP();
        VALVE1_CLOSE();
        Debug_UART_Write("[Valve1] CLOSE PB8=HIGH PC8=HIGH\r\n");
    }
    else if (command == DEBUG_CMD_VALVE2_OPEN)
    {
        ManualPump_Disarm();
        s_hold_open_active = 0U;
        DeflateControl_Cancel();
        PUMP_STOP();
        VALVE1_CLOSE();
        VALVE2_OPEN();
        Debug_UART_Write("[Deflate] VENT PB8=HIGH PC1=HIGH PC8=HIGH\r\n");
    }
    else if (command == DEBUG_CMD_HOLD_OPEN)
    {
        ManualPump_Disarm();
        DeflateControl_Cancel();
        PUMP_STOP();
        VALVE2_CLOSE();
        VALVE1_OPEN();
        s_hold_open_start_ms = HAL_GetTick();
        s_hold_open_active = 1U;
        Debug_UART_Write("[HoldOpen] PB8=LOW PC1=LOW PC8=HIGH timeout=15s NONHUMAN\r\n");
    }
    else if (command == DEBUG_CMD_DEFLATE_PWM)
    {
        DeflateControl_Cancel();
        s_deflate_pwm_on_ms = DEFLATE_PWM_BASE_ON_MS;
        s_deflate_pwm_enabled = 1U;
        s_deflate_next_pulse_ms = HAL_GetTick();
        Debug_UART_Write("[Deflate] PWM started: period=200ms SysTick pulse target=3.0mmHg/s\r\n");
    }
    else if (command == DEBUG_CMD_DEFLATE_TEST)
    {
        ADS1115_Sample_t sample;
        if (LoadedPulse_IsSafe() == 0U)
        {
            Debug_UART_Write("[DeflateTest] rejected: require fresh sealed 40-80mmHg, cal/ADS valid, pump off\r\n");
        }
        else if (ADS1115_ReadSample(&sample) != HAL_OK)
        {
            s_ads1115_ready = 0U;
            ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
            s_last_pressure_sample_valid = 0U;
            Debug_UART_Write("[Safety] Deflate test preflight ADS failure; emergency vent\r\n");
        }
        else if ((sample.pressure_mmhg < LOADED_PULSE_START_MIN_MMHG) ||
                 (sample.pressure_mmhg > LOADED_PULSE_START_MAX_MMHG))
        {
            Debug_UART_Write("[DeflateTest] rejected: pressure changed before start\r\n");
        }
        else
        {
            uint32_t now = HAL_GetTick();
            if (BP_Control_GetState() == BP_STATE_EMERGENCY) BP_Control_Reset();
            BP_Algorithm_Reset();
            BP_Algorithm_SetCaptureContext(2U, BP_Cal_IsValid(),
                                           BP_Cal_GetSlope(), BP_Cal_GetIntercept());
            g_last_pressure_mmhg = sample.pressure_mmhg;
            s_last_pressure_sample = sample;
            s_last_pressure_sample_ms = now;
            s_last_pressure_sample_valid = 1U;
            s_deflate_pwm_on_ms = DEFLATE_PWM_BASE_ON_MS;
            s_deflate_last_pressure = sample.pressure_mmhg;
            s_deflate_last_time_ms = now;
            s_deflate_speed_prev = 0.0f;
            s_algo_sample_last_ms = now - BP_SAMPLE_INTERVAL_MS;
            s_deflate_next_pulse_ms = now;
            s_deflate_test_start_ms = now;
            s_deflate_test_active = 1U;
            s_deflate_pwm_enabled = 1U;
            Debug_UART_Write("[DeflateTest] started target=2.0mmHg/s max_on=4ms period=200ms max_duration=10s stop=45mmHg\r\n");
        }
    }
    else if (command == DEBUG_CMD_VALVE2_CLOSE)
    {
        DeflateControl_Cancel();
        VALVE2_CLOSE();
        Debug_UART_Write("[Valve2] CLOSE PC1=LOW\r\n");
    }
    else if (command == DEBUG_CMD_CAPTURE_EXPORT)
    {
        if ((CaptureExport_IsSafe() == 0U) || (BP_CaptureExport_Begin() == 0U))
            Debug_UART_Write("[CaptureExport] rejected: busy/empty/context or unsafe; vent -> fresh low -> seal, stream on\r\n");
    }
    else if (command == DEBUG_CMD_ZERO_PULSE)
    {
        ADS1115_Sample_t sample;
        if ((CaptureExport_IsSafe() == 0U) ||
            (s_last_pressure_sample.pressure_mmhg > 1.0f) ||
            (ADS1115_ReadSample(&sample) != HAL_OK) ||
            (sample.pressure_mmhg > 1.0f))
        {
            Debug_UART_Write("[ZeroPulse] rejected: require fresh sealed zero, cal/ADS valid, pump off\r\n");
        }
        else
        {
            uint32_t now = HAL_GetTick();
            BP_Algorithm_Reset();
            BP_Algorithm_SetCaptureContext(2U, BP_Cal_IsValid(),
                                           BP_Cal_GetSlope(), BP_Cal_GetIntercept());
            s_hold_open_start_ms = now;
            s_algo_sample_last_ms = now - BP_SAMPLE_INTERVAL_MS;
            s_deflate_next_pulse_ms = now;
            s_hold_open_active = ZERO_PULSE_ACTIVE;
            Debug_UART_Write("[ZeroPulse] started PB8=HIGH PC8=HIGH; 5ms/200ms for 5s\r\n");
        }
    }
    else if ((command == DEBUG_CMD_LOADED_PULSE) ||
             ((command >= DEBUG_CMD_LOADED_PULSE_1) &&
              (command <= DEBUG_CMD_LOADED_PULSE_4)))
    {
        ADS1115_Sample_t sample;
        uint8_t on_ms = (command == DEBUG_CMD_LOADED_PULSE) ? ZERO_PULSE_ON_MS :
                        (uint8_t)(command - DEBUG_CMD_LOADED_PULSE_1 + 1U);
        if (LoadedPulse_IsSafe() == 0U)
        {
            Debug_UART_Write("[LoadedPulse] rejected: require fresh sealed 40-80mmHg, cal/ADS valid, pump off\r\n");
        }
        else if (ADS1115_ReadSample(&sample) != HAL_OK)
        {
            s_ads1115_ready = 0U;
            ManualPump_EmergencyStop(BP_FAULT_SENSOR_READ);
            s_last_pressure_sample_valid = 0U;
            Debug_UART_Write("[Safety] Loaded pulse preflight ADS failure; emergency vent\r\n");
        }
        else if ((sample.pressure_mmhg < LOADED_PULSE_START_MIN_MMHG) ||
                 (sample.pressure_mmhg > LOADED_PULSE_START_MAX_MMHG))
        {
            Debug_UART_Write("[LoadedPulse] rejected: pressure changed before start\r\n");
        }
        else
        {
            uint32_t now = HAL_GetTick();
            if (BP_Control_GetState() == BP_STATE_EMERGENCY)
            {
                BP_Control_Reset();
            }
            BP_Algorithm_Reset();
            BP_Algorithm_SetCaptureContext(2U, BP_Cal_IsValid(),
                                           BP_Cal_GetSlope(), BP_Cal_GetIntercept());
            s_hold_open_start_ms = now;
            s_algo_sample_last_ms = now - BP_SAMPLE_INTERVAL_MS;
            s_deflate_next_pulse_ms = now + LOADED_PULSE_BASELINE_MS;
            s_loaded_pulse_on_ms = on_ms;
            s_hold_open_active = LOADED_PULSE_ACTIVE;
            {
                char msg[100];
                snprintf(msg, sizeof(msg),
                         "[LoadedPulse] started PB8=HIGH PC8=HIGH; 1s sealed + 3s %ums/200ms\r\n",
                         (unsigned)on_ms);
                Debug_UART_Write(msg);
            }
        }
    }
    else if (command == DEBUG_CMD_READ_TEST)
    {
        ReadTest_Start();
    }
    else if (command == DEBUG_CMD_STACK)
    {
        Debug_PrintStackWatermark();
    }
    else if (command == DEBUG_CMD_PRESSURE)
    {
        (void)Debug_PrintPressureSample();
    }
    else if (command == DEBUG_CMD_HELP)
    {
        Debug_PrintHelp();
    }
    else if (command == DEBUG_CMD_VERSION)
    {
        Debug_PrintFirmwareVersion();
    }
    else if (command == DEBUG_CMD_STATUS)
    {
        Debug_PrintStatus();
    }
    else if (command == DEBUG_CMD_PINS)
    {
        Debug_PrintPins();
    }
    else if (command == DEBUG_CMD_FAULT)
    {
        Debug_PrintFault();
    }
    else if (command == DEBUG_CMD_STREAM_START)
    {
        s_pressure_stream_enabled = 1U;
        s_pressure_stream_last_ms = HAL_GetTick() - PRESSURE_STREAM_INTERVAL_MS;
        Debug_UART_Write("[Stream] pressure start interval=50ms\r\n");
    }
    else if (command == DEBUG_CMD_STREAM_STOP)
    {
        s_pressure_stream_enabled = 0U;
        Debug_UART_Write("[Stream] pressure stop\r\n");
    }
    else if (command == DEBUG_CMD_CAL)
    {
        Debug_PrintCalStatus();
    }
    else if (command == DEBUG_CMD_CAL_CLEAR)
    {
        BP_CalculationCancel();
        if (CaptureAcquisition_IsActive() != 0U)
        {
            Debug_UART_Write("[Cal] rejected: acquisition active; stop and close out first\r\n");
            return;
        }
        if (BP_Cal_Clear() == HAL_OK)
        {
            Debug_UART_Write("[Cal] cleared; pressure now UNCAL\r\n");
        }
        else
        {
            Debug_UART_Write("[Cal] clear FAILED\r\n");
        }
    }
    else if (command == DEBUG_CMD_CAL_WRITE)
    {
        BP_CalculationCancel();
        if (CaptureAcquisition_IsActive() != 0U)
        {
            Debug_UART_Write("[Cal] rejected: acquisition active; stop and close out first\r\n");
            return;
        }
        float slope = 0.0f;
        float intercept = 0.0f;
        char msg[96];

        if (sscanf(command_buffer + 10, "%f %f", &slope, &intercept) != 2)
        {
            Debug_UART_Write("[Cal] usage: cal write <slope_mmhg_per_V> <intercept_mmhg>\r\n");
        }
        else if (BP_Cal_Write(slope, intercept) == HAL_OK)
        {
            snprintf(msg, sizeof(msg),
                     "[Cal] written+verified slope=%.3f intercept=%.2f -> VALID\r\n",
                     slope, intercept);
            Debug_UART_Write(msg);
            Debug_PrintCalStatus();
        }
        else
        {
            Debug_UART_Write("[Cal] write FAILED (bad values or flash error)\r\n");
        }
    }
    else if ((command == DEBUG_CMD_PROFILE) ||
             (command == DEBUG_CMD_PROFILE_NORMAL) ||
             (command == DEBUG_CMD_PROFILE_PEAK))
    {
        if ((command == DEBUG_CMD_PROFILE) ||
            (DeflateProfile_Set((command == DEBUG_CMD_PROFILE_PEAK) ? 1U : 0U) != 0U))
            Debug_PrintDeflateProfile();
        else
            Debug_UART_Write("[Profile] rejected: require inactive sealed fresh calibrated zero\r\n");
    }
    else if (command == DEBUG_CMD_TARGET)
    {
        float target = 0.0f;
        char msg[96];

        if (CaptureAcquisition_IsActive() != 0U)
        {
            Debug_UART_Write("[Target] rejected: acquisition active; stop and close out first\r\n");
        }
        else if ((sscanf(command_buffer + 7, "%f", &target) != 1) ||
            (target < 20.0f) || (target > (float)BP_MAX_TARGET_MMHG))
        {
            Debug_UART_Write("[Target] usage: target <20-275 mmHg>\r\n");
        }
        else
        {
            s_inflate_target_mmhg = target;
            snprintf(msg, sizeof(msg),
                     "[Target] inflate target set to %.0f mmHg (max safe=%d)\r\n",
                     target, (int)BP_MAX_PRESSURE_MMHG);
            Debug_UART_Write(msg);
        }
    }
    else if (command == DEBUG_CMD_MOTOR)
    {
        unsigned int dir = 0U;
        unsigned int steps = 0U;
        unsigned int freq = 0U;
        uint8_t rc;
        char msg[96];

        if (sscanf(command_buffer + 6, "%u %u %u", &dir, &steps, &freq) != 3)
        {
            Debug_UART_Write("[Motor] usage: motor <dir 0/1> <steps> <freq 50-2000Hz>\r\n");
        }
        else if ((rc = Motor_StepN((uint8_t)dir, (uint32_t)steps, (uint32_t)freq)) != 0U)
        {
            snprintf(msg, sizeof(msg),
                     "[Motor] rejected rc=%u (1=busy 2=bad steps 3=bad freq 4=hw)\r\n",
                     rc);
            Debug_UART_Write(msg);
        }
        else
        {
            snprintf(msg, sizeof(msg),
                     "[Motor] dir=%u steps=%u freq=%uHz disp=%.3fmm busy=%u DIER=0x%04X SR=0x%04X ISER0=0x%08X\r\n",
                     dir, steps, freq, (double)steps * 0.01, (unsigned)Motor_IsBusy(),
                     (unsigned)TIM3->DIER, (unsigned)TIM3->SR, (unsigned)NVIC->ISER[0]);
            Debug_UART_Write(msg);
        }
    }
    else if (command == DEBUG_CMD_MOTOR_STOP)
    {
        char msg[96];
        Motor_Stop();
        Motor_Enable(0U);
        snprintf(msg, sizeof(msg),
                 "[Motor] stopped, disabled irq=%u\r\n", (unsigned)g_motor_irq_count);
        Debug_UART_Write(msg);
    }
    else if (command == DEBUG_CMD_I2C_SCAN)
    {
        Debug_I2CScan();
    }
    else
    {
        Debug_UART_Write("[DebugCmd] Unknown; use help\r\n");
    }
}

static void Debug_UART_Probe(void)
{
    Debug_UART_Write("[Debug] USART3 ready\r\n");
}

/** 启动 USART3 中断接收链（RXNE 中断源由此使能）。 */
static void Debug_UART_StartRxInterrupt(void)
{
    if (HAL_UART_Receive_IT(&huart3, &s_rx3_byte, 1U) != HAL_OK)
        Debug_CommandRejectLine();
}

/** 读取并清除 RCC_CSR 的复位来源标志，必须在 HAL_Init() 之前调用。
 *
 * 之前固件完全不读 RCC_CSR，所以 2026-11-07 那次中途复位只能靠串口时间戳
 * 反推：压力流在复位前 0.184 s 仍在打印，排除 IWDG（4000 ms）超时，指向
 * 电源塌陷。本函数把实测标志打印出来，以后同类事件可直接定因。
 *
 * RM0008 8.1.5：清除所有复位标志须同时置 RMVF 与全部 xxxRSTF 位。
 */
static void Boot_CaptureResetCause(void)
{
    uint32_t csr = RCC->CSR;
    s_reset_flags = csr & (RCC_CSR_PINRSTF | RCC_CSR_PORRSTF | RCC_CSR_SFTRSTF |
                           RCC_CSR_IWDGRSTF | RCC_CSR_WWDGRSTF | RCC_CSR_LPWRRSTF);
    RCC->CSR = RCC_CSR_RMVF | RCC_CSR_PINRSTF | RCC_CSR_PORRSTF | RCC_CSR_SFTRSTF |
               RCC_CSR_IWDGRSTF | RCC_CSR_WWDGRSTF | RCC_CSR_LPWRRSTF;
    (void)RCC->CSR;
}

/** 打印复位来源；在 USART3 可用之后调用。 */
static void Boot_PrintResetCause(void)
{
    char msg[112];
    snprintf(msg, sizeof(msg), "[Boot] reset_csr=0x%08lX %s%s%s%s%s%s\r\n",
             (unsigned long)s_reset_flags,
             (s_reset_flags & RCC_CSR_PORRSTF) ? "POR/PDR " : "",
             (s_reset_flags & RCC_CSR_PINRSTF) ? "PIN " : "",
             (s_reset_flags & RCC_CSR_IWDGRSTF) ? "IWDG " : "",
             (s_reset_flags & RCC_CSR_WWDGRSTF) ? "WWDG " : "",
             (s_reset_flags & RCC_CSR_SFTRSTF) ? "SOFT " : "",
             (s_reset_flags & RCC_CSR_LPWRRSTF) ? "LPWR " : "");
    Debug_UART_Write(msg);
}

/* USER CODE END 0 */

int main(void)
{
    /* USER CODE BEGIN 1 */
    (void)StackWatermark_Init();
    Boot_CaptureResetCause();
    /* USER CODE END 1 */

    HAL_Init();
    SystemClock_Config();

    /* USER CODE BEGIN Init */

    /* USER CODE END Init */

    /* Initialize peripherals */
    MX_GPIO_Init();
    MX_I2C1_Init();
    MX_USART1_UART_Init();
    MX_USART2_UART_Init();
    MX_USART3_UART_Init();
    MX_TIM8_Init();

    /* USER CODE BEGIN 2 */
    Motor_Init();
    Debug_UART_Write("[Motor] TMC2209 init: STEP=PA6(TIM3_CH1) DIR=PA7 EN=PB0 1/8ustep released\r\n");
    Debug_UART_Probe();
    Debug_UART_StartRxInterrupt();
    if (BP_Cal_Load() == HAL_OK)
    {
        Debug_UART_Write("[Cal] stored record valid\r\n");
    }
    else
    {
        Debug_UART_Write("[Cal] no valid record; UNCAL defaults\r\n");
    }
    BP_Control_Init();
    Debug_UART_Write(BP_Control_IsCalibrationValid()
                     ? "[BP_Control] Init OK calibration=VALID\r\n"
                     : "[BP_Control] Init OK calibration=UNCAL\r\n");
    Debug_UART_Write("[Boot] after probe\r\n");

    /* Application layer init */
    Debug_UART_Write("[Boot] ADS1115 probe address=0x48\r\n");
    s_ads1115_ready = (ADS1115_Init(&hi2c1) == HAL_OK) ? 1U : 0U;
    Debug_PrintADS1115InitResult(s_ads1115_ready);
    if (s_ads1115_ready == 0U)
    {
        Debug_UART_Write("[Boot] ADS1115 offline; pressure command will retry\r\n");
        BP_Control_RecordFault(BP_FAULT_SENSOR_INIT);
    }
    Debug_UART_Write("[Safety] MPXV5050GP range=0-375mmHg; adult BP 120/80 test supported\r\n");
#if BP_BRINGUP_RELAY_ONLY
    Debug_UART_Write("[Boot] Relay-only bring-up mode\r\n");
#endif
#if BP_BRINGUP_ENABLE_ESP8266
    printf("[Boot] ESP8266 init...\r\n");
    ESP8266_Init(&huart1);
    printf("[Boot] ESP8266 init done\r\n");
#else
    Debug_UART_Write("[ESP8266] Skipped for pump/pressure bring-up\r\n");
#endif
#if !BP_BRINGUP_RELAY_ONLY
    printf("[Boot] BP control init...\r\n");
    BP_Algorithm_Init();
#else
    PUMP_STOP();
    VALVE1_CLOSE();
    VALVE2_CLOSE();
    Debug_UART_Write("[Actuator] IDLE PB8=HIGH PC1=LOW PC8=HIGH\r\n");
#endif
    Boot_PressureSafetyCheck();
    (void)g_bp_result;   /* 预留结果存储，后续显示/上传使用 */

    Debug_UART_Write("\r\n[Blood Pressure Monitor] System Ready @ 72MHz\r\n");
    Debug_UART_Write("USART1=ESP8266, USART2=RS232, USART3=Debug\r\n");
    Debug_UART_Write("I2C1=ADS1115(0x48), PC8=Pump relay active-low\r\n");
    Debug_UART_Write("Commands: start stop open close vent seal pressure p help status pins fault stack\r\n");
    Debug_UART_Write("Commands: stream start | stream stop | cal | cal clear | cal write <slope> <intercept>\r\n");
    Debug_UART_Write("Commands: motor <dir 0/1> <steps> <freq 50-2000Hz> | motor stop\r\n");
    Debug_UART_Write("Commands: end with Enter\r\n\r\n");
    MX_IWDG_Init();
    Debug_UART_Write("[Safety] IWDG enabled nominal=4000ms debug-freeze=ON\r\n");
    s_pressure_stream_enabled = 1U;
    s_pressure_stream_last_ms = HAL_GetTick() - PRESSURE_STREAM_INTERVAL_MS;
    Debug_UART_Write("[Stream] auto-started every 250ms; use stream stop to disable\r\n");
    Debug_PrintFirmwareVersion();
    Debug_PrintStackWatermark();
    Boot_PrintResetCause();
    /* USER CODE END 2 */

    /* Infinite loop */
    /* USER CODE BEGIN WHILE */
    while (1)
    {
        /* USER CODE END WHILE */

        /* USER CODE BEGIN 3 */
        Debug_UART_RxTask();
        Process_DebugCommand();
#if BP_BRINGUP_ENABLE_BUTTONS
        Process_Buttons();     /* Non-blocking PA0/PA1 polling with debounce */
#endif
        ManualPump_TimeoutTask();
        HoldOpen_TimeoutTask();
        PulseDiagnostic_Task();
        ReadTest_Task();
        PressureStream_Task();
        BP_CalculationTask(); /* one batch, after command and safety/stream work */
        if (s_deflate_hold_until_ms != 0U)
        {
            uint32_t now = HAL_GetTick();
            if (now >= s_deflate_hold_until_ms)
            {
                s_deflate_hold_until_ms = 0U;
                s_deflate_pwm_enabled = 1U;
                s_deflate_next_pulse_ms = now;
                s_deflate_pwm_on_ms = DEFLATE_PWM_BASE_ON_MS;   /* 每次 deflate 重置，避免跨轮残留 */
                s_deflate_last_time_ms = now;
                s_deflate_last_pressure = g_last_pressure_mmhg;
                s_deflate_speed_prev = 0.0f;   /* 平滑速度跨轮重置 */
                s_algo_sample_last_ms = now;
                BP_Algorithm_Reset();   /* RELAY_ONLY 模式下 start 不走 BP_Control_Start，
                                          * 必须在每轮 deflate 开始处清零算法缓冲，
                                          * 否则 s_count 多轮累积满 800 后
                                          * 新样本进不去，结果用的是旧数据（run67-69 已证实）。 */
                BP_Algorithm_SetCaptureContext(2U, BP_Cal_IsValid(), BP_Cal_GetSlope(), BP_Cal_GetIntercept());
                Debug_UART_Write("[Deflate] PWM started after hold\r\n");
            }
            else
            {
                VALVE2_CLOSE();
            }
        }
        else if (s_deflate_pwm_enabled)
        {
            uint32_t now = HAL_GetTick();

            if ((s_deflate_test_active != 0U) &&
                ((now - s_deflate_test_start_ms) >= DEFLATE_TEST_DURATION_MS))
            {
                DeflateTest_Finish("timeout");
                continue;
            }

            /* Auto-stop when pressure drops below 15 mmHg.
             * 5→15：算法已含 12mmHg 低压截断（<12 数据不参与），deflate 无需
             * 放到 5；BP Pump 2 External 在低压段会维持 ~5-6mmHg 基础压力
             * （1.5cc 活塞持续注入），<5 结束条件可能永远达不到（run29 卡在
             * 5.6、deflate 46.8s 未结束）。低压验证 DBP=22.5 交叉点 ~23 在
             * 数据内（40→15）；成人 DBP=80 交叉点 ~82 远高于 15。 */
            if (g_last_pressure_mmhg < 15.0f)
            {
                DeflateControl_Cancel();
                VALVE2_CLOSE();
                Debug_UART_Write("[Deflate] done; valve2 closed\r\n");
                Debug_PrintCapture();

                /* Compute on subsequent iterations; command/ADS stream work
                 * continues between batches. The final valve stays closed. */
                s_calculation_pending = BP_Algorithm_BeginCalculate();
                if (s_calculation_pending == 0U)
                    Debug_UART_Write("[BP] calculation failed\r\n");

                /* Preserve the final closed-valve state. Do not execute one more
                 * PWM phase after declaring deflation complete. */
                continue;
            }

            /* Sample for algorithm every 25ms (40 Hz): read real ADS1115
             * pressure and sensor voltage so the oscillometric envelope is
             * computed from actual cuff pressure + superimposed pulse
             * oscillation. 10 ms was proven to stall the main loop because
             * each ADS1115 single conversion blocks for ~8-12 ms. */
            if ((now - s_algo_sample_last_ms) >= BP_SAMPLE_INTERVAL_MS)
            {
                s_algo_sample_last_ms = now;
                ADS1115_Sample_t sample;
                if (ADS1115_ReadSample(&sample) == HAL_OK)
                {
                    g_last_pressure_mmhg = sample.pressure_mmhg;
                    s_last_pressure_sample = sample;
                    s_last_pressure_sample_ms = HAL_GetTick();
                    s_last_pressure_sample_valid = 1U;
                    if ((s_deflate_test_active != 0U) &&
                        ((sample.pressure_mmhg < LOADED_PULSE_ABORT_MIN_MMHG) ||
                         (sample.pressure_mmhg > LOADED_PULSE_ABORT_MAX_MMHG)))
                    {
                        ManualPump_EmergencyStop(BP_FAULT_PRESSURE_RANGE);
                        Debug_UART_Write("[Safety] Deflate test pressure outside 20-85mmHg; emergency vent\r\n");
                        continue;
                    }
                    if (BP_Algorithm_AddSample(sample.pressure_mmhg,
                                               sample.sensor_voltage_v) == 0U)
                    {
                        ManualPump_EmergencyStop(BP_FAULT_SAMPLE_OVERFLOW);
                        Debug_UART_Write("[Safety] Sample overflow during deflate; emergency vent\r\n");
                        Debug_PrintCapture();
                        continue;
                    }
                    if ((s_deflate_test_active != 0U) &&
                        (sample.pressure_mmhg <= DEFLATE_TEST_STOP_MMHG))
                    {
                        DeflateTest_Finish("floor");
                        continue;
                    }
                }
                else
                {
                    s_ads1115_ready = 0U;
                    DeflateControl_Cancel();
                    BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
                    Debug_UART_Write("[Safety] Pressure read failed during deflate; emergency vent\r\n");
                    s_last_pressure_sample_valid = 0U;
                    Debug_PrintADS1115Diagnostics();
                    Debug_PrintCapture();
                    /* Preserve the emergency vent state; later PWM code must not
                     * overwrite PC1 in this loop iteration. */
                    continue;
                }
            }

            now = HAL_GetTick();
            if ((int32_t)(now - s_deflate_next_pulse_ms) >= 0)
            {
                DeflatePulse_Start(s_deflate_pwm_on_ms);
                /* Schedule from the actual start time.  If the main loop was
                 * delayed, do not emit catch-up pulses back-to-back. */
                s_deflate_next_pulse_ms = now + DEFLATE_PWM_PERIOD_MS;
            }

            /* Closed-loop: evaluate two complete valve periods before changing
             * the pulse width.  A shorter window measures individual valve
             * steps instead of the average deflation rate on rigid cuffs.
             * 速度一阶平滑 + 死区防抖：短时间差含压力振荡，直接按
             * actual_speed 调节会让 on_ms 在稳态附近来回 ±1，阀开时间抖动
             * 激起振铃（2026-09-29 真人实测 deflate 5-8s 第二波瞬态带通
             * 11781-16151 vs 脉搏 2000-3000）。平滑后 |err|<0.4 不调，
             * on_ms 保持稳定，放气斜率略偏（2.6-3.4/s）算法仍鲁棒。 */
            if ((now - s_deflate_last_time_ms) >= DEFLATE_CONTROL_INTERVAL_MS)
            {
                float dt = (now - s_deflate_last_time_ms) / 1000.0f;
                float actual_speed = (s_deflate_last_pressure - g_last_pressure_mmhg) / dt;
                /* Retain the established pressure-dependent deflation rate.
                 * Capacity expansion must not change this control rule.
                 * target writes are rejected while acquisition is active. */
                float target_speed = DeflateTargetSpeed();
                float smooth = 0.6f * actual_speed + 0.4f * s_deflate_speed_prev;
                s_deflate_speed_prev = smooth;
                float err = smooth - target_speed;

                if (err < -0.4f) { s_deflate_pwm_on_ms += 1U; }
                else if (err > 0.4f) { s_deflate_pwm_on_ms = (s_deflate_pwm_on_ms > 1U) ? (s_deflate_pwm_on_ms - 1U) : 1U; }

                if (s_deflate_test_active != 0U)
                {
                    if (s_deflate_pwm_on_ms > DEFLATE_TEST_MAX_ON_MS)
                        s_deflate_pwm_on_ms = DEFLATE_TEST_MAX_ON_MS;
                }
                else if (s_deflate_pwm_on_ms > DEFLATE_PWM_MAX_ON_MS)
                {
                    s_deflate_pwm_on_ms = DEFLATE_PWM_MAX_ON_MS;
                }

                s_deflate_last_pressure = g_last_pressure_mmhg;
                s_deflate_last_time_ms = now;

            }
        }
#if !BP_BRINGUP_RELAY_ONLY
        BP_Control_Task();   /* 状态机：充气/保压/放气/采样 */
        ESP8266_Task();      /* WiFi 数据上传任务 */
#endif
        if (BP_CaptureExport_IsActive() != 0U)
        {
            if (CaptureExport_IsSafe() == 0U) BP_CaptureExport_Cancel();
            else BP_CaptureExport_Task(Capture_UART_Write);
        }
        HAL_IWDG_Refresh(&hiwdg);
        /* USER CODE END 3 */
    }
}

/**
  * @brief System Clock Configuration
  *        HSE 8MHz → PLL ×9 → SYSCLK 72MHz
  *        AHB=72MHz, APB1=36MHz, APB2=72MHz
  */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    RCC_OscInitStruct.OscillatorType      = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState            = RCC_HSE_ON;
    RCC_OscInitStruct.HSEPredivValue      = RCC_HSE_PREDIV_DIV1;
    RCC_OscInitStruct.HSIState            = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState        = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource       = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLMUL          = RCC_PLL_MUL9;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_HCLK  | RCC_CLOCKTYPE_SYSCLK
                                     | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;   /* 36MHz */
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;   /* 72MHz */

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    {
        Error_Handler();
    }
}

/* USER CODE BEGIN 4 */
/**
  * @brief  EXTI line 5 — ADS1115 ALRT/DRDY callback
  */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == ADS_ALRT_Pin)
    {
        ADS1115_DataReadyCallback();
    }
}

/**
  * @brief  UART Rx callback — route to correct driver
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        ESP8266_RxCallback();
    }
    else if (huart->Instance == USART3)
    {
        /* HAL calls this BEFORE its error callback/ORE abort. Do not clear
         * ErrorCode by rearming or accept a byte from an errored frame. */
        if (huart->ErrorCode != HAL_UART_ERROR_NONE) return;
        Debug_CommandAcceptByte(s_rx3_byte);
        if (HAL_UART_Receive_IT(&huart3, &s_rx3_byte, 1U) != HAL_OK)
            Debug_CommandRejectLine();
    }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART3) return;

    if (s_uart3_rx_errors < UINT16_MAX) s_uart3_rx_errors++;
    Debug_CommandRejectLine();
    if ((s_pending_debug_cmd != DEBUG_CMD_STOP) &&
        (s_pending_debug_cmd != DEBUG_CMD_VALVE2_OPEN))
        s_pending_debug_cmd = DEBUG_CMD_NONE;
    /* F1 error flags clear by SR then DR read, including ORE without RXNE. */
    __HAL_UART_CLEAR_OREFLAG(huart);
    if (huart->RxState == HAL_UART_STATE_READY)
        (void)HAL_UART_Receive_IT(huart, &s_rx3_byte, 1U);
}
/* USER CODE END 4 */

void Error_Handler(void)
{
    /* USER CODE BEGIN Error_Handler_Debug */
    __disable_irq();
    /* TODO: flash LED or output error via debug UART */
    while (1) {}
    /* USER CODE END Error_Handler_Debug */
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    /* USER CODE BEGIN 6 */
    /* USER CODE END 6 */
}
#endif
