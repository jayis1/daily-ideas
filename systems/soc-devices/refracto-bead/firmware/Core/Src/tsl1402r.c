/**
 * tsl1402r.c — TSL1402R 256-pixel linear CCD driver
 *
 * Generates the CLK and SI signals via TIM2 and reads the analog output
 * (AO) via ADC1. Auto-exposure adjusts integration time to keep the
 * peak pixel value in the 30–90% full-scale range.
 */

#include "tsl1402r.h"
#include <string.h>

static TIM_HandleTypeDef *s_htim = NULL;
static ADC_HandleTypeDef *s_hadc = NULL;
static volatile uint32_t s_integration_us = 2000;  /* Default 2 ms */
static volatile uint8_t s_adc_dma_done = 0;

/* ADC DMA buffer for single-channel continuous read */
static uint16_t s_adc_val = 0;

void tsl1402r_init(TIM_HandleTypeDef *htim, ADC_HandleTypeDef *hadc) {
    s_htim = htim;
    s_hadc = hadc;

    /* Start CLK PWM on TIM2_CH1 (PA1) */
    HAL_TIM_PWM_Start(s_htim, TIM_CHANNEL_1);

    /* Ensure SI is low (TIM2_CH2 pulse = 0) */
    HAL_TIM_PWM_Stop(s_htim, TIM_CHANNEL_2);
}

void tsl1402r_set_integration(uint32_t us) {
    if (us < 500) us = 500;
    if (us > 10000) us = 10000;
    s_integration_us = us;
}

uint32_t tsl1402r_get_integration(void) {
    return s_integration_us;
}

/* Generate a single SI pulse (one CLK cycle high) */
static void generate_si_pulse(void) {
    /* Set CH2 pulse width to 1 CLK period (84 ticks at 1 MHz) */
    __HAL_TIM_SET_COMPARE(s_htim, TIM_CHANNEL_2, 42);

    /* Start CH2 PWM for exactly one period — use one-pulse mode */
    /* For simplicity, we toggle the GPIO directly */
    HAL_TIM_PWM_Stop(s_htim, TIM_CHANNEL_1);

    /* Manual SI pulse on PA2 */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, GPIO_PIN_SET);

    /* Start CLK again */
    HAL_TIM_PWM_Start(s_htim, TIM_CHANNEL_1);

    /* Wait one CLK cycle (1 µs) */
    /* At 170 MHz, ~170 NOPs = 1 µs */
    for (volatile int i = 0; i < 50; i++);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_2, GPIO_PIN_RESET);
}

/* Read a single ADC sample from channel 1 (PA0) */
static uint16_t read_adc_channel(uint32_t channel) {
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = channel;
    ch.Rank = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_1CYCLE_5;
    HAL_ADC_ConfigChannel(s_hadc, &ch);

    HAL_ADC_Start(s_hadc);
    HAL_ADC_PollForConversion(s_hadc, 10);
    uint16_t val = (uint16_t)HAL_ADC_GetValue(s_hadc);
    HAL_ADC_Stop(s_hadc);
    return val;
}

void tsl1402r_read(uint16_t *buffer) {
    if (!s_htim || !s_hadc || !buffer) return;

    /* Step 1: Generate SI pulse to start integration + readout */
    generate_si_pulse();

    /* Step 2: Wait for integration time (measured from SI pulse) */
    /* The integration happens during the 256-CLK readout cycle. */
    /* After the 256th clock, we can add a delay for longer integration. */
    uint32_t clk_cycles_elapsed = 256;  /* 256 µs at 1 MHz */

    if (s_integration_us > clk_cycles_elapsed) {
        uint32_t extra_delay = s_integration_us - clk_cycles_elapsed;
        HAL_Delay(extra_delay / 1000);  /* ms resolution (simplified) */
        /* For µs precision, use a busy-wait loop */
    }

    /* Step 3: Generate second SI pulse to start the actual readout */
    generate_si_pulse();

    /* Step 4: Clock out 256 pixels, sampling AO on each clock cycle */
    /* We read the ADC 256 times, synchronized to the CLK falling edge */
    for (int i = 0; i < TSL1402R_NUM_PIXELS; i++) {
        /* Wait for CLK rising edge, then sample on falling edge */
        /* The AO settles ~50 ns after CLK rising edge */
        for (volatile int j = 0; j < 10; j++);  /* Brief settle delay */

        buffer[i] = read_adc_channel(ADC_CHANNEL_1);
    }

    /* Step 5: Auto-exposure — adjust integration time based on peak value */
    uint16_t peak = 0;
    for (int i = 10; i < TSL1402R_NUM_PIXELS - 10; i++) {
        if (buffer[i] > peak) peak = buffer[i];
    }

    uint16_t target_lo = TSL1402R_ADC_MAX * 30 / 100;  /* 30% */
    uint16_t target_hi = TSL1402R_ADC_MAX * 90 / 100;  /* 90% */

    if (peak > target_hi && s_integration_us > 500) {
        /* Too bright — reduce integration time */
        s_integration_us = s_integration_us * 80 / 100;
        if (s_integration_us < 500) s_integration_us = 500;
    } else if (peak < target_lo && s_integration_us < 10000) {
        /* Too dim — increase integration time */
        s_integration_us = s_integration_us * 120 / 100;
        if (s_integration_us > 10000) s_integration_us = 10000;
    }
}