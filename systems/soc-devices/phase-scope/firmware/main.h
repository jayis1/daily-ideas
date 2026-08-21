/*
 * Phase Scope — Main header
 */

#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include "stm32g491xx.h"

/* Button events */
#define BTN_MODE    1
#define BTN_SELECT  2
#define BTN_HOLD    3

/* Display pages */
#define PAGE_PHASOR   0
#define PAGE_WAVEFORM 1
#define PAGE_HARMONICS 2
#define PAGE_NUMERIC  3
#define PAGE_TRANSIENT 4
#define NUM_PAGES     5

/* Font sizes */
#define FONT_SMALL  0
#define FONT_LARGE  1

/* System clock */
extern uint32_t SystemCoreClock;

/* Global state */
extern volatile uint32_t system_tick;
extern volatile uint8_t  display_page;
extern volatile uint8_t  logging_active;
extern volatile uint8_t  ble_streaming;
extern volatile uint8_t  button_event;

void delay_ms(uint32_t ms);
void delay_us(uint32_t us);

#endif /* MAIN_H */