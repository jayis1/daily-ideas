/*
 * ui.c — button + rotary encoder menu
 *
 * Rotary encoder: PA15 (A), PB0 (B), PB1 (push/select).
 * Mode button: PA14. Run/stop button: PC5 (shared with LED; we use a
 * separate physical button on PC13). Debounce is in software.
 */

#include "stm32g491_conf.h"
#include "ui.h"

static ui_item_t cur_item = UI_FREQ;
static int enc_count = 0;
static int enc_prev = 0;
static bool select_p = false, mode_p = false, run_p = false;

void ui_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN;
    /* PA15, PA14, PB0, PB1, PC13 = inputs with pull-ups */
    uint32_t m;
    m = GPIOA->MODER; m &= ~(0x3U << (2*15)); GPIOA->MODER = m;
    m = GPIOA->MODER; m &= ~(0x3U << (2*14)); GPIOA->MODER = m;
    m = GPIOB->MODER; m &= ~(0x3U << (2*0));  GPIOB->MODER = m;
    m = GPIOB->MODER; m &= ~(0x3U << (2*1));  GPIOB->MODER = m;
    m = GPIOC->MODER; m &= ~(0x3U << (2*13)); GPIOC->MODER = m;
    GPIOA->PUPDR |= (0x1U << (2*15)) | (0x1U << (2*14));
    GPIOB->PUPDR |= (0x1U << (2*0))  | (0x1U << (2*1));
    GPIOC->PUPDR |= (0x1U << (2*13));
    enc_prev = (GPIOA->IDR >> 15) & 1;
}

void ui_poll(void)
{
    int a = (GPIOA->IDR >> 15) & 1;
    int b = (GPIOB->IDR >> 0) & 1;
    if (a != enc_prev) {
        if (a != b) enc_count++; else enc_count--;
        enc_prev = a;
    }
    static uint16_t sel_db=0, mode_db=0, run_db=0;
    int sel  = !((GPIOB->IDR >> 1) & 1);
    int mode = !((GPIOA->IDR >> 14) & 1);
    int run  = !((GPIOC->IDR >> 13) & 1);
    sel_db  = (sel_db  << 1) | (sel  & 1); if ((sel_db  & 0x7FFF) == 0x7FFE) select_p = true;
    mode_db = (mode_db << 1) | (mode & 1); if ((mode_db & 0x7FFF) == 0x7FFE) mode_p = true;
    run_db  = (run_db  << 1) | (run  & 1); if ((run_db  & 0x7FFF) == 0x7FFE) run_p = true;
    if (mode_p) {
        cur_item = (ui_item_t)((cur_item + 1) % UI_COUNT);
        mode_p = false;
    }
}

ui_item_t ui_current(void) { return cur_item; }
int  ui_encoder_delta(void) { int d = enc_count; enc_count = 0; return d; }
bool ui_select_pressed(void) { bool p = select_p; select_p = false; return p; }
bool ui_mode_pressed(void)  { bool p = mode_p;  mode_p = false;  return p; }
bool ui_run_pressed(void)   { bool p = run_p;   run_p = false;   return p; }