/*
 * patient.c — Patient ID + age + sex + ethnicity input
 *
 * 4 tactile buttons (SW4-SW7) enter the patient demographics:
 *   SW4 (PB14): ID digit increment (0–9, wraps)
 *   SW5 (PC13): Age (rotary encoder adjusts, push to confirm)
 *   SW6 (PC14): Sex toggle (M/F)
 *   SW7 (PC15): Ethnicity cycle (Caucasian/Asian/African/Hispanic/Other)
 *
 * The rotary encoder sets numeric values; the buttons cycle through
 * the entry fields.
 */

#include "patient.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <stdbool.h>

static uint16_t p_id = 1;
static uint8_t  p_age = 55;
static uint8_t  p_sex = 1;          /* Default female (higher risk) */
static uint8_t  p_eth = ETH_CAUCAASIAN;
static bool     p_fracture = false;
static bool     entering = false;
static uint8_t  entry_field = 0;    /* 0=id, 1=age, 2=sex, 3=eth */

void patient_init(void)
{
    /* PB14, PC13, PC14, PC15: 4 tactile buttons (inputs, pull-up) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    GPIOB->MODER &= ~(3u << (14u * 2u));     /* PB14 input */
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (14u * 2u))) | (1u << (14u * 2u));
    GPIOC->MODER &= ~(3u << (13u * 2u));     /* PC13 input */
    GPIOC->MODER &= ~(3u << (14u * 2u));     /* PC14 input */
    GPIOC->MODER &= ~(3u << (15u * 2u));     /* PC15 input */
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (13u * 2u))) | (1u << (13u * 2u));
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (14u * 2u))) | (1u << (14u * 2u));
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (15u * 2u))) | (1u << (15u * 2u));
}

void patient_start_entry(void) { entering = true; entry_field = 0; }
bool patient_entry_complete(void)
{
    if (entering && entry_field > 3) {
        entering = false;
        return true;
    }
    return false;
}

static bool button_pressed(uint8_t field)
{
    /* Simplified debounce — real code debounces properly */
    switch (field) {
        case 0: return !(GPIOB->IDR & (1u << 14u));
        case 1: return !(GPIOC->IDR & (1u << 13u));
        case 2: return !(GPIOC->IDR & (1u << 14u));
        case 3: return !(GPIOC->IDR & (1u << 15u));
        default: return false;
    }
}

void patient_poll_input(void)
{
    if (!entering) return;

    if (button_pressed(entry_field)) {
        switch (entry_field) {
            case 0: p_id = (p_id + 1) % 10000; break;
            case 1: p_age = (p_age + 1) % 100; if (p_age < 20) p_age = 20; break;
            case 2: p_sex ^= 1; break;
            case 3: p_eth = (p_eth + 1) % ETHNICITY_COUNT; break;
        }
        /* Auto-advance after entry */
        entry_field++;
        if (entry_field > 3) entering = false;
    }
}

uint16_t patient_get_id(void) { return p_id; }
void     patient_set_id(uint16_t id) { p_id = id; }
uint8_t  patient_get_age(void) { return p_age; }
void     patient_set_age(uint8_t age) { p_age = age; }
uint8_t  patient_get_sex(void) { return p_sex; }
void     patient_set_sex(uint8_t sex) { p_sex = sex & 1; }
uint8_t  patient_get_ethnicity(void) { return p_eth; }
void     patient_set_ethnicity(uint8_t eth) { p_eth = eth % ETHNICITY_COUNT; }
bool     patient_has_prior_fracture(void) { return p_fracture; }