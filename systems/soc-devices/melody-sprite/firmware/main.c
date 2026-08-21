/*
 * Melody Sprite — RP2040 FM Synthesizer
 * main.c — Dual-core main entry point
 *
 * Core 0: UI, touch scanning, OLED, MIDI, sequencer logic
 * Core 1: Audio synthesis engine + I2S output
 *
 * Inter-core communication via multicore FIFO and shared RAM.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Pico SDK headers */
// #include "pico/stdlib.h"
// #include "pico/multicore.h"
// #include "pico/binary_info.h"
// #include "hardware/adc.h"
// #include "hardware/gpio.h"
// #include "hardware/i2c.h"
// #include "hardware/spi.h"
// #include "hardware/timer.h"
// #include "hardware/clocks.h"
// #include "hardware/watchdog.h"

/* Project headers */
#include "synth_engine.h"
#include "sequencer.h"
#include "i2s_audio.h"
#include "touch.h"
#include "display.h"

/* ========== Global State ========== */

static synth_engine_t   synth;
static sequencer_t      seq;
static touch_controller_t touch_ctrl;
static display_t        disp;

/* Shared parameter block (written by core 0, read by core 1) */
typedef struct {
    volatile float pot_mod;      /* Potentiometer 1 value (0–1) */
    volatile float pot_atk;      /* Potentiometer 2 value (0–1) */
    volatile float pot_rel;      /* Potentiometer 3 value (0–1) */
    volatile float pot_fb;       /* Potentiometer 4 value (0–1) */
    volatile bool   power_hold;  /* Keep system powered on */
    volatile bool   shutdown_req;/* Request graceful shutdown */
} shared_params_t;

static shared_params_t shared;

/* Note queue for inter-core communication */
#define NOTE_QUEUE_SIZE 32
typedef struct {
    uint8_t note;
    uint8_t velocity;
    bool    on;         /* true = note on, false = note off */
} note_event_t;

static volatile note_event_t note_queue[NOTE_QUEUE_SIZE];
static volatile int note_queue_head = 0;
static volatile int note_queue_tail = 0;

/* ========== GPIO Pin Definitions ========== */

#define PIN_POT_MOD    26  /* ADC0 (GPIO26) */
#define PIN_POT_ATK    27  /* ADC1 (GPIO27) */
#define PIN_POT_REL    28  /* ADC2 (GPIO28) */
#define PIN_POT_FB     29  /* ADC3 (GPIO29) */

/* Note: ADC channels 0-3 map to GPIO26-29 on RP2040 */
#define ADC_CH_MOD     0
#define ADC_CH_ATK     1
#define ADC_CH_REL     2
#define ADC_CH_FB      3

/* ========== Helper Functions ========== */

static uint16_t adc_read_channel(uint8_t channel)
{
    /* Real: adc_select_input(channel); return adc_read(); */
    (void)channel;
    return 2048; /* Midpoint default */
}

static float adc_to_float(uint16_t raw)
{
    /* 12-bit ADC → 0.0–1.0 with slight dead zone removal */
    float val = (float)raw / 4095.0f;
    if (val < 0.01f) val = 0.0f;
    if (val > 0.99f) val = 1.0f;
    return val;
}

/* Map pot value to synth parameter range */
static float map_range(float val, float min, float max)
{
    return min + val * (max - min);
}

/* ========== Potentiometer Scanning ========== */

static void scan_potentiometers(void)
{
    shared.pot_mod = adc_to_float(adc_read_channel(ADC_CH_MOD));
    shared.pot_atk = adc_to_float(adc_read_channel(ADC_CH_ATK));
    shared.pot_rel = adc_to_float(adc_read_channel(ADC_CH_REL));
    shared.pot_fb  = adc_to_float(adc_read_channel(ADC_CH_FB));

    /* Map pots to first voice parameters (for immediate feedback) */
    /* Mod Index: 0–1023 */
    synth_set_voice_param(&synth, 0, "mod_index", shared.pot_mod * 1023.0f);
    /* Attack: 1–5000 ms */
    synth_set_voice_param(&synth, 0, "attack", map_range(shared.pot_atk, 1.0f, 5000.0f));
    /* Release: 1–5000 ms */
    synth_set_voice_param(&synth, 0, "release", map_range(shared.pot_rel, 1.0f, 5000.0f));
    /* Feedback: 0–15 */
    synth_set_voice_param(&synth, 0, "feedback", shared.pot_fb * 15.0f);
}

