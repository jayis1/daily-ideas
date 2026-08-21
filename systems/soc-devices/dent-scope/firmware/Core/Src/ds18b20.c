/*
 * dent-scope / Core/Src/ds18b20.c
 * Dent Scope — DS18B20 1-wire temperature sensor
 * MIT License.
 */
#include "ds18b20.h"

#define ONEWIRE_PORT_IN()  HAL_GPIO_ReadPin(ONEWIRE_PORT, ONEWIRE_PIN)

static void ow_delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start) < cycles);
}

static void ow_drive_low(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = ONEWIRE_PIN; g.Mode = GPIO_MODE_OUTPUT_OD; g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_PORT, &g);
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_RESET);
}

static void ow_release(void)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = ONEWIRE_PIN; g.Mode = GPIO_MODE_OUTPUT_OD; g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_PORT, &g);
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_SET);
}

static int ow_reset(void)
{
    ow_drive_low();
    ow_delay_us(480);
    ow_release();
    ow_delay_us(70);
    int presence = (ONEWIRE_PORT_IN() == 0);
    ow_delay_us(410);
    return presence;
}

static void ow_write_bit(int bit)
{
    ow_drive_low();
    if (bit) {
        ow_delay_us(6);
        ow_release();
        ow_delay_us(64);
    } else {
        ow_delay_us(60);
        ow_release();
        ow_delay_us(10);
    }
}

static int ow_read_bit(void)
{
    ow_drive_low();
    ow_delay_us(4);
    ow_release();
    ow_delay_us(10);
    int bit = ONEWIRE_PORT_IN() ? 1 : 0;
    ow_delay_us(50);
    return bit;
}

static void ow_write(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 0x01);
        byte >>= 1;
    }
}

static uint8_t ow_read(void)
{
    uint8_t val = 0;
    for (int i = 0; i < 8; i++)
        val |= (ow_read_bit() << i);
    return val;
}

void ds18b20_init(void)
{
    /* enable DWT cycle counter for precise timing */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

float ds18b20_read_temp(void)
{
    if (!ow_reset()) return -1000.0f;
    ow_write(0xCC); /* skip ROM */
    ow_write(0x44); /* convert T */
    HAL_Delay(750); /* 12-bit conversion max 750 ms */

    if (!ow_reset()) return -1000.0f;
    ow_write(0xCC);
    ow_write(0xBE); /* read scratchpad */

    uint8_t lo = ow_read();
    uint8_t hi = ow_read();
    /* skip remaining 7 bytes (could read CRC) */
    for (int i = 0; i < 7; i++) ow_read();

    int16_t raw = (hi << 8) | lo;
    /* 12-bit resolution: raw / 16 = °C */
    return (float)raw / 16.0f;
}