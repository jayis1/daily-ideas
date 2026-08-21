/*
 * hall-puck / firmware / Core / Src / current_source.c
 * Programmable precision current source (Howland pump)
 *
 * STM32 internal DAC1 → OPA2188 Howland current pump
 * Two ranges: 1µA–100µA (low, 100kΩ sense) and 100µA–10mA (high, 1kΩ sense)
 *
 * MIT License.
 */
#include "current_source.h"
#include "main.h"

/* DAC1 is 12-bit: 0–4095 → 0–3.3V */
#define DAC_MAX_CODE    4095
#define DAC_VREF        3.3f

/* Howland pump: I_out = V_dac * (R_feedback / R_sense) / R_set
 * With R_set = 1kΩ (high range): I = V_dac / 1kΩ × gain
 * With R_set = 100kΩ (low range): I = V_dac / 100kΩ × gain
 *
 * Simplified model:
 *   High range: I = V_dac / 330 (→ 3.3V/330Ω = 10mA max)
 *   Low range:  I = V_dac / 33000 (→ 3.3V/33kΩ = 100µA max)
 */
#define HIGH_RANGE_FACTOR   330.0f       /* V/Ω → 10mA at 3.3V */
#define LOW_RANGE_FACTOR    33000.0f     /* V/Ω → 100µA at 3.3V */

static float set_current_ma = 0.0f;
static uint8_t current_range = I_RANGE_HIGH;
static bool enabled = false;

i_src_err_t current_source_init(void)
{
    /* Enable GPIO clocks and configure pins */
    /* PA4: DAC1_OUT (analog) — configured by DAC peripheral */
    /* PA2: I_RANGE_SEL — output */
    /* PA3: I_ENABLE — output */
    /* PA0: I_SENSE_MON — analog input (ADC) */

    /* Configure range select + enable pins as push-pull output */
    GPIOA->MODER &= ~(3 << (I_RANGE_SEL_PIN * 2) | 3 << (I_ENABLE_PIN * 2));
    GPIOA->MODER |= (1 << (I_RANGE_SEL_PIN * 2) | 1 << (I_ENABLE_PIN * 2));

    /* Default: disabled, high range */
    GPIOA->BSRR = (1 << I_ENABLE_PIN) << 16;  /* low = disabled */
    GPIOA->BSRR = (1 << I_RANGE_SEL_PIN) << 16; /* low = high range */
    enabled = false;

    /* Enable DAC1 channel 1 */
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;  /* ensure clocks */
    /* DAC clock enable (APB1) */
    RCC->APB1ENR1 |= RCC_APB1ENR1_DAC1EN;

    /* Configure DAC1 channel 1: enable, no trigger, no DMA */
    DAC1->CR = 0;
    DAC1->MCR = 0;  /* external pin + internal */
    DAC1->CR |= DAC_CR_EN1;

    /* Set initial output to 0 */
    DAC1->DHR12R1 = 0;

    return I_SRC_OK;
}

i_src_err_t current_source_set(float current_ma)
{
    if (current_ma < 0.001f || current_ma > I_MAX_MA)
        return I_SRC_ERR_RANGE;

    set_current_ma = current_ma;

    /* Select range: < 100µA → low range, ≥ 100µA → high range */
    if (current_ma < 0.1f) {
        current_range = I_RANGE_LOW;
        GPIOA->BSRR = (1 << I_RANGE_SEL_PIN);  /* high = low range */
    } else {
        current_range = I_RANGE_HIGH;
        GPIOA->BSRR = (1 << I_RANGE_SEL_PIN) << 16; /* low = high range */
    }

    /* Compute DAC code */
    float factor = (current_range == I_RANGE_LOW) ?
                    LOW_RANGE_FACTOR : HIGH_RANGE_FACTOR;
    float v_dac = current_ma * 1e-3f * factor;  /* mA → A × Ω = V */
    if (v_dac > DAC_VREF) v_dac = DAC_VREF;

    uint16_t dac_code = (uint16_t)((v_dac / DAC_VREF) * DAC_MAX_CODE);
    if (dac_code > DAC_MAX_CODE) dac_code = DAC_MAX_CODE;

    DAC1->DHR12R1 = dac_code;

    return I_SRC_OK;
}

void current_source_enable(void)
{
    GPIOA->BSRR = (1 << I_ENABLE_PIN);  /* high = enabled */
    enabled = true;
}

void current_source_disable(void)
{
    GPIOA->BSRR = (1 << I_ENABLE_PIN) << 16;  /* low = disabled */
    enabled = false;
}

float current_source_read_actual_ma(void)
{
    /* Read current sense monitor via ADC (PA0) */
    /* I_sense = V_sense / R_sense_mon
     * With 100Ω sense resistor and gain=1: V_adc = I × 100Ω
     * I = V_adc / 100
     */
    ADC1->SQR1 = 0;  /* 1 conversion */
    ADC1->SQR1 = (I_SENSE_MON_PIN << 6);  /* channel = PA0 = ADC_IN0 */
    ADC1->CR |= ADC_CR_ADSTART;

    while (ADC1->ISR & ADC_ISR_EOC == 0);  /* wait for conversion */
    uint16_t raw = ADC1->DR;

    float v_sense = (raw / 4095.0f) * 3.3f;
    float current_a = v_sense / 100.0f;  /* 100Ω sense resistor */
    return current_a * 1000.0f;  /* A → mA */
}

uint8_t current_source_get_range(void)
{
    return current_range;
}

float current_source_get_set_ma(void)
{
    return set_current_ma;
}