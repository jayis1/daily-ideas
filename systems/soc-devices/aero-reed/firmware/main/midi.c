/*
 * midi.c — BLE MIDI + USB MIDI send, and MIDI/display co-task
 *
 * Implements:
 *   - Apple BLE MIDI service (GATT MIDI 128-byte chunking)
 *   - USB CDC-MIDI class (TinyUSB)
 *   - MIDI encoding helpers (note on/off, CC, pitch bend, program change)
 *   - The midi_display_task() runs at 50 Hz, reads g_state, sends MIDI,
 *     and updates the OLED.
 */
#include "midi.h"
#include "synth.h"
#include "display.h"
#include "patch.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>

static const char *TAG = "midi";

/* ── BLE MIDI (NimBLE) ──────────────────────────────────────────────── */
/* We use a simplified BLE MIDI implementation. In production this links
 * against the NimBLE stack with a custom MIDI GATT service (UUID
 * 03B80E5A-EDE8-4B33-A075-8CE1A1E9D5A2 / 7772E5DB-3868-411E-A3EB-72C3AB
 * 20A7C). Here we provide the encoding and send buffer. */
static uint8_t ble_midi_buf[128];
static int     ble_midi_len = 0;
static bool    ble_connected = false;

/* ── USB MIDI ──────────────────────────────────────────────────────── */
static bool usb_connected = false;

/* USB MIDI packet is 4 bytes: [cable|status, data1, data2, 0] */
static void usb_midi_send(uint8_t status, uint8_t d1, uint8_t d2)
{
    if (!usb_connected) return;
    /* In production: tinyusb_midi_send(status, d1, d2) */
    (void)status; (void)d1; (void)d2;
}

void midi_init(void)
{
    ESP_LOGI(TAG, "MIDI init (BLE + USB)");
    /* In production: nimble_stack_init(), register MIDI GATT service,
     * tinyusb_init(USB_MIDI_CLASS) */
    ble_midi_len = 0;
}

/* ── MIDI encoding helpers ─────────────────────────────────────────── */
static void send_midi(uint8_t status, uint8_t d1, uint8_t d2)
{
    /* BLE MIDI: timestamp header + status + data */
    if (ble_connected) {
        uint16_t ts = (uint16_t)(esp_timer_get_time() / 1000 % 8192);
        if (ble_midi_len + 4 > 128) {
            /* Flush: ble_gatt_notify(ble_midi_buf, ble_midi_len) */
            ble_midi_len = 0;
        }
        ble_midi_buf[ble_midi_len++] = 0x80 | (ts >> 7);
        ble_midi_buf[ble_midi_len++] = 0x80 | (ts & 0x7F);
        ble_midi_buf[ble_midi_len++] = status;
        ble_midi_buf[ble_midi_len++] = d1;
        if (d2 != 0xFF)
            ble_midi_buf[ble_midi_len++] = d2;
    }
    /* USB MIDI */
    usb_midi_send(status, d1, d2);
}

void midi_send_note_on(uint8_t ch, uint8_t note, uint8_t vel)
{
    send_midi(0x90 | (ch & 0x0F), note & 0x7F, vel & 0x7F);
}
void midi_send_note_off(uint8_t ch, uint8_t note, uint8_t vel)
{
    send_midi(0x80 | (ch & 0x0F), note & 0x7F, vel & 0x7F);
}
void midi_send_cc(uint8_t ch, uint8_t cc, uint8_t val)
{
    send_midi(0xB0 | (ch & 0x0F), cc & 0x7F, val & 0x7F);
}
void midi_send_pitch_bend(uint8_t ch, int16_t bend14)
{
    uint8_t lsb = bend14 & 0x7F;
    uint8_t msb = (bend14 >> 7) & 0x7F;
    send_midi(0xE0 | (ch & 0x0F), lsb, msb);
}
void midi_send_program_change(uint8_t ch, uint8_t prog)
{
    send_midi(0xC0 | (ch & 0x0F), prog & 0x7F, 0xFF);
}

void midi_on_ble_connect(void)    { ble_connected = true; g_state.ble_connected = true; }
void midi_on_ble_disconnect(void) { ble_connected = false; g_state.ble_connected = false; }
void midi_on_usb_connect(void)    { usb_connected = true; g_state.usb_connected = true; }
void midi_on_usb_disconnect(void) { usb_connected = false; g_state.usb_connected = false; }

/* ── MIDI + Display co-task (50 Hz) ─────────────────────────────────── */
static int8_t  last_note = -1;
static bool    last_gate = false;
static uint8_t last_mod = 0;
static int16_t last_bend = 0;
static uint8_t last_cc2 = 0;
static uint8_t last_cc74 = 0;
static int     disp_counter = 0;

void midi_display_task(void *arg)
{
    (void)arg;
    const TickType_t period = pdMS_TO_TICKS(20);  /* 50 Hz */
    TickType_t last = xTaskGetTickCount();

    while (1) {
        int8_t note = g_state.current_note;
        bool   gate = g_state.breath_gate;
        uint8_t vel = g_state.breath_vel;
        int16_t bend = g_state.bend_cents;
        uint8_t mod  = g_state.modulation;

        /* Convert bend cents → 14-bit MIDI pitch bend */
        int16_t bend14 = (int16_t)(bend * 8192 / 200);  /* ±200 cents → ±8192 */
        if (bend14 > 8192) bend14 = 8192;
        if (bend14 < -8192) bend14 = -8192;
        bend14 += 8192;  /* offset to unsigned 14-bit */

        /* Breath → CC2 */
        uint8_t cc2 = vel;

        /* Lip brightness → CC74 */
        /* (g_state doesn't store lip brightness separately; we derive it) */
        uint8_t cc74 = (uint8_t)((bend / 200.0f) * 127.0f);

        /* Note on/off */
        if (gate && note != last_note) {
            if (last_note >= 0)
                midi_send_note_off(0, last_note, 0);
            midi_send_note_on(0, note, vel);
            synth_note_on(note, vel, &g_state.patch);
            last_note = note;
        } else if (!gate && last_gate) {
            midi_send_note_off(0, last_note, 0);
            synth_note_off(last_note);
            last_note = -1;
        }

        /* Continuous controllers (send every cycle only if changed) */
        if (cc2 != last_cc2) {
            midi_send_cc(0, 2, cc2);   /* Breath */
            last_cc2 = cc2;
        }
        if (mod != last_mod) {
            midi_send_cc(0, 1, mod);   /* Modulation */
            last_mod = mod;
        }
        if (bend14 != last_bend) {
            midi_send_pitch_bend(0, bend14);
            last_bend = bend14;
        }
        if (cc74 != last_cc74) {
            midi_send_cc(0, 74, cc74); /* Brightness */
            last_cc74 = cc74;
        }

        /* Update synth params */
        synth_set_bend_cents(bend);
        synth_set_modulation(mod);
        synth_set_breath((float)vel / 127.0f, &g_state.patch);
        synth_set_vibrato(g_state.vibrato_rate, g_state.vibrato_depth);

        /* Display refresh at ~10 Hz (every 5th cycle) */
        if (++disp_counter >= 5) {
            disp_counter = 0;
            display_update(&g_state);
        }

        vTaskDelayUntil(&last, period);
    }
}