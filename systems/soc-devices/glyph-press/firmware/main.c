/**
 * glyph_press/firmware/main.c — Glyph Press Portable Braille Embosser
 *
 * RP2040 (Dual Cortex-M0+ @ 133 MHz, 264 KB SRAM)
 *
 * Main firmware — Core 0 runs the emboss state machine + Braille translation +
 * stepper paper feed + BLE/SD text input. Core 1 runs the solenoid driver +
 * UI (OLED, buttons, encoder, buzzer) + BLE UART protocol.
 *
 * Emboss state machine:
 *   IDLE → (text received) → TRANSLATE → EMBOSS_CELL → ADVANCE → EMBOSS_CELL ...
 *           └─(line end)──→ LINE_FEED → EMBOSS_CELL
 *           └─(text end)──→ DONE → IDLE
 *
 * Build: see firmware/Makefile (Pico SDK + arm-none-eabi-gcc)
 */

#include "main.h"
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/bootrom.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"
#include "hardware/pwm.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/pio.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "GLYPH";

/* ── Global state ──────────────────────────────────────────────────── */

volatile gp_state_t  g_state = STATE_IDLE;
volatile gp_config_t g_config;
gp_buffer_t          g_buffer;
volatile bool g_emboss_trigger  = false;
volatile uint8_t g_current_dots = 0;
volatile bool g_emboss_done      = false;
volatile bool g_feed_done        = false;
volatile bool g_paper_present    = false;
volatile bool g_ble_text_ready   = false;
volatile uint16_t g_batt_mv      = 4200;

/* ── Core 1 entry: solenoid driver + UI ────────────────────────────── */

static void core1_main(void)
{
    /* Initialise UI + solenoid subsystems */
    oled_init();
    oled_clear();
    oled_status("Glyph Press", "Ready");
    ws2812_set(0, 8, 0);  /* dim green = idle */

    emboss_init();
    buttons_init();
    encoder_init();
    ble_init();
    paper_sensor_init();

    bool prev_start = false, prev_mode = false, prev_feed = false;
    uint32_t last_ui_update = 0;

    while (true) {
        /* ── Solenoid driver: fire on trigger ── */
        if (g_emboss_trigger) {
            emboss_fire_cell(g_current_dots);
            g_emboss_trigger = false;
            g_emboss_done = true;
        }

        /* ── BLE UART protocol handler ── */
        ble_task();

        /* ── Button polling ── */
        buttons_poll();
        bool start = button_start_pressed();
        bool mode  = button_mode_pressed();
        bool feed  = button_feed_pressed();

        if (start && !prev_start) {
            if (g_state == STATE_IDLE && g_buffer.text_len > 0) {
                g_state = STATE_TRANSLATE;
                g_config.cells_done = 0;
                g_buffer.text_pos = 0;
                buzzer_beep(880, 100);
            }
        }
        if (mode && !prev_mode) {
            g_config.mode = (gp_mode_t)((g_config.mode + 1) % MODE_COUNT);
            buzzer_beep(660, 50);
        }
        if (feed && !prev_feed) {
            feed_mm(10.0f);
        }

        prev_start = start;
        prev_mode  = mode;
        prev_feed  = feed;

        /* ── Encoder: adjust force ── */
        int8_t enc = encoder_delta();
        if (enc != 0) {
            int16_t f = (int16_t)g_config.force + enc;
            if (f < 0) f = 0;
            if (f > 9) f = 9;
            g_config.force = (uint8_t)f;
        }

        /* ── Paper sensor ── */
        g_paper_present = paper_is_present();

        /* ── UI update @ 5 Hz ── */
        uint32_t now = to_ms_since_boot(get_absolute_time());
        if (now - last_ui_update > 200) {
            last_ui_update = now;
            char l1[32], l2[32];
            const char *mode_str[] = {"G1","G2","8dot","Label","Page"};
            const char *lang_str[] = {"en","fr","es","de","pt","ar","hi","zh"};
            snprintf(l1, sizeof(l1), "Mode:%s Lang:%s F%d",
                     mode_str[g_config.mode % 5],
                     lang_str[g_config.lang % LANG_COUNT],
                     g_config.force);
            snprintf(l2, sizeof(l2), "Cells:%d/%d %s",
                     g_config.cells_done, g_config.cells_total,
                     g_paper_present ? "Paper OK" : "NO PAPER");
            oled_status(l1, l2);

            /* Battery read */
            g_batt_mv = battery_read_mv();
        }

        sleep_ms(2);
    }
}

/* ── Core 0: emboss state machine ──────────────────────────────────── */

