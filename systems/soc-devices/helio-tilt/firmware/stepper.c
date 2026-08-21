/*
 * stepper.c — NEMA8 AZ/EL stepper motor control
 *
 * Two A4988 stepper drivers, one per axis.
 *   Azimuth:   PB10=DIR, PB11=STEP, PA7=ENABLE, PC7=HOME
 *   Elevation: PB12=DIR, PB13=STEP, PB9=ENABLE, PC8=HOME
 * Microstep: 1/16 (MS1=PC5=1, MS2=PC6=1, MS3=PC12=1 → 1/16)
 *
 * Stepping is done via GPIO bit-bang with a simple ramp.
 * In a production build, TIM2/TIM3 would generate step pulses via DMA.
 */

#include "stepper.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <math.h>

/* ---- Pin definitions ---- */
#define AZ_DIR_PIN     10    /* PB10 */
#define AZ_STEP_PIN    11    /* PB11 */
#define AZ_ENABLE_PIN   7    /* PA7 */
#define AZ_HOME_PIN     7    /* PC7 */

#define EL_DIR_PIN     12    /* PB12 */
#define EL_STEP_PIN    13    /* PB13 */
#define EL_ENABLE_PIN   9    /* PB9 */
#define EL_HOME_PIN     8    /* PC8 */

/* ---- State ---- */
static float az_current_deg = 0.0f;
static float el_current_deg = 0.0f;
static int32_t az_steps = 0;
static int32_t el_steps = 0;

/* ---- GPIO helpers ---- */
static void gpio_set(volatile uint32_t *odr, uint8_t pin)
{
    *odr |= (1u << pin);
}

static void gpio_clr(volatile uint32_t *odr, uint8_t pin)
{
    *odr &= ~(1u << pin);
}

static bool gpio_read(volatile uint32_t *idr, uint8_t pin)
{
    return (*idr & (1u << pin)) != 0;
}

static void stepper_delay_us(uint32_t us)
{
    /* Simple busy-wait delay: 170 MHz → 170 cycles/µs */
    volatile uint32_t count = us * 170 / 5;  /* Approximate, 5 cycles/loop */
    while (count--) ;
}

static void step_pulse(stepper_axis_t axis)
{
    volatile uint32_t *odr = (axis == AXIS_AZIMUTH)
        ? &GPIOB->ODR : &GPIOB->ODR;
    uint8_t step_pin = (axis == AXIS_AZIMUTH) ? AZ_STEP_PIN : EL_STEP_PIN;

    gpio_set(odr, step_pin);
    stepper_delay_us(2);     /* Min 1 µs HIGH */
    gpio_clr(odr, step_pin);
    stepper_delay_us(500);   /* 2 kHz step rate → ~0.1°/s at 1/16 microstep */
}

static void set_dir(stepper_axis_t axis, bool cw)
{
    volatile uint32_t *odr = &GPIOB->ODR;
    uint8_t dir_pin = (axis == AXIS_AZIMUTH) ? AZ_DIR_PIN : EL_DIR_PIN;
    if (cw) gpio_set(odr, dir_pin);
    else    gpio_clr(odr, dir_pin);
}

void stepper_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN
                  | RCC_AHB2ENR_GPIOCEN;

    /* AZ pins */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (AZ_DIR_PIN * 2u)))  | (1u << (AZ_DIR_PIN * 2u));
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (AZ_STEP_PIN * 2u))) | (1u << (AZ_STEP_PIN * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (AZ_ENABLE_PIN * 2u)))| (1u << (AZ_ENABLE_PIN * 2u));
    GPIOC->MODER &= ~(3u << (AZ_HOME_PIN * 2u));    /* Input */
    GPIOC->PUPDR |=  (2u << (AZ_HOME_PIN * 2u));    /* Pull-down */

    /* EL pins */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (EL_DIR_PIN * 2u)))  | (1u << (EL_DIR_PIN * 2u));
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (EL_STEP_PIN * 2u))) | (1u << (EL_STEP_PIN * 2u));
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (EL_ENABLE_PIN * 2u)))| (1u << (EL_ENABLE_PIN * 2u));
    GPIOC->MODER &= ~(3u << (EL_HOME_PIN * 2u));
    GPIOC->PUPDR |=  (2u << (EL_HOME_PIN * 2u));

    /* Microstep MS1=PC5, MS2=PC6, MS3=PC12 → all high for 1/16 */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (5u * 2u)))  | (1u << (5u * 2u));
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (6u * 2u)))  | (1u << (6u * 2u));
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (12u * 2u))) | (1u << (12u * 2u));
    gpio_set(&GPIOC->ODR, 5);
    gpio_set(&GPIOC->ODR, 6);
    gpio_set(&GPIOC->ODR, 12);

    /* Disable both steppers initially (A4988 enable is active-low) */
    stepper_enable(AXIS_AZIMUTH, false);
    stepper_enable(AXIS_ELEVATION, false);
}

