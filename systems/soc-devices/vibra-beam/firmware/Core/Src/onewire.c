/*
 * onewire.c — DS18B20 1-Wire bit-banged driver (PC8)
 */

#include "onewire.h"
#include "stm32g4xx_hal.h"
#include "config.h"
#include <string.h>

#define ONEWIRE_PORT  CONFIG_DS18B20_GPIO_PORT
#define ONEWIRE_PIN   CONFIG_DS18B20_GPIO_PIN

static void ow_delay_us(uint32_t us)
{
    uint32_t ticks = us * (SystemCoreClock / 1000000U) / 8;
    while (ticks--) __NOP();
}

static void ow_output(void)
{
    GPIO_InitTypeDef gp = {0};
    gp.Pin = ONEWIRE_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_OD;
    gp.Pull = GPIO_PULLUP;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_PORT, &gp);
}

static void ow_input(void)
{
    GPIO_InitTypeDef gp = {0};
    gp.Pin = ONEWIRE_PIN;
    gp.Mode = GPIO_MODE_INPUT;
    gp.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ONEWIRE_PORT, &gp);
}

static uint8_t ow_reset(void)
{
    ow_output();
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_RESET);
    ow_delay_us(480);
    ow_input();
    ow_delay_us(70);
    uint8_t presence = (HAL_GPIO_ReadPin(ONEWIRE_PORT, ONEWIRE_PIN) == GPIO_PIN_RESET);
    ow_delay_us(410);
    return presence;
}

static void ow_write_bit(uint8_t bit)
{
    ow_output();
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_RESET);
    ow_delay_us(bit ? 6 : 60);
    if (bit) {
        ow_input();
        ow_delay_us(64);
    } else {
        ow_input();
        ow_delay_us(10);
    }
}

static uint8_t ow_read_bit(void)
{
    ow_output();
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_RESET);
    ow_delay_us(4);
    ow_input();
    ow_delay_us(10);
    uint8_t b = HAL_GPIO_ReadPin(ONEWIRE_PORT, ONEWIRE_PIN);
    ow_delay_us(50);
    return b;
}

static void ow_write_byte(uint8_t b)
{
    for (int i = 0; i < 8; i++) ow_write_bit((b >> i) & 1);
}

static uint8_t ow_read_byte(void)
{
    uint8_t b = 0;
    for (int i = 0; i < 8; i++) b |= (ow_read_bit() << i);
    return b;
}

void onewire_init(void)
{
    ow_input();
}

float onewire_read_temp_c(void)
{
    if (!ow_reset()) return -999.0f;
    ow_write_byte(0xCC);  /* skip ROM */
    ow_write_byte(0x44);  /* convert T */
    HAL_Delay(750);

    ow_reset();
    ow_write_byte(0xCC);
    ow_write_byte(0xBE);  /* read scratchpad */

    uint8_t lsb = ow_read_byte();
    uint8_t msb = ow_read_byte();
    int16_t raw = (msb << 8) | lsb;
    return (float)raw / 16.0f;
}