#include "stack_watermark.h"

#include <stddef.h>
#include <stdint.h>

extern uint32_t __stack_base;
extern uint32_t __initial_sp;

static uint8_t s_stack_watermark_initialized = 0U;

uint8_t StackWatermark_InitRange(uint32_t *base,
                                 uint32_t *top,
                                 uintptr_t current_sp)
{
    uintptr_t base_addr = (uintptr_t)base;
    uintptr_t top_addr = (uintptr_t)top;
    uintptr_t fill_end_addr;
    volatile uint32_t *cursor;
    volatile uint32_t *fill_end;

    if ((base == NULL) || (top == NULL) ||
        (top_addr <= base_addr) ||
        ((top_addr - base_addr) != STACK_WATERMARK_RESERVED_BYTES) ||
        (current_sp <= (base_addr + STACK_WATERMARK_GUARD_BYTES)) ||
        (current_sp > top_addr))
    {
        return 0U;
    }

    fill_end_addr = (current_sp - STACK_WATERMARK_GUARD_BYTES) &
                    ~((uintptr_t)sizeof(uint32_t) - 1U);
    cursor = (volatile uint32_t *)base_addr;
    fill_end = (volatile uint32_t *)fill_end_addr;
    while (cursor < fill_end)
    {
        *cursor++ = STACK_WATERMARK_PATTERN;
    }
    return 1U;
}

uint8_t StackWatermark_Init(void)
{
    uintptr_t current_sp;

#if defined(__ARMCC_VERSION) && defined(__arm__)
    __asm volatile ("MRS %0, msp" : "=r" (current_sp));
#else
    current_sp = (uintptr_t)&__initial_sp;
#endif

    s_stack_watermark_initialized =
        StackWatermark_InitRange(&__stack_base, &__initial_sp, current_sp);
    return s_stack_watermark_initialized;
}

uint8_t StackWatermark_ScanRange(const uint32_t *base,
                                 const uint32_t *top,
                                 StackWatermark_Result_t *result)
{
    uintptr_t base_addr;
    uintptr_t top_addr;
    const volatile uint32_t *cursor;
    const volatile uint32_t *end;
    uint32_t reserved_bytes;
    uint32_t free_bytes;

    if (result == NULL)
    {
        return 0U;
    }

    result->reserved_bytes = 0U;
    result->used_bytes = 0U;
    result->free_bytes = 0U;
    result->saturated = 0U;

    base_addr = (uintptr_t)base;
    top_addr = (uintptr_t)top;
    if ((base == NULL) || (top == NULL) || (top_addr <= base_addr) ||
        (((top_addr - base_addr) & (sizeof(uint32_t) - 1U)) != 0U))
    {
        return 0U;
    }

    reserved_bytes = (uint32_t)(top_addr - base_addr);
    cursor = (const volatile uint32_t *)base_addr;
    end = (const volatile uint32_t *)top_addr;
    while ((cursor < end) && (*cursor == STACK_WATERMARK_PATTERN))
    {
        cursor++;
    }

    free_bytes = (uint32_t)((uintptr_t)cursor - base_addr);
    result->reserved_bytes = reserved_bytes;
    result->free_bytes = free_bytes;
    result->used_bytes = reserved_bytes - free_bytes;
    result->saturated = (free_bytes == 0U) ? 1U : 0U;
    return 1U;
}

uint8_t StackWatermark_Get(StackWatermark_Result_t *result)
{
    if (s_stack_watermark_initialized == 0U)
    {
        return 0U;
    }

    if (StackWatermark_ScanRange(&__stack_base, &__initial_sp, result) == 0U)
    {
        return 0U;
    }

    if (result->reserved_bytes != STACK_WATERMARK_RESERVED_BYTES)
    {
        result->reserved_bytes = 0U;
        result->used_bytes = 0U;
        result->free_bytes = 0U;
        result->saturated = 0U;
        return 0U;
    }

    return 1U;
}
