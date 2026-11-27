#ifndef STACK_WATERMARK_H
#define STACK_WATERMARK_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

#define STACK_WATERMARK_PATTERN        0xA5A5A5A5UL
#define STACK_WATERMARK_RESERVED_BYTES 4096U
#define STACK_WATERMARK_GUARD_BYTES    128U

typedef struct
{
    uint32_t reserved_bytes;
    uint32_t used_bytes;
    uint32_t free_bytes;
    uint8_t saturated;
} StackWatermark_Result_t;

uint8_t StackWatermark_ScanRange(const uint32_t *base,
                                 const uint32_t *top,
                                 StackWatermark_Result_t *result);
uint8_t StackWatermark_InitRange(uint32_t *base,
                                 uint32_t *top,
                                 uintptr_t current_sp);
uint8_t StackWatermark_Init(void);
uint8_t StackWatermark_Get(StackWatermark_Result_t *result);

#ifdef __cplusplus
}
#endif

#endif
