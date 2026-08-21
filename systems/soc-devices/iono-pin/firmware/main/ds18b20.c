/*
 * ds18b20.c — DS18B20 1-Wire drift-tube wall temperature
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * One-Wire on PB6 (open-drain). Provides drift-gas temperature for K0
 * normalization (more representative than ambient BME280 temp).
 *
 * SPDX-License-Identifier: MIT
 */
#include "ds18b20.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

#define OW_PIN      GPIO_PIN_6
#define OW_PORT     GPIOB

static void ow_set_output(void)
{
    GPIO_InitTypeDef io = {0};
    io.Pin = OW_PIN; io.Mode = GPIO_MODE_OUTPUT_OD; io.Pull = GPIO_NOPULL;
    io.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(OW_PORT, &io);
}
static void ow_set_input(void)
{
    GPIO_InitTypeDef io = {0};
    io.Pin = OW_PIN; io.Mode = GPIO_MODE_INPUT; io.Pull = GPIO_PULLUP;
    io.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(OW_PORT, &io);
}
static int ow_read(void) { return HAL_GPIO_ReadPin(OW_PORT, OW_PIN); }
static void ow_low(void) { HAL_GPIO_WritePin(OW_PORT, OW_PIN, GPIO_PIN_RESET); }
static void ow_high(void){ HAL_GPIO_WritePin(OW_PORT, OW_PIN, GPIO_PIN_SET); }

static int ow_reset(void)
{
    ow_set_output(); ow_low();
    for (volatile int i = 0; i < 600; i++) __NOP();   /* ~480us @170MHz */
    ow_set_input();
    for (volatile int i = 0; i < 70; i++) __NOP();    /* ~70us */
    int presence = (ow_read() == 0);
    for (volatile int i = 0; i < 500; i++) __NOP();   /* ~410us */
    return presence;
}
static void ow_write_bit(int b)
{
    ow_set_output(); ow_low();
    for (volatile int i = 0; i < 6; i++) __NOP();
    if (b) { ow_high(); }
    for (volatile int i = 0; i < 64; i++) __NOP();
    ow_high(); ow_set_input();
}
static int ow_read_bit(void)
{
    ow_set_output(); ow_low();
    for (volatile int i = 0; i < 4; i++) __NOP();
    ow_set_input();
    for (volatile int i = 0; i < 8; i++) __NOP();
    int b = ow_read();
    for (volatile int i = 0; i < 60; i++) __NOP();
    return b;
}
static void ow_write(uint8_t b)
{
    for (int i = 0; i < 8; i++) { ow_write_bit(b & 1); b >>= 1; }
}
static uint8_t ow_read_byte(void)
{
    uint8_t b = 0;
    for (int i = 0; i < 8; i++) { b >>= 1; if (ow_read_bit()) b |= 0x80; }
    return b;
}

void ds18b20_init(void)
{
    ow_set_input();
}

bool ds18b20_read(float *temp_c)
{
    if (!ow_reset()) return false;
    ow_write(0xCC);   /* skip ROM */
    ow_write(0x44);   /* convert T */
    HAL_Delay(750);
    if (!ow_reset()) return false;
    ow_write(0xCC);
    ow_write(0xBE);
    uint8_t s[9];
    for (int i = 0; i < 9; i++) s[i] = ow_read_byte();
    int16_t raw = (int16_t)(s[0] | (s[1] << 8));
    if (temp_c) *temp_c = (float)raw / 16.0f;
    return true;
}