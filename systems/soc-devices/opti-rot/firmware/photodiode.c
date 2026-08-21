/*
 * photodiode.c — TSL257 light-to-voltage sensor driver
 * Opti Rot — Pocket Digital Polarimeter
 *
 * The TSL257 converts light intensity to an analog voltage (0 to Vcc)
 * with a built-in transimpedance amplifier. Output is linearly
 * proportional to irradiance. We read it via ADC1 Channel 2 (PA2)
 * with oversampling for noise reduction.
 *
 * The TSL257 is powered from the ultra-low-noise LP5907-3.3 LDO to
 * minimize noise on the photodiode output. The ADC reference is the
 * 3.3V analog rail (same supply, ratiometric measurement).
 */
#include "stm32g4xx_hal.h"
#include "sdkconfig.h"
#include "photodiode.h"

extern ADC_HandleTypeDef hadc1;

void photodiode_init(void)
{
    /* ADC channel 2 (PA2) is configured in main.c ADC1_Init().
     * Configure the specific channel here. */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel       = PHOTODIODE_ADC_CHANNEL;
    sConfig.Rank           = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime   = ADC_SAMPLETIME_247CYCLES_5;  /* long for noise */
    sConfig.SingleDiff     = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber   = ADC_OFFSET_NONE;
    sConfig.Offset         = 0;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
}

uint16_t photodiode_read_raw(void)
{
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, HAL_MAX_DELAY);
    uint16_t value = (uint16_t)HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    return value;
}

uint16_t photodiode_oversample(uint16_t n)
{
    uint32_t sum = 0;
    for (uint16_t i = 0; i < n; i++) {
        sum += photodiode_read_raw();
    }
    return (uint16_t)(sum / n);
}

double photodiode_read_normalized(void)
{
    uint16_t raw = photodiode_oversample(PHOTODIODE_OVERSAMPLE_N);
    return (double)raw / (double)PHOTODIODE_ADC_MAX;
}

uint8_t photodiode_signal_ok(void)
{
    return photodiode_oversample(20) > MALUS_FIT_MIN_INTENSITY;
}