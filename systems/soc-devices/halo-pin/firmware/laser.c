/*
 * laser.c — 650 nm laser diode constant-power control
 *
 * Hardware:
 *   PB4  (TIM3_CH1 PWM) ─▶ laser driver IC (e.g., NCP500) SET pin
 *   PA6  (ADC2_IN3)     ◀─ monitor photodiode (current→voltage via TIA)
 *   PB12 (GPIO input)  ◀─ reed switch (cell cover interlock, active-low)
 *
 * Closed-loop: PI controller adjusts PWM duty to hold monitor-PD
 * voltage at the calibrated setpoint for 5 mW output. The loop runs
 * at 100 Hz (called from the main loop).
 */

#include "laser.h"
#include "stm32g474_conf.h"

#define MONITOR_ADC_CH      3       /* ADC2_IN3 = PA6 */
#define MONITOR_TARGET_RAW  2048    /* ~2.0 V at 5 mW (calibrated) */

static bool  enabled = false;
static float drive_duty = 0.0f;    /* 0..1 */
static float integ = 0.0f;
static float last_mw = 0.0f;

static uint16_t adc2_read(uint8_t ch)
{
    ADC2->SQR1 = (1u << 6) | (ch << 9);
    ADC2->CR |= ADC_CR_ADSTART;
    while (!(ADC2->ISR & ADC_ISR_EOC)) ;
    return (uint16_t)ADC2->DR;
}

void laser_init(void)
{
    /* PB4 = TIM3_CH1 alternate function */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->AFR[0] &= ~GPIO_AFRL_AFSEL4;
    GPIOB->AFR[0] |= (2u << GPIO_AFRL_AFSEL4_Pos);   /* AF2 = TIM3_CH1 */
    GPIOB->MODER = (GPIOB->MODER & ~GPIO_MODER_MODE4) | (2u << GPIO_MODER_MODE4_Pos);

    /* TIM3 CH1 PWM: 50 kHz, duty 0..1 */
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM3EN;
    TIM3->PSC = (SYSCLK_FREQ / 50000u) - 1;   /* 50 kHz tick */
    TIM3->ARR = 1000u - 1;                    /* 1 kHz PWM? no: 50 kHz / 1000 = 50 Hz — too slow */
    TIM3->ARR = 100u - 1;                      /* 50 kHz / 100 = 500 Hz PWM */
    TIM3->CCR1 = 0;
    TIM3->CCMR1 = TIM_CCMR1_OC1M_PWM1 | TIM_CCMR1_OC1PE;
    TIM3->CCER = TIM_CCER_CC1E;
    TIM3->BDTR |= TIM_BDTR_MOE;
    TIM3->CR1 = TIM_CR1_CEN;

    /* PB12 reed interlock input, pull-up */
    GPIOB->MODER &= ~GPIO_MODER_MODE12;
    GPIOB->PUPDR = (GPIOB->PUPDR & ~GPIO_PUPDR_PUPD12) | (1u << GPIO_PUPDR_PUPD12_Pos);

    /* ADC2 for monitor photodiode */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC12EN;
    ADC2->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 10000; ++i) ;   /* ADC startup */
    ADC2->CR &= ~ADC_CR_DEEPPWD;
    ADC2->CR |= ADC_CR_ADCAL;
    while (ADC2->CR & ADC_CR_ADCAL) ;
    ADC2->CR |= ADC_CR_ADEN;
    while (!(ADC2->ISR & ADC_ISR_ADRDY)) ;
}

static bool interlock_ok(void)
{
    /* PB12 active-low: 0 = cover closed (laser safe to fire) */
    return (GPIOB->IDR & GPIO_IDR_ID12) == 0;
}

void laser_on(void)
{
    if (!interlock_ok()) {
        enabled = false;
        return;
    }
    enabled = true;
    integ = 0.0f;
    drive_duty = 0.2f;
    TIM3->CCR1 = (uint32_t)(drive_duty * 100.0f);
}

void laser_off(void)
{
    enabled = false;
    drive_duty = 0.0f;
    TIM3->CCR1 = 0;
}

bool laser_ok(void)
{
    if (!enabled) return false;
    if (!interlock_ok()) return false;
    float mw = laser_read_mw();
    return (mw > LASER_TARGET_MW * 0.9f && mw < LASER_TARGET_MW * 1.1f);
}

float laser_read_mw(void)
{
    if (!enabled) return 0.0f;
    /* Monitor PD voltage → mW (calibrated: 2.0 V = 5.0 mW) */
    uint16_t raw = adc2_read(MONITOR_ADC_CH);
    float v = (float)raw / 4095.0f * 3.3f;
    last_mw = v / 2.0f * 5.0f;
    return last_mw;
}

/* Called from main loop at ~100 Hz to run the PI controller */
void laser_loop(void)
{
    if (!enabled) { TIM3->CCR1 = 0; return; }
    if (!interlock_ok()) { TIM3->CCR1 = 0; return; }
    uint16_t raw = adc2_read(MONITOR_ADC_CH);
    float err = (float)MONITOR_TARGET_RAW - (float)raw;
    /* Scale error to fraction of full-scale */
    err /= 4095.0f;
    integ += err * 0.05f;
    if (integ > 0.5f) integ = 0.5f;
    if (integ < 0.0f) integ = 0.0f;
    drive_duty = 0.2f + 5.0f * err + 2.0f * integ;
    if (drive_duty > 0.95f) drive_duty = 0.95f;
    if (drive_duty < 0.0f)  drive_duty = 0.0f;
    TIM3->CCR1 = (uint32_t)(drive_duty * 100.0f);
}