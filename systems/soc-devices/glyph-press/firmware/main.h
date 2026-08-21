/**
 * glyph_press/firmware/main.h — Glyph Press Portable Braille Embosser
 *
 * RP2040 (Dual Cortex-M0+ @ 133 MHz, 264 KB SRAM, 16 KB ROM)
 * main firmware header.
 *
 * Dual-core architecture:
 *   Core 0: emboss_fsm, braille translation, stepper paper feed, BLE/SD input
 *   Core 1: solenoid driver (shift register + DRV8833), UI (OLED/buttons/encoder/buzzer)
 *
 * Build: see firmware/Makefile (arm-none-eabi-gcc + Pico SDK)
 */

#ifndef GLYPH_PRESS_MAIN_H
#define GLYPH_PRESS_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

/* ── Pin assignments (RP2040 QFN-56) ────────────────────────────── */

/* UART0 — BLE bridge (HC-05) */
#define PIN_UART0_TX        0   /* GP0  → HC-05 RX */
#define PIN_UART0_RX        1   /* GP1  ← HC-05 TX */

/* SPI0 — external flash (W25Q16) + microSD */
#define PIN_SPI0_SCK        2   /* GP2  SPI0 SCK */
#define PIN_SPI0_MOSI       3   /* GP3  SPI0 MOSI */
#define PIN_SPI0_MISO       4   /* GP4  SPI0 MISO */
#define PIN_FLASH_CS        5   /* GP5  W25Q16 CS (active low) */
#define PIN_SD_CS           6   /* GP6  microSD CS (active low) */

/* I2C0 — OLED */
#define PIN_I2C_SDA         7   /* GP7  I2C0 SDA */
#define PIN_I2C_SCL         8   /* GP8  I2C0 SCL */

/* Stepper — TMC2209 / NEMA8 paper feed */
#define PIN_STEP_STEP       9   /* GP9  PIO SM0 → TMC2209 STEP */
#define PIN_STEP_DIR        10  /* GP10 GPIO → TMC2209 DIR */
#define PIN_STEP_EN         11  /* GP11 GPIO → TMC2209 EN (active low) */

/* Servo — paper release/cut */
#define PIN_SERVO            12  /* GP12 PWM → SG90 */

/* Paper sensor */
#define PIN_PAPER_SENSOR     13  /* GP13 ADC1 (TCRT5000) */

/* Buttons */
#define PIN_BTN_START        14  /* GP14 active-low, pull-up */
#define PIN_BTN_MODE         15  /* GP15 active-low, pull-up */
#define PIN_BTN_FEED         16  /* GP16 active-low, pull-up */

/* Rotary encoder */
#define PIN_ENC_A            17  /* GP17 encoder A */
#define PIN_ENC_B            18  /* GP18 encoder B */
#define PIN_ENC_BTN          19  /* GP19 encoder push */

/* Buzzer */
#define PIN_BUZZER           20  /* GP20 piezo drive */

/* WS2812 status LED */
#define PIN_WS2812           21  /* GP21 PIO SM1 */

/* Status LED */
#define PIN_LED_STATUS       22  /* GP22 green LED */

/* ADC */
#define PIN_BATT_ADC         26  /* GP26 ADC0 (battery divider) */
#define PIN_FORCE_ADC        27  /* GP27 ADC1 (force feedback, spare) */
#define PIN_SPARE_ADC        28  /* GP28 ADC2 (spare) */

/* Shift register for solenoid driver (74HC595 chain) */
#define PIN_SR_DATA          19  /* GP19 reconfigured during emboss */
#define PIN_SR_CLK           20  /* GP20 reconfigured during emboss */
#define PIN_SR_LATCH         21  /* GP21 reconfigured during emboss */

/* ── Constants ─────────────────────────────────────────────────── */

#define TEXT_BUFFER_SIZE     4096    /* max input text chars */
#define BRAILLE_DOTS_PER_CELL 8      /* 8-dot mode max */
#define SOLID_DWELL_MS       20      /* solenoid ON time per dot */
#define SOLID_RELEASE_MS     30      /* solenoid OFF recovery */
#define CELL_WIDTH_MM        6.0f    /* Braille cell horizontal spacing */
#define LINE_HEIGHT_MM       10.0f   /* Braille line spacing */
#define STEPS_PER_REV        3200    /* NEMA8 microstepped */
#define ROLLER_DIAMETER_MM   19.1f   /* feed roller diameter */
#define STEPS_PER_MM         (STEPS_PER_REV / (3.14159f * ROLLER_DIAMETER_MM))
#define STEPS_PER_CELL       ((uint32_t)(CELL_WIDTH_MM * STEPS_PER_MM))
#define STEPS_PER_LINE       ((uint32_t)(LINE_HEIGHT_MM * STEPS_PER_MM))

#define DEFAULT_CELLS_PER_LINE  28
#define MIN_CELLS_PER_LINE      20
#define MAX_CELLS_PER_LINE      40
#define DEFAULT_FORCE           5     /* 0-9 scale */
#define DEFAULT_LANG            0     /* English */

