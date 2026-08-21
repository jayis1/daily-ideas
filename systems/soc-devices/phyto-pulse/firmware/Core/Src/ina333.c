/*
 * ina333.c — INA333 gain control via 74HC4051
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "ina333.h"
#include "main.h"

/* 74HC4051 select pins: A=PB11, B=PB12, C=PB13 */
#define GAIN_SEL0_Port  GAIN_SEL0_GPIO_Port
#define GAIN_SEL0_Pin   GAIN_SEL0_Pin
#define GAIN_SEL1_Port  GAIN_SEL1_GPIO_Port
#define GAIN_SEL1_Pin   GAIN_SEL1_Pin
#define GAIN_SEL2_Port  GAIN_SEL2_GPIO_Port
#define GAIN_SEL2_Pin   GAIN_SEL2_Pin

static ina333_gain_t g_current_gain = INA333_GAIN_101X;

void ina333_init(void)
{
    ina333_set_gain(INA333_GAIN_101X);
}

void ina333_set_gain(ina333_gain_t gain)
{
    g_current_gain = gain;

    /* 74HC4051 select: C:B:A → PB13:PB12:PB11 */
    HAL_GPIO_WritePin(GAIN_SEL0_Port, GAIN_SEL0_Pin,
                      (gain & 0x01) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GAIN_SEL1_Port, GAIN_SEL1_Pin,
                      (gain & 0x02) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GAIN_SEL2_Port, GAIN_SEL2_Pin,
                      (gain & 0x04) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    HAL_Delay(2);  /* mux settle + INA333 settle */
}

ina333_gain_t ina333_get_gain(void)
{
    return g_current_gain;
}

float ina333_get_gain_value(void)
{
    switch (g_current_gain) {
        case INA333_GAIN_2X:    return 2.0f;
        case INA333_GAIN_11X:   return 11.0f;
        case INA333_GAIN_101X:  return 101.0f;
        case INA333_GAIN_1001X: return 1001.0f;
        default: return 101.0f;
    }
}

float ina333_get_input_range(void)
{
    /* ADS1256 input range = ±Vref/PGA. INA input range = that / INA gain.
     * With PGA=64, Vref=2.5V: ADC input range = ±2.5/64 = ±39 mV.
     * At INA G=101: input range = ±39mV/101 = ±0.39 mV... wait, that's wrong.
     * Actually the ADC measures Vmid-referenced single-ended, range 0–Vref/PGA.
     * Let's use the practical input ranges from the README. */
    switch (g_current_gain) {
        case INA333_GAIN_2X:    return 2.5f;     /* ±2.5V */
        case INA333_GAIN_11X:   return 0.2f;     /* ±200mV */
        case INA333_GAIN_101X:  return 0.02f;    /* ±20mV */
        case INA333_GAIN_1001X: return 0.002f;   /* ±2mV */
        default: return 0.02f;
    }
}

bool ina333_auto_range(float peak_amplitude_v)
{
    /* Hysteresis: switch up at 80% of range, down at 10% */
    float range = ina333_get_input_range();
    ina333_gain_t new_gain = g_current_gain;
    bool changed = false;

    if (peak_amplitude_v > 0.8f * range) {
        /* Signal too large — reduce gain */
        if (g_current_gain > INA333_GAIN_2X) {
            new_gain = (ina333_gain_t)(g_current_gain - 1);
            changed = true;
        }
    } else if (peak_amplitude_v < 0.1f * range) {
        /* Signal too small — increase gain */
        if (g_current_gain < INA333_GAIN_1001X) {
            new_gain = (ina333_gain_t)(g_current_gain + 1);
            changed = true;
        }
    }

    if (changed) {
        ina333_set_gain(new_gain);
    }
    return changed;
}