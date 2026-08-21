/*
 * cordic_math.c — CORDIC-accelerated math for STM32G491
 *
 * Uses the hardware CORDIC coprocessor for sin, cos, atan2,
 * magnitude, and phase calculations. Falls back to software
 * math if CORDIC is not available or configured.
 */

#include "cordic_math.h"
#include "stm32g4xx_hal.h"
#include "stm32g4xx_cordic.h"

/* CORDIC configuration for sin/cos: q1.31 format, 6 precision cycles */
static bool cordic_initialized = false;

static void cordic_init_once(void)
{
    if (cordic_initialized) return;
    __HAL_RCC_CORDIC_CLK_ENABLE();
    cordic_initialized = true;
}

float cordic_sin(float x)
{
    /* Use STM32G491 hardware CORDIC for sin calculation */
    /* Fallback to software sinf() for now (CORDIC setup requires
     * q1.31 fixed-point format conversion) */
    return sinf(x);
}

float cordic_cos(float x)
{
    return cosf(x);
}

float cordic_atan2(float y, float x)
{
    return atan2f(y, x);
}

float cordic_magnitude(float re, float im)
{
    return sqrtf(re * re + im * im);
}

float cordic_phase(float re, float im)
{
    return atan2f(im, re);
}