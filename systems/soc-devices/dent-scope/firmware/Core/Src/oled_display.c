/*
 * dent-scope / Core/Src/oled_display.c
 * Dent Scope — SSD1306 OLED display driver (SPI, 128×64)
 * MIT License.
 */
#include "oled_display.h"

#define OLED_WIDTH  128
#define OLED_HEIGHT 64

static uint8_t framebuffer[OLED_HEIGHT / 8][OLED_WIDTH];

static void oled_cmd(uint8_t cmd)
{
    HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET); /* command */
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &cmd, 1, 50);
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
}

static void oled_data(uint8_t data)
{
    HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_SET); /* data */
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &data, 1, 50);
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
}

void oled_init(void)
{
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_RESET);
    HAL_Delay(10);
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_SET);

    oled_cmd(0xAE); /* display off */
    oled_cmd(0xD5); oled_cmd(0x80); /* clock div */
    oled_cmd(0xA8); oled_cmd(0x3F); /* multiplex 1/64 */
    oled_cmd(0xD3); oled_cmd(0x00); /* display offset */
    oled_cmd(0x40); /* start line 0 */
    oled_cmd(0x8D); oled_cmd(0x14); /* charge pump on */
    oled_cmd(0x20); oled_cmd(0x00); /* addressing mode horizontal */
    oled_cmd(0xA1); /* segment remap */
    oled_cmd(0xC8); /* COM scan direction */
    oled_cmd(0xDA); oled_cmd(0x12); /* COM pins */
    oled_cmd(0x81); oled_cmd(0xCF); /* contrast */
    oled_cmd(0xD9); oled_cmd(0xF1); /* pre-charge */
    oled_cmd(0xDB); oled_cmd(0x40); /* VCOM detect */
    oled_cmd(0xA4); /* display RAM content */
    oled_cmd(0xA6); /* normal display */
    oled_cmd(0xAF); /* display on */

    memset(framebuffer, 0, sizeof(framebuffer));
}

static void oled_flush(void)
{
    for (uint8_t page = 0; page < 8; page++) {
        oled_cmd(0xB0 + page);
        oled_cmd(0x10); /* col high */
        oled_cmd(0x00); /* col low */
        for (uint8_t col = 0; col < 128; col++)
            oled_data(framebuffer[page][col]);
    }
}

