/*
 * onewire.c — DS18B20 1-Wire interface (bit-banged)
 */

#include "main.h"
#include "onewire.h"

#define ONEWIRE_GPIO_PORT  GPIOC
#define ONEWIRE_GPIO_PIN   GPIO_PIN_13

static void delay_us(uint32_t us)
{
    /* Approximate at 170 MHz: 170 cycles per µs */
    uint32_t cycles = us * 170 / 10;
    while (cycles--) {
        __NOP();
    }
}

int onewire_reset(void)
{
    int presence;

    HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_RESET);
    /* Set as output (already push-pull, we toggle) */
    GPIO_InitTypeDef gp = {0};
    gp.Pin = ONEWIRE_GPIO_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_OD; /* open-drain for 1-Wire */
    gp.Pull = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_GPIO_PORT, &gp);

    delay_us(480); /* reset pulse */

    /* Release bus (open-drain high) */
    HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_SET);
    delay_us(70);

    /* Read presence pulse */
    presence = (HAL_GPIO_ReadPin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN) == GPIO_PIN_RESET) ? 1 : 0;
    delay_us(410);

    return presence;
}

void onewire_write_byte(uint8_t byte)
{
    for (uint8_t i = 0; i < 8; i++) {
        HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_RESET);
        if (byte & 1) {
            delay_us(6);
            HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_SET);
            delay_us(64);
        } else {
            delay_us(60);
            HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_SET);
            delay_us(10);
        }
        byte >>= 1;
    }
}

uint8_t onewire_read_byte(void)
{
    uint8_t byte = 0;
    for (uint8_t i = 0; i < 8; i++) {
        HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_RESET);
        delay_us(6);
        HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_SET);
        delay_us(9);
        byte >>= 1;
        if (HAL_GPIO_ReadPin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN))
            byte |= 0x80;
        delay_us(55);
    }
    return byte;
}

int onewire_init(void)
{
    /* Configure GPIO as open-drain */
    GPIO_InitTypeDef gp = {0};
    gp.Pin = ONEWIRE_GPIO_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_OD;
    gp.Pull = GPIO_PULLUP;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_GPIO_PORT, &gp);

    HAL_GPIO_WritePin(ONEWIRE_GPIO_PORT, ONEWIRE_GPIO_PIN, GPIO_PIN_SET);
    HAL_Delay(10);

    return onewire_reset() ? 0 : -1;
}

float ds18b20_read_temp(void)
{
    if (onewire_reset() == 0) return -999.0f;

    /* Skip ROM (address all devices) */
    onewire_write_byte(0xCC);
    /* Convert T */
    onewire_write_byte(0x44);

    HAL_Delay(750); /* 12-bit conversion */

    if (onewire_reset() == 0) return -999.0f;

    onewire_write_byte(0xCC);
    /* Read scratchpad */
    onewire_write_byte(0xBE);

    uint8_t lsb = onewire_read_byte();
    uint8_t msb = onewire_read_byte();

    int16_t raw = ((int16_t)msb << 8) | lsb;
    return (float)raw / 16.0f;
}