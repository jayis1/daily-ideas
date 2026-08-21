/*
 * ui.c — Encoder + buttons + menu
 *
 * EC11 rotary encoder on PB0 (mode), PB1 (start/stop), PB2 (calibrate).
 * Encoder A/B on PC13/PC14 (or use external interrupt).
 * Buttons are active-low with internal pull-up.
 */

#include "ui.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static int32_t encoder_pos = 0;
static uint8_t prev_a = 0, prev_b = 0;

void ui_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN;

    /* PB0=Mode, PB1=Start/Stop, PB2=Calibrate: input + pull-up */
    for (int pin = 0; pin <= 2; pin++) {
        GPIOB->MODER &= ~(3u << (pin * 2u));     /* Input */
        GPIOB->PUPDR |=  (1u << (pin * 2u));     /* Pull-up */
    }

    /* PC13=Encoder A, PC14=Encoder B: input + pull-up */
    GPIOC->MODER &= ~(3u << (13u * 2u));
    GPIOC->MODER &= ~(3u << (14u * 2u));
    GPIOC->PUPDR |=  (1u << (13u * 2u));
    GPIOC->PUPDR |=  (1u << (14u * 2u));

    prev_a = (GPIOC->IDR >> 13) & 1;
    prev_b = (GPIOC->IDR >> 14) & 1;
}

ui_event_t ui_poll(void)
{
    /* Check buttons (active-low) */
    if (!(GPIOB->IDR & (1u << 0))) return UI_EVENT_MODE;
    if (!(GPIOB->IDR & (1u << 1))) return UI_EVENT_START;
    if (!(GPIOB->IDR & (1u << 2))) return UI_EVENT_CALIBRATE;

    /* Check encoder (gray code: A,B transitions) */
    uint8_t a = (GPIOC->IDR >> 13) & 1;
    uint8_t b = (GPIOC->IDR >> 14) & 1;

    if (a != prev_a) {
        if (a != b) {
            encoder_pos++;
            prev_a = a;
            return UI_EVENT_ENCODER_CW;
        } else {
            encoder_pos--;
            prev_a = a;
            return UI_EVENT_ENCODER_CCW;
        }
    }
    prev_a = a;
    prev_b = b;

    return UI_EVENT_NONE;
}

int32_t ui_encoder_pos(void)
{
    return encoder_pos;
}