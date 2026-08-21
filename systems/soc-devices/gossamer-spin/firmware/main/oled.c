/*
 * gossamer-spin / firmware / oled.c
 * SSD1306 OLED display (128×64, I2C) for process dashboard.
 *
 * Layout (128×64):
 *   Line 0: Recipe name + state       (8x16 font)
 *   Line 2: HV: 18.0kV  I: 200nA
 *   Line 3: Flow: 1.0mL/h  RPM: 800
 *   Line 4: T: 23°C  RH: 35%
 *   Line 5: Jet: STABLE  σ: 25nA
 *   Line 7: Time: 12:34 / 30:00
 */
#include "main.h"

static void *h_i2c1 = (void *)1;

#define OLED_ADDR  0x3C

static void oled_cmd(uint8_t c)
{
    /* I2C write: [OLED_ADDR, 0x00, c] */
    (void)c;
}

static void oled_data(uint8_t d)
{
    /* I2C write: [OLED_ADDR, 0x40, d] */
    (void)d;
}

static void oled_set_cursor(int col, int row)
{
    oled_cmd(0xB0 + row);            /* page address */
    oled_cmd(0x00 + (col & 0x0F));   /* low column */
    oled_cmd(0x10 + (col >> 4));     /* high column */
}

/* Simple 8x16 font — draws ASCII chars (subset). In a real build,
   this would use a font table. Placeholder draws text via printf-style
   string rendering. */
static void oled_text(int col, int row, const char *s)
{
    oled_set_cursor(col, row);
    /* In real build: look up each char in font table, send 8 bytes per
       column, 8 columns per char (8×16 font). */
    (void)s;
}

void oled_init(void)
{
    /* SSD1306 init sequence:
       0xAE (display off)
       0xD5 0x80 (set display clock divide)
       0xA8 0x3F (set multiplex ratio)
       0xD3 0x00 (set display offset)
       0x40 (set start line)
       0x8D 0x14 (enable charge pump)
       0xA1 (set segment remap)
       0xC8 (set COM output scan direction)
       0xDA 0x12 (set COM pins)
       0x81 0xCF (set contrast)
       0xD9 0xF1 (set pre-charge period)
       0xDB 0x40 (set VCOMH deselect level)
       0xA4 (display from RAM)
       0xA6 (normal display, not inverted)
       0xAF (display on) */
    (void)h_i2c1;
}

void oled_update(spin_ctx_t *ctx)
{
    char buf[22];
    process_t *p = &ctx->proc;

    /* Line 0: Recipe name + state */
    snprintf(buf, sizeof(buf), "%-8s %6s",
             ctx->recipe.name,
             ctx->state == ST_RUNNING ? "RUN" :
             ctx->state == ST_SAFE   ? "SAFE" :
             ctx->state == ST_IDLE   ? "IDLE" : "????");
    oled_text(0, 0, buf);

    /* Line 2: HV + jet current */
    snprintf(buf, sizeof(buf), "HV:%4.1fkV I:%4.0fnA",
             p->voltage_kv, p->current_na);
    oled_text(0, 2, buf);

    /* Line 3: Flow + RPM */
    snprintf(buf, sizeof(buf), "F:%4.1fmL R:%4drpm",
             p->flow_mlh, (int)p->drum_rpm);
    oled_text(0, 3, buf);

    /* Line 4: Temp + humidity */
    snprintf(buf, sizeof(buf), "T:%4.1fC H:%4.1f%%",
             p->temp_c, p->rh_pct);
    oled_text(0, 4, buf);

    /* Line 5: Jet state + sigma */
    const char *jn = "IDLE";
    if (p->jet_state >= 0 && p->jet_state < 5)
        jn = JET_STATE_NAMES[p->jet_state];
    snprintf(buf, sizeof(buf), "J:%-6s s:%4.0fnA", jn, p->jet_sigma_na);
    oled_text(0, 5, buf);

    /* Line 7: Elapsed / total time */
    uint32_t el = p->elapsed_s;
    uint32_t tot = ctx->recipe.duration_s;
    snprintf(buf, sizeof(buf), "%02lu:%02lu / %02lu:%02lu",
             (unsigned long)(el / 60), (unsigned long)(el % 60),
             (unsigned long)(tot / 60), (unsigned long)(tot % 60));
    oled_text(0, 7, buf);
}