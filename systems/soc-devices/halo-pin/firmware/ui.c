/*
 * ui.c — button + rotary encoder + scan button
 *
 * PB5 = encoder A, PB6 = encoder B, PB7 = encoder push
 * PB8 = scan button, PB9 = mode button
 */

#include "ui.h"
#include "stm32g474_conf.h"

static ui_menu_t menu_idx = UI_SAMPLE;
static int enc_delta = 0;
static uint8_t enc_last = 0;
static bool scan_p = false, mode_p = false, sel_p = false;

void ui_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* Inputs with pull-up */
    uint32_t mask = GPIO_MODER_MODE5 | GPIO_MODER_MODE6 | GPIO_MODER_MODE7
                  | GPIO_MODER_MODE8 | GPIO_MODER_MODE9;
    GPIOB->MODER &= ~mask;
    GPIOB->PUPDR |= (1u << GPIO_PUPDR_PUPD5_Pos) | (1u << GPIO_PUPDR_PUPD6_Pos)
                  | (1u << GPIO_PUPDR_PUPD7_Pos) | (1u << GPIO_PUPDR_PUPD8_Pos)
                  | (1u << GPIO_PUPDR_PUPD9_Pos);
    enc_last = (GPIOB->IDR >> 5) & 3;
}

void ui_poll(void)
{
    scan_p = !(GPIOB->IDR & GPIO_IDR_ID8);
    mode_p = !(GPIOB->IDR & GPIO_IDR_ID9);
    sel_p  = !(GPIOB->IDR & GPIO_IDR_ID7);

    /* Rotary encoder: gray code */
    uint8_t now = (GPIOB->IDR >> 5) & 3;
    uint8_t diff = now ^ enc_last;
    if (diff) {
        if ((now == 3 && enc_last == 1) || (now == 0 && enc_last == 2))
            enc_delta--;
        else if ((now == 3 && enc_last == 2) || (now == 0 && enc_last == 1))
            enc_delta++;
        enc_last = now;
    }
}

bool ui_scan_pressed(void)   { bool p = scan_p; scan_p = false; return p; }
bool ui_mode_pressed(void)   { bool p = mode_p; mode_p = false; return p; }
bool ui_select_pressed(void) { bool p = sel_p; sel_p = false; return p; }

int ui_encoder_delta(void)
{
    int d = enc_delta;
    enc_delta = 0;
    if (d != 0) {
        if (d > 0) menu_idx = (menu_idx + 1) % UI_MAX;
        else menu_idx = (menu_idx + UI_MAX - 1) % UI_MAX;
    }
    return d;
}

ui_menu_t ui_current(void) { return menu_idx; }