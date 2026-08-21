/**
 * lumen_cast/firmware/servo.c — SG90 servo control for elevation axis
 *
 * SG90 servo: 50 Hz PWM, 500–2400µs pulse width → 0–180°
 * TIM3_CH1 (PA6) generates the servo PWM signal.
 *
 * Elevation mapping:
 *   elevation_deg = -90° → servo 0°   (500µs)
 *   elevation_deg =  0° → servo 90°  (1450µs)
 *   elevation_deg = +90° → servo 180° (2400µs)
 */

#include "main.h"

#define TAG "SERVO"
#define PI 3.14159265358979f

/* TIM3 clock = 170 MHz
 * For 50 Hz (20ms period): prescaler = 170MHz / (50 × 65536) ≈ 51.8
 * Use PSC=1699 → timer clock = 100 kHz, ARR = 2000 → 50 Hz
 * Pulse width: 500µs = 50 counts, 2400µs = 240 counts
 */
#define SERVO_TIM_PSC    1699    /* 170MHz / (1699+1) = 100 kHz */
#define SERVO_TIM_ARR    1999    /* 100kHz / 2000 = 50 Hz */
#define SERVO_US_TO_TICK(us)  ((us) * 100 / 1000)  /* 100kHz → 1µs = 0.1 ticks */

static float s_current_elev = 0.0f;

void servo_init(void)
{
    /* Enable TIM3 clock */
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM3EN;

    /* PA6 as TIM3_CH1 alternate function */
    GPIOA->MODER &= ~(3 << (PIN_SERVO * 2));
    GPIOA->MODER |= (2 << (PIN_SERVO * 2));  /* AF mode */
    GPIOA->AFR[0] &= ~(0xF << (PIN_SERVO * 4));
    GPIOA->AFR[0] |= (2 << (PIN_SERVO * 4));  /* AF2 = TIM3 */

    /* TIM3: 50 Hz PWM */
    TIM3->PSC = SERVO_TIM_PSC;
    TIM3->ARR = SERVO_TIM_ARR;
    TIM3->CCR1 = SERVO_US_TO_TICK(1450);  /* center = 90° = 1450µs */

    /* PWM mode 1 on CH1 */
    TIM3->CCMR1 = (6 << TIM_CCMR1_OC1M_Pos) | TIM_CCMR1_OC1PE;
    TIM3->CCER = TIM_CCER_CC1E;
    TIM3->EGR = TIM_EGR_UG;
    TIM3->CR1 |= TIM_CR1_CEN;  /* start */

    s_current_elev = 0.0f;
    LOGI(TAG, "Servo init: SG90 on TIM3_CH1 (50 Hz)");
}

void servo_set_elevation(float elev_deg)
{
    /* Map elevation (-90 to +90°) to servo angle (0 to 180°) */
    float servo_deg = elev_deg + 90.0f;
    if (servo_deg < 0) servo_deg = 0;
    if (servo_deg > 180) servo_deg = 180;

    /* Map servo angle to pulse width: 500–2400µs over 0–180° */
    float us = 500.0f + (servo_deg / 180.0f) * (2400.0f - 500.0f);

    TIM3->CCR1 = SERVO_US_TO_TICK((int)us);
    s_current_elev = elev_deg;
}