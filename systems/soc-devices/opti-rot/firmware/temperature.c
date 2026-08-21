/*
 * temperature.c — DS18B20 1-Wire temperature sensor driver
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Implements a bit-banged 1-Wire protocol on PC0 to read the
 * DS18B20 digital temperature sensor. The sensor is mounted in
 * the sample chamber wall to measure the temperature of the
 * liquid under test for specific-rotation compensation.
 *
 * 1-Wire timing is critical — all delays are in microseconds
 * and must not be interrupted. We disable interrupts during
 * critical timing windows.
 */
#include "stm32g4xx_hal.h"
#include <string.h>
#include "sdkconfig.h"
#include "temperature.h"

#define DS_GPIO_PORT   GPIOC
#define DS_GPIO_PIN    GPIO_PIN_0

/* 1-Wire commands */
#define OW_SKIP_ROM    0xCC
#define OW_CONVERT_T    0x44
#define OW_READ_SCRATCH 0xBE

static uint8_t present = 0;

/* ---- Microsecond delay (cycle-counted for 170 MHz) ---- */

static inline void delay_us(uint32_t us)
{
    /* TIM6 or DWT cycle counter. Use DWT for precise timing. */
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start) < cycles);
}

/* ---- 1-Wire low-level ---- */

static void ow_pin_output(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin  = DS_GPIO_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(DS_GPIO_PORT, &GPIO_InitStruct);
}

static void ow_pin_input(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin  = DS_GPIO_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(DS_GPIO_PORT, &GPIO_InitStruct);
}

static void ow_low(void)
{
    HAL_GPIO_WritePin(DS_GPIO_PORT, DS_GPIO_PIN, GPIO_PIN_RESET);
}

static void ow_high(void)
{
    HAL_GPIO_WritePin(DS_GPIO_PORT, DS_GPIO_PIN, GPIO_PIN_SET);
}

static uint8_t ow_read(void)
{
    return (HAL_GPIO_ReadPin(DS_GPIO_PORT, DS_GPIO_PIN) == GPIO_PIN_SET) ? 1 : 0;
}

/* Reset pulse — returns 1 if device present */
static uint8_t ow_reset(void)
{
    uint8_t presence;

    __disable_irq();
    ow_pin_output();
    ow_low();
    delay_us(500);                  /* 500 µs reset pulse */
    ow_pin_input();
    delay_us(70);                    /* wait for presence pulse */
    presence = !ow_read();           /* low = device present */
    __enable_irq();
    delay_us(430);                   /* complete reset slot */
    return presence;
}

static void ow_write_bit(uint8_t bit)
{
    __disable_irq();
    ow_pin_output();
    ow_low();
    if (bit) {
        delay_us(6);
        ow_pin_input();
        delay_us(64);
    } else {
        delay_us(60);
        ow_pin_input();
        delay_us(10);
    }
    __enable_irq();
}

static uint8_t ow_read_bit(void)
{
    uint8_t bit;
    __disable_irq();
    ow_pin_output();
    ow_low();
    delay_us(4);
    ow_pin_input();
    delay_us(8);
    bit = ow_read();
    __enable_irq();
    delay_us(52);
    return bit;
}

static void ow_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 1);
        byte >>= 1;
    }
}

static uint8_t ow_read_byte(void)
{
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte >>= 1;
        if (ow_read_bit())
            byte |= 0x80;
    }
    return byte;
}

/* ---- Public API ---- */

void temperature_init(void)
{
    /* Enable GPIO port C clock */
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Enable DWT cycle counter for microsecond timing */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    /* Detect sensor */
    present = ow_reset();
}

uint8_t temperature_is_present(void)
{
    return present;
}

double temperature_read(void)
{
    if (!present)
        return 20.0;  /* default if no sensor */

    /* Issue temperature conversion */
    ow_reset();
    ow_write_byte(OW_SKIP_ROM);
    ow_write_byte(OW_CONVERT_T);

    HAL_Delay(DS18B20_CONV_TIME_MS);  /* 750 ms for 12-bit */

    /* Read scratchpad */
    ow_reset();
    ow_write_byte(OW_SKIP_ROM);
    ow_write_byte(OW_READ_SCRATCH);

    uint8_t temp_lsb = ow_read_byte();
    uint8_t temp_msb = ow_read_byte();

    /* 12-bit resolution: temp = (msb << 8 | lsb) / 16.0 */
    int16_t raw = (int16_t)((temp_msb << 8) | temp_lsb);
    double temp_c = (double)raw / 16.0;

    return temp_c;
}