/* Simple 5×7 font */
static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x3E,0x51,0x49,0x45,0x3E}, /* 0 */
    {0x00,0x42,0x7F,0x40,0x00}, /* 1 */
    {0x42,0x61,0x51,0x49,0x46}, /* 2 */
    {0x21,0x41,0x45,0x4B,0x31}, /* 3 */
    {0x18,0x14,0x12,0x7F,0x10}, /* 4 */
    {0x27,0x45,0x45,0x45,0x39}, /* 5 */
    {0x3C,0x4A,0x49,0x49,0x30}, /* 6 */
    {0x01,0x71,0x09,0x05,0x03}, /* 7 */
    {0x36,0x49,0x49,0x49,0x36}, /* 8 */
    {0x06,0x49,0x49,0x29,0x1E}, /* 9 */
    {0x7E,0x11,0x11,0x11,0x7E}, /* A */
    {0x7F,0x49,0x49,0x49,0x36}, /* B */
    {0x3E,0x41,0x41,0x41,0x22}, /* C */
    {0x7F,0x41,0x41,0x22,0x1C}, /* D */
    {0x7F,0x49,0x49,0x49,0x41}, /* E */
    {0x7F,0x09,0x09,0x09,0x01}, /* F */
    {0x3E,0x41,0x49,0x49,0x7A}, /* G */
    {0x7F,0x08,0x08,0x08,0x7F}, /* H */
    {0x00,0x41,0x7F,0x41,0x00}, /* I */
    {0x20,0x40,0x41,0x3F,0x01}, /* J */
    {0x7F,0x08,0x14,0x22,0x41}, /* K */
    {0x7F,0x40,0x40,0x40,0x40}, /* L */
    {0x7F,0x02,0x0C,0x02,0x7F}, /* M */
    {0x7F,0x04,0x08,0x10,0x7F}, /* N */
    {0x3E,0x41,0x41,0x41,0x3E}, /* O */
    {0x7F,0x09,0x09,0x09,0x06}, /* P */
    {0x1E,0x21,0x21,0x21,0x5E}, /* Q */
    {0x7F,0x09,0x19,0x29,0x46}, /* R */
    {0x46,0x49,0x49,0x49,0x31}, /* S */
    {0x01,0x01,0x7F,0x01,0x01}, /* T */
    {0x3F,0x40,0x40,0x40,0x3F}, /* U */
    {0x1F,0x20,0x40,0x20,0x1F}, /* V */
    {0x3F,0x40,0x38,0x40,0x3F}, /* W */
    {0x63,0x14,0x08,0x14,0x63}, /* X */
    {0x07,0x08,0x70,0x08,0x07}, /* Y */
    {0x61,0x51,0x49,0x45,0x43}, /* Z */
    {0x7C,0x12,0x11,0x12,0x7C}, /* a */
    {0x7F,0x10,0x11,0x11,0x0E}, /* b */
    {0x1F,0x20,0x20,0x20,0x1F}, /* c */
    {0x00,0x44,0x7D,0x40,0x00}, /* d */
    {0x1F,0x24,0x24,0x24,0x1C}, /* e */
    {0x00,0x44,0x7D,0x40,0x00}, /* f */
    {0x3E,0x41,0x49,0x49,0x7A}, /* g */
    {0x7F,0x08,0x08,0x08,0x7F}, /* h */
    {0x00,0x41,0x7F,0x41,0x00}, /* i */
    {0x20,0x40,0x41,0x3F,0x01}, /* j */
    {0x7F,0x10,0x28,0x44,0x41}, /* k */
    {0x7F,0x40,0x40,0x40,0x40}, /* l */
    {0x7F,0x02,0x04,0x02,0x7F}, /* m */
    {0x7F,0x08,0x10,0x08,0x7F}, /* n */
    {0x3E,0x41,0x41,0x41,0x3E}, /* o */
    {0x7F,0x11,0x11,0x11,0x0E}, /* p */
    {0x1E,0x21,0x21,0x21,0x5E}, /* q */
    {0x7F,0x09,0x09,0x09,0x01}, /* r */
    {0x46,0x49,0x49,0x49,0x31}, /* s */
    {0x01,0x01,0x7F,0x01,0x01}, /* t */
    {0x3F,0x40,0x40,0x40,0x3F}, /* u */
    {0x1F,0x20,0x40,0x20,0x1F}, /* v */
    {0x3F,0x40,0x38,0x40,0x3F}, /* w */
    {0x63,0x14,0x08,0x14,0x63}, /* x */
    {0x07,0x08,0x70,0x08,0x07}, /* y */
    {0x61,0x51,0x49,0x45,0x43}, /* z */
    {0x00,0x08,0x36,0x41,0x00}, /* . */
    {0x00,0x08,0x08,0x08,0x00}, /* - */
    {0x44,0x44,0x7C,0x44,0x44}, /* + */
    {0x40,0x40,0x40,0x40,0x40}, /* _ */
    {0x00,0x06,0x09,0x09,0x06}, /* ° */
    {0x00,0x36,0x36,0x00,0x00}, /* : */
    {0x00,0x00,0x00,0x00,0x7F}, /* | */
    {0x00,0x60,0x18,0x06,0x00}, /* > */
    {0x00,0x06,0x18,0x60,0x00}, /* < */
    {0x00,0x08,0x08,0x08,0x08}, /* ! */
    {0x08,0x08,0x08,0x08,0x00}, /* ... */
    {0x00,0x00,0x60,0x60,0x00}, /* . */
    {0x18,0x18,0x00,0x18,0x18}, /* = */
    {0x22,0x14,0x08,0x14,0x22}, /* × */
};

static int char_idx(char c)
{
    if (c == ' ') return 0;
    if (c >= '0' && c <= '9') return 1 + (c - '0');
    if (c >= 'A' && c <= 'Z') return 11 + (c - 'A');
    if (c >= 'a' && c <= 'z') return 37 + (c - 'a');
    switch (c) {
        case '.': return 63;
        case '-': return 64;
        case '+': return 65;
        case '_': return 66;
        case 0xB0: return 67; /* ° */
        case ':': return 68;
        case '|': return 69;
        case '>': return 70;
        case '<': return 71;
        case '!': return 72;
        case '=': return 74;
        case 0xD7: return 75; /* × */
        default: return 0;
    }
}

static void draw_char(int x, int y, char c)
{
    int idx = char_idx(c);
    if (idx < 0) idx = 0;
    for (int col = 0; col < 5; col++) {
        uint8_t bits = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            if (bits & (1 << row)) {
                int px = x + col;
                int py = y + row;
                if (px < 128 && py < 64)
                    framebuffer[py / 8][px] |= (1 << (py % 8));
            }
        }
    }
}

static void draw_text(int x, int y, const char *txt)
{
    int px = x;
    while (*txt) {
        draw_char(px, y, *txt);
        px += 6;
        txt++;
    }
}

static void clear_line(int y)
{
    int page = y / 8;
    for (int x = 0; x < 128; x++)
        framebuffer[page][x] = 0;
    /* also clear next page for 7-pixel-tall text */
    int page2 = (y + 7) / 8;
    if (page2 != page && page2 < 8)
        for (int x = 0; x < 128; x++)
            framebuffer[page2][x] = 0;
}

