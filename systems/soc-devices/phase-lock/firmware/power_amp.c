/*
 * power_amp.c — OPA569 power-amplifier control
 *
 * The OPA569 is a high-current power op-amp (±10 V, 200 mA continuous,
 * 500 mA peak) that buffers the DAC1 reference sine to ±10 V for the
 * "Ref Out" excitation BNC. It is powered from the ±10 V TPS65131 rail.
 *
 * The OPA569 has:
 *   - Enable/shutdown pin (PB12 on STM32)
 *   - Current-limit set pin (PB14 PWM → RC filter → I-limit)
 *   - Current-sense output (PA6 ADC)
 *   - Output voltage monitor (PC0 ADC2)
 *
 * The firmware watches the output voltage and current and shuts down
 * the amp if either exceeds safety limits.
 */

#include "stm32g491_conf.h"
#include "power_amp.h"
#include "adc.h"
#include <math.h>

static bool amp_enabled = false;
static uint16_t ilimit_ma = 200;

void power_amp_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* PB12 (enable), PB14 (I-limit PWM) as outputs */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3U << (2*12))) | (0x1U << (2*12));
    GPIOB->MODER = (GPIOB->MODER & ~(0x3U << (2*14))) | (0x1U << (2*14));
    GPIOB->BSRR = (1U << (12 + 16));  /* PB12 low = shutdown */
    GPIOB->BSRR = (1U << (14 + 16));  /* PB14 low = no I-limit */
    amp_enabled = false;
}

void power_amp_enable(void)
{
    GPIOB->BSRR = (1U << 12);   /* PB12 high = enable */
    amp_enabled = true;
}

void power_amp_disable(void)
{
    GPIOB->BSRR = (1U << (12 + 16));
    amp_enabled = false;
}

bool power_amp_is_enabled(void) { return amp_enabled; }

void power_amp_set_ilimit(uint16_t ma)
{
    if (ma > 500) ma = 500;
    ilimit_ma = ma;
    /* Crude PWM: a simple duty-cycle loop (run from a low-priority timer).
     * The RC filter on PB14 (10k/100n) turns the duty into a voltage
     * that sets the OPA569 I-limit.
     * For simplicity here, we just set the duty as a static value.
     */
    uint16_t duty = (uint16_t)((uint32_t)ma * 65535U / 500U);
    /* Configure PB14 as a TIM-channel PWM (here, just set high/low for now) */
    if (duty > 32768) GPIOB->BSRR = (1U << 14);
    else            GPIOB->BSRR = (1U << (14 + 16));
}

float power_amp_read_current(void)
{
    /* PA6 is ADC1_IN3 — but we use ADC2 for monitoring; here we read PA6 as ADC1 ch 3 */
    /* Simplified: read PA6 via ADC1 regular, single conversion */
    ADC1->SQR1 = (0U << ADC_SQR1_L_Pos) | (3U << ADC_SQR1_SQ1_Pos);
    /* disable oversampling briefly */
    ADC1->CFGR2 = 0;
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) ;
    uint16_t v = (uint16_t)ADC1->DR;
    /* Re-enable oversampling */
    ADC1->CFGR2 = (7U << ADC_CFGR2_OVSR_Pos) | ADC_CFGR2_OVSS_0 | ADC_CFGR2_OVSS_3;
    /* OPA569 I-mon: 250 µA/A → divider → 0..3.3 V → 0..500 mA */
    return (float)v / 65535.0f * 3.3f * 500.0f / 3.3f;
}

float power_amp_read_voltage(void)
{
    /* PC0 = ADC2 channel 1 */
    ADC2->SQR1 = (0U << ADC_SQR1_L_Pos) | (1U << ADC_SQR1_SQ1_Pos);
    ADC2->CR |= ADC_CR_ADSTART;
    while (!(ADC2->ISR & ADC_ISR_EOC)) ;
    uint16_t v = (uint16_t)ADC2->DR;
    /* PC0 has a ÷6.06 divider to bring ±10 V into 0..3.3 V */
    return (float)v / 65535.0f * 3.3f * 6.06f - 20.0f;   /* bipolar ±10 V */
}

bool power_amp_safety_check(void)
{
    float v = power_amp_read_voltage();
    float i = power_amp_read_current();
    if (fabsf(v) > 11.0f) { power_amp_disable(); return false; }
    if (i > 250.0f)        { power_amp_disable(); return false; }
    return true;
}