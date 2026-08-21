/*
 * ui.c — Button + rotary encoder + numeric pad menu
 *
 * EC11 rotary encoder: PB1=A, PB2=B, PB3=push (select)
 * SW2 (PB0): Mode button
 * SW3 (PB? : Scan button — mapped to encoder push in this simplified build)
 */

#include "ui.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static int   cur_menu = 0;
static int   enc_state = 0;
static int   enc_delta = 0;
static bool  select_pressed_flag = false;
static bool  scan_pressed_flag = false;
static bool  mode_pressed_flag = false;

void ui_init(void)
{
    /* PB0: Mode button (input, pull-up) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER &= ~(3u << (0u * 2u));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (0u * 2u))) | (1u << (0u * 2u));
    /* PB1: encoder A (input, pull-up) */
    GPIOB->MODER &= ~(3u << (1u * 2u));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (1u * 2u))) | (1u << (1u * 2u));
    /* PB2: encoder B */
    GPIOB->MODER &= ~(3u << (2u * 2u));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (2u * 2u))) | (1u << (2u * 2u));
    /* PB3: encoder push / select */
    GPIOB->MODER &= ~(3u << (3u * 2u));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (3u * 2u))) | (1u << (3u * 2u));

    cur_menu = 0;
    enc_state = 0;
}

void ui_poll(void)
{
    /* Read encoder (quadrature decode) */
    int a = (GPIOB->IDR >> 1) & 1;
    int b = (GPIOB->IDR >> 2) & 1;
    int new_state = (a << 1) | b;
    int transition = (enc_state << 2) | new_state;
    /* Quadrature lookup table */
    static const int qtab[16] = {
         0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0
    };
    enc_delta += qtab[transition];
    if (enc_delta >= 4) { enc_delta -= 4; cur_menu++; if (cur_menu > 4) cur_menu = 4; }
    if (enc_delta <= -4) { enc_delta += 4; cur_menu--; if (cur_menu < 0) cur_menu = 0; }
    enc_state = new_state;

    /* Select (encoder push) */
    if (!(GPIOB->IDR & (1u << 3u))) select_pressed_flag = true;

    /* Mode button (PB0) */
    if (!(GPIOB->IDR & (1u << 0u))) mode_pressed_flag = true;

    /* Scan: encoder push + mode pressed together, or separate button */
    if (select_pressed_flag && cur_menu == UI_SCAN) scan_pressed_flag = true;
}

int  ui_current(void) { return cur_menu; }
int  ui_encoder_delta(void)
{
    int d = enc_delta / 4;
    enc_delta %= 4;
    return d;
}
bool ui_select_pressed(void)
{
    bool p = select_pressed_flag;
    select_pressed_flag = false;
    return p;
}
bool ui_scan_pressed(void)
{
    bool p = scan_pressed_flag;
    scan_pressed_flag = false;
    return p;
}
bool ui_mode_pressed(void)
{
    bool p = mode_pressed_flag;
    mode_pressed_flag = false;
    return p;
}