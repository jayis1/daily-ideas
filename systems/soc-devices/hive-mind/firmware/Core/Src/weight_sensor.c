/*
 * Hive Mind — Weight Sensor Driver
 * HX711 24-bit ADC + 50 kg load cell
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "weight_sensor.h"
#include "main.h"

#define HX711_GAIN_128  25  /* 25 clock pulses for channel A, gain 128 */
#define HX711_GAIN_64   27  /* 27 clock pulses for channel A, gain 64 */

static int32_t offset = 0;
static float scale_factor = 1.0f;  /* counts per gram */

extern GPIO_TypeDef *HX711_DOUT_PORT;
extern uint16_t HX711_DOUT_PIN;
extern GPIO_TypeDef *HX711_SCK_PORT;
extern uint16_t HX711_SCK_PIN;
extern GPIO_TypeDef *HX711_PWR_PORT;
extern uint16_t HX711_PWR_PIN;

/* ------------------------------------------------------------------ */
/* Private helpers                                                     */
/* ------------------------------------------------------------------ */

static void hx711_sck_pulse(void)
{
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
    /* 1 µs minimum pulse width at 48 MHz = ~48 cycles */
    for (volatile int i = 0; i < 5; i++) __NOP();
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
    for (volatile int i = 0; i < 5; i++) __NOP();
}

static int32_t hx711_read_raw(void)
{
    int32_t value = 0;

    /* Wait for DOUT to go low (data ready) — timeout 100 ms */
    uint32_t timeout = HAL_GetTick() + 100;
    while (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN) == GPIO_PIN_SET) {
        if (HAL_GetTick() > timeout) {
            return 0;  /* Timeout */
        }
    }

    /* Read 24 bits MSB first */
    for (int i = 0; i < 24; i++) {
        hx711_sck_pulse();
        value <<= 1;
        if (HAL_GPIO_ReadPin(HX711_DOUT_PORT, HX711_DOUT_PIN) == GPIO_PIN_SET) {
            value |= 1;
        }
    }

    /* Set gain for next reading (channel A, gain 128 = 25 pulses) */
    for (int i = 0; i < 1; i++) {
        hx711_sck_pulse();
    }

    /* Convert from 24-bit two's complement */
    if (value & 0x800000) {
        value |= 0xFF000000;  /* Sign extend */
    }

    return value;
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void weight_sensor_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable HX711 power (PB7) */
    HAL_GPIO_WritePin(HX711_PWR_PORT, HX711_PWR_PIN, GPIO_PIN_SET);

    /* Configure PD_SCK as output (PA2) */
    GPIO_InitStruct.Pin = HX711_SCK_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(HX711_SCK_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);

    /* Configure DOUT as input (PA1) */
    GPIO_InitStruct.Pin = HX711_DOUT_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(HX711_DOUT_PORT, &GPIO_InitStruct);

    /* Wait for HX711 to power up and stabilize */
    HAL_Delay(500);

    /* Default scale factor for 50 kg load cell:
     * HX711 at gain 128 = ~430 counts per mV
     * Load cell rated output: 1.0 mV/V at 50 kg
     * With 3.3 V excitation: 1.0 * 3.3 = 3.3 mV full scale
     * Counts at 50 kg ≈ 430 * 3.3 ≈ 1419
     * Scale factor ≈ 1419 / 50000 g ≈ 0.02838 counts/g
     * So grams = raw / 0.02838 = raw * 35.24
     * User should calibrate with known weight. */
    scale_factor = 35.24f;
    offset = 0;

    /* Take initial readings to discard */
    for (int i = 0; i < 5; i++) {
        hx711_read_raw();
    }
}

void weight_sensor_tare(void)
{
    /* Average 10 readings for tare */
    int32_t sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += hx711_read_raw();
        HAL_Delay(10);
    }
    offset = sum / 10;
}

float weight_sensor_read_grams(void)
{
    /* Take 3 readings and average for noise reduction */
    int32_t sum = 0;
    for (int i = 0; i < 3; i++) {
        sum += hx711_read_raw();
    }
    int32_t avg = sum / 3;

    /* Convert to grams */
    float grams = (float)(avg - offset) * scale_factor;
    if (grams < 0.0f) grams = 0.0f;

    return grams;
}

void weight_sensor_set_calibration(float known_weight_grams)
{
    /* Call with a known weight on the scale.
     * Takes the current raw reading and sets the scale factor
     * so that the current reading = known_weight_grams. */
    int32_t sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += hx711_read_raw();
        HAL_Delay(10);
    }
    int32_t avg = sum / 10;
    int32_t net = avg - offset;

    if (net != 0 && known_weight_grams > 0.0f) {
        scale_factor = known_weight_grams / (float)net;
    }
}

void weight_sensor_power_off(void)
{
    /* Put HX711 to sleep by holding PD_SCK high for >60 µs */
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_SET);
    HAL_Delay(1);
}

void weight_sensor_power_on(void)
{
    /* Wake up HX711 by setting PD_SCK low */
    HAL_GPIO_WritePin(HX711_SCK_PORT, HX711_SCK_PIN, GPIO_PIN_RESET);
    HAL_Delay(500);  /* Wait for stabilization */
}