/* ========== Touch Callbacks ========== */

static void on_key_event(uint8_t key, uint8_t velocity, bool pressed)
{
    /* Convert key index to MIDI note (with octave offset) */
    uint8_t midi_note = key_to_midi[key] + (synth.octave_offset * 12);

    if (midi_note < MIDI_NOTE_MIN || midi_note > MIDI_NOTE_MAX) return;

    if (pressed) {
        synth_note_on(&synth, midi_note, velocity);

        /* If sequencer is recording, queue this note */
        if (seq.recording) {
            seq.pending_note = midi_note;
            seq.pending_vel  = velocity;
        }
    } else {
        if (!synth.hold_active) {
            synth_note_off(&synth, midi_note);
        }
    }
}

static void on_button_event(uint8_t button, bool pressed)
{
    if (!pressed) return; /* Only act on press */

    switch (button) {
    case BTN_SEQ:
        if (seq.recording) {
            seq_record_stop(&seq);
        } else if (seq.playing) {
            seq_stop(&seq);
        } else {
            seq_record_start(&seq);
        }
        break;

    case BTN_OCT_DN:
        if (synth.octave_offset > -2)
            synth.octave_offset--;
        break;

    case BTN_OCT_UP:
        if (synth.octave_offset < 2)
            synth.octave_offset++;
        break;

    case BTN_WAVE:
        /* Cycle through FM presets */
        /* TODO: implement preset cycling */
        break;

    case BTN_FX1:
        synth_toggle_fx(&synth, "delay", !synth.fx.delay_on);
        break;

    case BTN_FX2:
        synth_toggle_fx(&synth, "crush", !synth.fx.crush_on);
        break;

    case BTN_FX3:
        synth_toggle_fx(&synth, "lpf", !synth.fx.lpf_on);
        break;

    case BTN_HOLD:
        synth.hold_active = !synth.hold_active;
        if (!synth.hold_active) {
            synth_note_all_off(&synth);
        }
        break;
    }
}

/* ========== Rotary Encoder ========== */

static int32_t encoder_count = 0;
static bool encoder_prev_a = false;
static bool encoder_prev_b = false;

static void poll_encoder(void)
{
    /* Real: gpio_get(GPIO10), gpio_get(GPIO11) */
    bool a = false; /* GPIO10 */
    bool b = false; /* GPIO11 */

    /* Quadrature decode */
    if (a != encoder_prev_a) {
        if (a != b) {
            encoder_count++;  /* Clockwise */
        } else {
            encoder_count--;  /* Counter-clockwise */
        }
    }
    encoder_prev_a = a;
    encoder_prev_b = b;

    /* Encoder push button (GPIO12) */
    /* Real: if (!gpio_get(GPIO12)) { ... } */
}

/* ========== Power Management ========== */

static void check_power_timeout(void)
{
    /* Auto-power-off after 30 minutes of no activity */
    static int64_t last_activity_time = 0;
    /* Real: int64_t now = time_us_64(); */
    /* If (now - last_activity_time > 30 * 60 * 1000000) shared.power_hold = false; */
}

/* ========== Core 1 Entry — Audio Engine ========== */

static void audio_core_entry(void)
{
    /* Initialize synthesis engine */
    synth_init(&synth);

    /* Initialize I2S output */
    i2s_init();
    i2s_start();

    /* Audio processing loop — runs on Core 1 exclusively */
    while (1) {
        /* Check for note events from Core 0 */
        while (note_queue_tail != note_queue_head) {
            note_event_t evt = note_queue[note_queue_tail];
            note_queue_tail = (note_queue_tail + 1) % NOTE_QUEUE_SIZE;

            if (evt.on) {
                synth_note_on(&synth, evt.note, evt.velocity);
            } else {
                synth_note_off(&synth, evt.note);
            }
        }

        /* Process synthesis (fills audio_buffer) */
        synth_process(&synth);

        /* Push audio buffer to I2S DMA */
        if (i2s_buffer_available()) {
            i2s_push_buffer(synth.audio_buffer, BUFFER_SIZE);
        }

        /* Check shutdown request */
        if (shared.shutdown_req) {
            i2s_stop();
            break;
        }
    }
}