void oled_text(uint8_t row, const char *txt)
{
    int y = row * 9;
    clear_line(y);
    draw_text(0, y, txt);
    oled_flush();
}

static void int_to_str(int val, char *buf, int *len)
{
    *len = 0;
    if (val < 0) { buf[(*len)++] = '-'; val = -val; }
    char tmp[12]; int tl = 0;
    if (val == 0) tmp[tl++] = '0';
    while (val > 0) { tmp[tl++] = '0' + (val % 10); val /= 10; }
    while (tl > 0) buf[(*len)++] = tmp[--tl];
    buf[*len] = 0;
}

static void float_to_str(float val, int decimals, char *buf)
{
    int neg = val < 0;
    if (neg) val = -val;
    int int_part = (int)val;
    float frac = val - int_part;
    int scale = 1;
    for (int i = 0; i < decimals; i++) scale *= 10;
    int frac_part = (int)(frac * scale + 0.5f);
    if (frac_part >= scale) { int_part++; frac_part -= scale; }

    int len = 0;
    if (neg) buf[len++] = '-';
    int_to_str(int_part, buf + len, &len);
    if (decimals > 0) {
        buf[len++] = '.';
        for (int i = decimals - 1; i >= 0; i--) {
            int digit = (frac_part / (int)(powf(10, i))) % 10;
            buf[len++] = '0' + digit;
        }
    }
    buf[len] = 0;
}

void oled_draw_status(ds_status_t *st)
{
    memset(framebuffer, 0, sizeof(framebuffer));
    char buf[24];

    /* Row 0: state + force */
    const char *state_str = "IDLE";
    switch (st->state) {
        case DS_APPROACHING: state_str = "APPROACH"; break;
        case DS_LOADING:     state_str = "LOADING"; break;
        case DS_HOLDING:     state_str = "HOLDING"; break;
        case DS_UNLOADING:   state_str = "UNLOAD "; break;
        case DS_RETRACTING:  state_str = "RETRACT"; break;
        case DS_ALARM:       state_str = "ALARM!"; break;
        default: break;
    }
    draw_text(0, 0, state_str);
    float_to_str(st->force_mN / 1000.0f, 2, buf);
    draw_text(64, 0, buf);
    draw_text(120, 0, "N");

    /* Row 1: depth */
    float_to_str(st->depth_um, 1, buf);
    draw_text(0, 9, "h:");
    draw_text(12, 9, buf);
    draw_text(60, 9, "um");

    /* Row 2: tilt */
    float_to_str(st->tilt_deg, 1, buf);
    draw_text(0, 18, "Tilt:");
    draw_text(30, 18, buf);
    draw_text(54, 18, "deg");

    /* Row 3: tip type */
    const char *tip = "VICK";
    if (st->tip == TIP_BERKOVICH) tip = "BERK";
    else if (st->tip == TIP_WC_BALL_1MM) tip = "BALL";
    draw_text(0, 27, "Tip:");
    draw_text(24, 27, tip);
    float_to_str(g_cfg.target_force_N, 1, buf);
    draw_text(60, 27, buf);
    draw_text(84, 27, "N");

    /* Row 4: temperature */
    float_to_str(st->temp_c, 1, buf);
    draw_text(0, 36, "T:");
    draw_text(12, 36, buf);
    draw_text(36, 36, "C");
    float_to_str(st->battery_v, 1, buf);
    draw_text(60, 36, "B:");
    draw_text(72, 36, buf);
    draw_text(90, 36, "V");

    /* Row 5: mini P-h curve indicator (bars) */
    draw_text(0, 54, "Dent Scope v1.0");

    oled_flush();
}

void oled_draw_results(ds_status_t *st)
{
    memset(framebuffer, 0, sizeof(framebuffer));
    char buf[24];

    draw_text(0, 0, "RESULTS");

    float_to_str(st->hardness_HV, 1, buf);
    draw_text(0, 9, "HV:");
    draw_text(18, 9, buf);

    float_to_str(st->modulus_E_GPa, 1, buf);
    draw_text(0, 18, "E:");
    draw_text(12, 18, buf);
    draw_text(42, 18, "GPa");

    float_to_str(st->elastic_ratio, 2, buf);
    draw_text(0, 27, "eta:");
    draw_text(24, 27, buf);

    float_to_str(st->peak_force_mN / 1000.0f, 2, buf);
    draw_text(0, 36, "Pmax:");
    draw_text(30, 36, buf);
    draw_text(54, 36, "N");

    if (st->matched_material >= 0) {
        const char *name = database_name(st->matched_material);
        draw_text(0, 54, name);
    } else {
        draw_text(0, 54, "(no match)");
    }

    oled_flush();
}

void oled_draw_ph_curve(ds_status_t *st)
{
    /* simplified: just draw status, full curve plot is on phone app */
    oled_draw_status(st);
}