/* No device I/O: exercise the exact main.c pressure formatter on the host. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ads1115.h"

static char transmitted[144];
static uint8_t calibration_valid;
static uint8_t BP_Control_IsCalibrationValid(void) { return calibration_valid; }
static void Debug_UART_Write(const char *text)
{
    assert(strlen(text) < sizeof(transmitted));
    strcpy(transmitted, text);
}
#include "pressure_record_under_test.h"

static void check_record(int raw, int ads, int sensor, float pressure)
{
    ADS1115_Sample_t sample = {0};
    char expected[144];
    size_t length;
    int32_t px10;
    sample.raw = (int16_t)raw;
    sample.ads_voltage_v = (float)ads / 1000.0f;
    sample.sensor_voltage_v = (float)sensor / 1000.0f;
    sample.pressure_mmhg = pressure;
    px10 = (int32_t)(pressure * 10.0f + 0.5f);
    snprintf(expected, sizeof(expected),
             "[Pressure] raw=%d ads=%ldmV sensor=%ldmV est=%ld.%01ldmmHg %s",
             raw, (long)ads, (long)sensor, (long)(px10 / 10L),
             (long)(px10 % 10L), calibration_valid ? "VALID" : "UNCAL");
    Debug_PrintPressureRecord(&sample);
    length = strlen(transmitted);
    /* Check record lengths only; this does not model USB packetization. */
    assert(length % 64U != 0U);
    assert(length < sizeof(transmitted));
    assert(length >= 2U && strcmp(transmitted + length - 2U, "\r\n") == 0);
    assert(strncmp(transmitted, expected, strlen(expected)) == 0);
    assert(length == strlen(expected) + 2U || length == strlen(expected) + 3U);
    if (length == strlen(expected) + 3U) {
        assert((strlen(expected) + 2U) % 64U == 0U);
        assert(transmitted[strlen(expected)] == ' ');
    }
}

int main(void)
{
    int raw, ads, sensor, flag;
    const float pressures[] = {0.0f, 0.1f, 9.9f, 10.0f, 93.6f, 94.2f, 99.9f, 100.0f, 150.0f, 375.0f};
    size_t p;
    for (flag = 0; flag <= 1; ++flag) {
        calibration_valid = (uint8_t)flag;
        /* Reproduce the two actual boundary records, then vary field widths. */
        check_record(8031, 1004, 1385, 94.2f);
        check_record(7992, 999, 1379, 93.6f);
        for (raw = 999; raw <= 10001; raw += 1000)
            for (ads = 995; ads <= 1005; ++ads)
                for (sensor = 995; sensor <= 1005; ++sensor)
                    for (p = 0; p < sizeof(pressures) / sizeof(pressures[0]); ++p)
                        check_record(raw, ads, sensor, pressures[p]);
    }
    puts("PASS pressure frame boundary/CRLF/field preservation");
    return 0;
}