/* ========== Core 0 — Main Loop ========== */

int main(void)
{
    /* Initialize stdio (for debug UART) */
    // stdio_uart_init();

    /* Initialize GPIO */
    // gpio_init(PIN_PWR_HOLD);
    // gpio_set_dir(PIN_PWR_HOLD, GPIO_OUT);
    // gpio_put(PIN_PWR_HOLD, 1);  /* Hold power on */
    shared.power_hold = true;

    /* Initialize ADC for potentiometers */
    // adc_init();
    // adc_gpio_init(PIN_POT_MOD);
    // adc_gpio_init(PIN_POT_ATK);
    // adc_gpio_init(PIN_POT_REL);
    // adc_gpio_init(PIN_POT_FB);

    /* Initialize I2C for touch and OLED */
    // i2c_init(i2c0, 400000);
    // gpio_set_function(I2C_SDA_PIN, GPIO_FUNC_I2C);
    // gpio_set_function(I2C_SCL_PIN, GPIO_FUNC_I2C);
    // gpio_pull_up(I2C_SDA_PIN);
    // gpio_pull_up(I2C_SCL_PIN);

    /* Initialize SPI for external flash */
    // spi_init(spi0, 32000000);
    // gpio_set_function(16, GPIO_FUNC_SPI);  /* TX */
    // gpio_set_function(17, GPIO_FUNC_SPI);  /* RX */
    // gpio_set_function(18, GPIO_FUNC_SPI);  /* SCK */
    // gpio_init(19); gpio_set_dir(19, GPIO_OUT);  /* CS */

    /* Initialize touch controller */
    touch_init(&touch_ctrl);
    touch_set_key_callback(&touch_ctrl, on_key_event);
    touch_set_button_callback(&touch_ctrl, on_button_event);

    /* Initialize display */
    display_init(&disp);
    display_set_mode(&disp, DISPLAY_MODE_BOOT);
    display_render(&disp);
    display_flush(&disp);

    /* Initialize sequencer */
    seq_init(&seq);

    /* Load default pattern */
    seq_load_pattern(&seq, 0);

    /* Start Core 1 audio engine */
    // multicore_launch_core1(audio_core_entry);

    /* Boot delay — show splash screen */
    // sleep_ms(1500);

    /* Switch to waveform display */
    display_set_mode(&disp, DISPLAY_MODE_WAVEFORM);
    display_render(&disp);

    /* ========== Main Loop ========== */
    uint32_t loop_count = 0;

    while (shared.power_hold) {
        /* 1. Scan capacitive touch (every 5ms) */
        if (loop_count % 5 == 0) {
            touch_scan(&touch_ctrl);
        }

        /* 2. Scan potentiometers (every 10ms) */
        if (loop_count % 10 == 0) {
            scan_potentiometers();
        }

        /* 3. Poll rotary encoder (every 1ms) */
        poll_encoder();

        /* 4. Advance sequencer (every step interval) */
        seq_tick(&seq, &synth);

        /* 5. Update display (every 33ms ≈ 30 fps) */
        if (loop_count % 33 == 0) {
            /* Update display with current synth state */
            display_set_waveform(&disp, synth.audio_buffer, BUFFER_SIZE);

            /* Update sequencer display data */
            seq_display_t seq_disp;
            seq_disp.current_step = seq.current_step;
            seq_disp.tempo = seq.pattern.tempo;
            seq_disp.playing = seq.playing;
            seq_disp.recording = seq.recording;
            display_set_seq_data(&disp, &seq_disp);

            display_render(&disp);
            display_flush(&disp);
        }

        /* 6. Check power timeout */
        check_power_timeout();

        /* 7. Process serial commands (if any) */
        /* TODO: UART command parser for debugging */

        loop_count++;
        // sleep_ms(1);  /* ~1ms per loop iteration */
    }

    /* Graceful shutdown */
    shared.shutdown_req = true;
    // sleep_ms(50);  /* Wait for audio core to finish */
    // gpio_put(PIN_PWR_HOLD, 0);  /* Cut power */

    return 0;
}