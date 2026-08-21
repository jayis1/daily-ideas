/*
 * display.c — SSD1306 OLED UI driver
 */

#include "display.h"
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>

/* SSD1306 I2C address */
#define SSD1306_ADDR  0x3C

extern I2C_HandleTypeDef hi2c1;

/* Simple 128x64 framebuffer */
static uint8_t fb[128 * 64 / 8];

int display_init(void)
{
    /* SSD1306 initialization sequence */
    uint8_t init_cmds[] = {
        0xAE,       /* Display OFF */
        0xD5, 0x80, /* Set display clock divide */
        0xA8, 0x3F, /* Set multiplex ratio (64) */
        0xD3, 0x00, /* Set display offset (0) */
        0x40,       /* Set start line (0) */
        0x8D, 0x14, /* Set charge pump (enable) */
        0x20, 0x00, /* Set memory addressing mode (horizontal) */
        0xA1,       /* Set segment remap (column 127) */
        0xC8,       /* Set COM output scan direction (remap) */
        0xDA, 0x12, /* Set COM pins (64-height) */
        0x81, 0xCF, /* Set contrast */
        0xD9, 0xF1, /* Set pre-charge period */
        0xDB, 0x40, /* Set VCOMH deselect level */
        0xA4,       /* Resume to RAM content */
        0xA6,       /* Set normal display */
        0xAF,       /* Display ON */
    };

    for (int i = 0; i < sizeof(init_cmds); i++) {
        uint8_t buf[2] = {0x00, init_cmds[i]};  /* Co=0, D/C#=0 (command) */
        HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 2, 100);
    }

    memset(fb, 0, sizeof(fb));
    return 0;
}

static void display_send_fb(void)
{
    uint8_t buf[129];
    buf[0] = 0x40;  /* D/C#=1 (data) */
    for (int page = 0; page < 8; page++) {
        /* Set page address */
        uint8_t page_cmds[] = {0x00, 0xB0 | page, 0x00, 0x10};
        for (int j = 0; j < 4; j++) {
            uint8_t cmd[] = {0x00, page_cmds[j]};
            HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, cmd, 2, 10);
        }
        /* Send page data */
        memcpy(&buf[1], &fb[page * 128], 128);
        HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 129, 50);
    }
}

void display_update(const crystal_t *crystal, display_mode_t mode)
{
    memset(fb, 0, sizeof(fb));
    char line[22];

    switch (mode) {
    case DISPLAY_PARAMS:
        snprintf(line, sizeof(line), "fS=%.3f MHz", crystal->params.f_s / 1e6f);
        /* Render line at y=0 */
        snprintf(line, sizeof(line), "R1=%.1f ohm", crystal->params.R1);
        snprintf(line, sizeof(line), "C1=%.1f fF", crystal->params.C1 * 1e15f);
        snprintf(line, sizeof(line), "L1=%.2f mH", crystal->params.L1 * 1e3f);
        snprintf(line, sizeof(line), "C0=%.2f pF", crystal->params.C0 * 1e12f);
        snprintf(line, sizeof(line), "Q=%.0f", crystal->params.Q);
        snprintf(line, sizeof(line), "ESR=%.1f ohm", crystal->params.ESR);
        /* (Simplified: in real firmware, render to framebuffer with font) */
        break;

    case DISPLAY_CIRCLE:
        /* Draw admittance circle: G on x-axis, B on y-axis */
        snprintf(line, sizeof(line), "Admittance Circle");
        /* Plot each sweep point as a pixel */
        for (int i = 0; i < crystal->sweep.n_points && i < 128; i++) {
            int x = (int)(crystal->sweep.points[i].admittance.re * 1e4f) % 128;
            int y = 32 + (int)(crystal->sweep.points[i].admittance.im * 1e4f) % 32;
            if (x >= 0 && x < 128 && y >= 0 && y < 64) {
                fb[(y / 8) * 128 + x] |= (1 << (y % 8));
            }
        }
        break;

    case DISPLAY_TURNOVER:
        snprintf(line, sizeof(line), "Turnover T0=%.1fC", crystal->turnover.T0);
        for (int i = 0; i < crystal->turnover.n_points && i < 128; i++) {
            int x = i;
            int y = 32 - (int)(crystal->turnover.points[i].delta_f_ppm * 100) % 32;
            if (y >= 0 && y < 64) {
                fb[(y / 8) * 128 + x] |= (1 << (y % 8));
            }
        }
        break;

    case DISPLAY_ALLAN:
        snprintf(line, sizeof(line), "Allan Dev");
        break;

    case DISPLAY_CLASSIFY:
        snprintf(line, sizeof(line), "%s (%.0f%%)",
                 crystal->classification.name,
                 crystal->classification.confidence * 100);
        break;
    }

    display_send_fb();
}

void display_show_message(const char *msg)
{
    /* Clear framebuffer and display message */
    memset(fb, 0, sizeof(fb));
    /* (Simplified: in real firmware, render msg with bitmap font) */
    display_send_fb();
}

void display_show_state(device_state_t state)
{
    const char *states[] = {
        "Ready", "Calibrating", "Sweeping",
        "Temp Sweep", "Allan Dev", "Results", "Error"
    };
    if (state >= 0 && state <= 6) {
        display_show_message(states[state]);
    }
}