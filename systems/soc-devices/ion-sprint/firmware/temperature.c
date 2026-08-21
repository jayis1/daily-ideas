/*
 * temperature.c — DS18B20 1-Wire temperature sensor
 *
 * PC6 (1-Wire bus) reads DS18B20 for BGE/carrier temperature.
 * Used for electrophoretic mobility correction (2% per °C).
 */

#include "temperature.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static float last_temp = 25.0f;

/* 1-Wire bit-bang on PC6 */
static void ow_low(void)
{
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (6u * 2u))) | (1u << (6u * 2u));
    GPIOC->BSRR = (1u << (6 + 16));  /* Low */
}

static void ow_release(void)
{
    GPIOC->MODER &= ~(3u << (6u * 2u));  /* Input (pull-up) */
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (6u * 2u))) | (1u << (6u * 2u));
}

static uint8_t ow_read(void)
{
    ow_release();
    for (volatile int i = 0; i < 10; i++) ;
    return (GPIOC->IDR & (1u << 6)) ? 1 : 0;
}

static void ow_write_bit(uint8_t bit)
{
    ow_low();
    for (volatile int i = 0; i < (bit ? 1 : 30); i++) ;
    ow_release();
    for (volatile int i = 0; i < 50; i++) ;
}

static uint8_t ow_read_bit(void)
{
    ow_low();
    for (volatile int i = 0; i < 2; i++) ;
    ow_release();
    for (volatile int i = 0; i < 5; i++) ;
    uint8_t bit = ow_read();
    for (volatile int i = 0; i < 50; i++) ;
    return bit;
}

static uint8_t ow_reset(void)
{
    ow_low();
    for (volatile int i = 0; i < 500; i++) ;  /* ~480 µs */
    ow_release();
    for (volatile int i = 0; i < 50; i++) ;   /* ~65 µs */
    uint8_t presence = ow_read() ? 0 : 1;     /* Low = present */
    for (volatile int i = 0; i < 400; i++) ;
    return presence;
}

static uint8_t ow_read_byte(void)
{
    uint8_t val = 0;
    for (int i = 0; i < 8; i++) {
        val >>= 1;
        if (ow_read_bit()) val |= 0x80;
    }
    return val;
}

static void ow_write_byte(uint8_t val)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(val & 1);
        val >>= 1;
    }
}

void temperature_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    ow_release();
    last_temp = 25.0f;
}

float temperature_read(void)
{
    if (!ow_reset()) return last_temp;  /* No sensor */

    ow_write_byte(0xCC);  /* Skip ROM */
    ow_write_byte(0x44);  /* Convert T */
    for (volatile int i = 0; i < 800000; i++) ;  /* ~750 ms */

    if (!ow_reset()) return last_temp;
    ow_write_byte(0xCC);
    ow_write_byte(0xBE);  /* Read scratchpad */

    uint8_t lsb = ow_read_byte();
    uint8_t msb = ow_read_byte();
    int16_t raw = (int16_t)((msb << 8) | lsb);
    last_temp = (float)raw / 16.0f;
    return last_temp;
}

float temperature_mobility_correction(float temp_c)
{
    return 1.0f + MT_NORM_TEMP_COEF * (temp_c - BGE_TEMP_REF_C);
}