static void emboss_fsm(void)
{
    while (true) {
        switch (g_state) {
        case STATE_IDLE:
            /* Check for new text from BLE or SD */
            if (g_ble_text_ready) {
                g_ble_text_ready = false;
                g_state = STATE_TRANSLATE;
                g_config.cells_done = 0;
                g_buffer.text_pos = 0;
            }
            sleep_ms(10);
            break;

        case STATE_TRANSLATE: {
            /* Translate remaining text into dot patterns for the current line */
            uint16_t remaining = g_buffer.text_len - g_buffer.text_pos;
            uint16_t to_translate = remaining;
            if (to_translate > g_config.cells_per_line)
                to_translate = g_config.cells_per_line;

            uint16_t cells = braille_translate(
                &g_buffer.text[g_buffer.text_pos],
                to_translate,
                g_buffer.dots,
                g_config.mode,
                g_config.lang);

            g_buffer.dot_count  = cells;
            g_buffer.dot_pos     = 0;
            g_config.cells_total += cells;

            if (cells == 0) {
                g_state = STATE_DONE;
            } else {
                g_state = STATE_EMBOSS_CELL;
            }
            break;
        }

        case STATE_EMBOSS_CELL: {
            if (!g_paper_present) {
                buzzer_beep(200, 500);
                g_state = STATE_ERROR;
                break;
            }
            /* Fire solenoids for current cell */
            uint8_t dots = g_buffer.dots[g_buffer.dot_pos];
            g_current_dots   = dots;
            g_emboss_done    = false;
            g_emboss_trigger = true;

            /* Wait for Core 1 to finish embossing */
            uint32_t timeout = to_ms_since_boot(get_absolute_time()) + 200;
            while (!g_emboss_done) {
                if (to_ms_since_boot(get_absolute_time()) > timeout) {
                    g_state = STATE_ERROR;
                    break;
                }
                tight_loop_contents();
            }
            if (g_state == STATE_ERROR) break;

            g_config.cells_done++;
            g_buffer.dot_pos++;
            g_buffer.text_pos++;

            if (g_buffer.dot_pos >= g_buffer.dot_count) {
                /* End of line */
                g_state = STATE_LINE_FEED;
            } else {
                g_state = STATE_ADVANCE;
            }
            break;
        }

        case STATE_ADVANCE:
            /* Advance paper by one cell width */
            g_feed_done = false;
            feed_cell();
            {
                uint32_t timeout = to_ms_since_boot(get_absolute_time()) + 500;
                while (!g_feed_done) {
                    if (to_ms_since_boot(get_absolute_time()) > timeout) {
                        g_state = STATE_ERROR;
                        break;
                    }
                    tight_loop_contents();
                }
            }
            if (g_state != STATE_ERROR)
                g_state = STATE_EMBOSS_CELL;
            break;

        case STATE_LINE_FEED:
            /* Check if more text remains */
            if (g_buffer.text_pos >= g_buffer.text_len) {
                g_state = STATE_DONE;
            } else {
                /* Feed one line height, then continue */
                g_feed_done = false;
                feed_line();
                uint32_t timeout = to_ms_since_boot(get_absolute_time()) + 1000;
                while (!g_feed_done) {
                    if (to_ms_since_boot(get_absolute_time()) > timeout) {
                        g_state = STATE_ERROR;
                        break;
                    }
                    tight_loop_contents();
                }
                if (g_state != STATE_ERROR)
                    g_state = STATE_TRANSLATE;
            }
            break;

        case STATE_DONE:
            buzzer_beep(1000, 200);
            sleep_ms(300);
            buzzer_beep(1200, 200);
            ws2812_set(0, 8, 0);
            g_state = STATE_IDLE;
            g_config.cells_total = 0;
            break;

        case STATE_ERROR:
            ws2812_set(8, 0, 0);
            buzzer_beep(200, 500);
            sleep_ms(1000);
            g_state = STATE_IDLE;
            break;
        }
    }
}

/* ── System initialization ─────────────────────────────────────────── */

void system_init(void)
{
    /* Default configuration */
    memset(&g_buffer, 0, sizeof(g_buffer));
    g_config.mode           = MODE_GRADE2;
    g_config.lang           = LANG_EN;
    g_config.force          = DEFAULT_FORCE;
    g_config.cells_per_line = DEFAULT_CELLS_PER_LINE;
    g_config.current_line   = 0;
    g_config.cells_done     = 0;
    g_config.cells_total    = 0;
}

/* ── Buzzer ────────────────────────────────────────────────────────── */

void buzzer_beep(uint16_t freq_hz, uint16_t dur_ms)
{
    /* Simple GPIO toggle buzzer (piezo) */
    uint32_t half_period_us = 500000 / freq_hz;
    uint32_t total_us = (uint32_t)dur_ms * 1000;
    uint32_t elapsed = 0;
    while (elapsed < total_us) {
        gpio_put(PIN_BUZZER, 1);
        sleep_us(half_period_us);
        gpio_put(PIN_BUZZER, 0);
        sleep_us(half_period_us);
        elapsed += half_period_us * 2;
    }
}

/* ── Main entry (Core 0) ──────────────────────────────────────────── */

int main(void)
{
    /* Set system clock to 133 MHz */
    set_sys_clock_khz(133000, true);

    stdio_init_all();
    system_init();

    /* Initialise GPIO for buzzer, LED */
    gpio_init(PIN_BUZZER);
    gpio_set_dir(PIN_BUZZER, GPIO_OUT);
    gpio_init(PIN_LED_STATUS);
    gpio_set_dir(PIN_LED_STATUS, GPIO_OUT);
    gpio_put(PIN_LED_STATUS, 1);

    /* Initialise battery ADC */
    battery_init();

    /* Initialise external flash (Braille tables) */
    flash_table_init();

    /* Initialise stepper feed */
    feed_init();

    /* Launch Core 1 */
    multicore_launch_core1(core1_main);

    printf("%s: Glyph Press starting...\n", TAG);

    /* Startup beep */
    buzzer_beep(523, 100);
    sleep_ms(100);
    buzzer_beep(659, 100);
    sleep_ms(100);
    buzzer_beep(784, 150);

    /* Run emboss state machine on Core 0 */
    emboss_fsm();

    return 0;
}