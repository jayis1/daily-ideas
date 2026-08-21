/*
 * ui.c — User interface: EC11 encoder + 3 tactile buttons
 *
 * PB0=Mode (input, pull-up)
 * PB1=Start/Stop (input, pull-up)
 * PB2=Inject (input, pull-up)
 * Encoder on PA13/PA14 (or external pins — simplified)
 *
 * The encoder adjusts the selected menu parameter.
 */

#include "ui.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static bool btn_pressed[3] = {false, false, false};
static int16_t enc_count = 0;

void ui_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* PB0, PB1, PB2: buttons (input, pull-up) */
    for (uint8_t pin = 0; pin <= 2; pin++) {
        GPIOB->MODER &= ~(3u << (pin * 2u));
        GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (pin * 2u))) | (1u << (pin * 2u));
    }
}

void ui_poll(void)
{
    /* Check button presses (active-low with pull-up) */
    if (!(GPIOB->IDR & (1u << 0))) btn_pressed[BTN_MODE] = true;
    if (!(GPIOB->IDR & (1u << 1))) btn_pressed[BTN_START] = true;
    if (!(GPIOB->IDR & (1u << 2))) btn_pressed[BTN_INJECT] = true;
}

bool ui_button_pressed(uint8_t btn)
{
    if (btn > 2) return false;
    bool result = btn_pressed[btn];
    btn_pressed[btn] = false;
    return result;
}

void ui_menu_update(float *hv_kv, uint8_t *bge, uint8_t *inj,
                    float *inj_dur, uint16_t *timeout_s)
{
    /* Encoder adjusts selected parameter (simplified) */
    /* Real implementation reads encoder delta and adjusts the
     * currently-selected parameter, cycling through:
     *   HV voltage → BGE recipe → injection mode → injection duration → timeout
     */
    if (enc_count != 0) {
        *hv_kv += (float)enc_count * 0.5f;
        if (*hv_kv < 5.0f) *hv_kv = 5.0f;
        if (*hv_kv > HV_TARGET_KV_MAX) *hv_kv = HV_TARGET_KV_MAX;
        enc_count = 0;
    }
}