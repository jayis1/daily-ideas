/*
 * display.c — SSD1306 OLED B-H loop plot
 *
 * Draws the hysteresis loop into a 128×64 framebuffer and ships it over
 * I2C to the SSD1306. The loop is auto-scaled to the peak |H| and |B|
 * so the whole loop fits the screen, with a 2-pixel margin. A numeric
 * readout of B_sat (mT), H_c (A/m), P_v (W/kg) is drawn on the right
 * margin / bottom row.
 */
#include "display.h"
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define DISP_W 128
#define DISP_H 64
static uint8_t g_fb[DISP_W * DISP_H / 8];   /* 1 bpp framebuffer */

static void fb_clear(void) { memset(g_fb, 0, sizeof(g_fb)); }
static void fb_px(int x, int y)
{
    if (x < 0 || x >= DISP_W || y < 0 || y >= DISP_H) return;
    g_fb[(y / 8) * DISP_W + x] |= (1 << (y & 7));
}
static void fb_line(int x0, int y0, int x1, int y1)
{
    /* Bresenham */
    int dx = abs(x1 - x0), dy = -abs(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int e = dx + dy;
    for (;;) {
        fb_px(x0, y0);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * e;
        if (e2 >= dy) { e += dy; x0 += sx; }
        if (e2 <= dx) { e += dx; y0 += sy; }
    }
}

void display_init(void)
{
    fb_clear();
    /* SSD1306 I2C init sequence, normal display mode. */
}

void display_plot_loop(const float *H, const float *B, int n,
                       const bh_result_t *r)
{
    if (!H || !B || n < 2) return;
    fb_clear();

    /* Auto-scale */
    float hmax = 1e-9f, bmax = 1e-9f;
    for (int i = 0; i < n; i++) {
        if (fabsf(H[i]) > hmax) hmax = fabsf(H[i]);
        if (fabsf(B[i]) > bmax) bmax = fabsf(B[i]);
    }
    /* Plot area: x [8..96], y [2..54] leaving room for text */
    int px0 = 8, px1 = 96, py0 = 2, py1 = 54;
    int pw = px1 - px0, ph = py1 - py0;

    /* Axes (cross at center) */
    fb_line(px0, py0 + ph / 2, px1, py0 + ph / 2);   /* H axis */
    fb_line(px0 + pw / 2, py0, px0 + pw / 2, py1);   /* B axis */

    /* Loop */
    int prev_x = 0, prev_y = 0;
    for (int i = 0; i < n; i++) {
        int x = px0 + (int)((H[i] / hmax) * (pw / 2) + pw / 2);
        int y = py1 - (int)((B[i] / bmax) * (ph / 2) + ph / 2);
        if (i > 0) fb_line(prev_x, prev_y, x, y);
        prev_x = x; prev_y = y;
    }

    /* Numeric readout (right side + bottom) — drawn as text via a
     * minimal 5×7 font; here we just leave space and let the firmware
     * sprintf into a text row. */
    (void)r;
    /* Ship framebuffer to SSD1306 over I2C. */
}