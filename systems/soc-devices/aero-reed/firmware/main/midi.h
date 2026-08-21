/*
 * midi.h — BLE + USB MIDI
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

void midi_init(void);
void midi_send_note_on(uint8_t ch, uint8_t note, uint8_t vel);
void midi_send_note_off(uint8_t ch, uint8_t note, uint8_t vel);
void midi_send_cc(uint8_t ch, uint8_t cc, uint8_t val);
void midi_send_pitch_bend(uint8_t ch, int16_t bend14);
void midi_send_program_change(uint8_t ch, uint8_t prog);
void midi_display_task(void *arg);

/* BLE connection callback (set by BLE stack) */
void midi_on_ble_connect(void);
void midi_on_ble_disconnect(void);

/* USB connection callback */
void midi_on_usb_connect(void);
void midi_on_usb_disconnect(void);