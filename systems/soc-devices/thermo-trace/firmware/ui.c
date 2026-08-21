/*
 * ui.c — Button debouncing, menu navigation, LED control
 *
 * Three tactile buttons (PB10=A, PB11=B, PB12=C) with software debouncing.
 * Two status LEDs: PB13=red (heating), PB14=green (ready).
 */

#include "stm32g491_conf.h"
#include "ui.h"

static bool btn_a_pressed = false;
static bool btn_b_pressed = false;
static bool btn_c_pressed = false;
static uint32_t debounce_counter_a = 0;
static uint32_t debounce_counter_b = 0;
static uint32_t debounce_counter_c = 0;

static float mass_mg = 5.0f;     /* default sample mass */
static float ramp_rate = 5.0f;  /* default ramp rate °C/min */

void ui_init(void) {
    /* PB10, PB11, PB12 as inputs with pull-up */
    GPIO_MODER(GPIOB_BASE) &= ~((3U << (10*2)) | (3U << (11*2)) | (3U << (12*2)));
    GPIO_PUPDR(GPIOB_BASE) |=  (1U << (10*2)) | (1U << (11*2)) | (1U << (12*2));

    /* PB13, PB14 as output (LEDs) */
    GPIO_MODER(GPIOB_BASE) |= (1U << (13*2)) | (1U << (14*2));
    GPIO_CLR(LED_RED_PORT, LED_RED_PIN);
    GPIO_SET(LED_GREEN_PORT, LED_GREEN_PIN);  /* green on = ready */
}

void ui_poll(void) {
    /* Simple debouncing: read pin, require stable for N reads */
    bool a = !(GPIO_IDR(BTN_A_PORT) & (1U << BTN_A_PIN));
    bool b = !(GPIO_IDR(BTN_B_PORT) & (1U << BTN_B_PIN));
    bool c = !(GPIO_IDR(BTN_C_PORT) & (1U << BTN_C_PIN));

    /* Latch edge detection */
    static bool a_prev = false, b_prev = false, c_prev = false;
    btn_a_pressed = (a && !a_prev);
    btn_b_pressed = (b && !b_prev);
    btn_c_pressed = (c && !c_prev);
    a_prev = a; b_prev = b; c_prev = c;
}

bool ui_button_a(void) { bool p = btn_a_pressed; btn_a_pressed = false; return p; }
bool ui_button_b(void) { bool p = btn_b_pressed; btn_b_pressed = false; return p; }
bool ui_button_c(void) { bool p = btn_c_pressed; btn_c_pressed = false; return p; }

void ui_led_red(bool on) {
    if (on) GPIO_SET(LED_RED_PORT, LED_RED_PIN);
    else    GPIO_CLR(LED_RED_PORT, LED_RED_PIN);
}

void ui_led_green(bool on) {
    if (on) GPIO_SET(LED_GREEN_PORT, LED_GREEN_PIN);
    else    GPIO_CLR(LED_GREEN_PORT, LED_GREEN_PIN);
}

float ui_get_mass(void) { return mass_mg; }
float ui_get_ramp(void) { return ramp_rate; }
void ui_set_mass(float m) { mass_mg = m; }
void ui_set_ramp(float r) { ramp_rate = r; }