void stepper_enable(stepper_axis_t axis, bool en)
{
    /* A4988 ENABLE is active-low: LOW = enabled, HIGH = disabled */
    if (axis == AXIS_AZIMUTH) {
        if (en) gpio_clr(&GPIOA->ODR, AZ_ENABLE_PIN);
        else    gpio_set(&GPIOA->ODR, AZ_ENABLE_PIN);
    } else {
        if (en) gpio_clr(&GPIOB->ODR, EL_ENABLE_PIN);
        else    gpio_set(&GPIOB->ODR, EL_ENABLE_PIN);
    }
}

void stepper_move_to(stepper_axis_t axis, float target_deg)
{
    float current = (axis == AXIS_AZIMUTH) ? az_current_deg : el_current_deg;
    float delta = target_deg - current;

    /* Wrap azimuth to shortest path */
    if (axis == AXIS_AZIMUTH) {
        if (delta > 180.0f)  delta -= 360.0f;
        if (delta < -180.0f) delta += 360.0f;
    }

    /* Clamp elevation */
    if (axis == AXIS_ELEVATION) {
        if (target_deg < 0.0f) target_deg = 0.0f;
        if (target_deg > 90.0f) target_deg = 90.0f;
        delta = target_deg - current;
    }

    float steps_per_deg = (axis == AXIS_AZIMUTH)
        ? AZ_STEPS_PER_DEG : EL_STEPS_PER_DEG;
    int32_t total_steps = (int32_t)(delta * steps_per_deg);

    if (total_steps == 0) return;

    stepper_enable(axis, true);
    set_dir(axis, total_steps > 0);

    uint32_t abs_steps = (total_steps < 0) ? -total_steps : total_steps;
    for (uint32_t i = 0; i < abs_steps; i++) {
        step_pulse(axis);
        if (total_steps > 0) {
            if (axis == AXIS_AZIMUTH) az_steps++;
            else                      el_steps++;
        } else {
            if (axis == AXIS_AZIMUTH) az_steps--;
            else                      el_steps--;
        }
    }

    /* Update current angle */
    if (axis == AXIS_AZIMUTH) {
        az_current_deg = fmodf(az_current_deg + delta, 360.0f);
        if (az_current_deg < 0) az_current_deg += 360.0f;
    } else {
        el_current_deg += delta;
    }
}

float stepper_get_angle(stepper_axis_t axis)
{
    return (axis == AXIS_AZIMUTH) ? az_current_deg : el_current_deg;
}

int stepper_home(stepper_axis_t axis)
{
    stepper_enable(axis, true);
    set_dir(axis, false);   /* Move toward home (CCW / down) */

    /* Step until home switch triggers */
    uint32_t max_steps = STEPPER_STEPS_PER_REV * AZ_WORM_RATIO;  /* Safety limit */
    for (uint32_t i = 0; i < max_steps; i++) {
        bool home;
        if (axis == AXIS_AZIMUTH)
            home = gpio_read(&GPIOC->IDR, AZ_HOME_PIN);
        else
            home = gpio_read(&GPIOC->IDR, EL_HOME_PIN);

        if (home) {
            if (axis == AXIS_AZIMUTH) {
                az_current_deg = 0.0f;
                az_steps = 0;
            } else {
                el_current_deg = 0.0f;
                el_steps = 0;
            }
            stepper_enable(axis, false);
            return 0;
        }
        step_pulse(axis);
    }

    stepper_enable(axis, false);
    return -1;   /* Home not found */
}

void stepper_stop(stepper_axis_t axis)
{
    stepper_enable(axis, false);
}