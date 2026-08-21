/*
 * Hive Mind — Bee Counter Driver
 * Dual IR break-beam sensors at hive entrance
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "bee_counter.h"
#include "main.h"

/* IR gate configuration */
#define IR_DEBOUNCE_MS       50    /* 50 ms debounce */
#define IR_MIN_GAP_MS        100   /* Minimum gap between detections */
#define IR_GATE_THRESHOLD    200   /* ADC threshold for beam break (out of 4095) */

/* State tracking for each gate */
typedef struct {
    uint32_t last_trigger_ms;
    uint32_t count;
    uint8_t  last_state;       /* 0 = unbroken, 1 = broken */
    uint8_t  debounce_counter;
} ir_gate_t;

static ir_gate_t gate_out;  /* Outgoing bees */
static ir_gate_t gate_in;   /* Incoming bees */

extern GPIO_TypeDef *IR_LED_OUT_PORT;
extern uint16_t IR_LED_OUT_PIN;
extern GPIO_TypeDef *IR_PHOTO_OUT_PORT;
extern uint16_t IR_PHOTO_OUT_PIN;
extern GPIO_TypeDef *IR_LED_IN_PORT;
extern uint16_t IR_LED_IN_PIN;
extern GPIO_TypeDef *IR_PHOTO_IN_PORT;
extern uint16_t IR_PHOTO_IN_PIN;

/* ------------------------------------------------------------------ */
/* Private helpers                                                     */
/* ------------------------------------------------------------------ */

static uint8_t read_ir_gate(GPIO_TypeDef *photo_port, uint16_t photo_pin)
{
    /* Simple digital read: beam broken = LOW, unbroken = HIGH */
    return (HAL_GPIO_ReadPin(photo_port, photo_pin) == GPIO_PIN_RESET) ? 1 : 0;
}

static void update_gate(ir_gate_t *gate, uint8_t current_state, uint32_t now_ms)
{
    /* Debounce: require consistent readings */
    if (current_state != gate->last_state) {
        gate->debounce_counter++;
        if (gate->debounce_counter >= 3) {  /* 3 consecutive different readings */
            gate->last_state = current_state;
            gate->debounce_counter = 0;

            /* Count on transition from unbroken → broken (bee entering beam) */
            if (current_state == 1) {
                if ((now_ms - gate->last_trigger_ms) > IR_MIN_GAP_MS) {
                    gate->count++;
                    gate->last_trigger_ms = now_ms;
                }
            }
        }
    } else {
        gate->debounce_counter = 0;
    }
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void bee_counter_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Configure IR LEDs as outputs */
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

    GPIO_InitStruct.Pin = IR_LED_OUT_PIN;
    HAL_GPIO_Init(IR_LED_OUT_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = IR_LED_IN_PIN;
    HAL_GPIO_Init(IR_LED_IN_PORT, &GPIO_InitStruct);

    /* Configure IR phototransistors as inputs with pull-up */
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;

    GPIO_InitStruct.Pin = IR_PHOTO_OUT_PIN;
    HAL_GPIO_Init(IR_PHOTO_OUT_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = IR_PHOTO_IN_PIN;
    HAL_GPIO_Init(IR_PHOTO_IN_PORT, &GPIO_InitStruct);

    /* Turn on IR LEDs */
    HAL_GPIO_WritePin(IR_LED_OUT_PORT, IR_LED_OUT_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(IR_LED_IN_PORT, IR_LED_IN_PIN, GPIO_PIN_SET);

    /* Initialize gate states */
    memset(&gate_out, 0, sizeof(gate_out));
    memset(&gate_in, 0, sizeof(gate_in));

    /* Warm-up: let IR beams stabilize */
    HAL_Delay(100);
}

bee_counts_t bee_counter_count(uint32_t window_ms)
{
    bee_counts_t result = {0, 0};
    uint32_t start = HAL_GetTick();
    uint32_t now;

    /* Reset counters for this window */
    gate_out.count = 0;
    gate_in.count = 0;

    /* Poll for the specified window */
    while ((now = HAL_GetTick()) - start < window_ms) {
        uint8_t out_state = read_ir_gate(IR_PHOTO_OUT_PORT, IR_PHOTO_OUT_PIN);
        uint8_t in_state = read_ir_gate(IR_PHOTO_IN_PORT, IR_PHOTO_IN_PIN);

        update_gate(&gate_out, out_state, now);
        update_gate(&gate_in, in_state, now);

        /* Small delay between polls (1 ms) */
        HAL_Delay(1);
    }

    result.out_count = gate_out.count;
    result.in_count = gate_in.count;

    return result;
}

void bee_counter_leds_on(void)
{
    HAL_GPIO_WritePin(IR_LED_OUT_PORT, IR_LED_OUT_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(IR_LED_IN_PORT, IR_LED_IN_PIN, GPIO_PIN_SET);
}

void bee_counter_leds_off(void)
{
    /* Turn off IR LEDs to save power between counting windows */
    HAL_GPIO_WritePin(IR_LED_OUT_PORT, IR_LED_OUT_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(IR_LED_IN_PORT, IR_LED_IN_PIN, GPIO_PIN_RESET);
}