/* ── Types ──────────────────────────────────────────────────────── */

typedef enum {
    MODE_GRADE1 = 0,    /* uncontracted Braille */
    MODE_GRADE2,        /* UEB contracted */
    MODE_8DOT,          /* 8-dot Unicode pass-through */
    MODE_LABEL,         /* single-line centered label */
    MODE_PAGE,          /* multi-line page */
    MODE_COUNT
} gp_mode_t;

typedef enum {
    STATE_IDLE = 0,
    STATE_TRANSLATE,
    STATE_EMBOSS_CELL,
    STATE_ADVANCE,
    STATE_LINE_FEED,
    STATE_DONE,
    STATE_ERROR
} gp_state_t;

typedef enum {
    LANG_EN = 0,    /* English */
    LANG_FR,        /* French */
    LANG_ES,        /* Spanish */
    LANG_DE,        /* German */
    LANG_PT,        /* Portuguese */
    LANG_AR,        /* Arabic */
    LANG_HI,        /* Hindi */
    LANG_ZH,        /* Chinese pinyin */
    LANG_COUNT
} gp_lang_t;

typedef struct {
    gp_mode_t  mode;
    gp_lang_t  lang;
    uint8_t    force;          /* 0-9 */
    uint8_t    cells_per_line; /* 20-40 */
    uint8_t    current_line;
    uint16_t   cells_done;
    uint16_t   cells_total;
} gp_config_t;

typedef struct {
    char        text[TEXT_BUFFER_SIZE];
    uint16_t    text_len;
    uint16_t    text_pos;      /* current position in text */
    uint8_t     dots[DEFAULT_CELLS_PER_LINE * 8]; /* translated dot patterns for current line */
    uint16_t    dot_pos;       /* current cell being embossed */
    uint16_t    dot_count;     /* cells in current line */
} gp_buffer_t;

/* ── Global state (shared between cores via SRAM) ──────────────── */

extern volatile gp_state_t g_state;
extern volatile gp_config_t g_config;
extern gp_buffer_t g_buffer;
extern volatile bool g_emboss_trigger;     /* Core 0 → Core 1: fire solenoids */
extern volatile uint8_t g_current_dots;    /* 8-bit dot pattern to fire */
extern volatile bool g_emboss_done;        /* Core 1 → Core 0: emboss complete */
extern volatile bool g_feed_done;           /* stepper feed complete */
extern volatile bool g_paper_present;      /* paper sensor reading */
extern volatile bool g_ble_text_ready;     /* new text received via BLE */
extern volatile uint16_t g_batt_mv;        /* battery voltage in mV */

/* ── Function declarations ─────────────────────────────────────── */

/* main.c */
void system_init(void);
void buzzer_beep(uint16_t freq_hz, uint16_t dur_ms);

/* braille.c */
uint16_t braille_translate(const char *text, uint16_t len, uint8_t *out_dots,
                            gp_mode_t mode, gp_lang_t lang);
uint8_t  braille_grade1(char ch, gp_lang_t lang);
uint16_t braille_grade2(const char *text, uint16_t pos, uint16_t len,
                        uint8_t *out_dot, gp_lang_t lang);

/* emboss.c */
void emboss_init(void);
void emboss_fire_cell(uint8_t dots);
void emboss_wait(void);

/* feed.c */
void feed_init(void);
void feed_cell(void);
void feed_line(void);
void feed_mm(float mm);
void feed_wait(void);

/* sh1106.c */
void oled_init(void);
void oled_clear(void);
void oled_text(uint8_t x, uint8_t y, const char *text);
void oled_braille_preview(uint8_t x, uint8_t y, const uint8_t *dots, uint16_t count);
void oled_progress(uint8_t x, uint8_t y, uint8_t w, uint8_t pct);
void oled_status(const char *line1, const char *line2);

/* ble_uart.c */
void ble_init(void);
void ble_task(void);       /* called from Core 1 super-loop */
bool ble_get_line(char *buf, uint16_t maxlen);
void ble_send(const char *str);

/* sd_card.c */
bool sd_init(void);
bool sd_read_first_txt(char *buf, uint16_t maxlen, uint16_t *len_out);

/* flash_table.c */
bool flash_table_init(void);
bool flash_table_load(gp_lang_t lang, uint8_t *table, uint16_t maxlen);

/* buttons.c */
void buttons_init(void);
void buttons_poll(void);
bool button_start_pressed(void);
bool button_mode_pressed(void);
bool button_feed_pressed(void);

/* encoder.c */
void encoder_init(void);
int8_t encoder_delta(void);  /* returns -1, 0, +1 */

/* ws2812.c */
void ws2812_init(void);
void ws2812_set(uint8_t r, uint8_t g, uint8_t b);

/* battery.c */
void battery_init(void);
uint16_t battery_read_mv(void);

/* paper_sensor.c */
void paper_sensor_init(void);
bool paper_is_present(void);

#endif /* GLYPH_PRESS_MAIN_H */