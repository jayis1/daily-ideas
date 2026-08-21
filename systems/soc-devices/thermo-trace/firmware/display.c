/*
 * display.c — SH1106 OLED driver (128×64, I2C)
 *
 * Draws the DSC heat-flow curve, peak markers, status bar, and material
 * match results on a SH1106 OLED.
 */

#include "stm32g491_conf.h"
#include "display.h"
#include <string.h>

#define OLED_WIDTH  128
#define OLED_HEIGHT 64
#define OLED_PAGES  (OLED_HEIGHT / 8)

static uint8_t framebuffer[OLED_WIDTH * OLED_PAGES];

#define OLED_ADDR 0x3C

/* ---- I2C helpers ---- */
static void i2c_wait_tx_empty(void) {
    for (volatile int i = 0; i < 100000; i++) {
        if (I2C1_ISR & (1U << 0)) break;  /* TXE */
    }
}

static void i2c_write_byte(uint8_t byte) {
    I2C1_TXDR = byte;
    while (!(I2C1_ISR & (1U << 0))) ;  /* wait TXE */
}

static void i2c_start_write(uint8_t addr) {
    I2C1_CR2 = (addr << 1) | (1U << 13);  /* start + write */
    i2c_wait_tx_empty();
}

static void i2c_stop(void) {
    I2C1_CR2 |= (1U << 14);  /* STOP */
    for (volatile int i = 0; i < 1000; i++) ;
}

static void oled_command(uint8_t cmd) {
    i2c_start_write(OLED_ADDR);
    i2c_write_byte(0x00);  /* Co=0, D/C=0: command */
    i2c_write_byte(cmd);
    i2c_stop();
}

static void oled_data(uint8_t data) {
    i2c_start_write(OLED_ADDR);
    i2c_write_byte(0x40);  /* Co=0, D/C=1: data */
    i2c_write_byte(data);
    i2c_stop();
}

void display_init(void) {
    /* Enable I2C1 clock */
    RCC_APB1ENR1 |= (1U << 21);  /* I2C1EN */

    /* PB6 SCL, PB7 SDA as AF4 (I2C1) */
    GPIO_MODER(GPIOB_BASE) &= ~((3U << (6*2)) | (3U << (7*2)));
    GPIO_MODER(GPIOB_BASE) |=  (2U << (6*2)) | (2U << (7*2));
    GPIO_AFRL(GPIOB_BASE) = (GPIO_AFRL(GPIOB_BASE) & ~((0xF << (6*4)) | (0xF << (7*4))))
                           | (4U << (6*4)) | (4U << (7*4));
    GPIO_OTYPER(GPIOB_BASE) |= (1U << 6) | (1U << 7);  /* open-drain */
    GPIO_PUPDR(GPIOB_BASE) |= (1U << (6*2)) | (1U << (7*2));  /* pull-up */

    /* PB0 DC, PB1 RST as output */
    GPIO_MODER(GPIOB_BASE) |= (1U << (0*2)) | (1U << (1*2));

    /* I2C1 timing for 400 kHz at 170 MHz: PRESC=6, SCLL=0x13, SCLH=0x0F */
    I2C1_CR1 = 0;
    I2C1_TIMINGR = (6U << 28) | 0x13U << 20 | 0x0FU;
    I2C1_CR1 = (1U << 0);  /* PE: enable */

    /* Reset OLED */
    GPIO_SET(OLED_RST_PORT, OLED_RST_PIN);
    for (volatile int i = 0; i < 100000; i++) ;
    GPIO_CLR(OLED_RST_PORT, OLED_RST_PIN);
    for (volatile int i = 0; i < 100000; i++) ;
    GPIO_SET(OLED_RST_PORT, OLED_RST_PIN);

    /* SH1106 init sequence */
    oled_command(0xAE);  /* display off */
    oled_command(0xD5); oled_command(0x50);  /* osc freq */
    oled_command(0xA8); oled_command(0x3F);  /* multiplex 1/64 */
    oled_command(0xD3); oled_command(0x00);  /* display offset */
    oled_command(0x40);  /* start line 0 */
    oled_command(0x8D); oled_command(0x14);  /* charge pump on */
    oled_command(0x20); oled_command(0x00);  /* horizontal addressing */
    oled_command(0xA1);  /* segment remap */
    oled_command(0xC8);  /* COM scan direction */
    oled_command(0xDA); oled_command(0x12);  /* COM pins */
    oled_command(0x81); oled_command(0xCF);  /* contrast */
    oled_command(0xD9); oled_command(0xF1);  /* pre-charge period */
    oled_command(0xDB); oled_command(0x40);  /* VCOMH deselect */
    oled_command(0xA4);  /* display resume RAM */
    oled_command(0xA6);  /* normal display */
    oled_command(0xAF);  /* display on */

    display_clear();
    display_update();
}

void display_clear(void) {
    memset(framebuffer, 0, sizeof(framebuffer));
}

void display_set_pixel(int16_t x, int16_t y, uint8_t val) {
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    if (val)
        framebuffer[(y/8)*OLED_WIDTH + x] |=  (1U << (y & 7));
    else
        framebuffer[(y/8)*OLED_WIDTH + x] &= ~(1U << (y & 7));
}

void display_draw_hline(int16_t x, int16_t y, int16_t w) {
    for (int16_t i = 0; i < w; i++) display_set_pixel(x + i, y, 1);
}

void display_draw_vline(int16_t x, int16_t y, int16_t h) {
    for (int16_t i = 0; i < h; i++) display_set_pixel(x, y + i, 1);
}

/* Tiny 5×7 font (simplified — only digits, letters, symbols) */
static const uint8_t font5x7[96][5] = {
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0},
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0},
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    {0x00,0x07,0x00,0x07,0x00}, /* " */
    {0x14,0x7F,0x14,0x7F,0x14}, /* # */
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, /* % through + (skip) */
    {0x00,0x3E,0x3E,0x00,0x00}, /* ( simplified */
    {0x00,0x7E,0x7E,0x00,0x00}, /* ) */
    {0}, {0}, /* * + */
    {0}, {0x7F,0x7F,0x7F,0x7F}, /* , - */
    {0x00,0x00,0x00,0x00,0x00}, /* . */
    {0}, {0}, {0}, {0}, /* / */
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
    {0}, {0}, {0}, {0}, {0}, {0}, /* : ; < = > ? (simplified) */
    {0}, /* @ */
    {0x7E,0x11,0x11,0x11,0x7E}, /* A */
    {0x7F,0x49,0x49,0x49,0x36}, /* B */
    {0x3E,0x41,0x41,0x41,0x22}, /* C */
    {0x7F,0x41,0x41,0x22,0x1C}, /* D */
    {0x7F,0x49,0x49,0x49,0x41}, /* E */
    {0x7F,0x09,0x09,0x09,0x01}, /* F */
    {0x3E,0x41,0x49,0x49,0x4A}, /* G */
    {0x7F,0x08,0x08,0x08,0x7F}, /* H */
    {0x00,0x41,0x7F,0x41,0x00}, /* I */
    {0x20,0x40,0x41,0x3F,0x01}, /* J */
    {0x7F,0x08,0x14,0x22,0x41}, /* K */
    {0x7F,0x40,0x40,0x40,0x40}, /* L */
    {0x7F,0x02,0x0C,0x02,0x7F}, /* M */
    {0x7F,0x04,0x08,0x10,0x7F}, /* N */
    {0x3E,0x41,0x41,0x41,0x3E}, /* O */
    {0x7F,0x09,0x09,0x09,0x06}, /* P */
    {0}, {0}, {0}, /* Q R S (skip) */
    {0x41,0x49,0x49,0x49,0x36}, /* T */
    {0x1F,0x20,0x20,0x20,0x1F}, /* U */
    {0x07,0x18,0x60,0x18,0x07}, /* V */
    {0x63,0x14,0x08,0x14,0x63}, /* W */
    {0x41,0x22,0x1C,0x22,0x41}, /* X */
    {0x07,0x08,0x70,0x08,0x07}, /* Y */
    {0x61,0x51,0x49,0x45,0x43}, /* Z */
    {0}, {0}, {0}, {0}, {0}, /* [ \ ] ^ _ (skip) */
    {0x7F,0x08,0x14,0x22,0x41}, /* a (lower simplified) */
    {0x7F,0x40,0x40,0x40,0x40}, /* b */
    {0}, {0}, {0}, {0}, {0}, /* c d e f (skip) */
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, /* g-p (skip) */
    {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, {0}, /* q-z (skip) */
    {0}, {0}, {0}, {0}, {0}, {0}, /* { | } ~ DEL (skip) */
};

void display_text(int16_t x, int16_t y, const char *str) {
    for (int i = 0; str[i]; i++) {
        char c = str[i];
        uint8_t idx = (uint8_t)c - 32;
        if (idx >= 96) idx = 0;
        for (int col = 0; col < 5; col++) {
            uint8_t bits = font5x7[idx][col];
            for (int row = 0; row < 7; row++) {
                if (bits & (1U << row))
                    display_set_pixel(x + i * 6 + col, y + row, 1);
            }
        }
    }
}

void display_update(void) {
    for (uint8_t page = 0; page < OLED_PAGES; page++) {
        oled_command(0xB0 + page);  /* page address */
        oled_command(0x02);          /* lower column = 2 (SH1106 offset) */
        oled_command(0x10);          /* upper column = 0 */
        i2c_start_write(OLED_ADDR);
        i2c_write_byte(0x40);
        for (int col = 0; col < OLED_WIDTH; col++) {
            i2c_write_byte(framebuffer[page * OLED_WIDTH + col]);
        }
        i2c_stop();
    }
}

void display_status(float temp, float setpoint, float heat_flow,
                     float ramp_rate, uint8_t battery) {
    char buf[24];
    display_clear();
    /* Top line: temperature */
    int t = (int)temp;
    int sp = (int)setpoint;
    /* Format: "T:123 SP:150" */
    buf[0]='T'; buf[1]=':'; buf[2]=(t/100)+'0'; buf[3]=((t/10)%10)+'0';
    buf[4]=(t%10)+'0'; buf[5]=' '; buf[6]='S'; buf[7]='P'; buf[8]=':';
    buf[9]=(sp/100)+'0'; buf[10]=((sp/10)%10)+'0'; buf[11]=(sp%10)+'0';
    buf[12]='\0';
    display_text(0, 0, buf);
    /* Middle: heat flow + ramp rate */
    int hf = (int)(heat_flow * 10);
    int rr = (int)(ramp_rate * 10);
    buf[0]='H'; buf[1]='F'; buf[2]=':'; buf[3]=((hf<0)?'-':' ');
    hf = (hf<0)?-hf:hf; buf[4]=(hf/1000)+'0'; buf[5]=((hf/100)%10)+'0';
    buf[6]=((hf/10)%10)+'0'; buf[7]='.'; buf[8]=(hf%10)+'0';
    buf[9]=' '; buf[10]='R'; buf[11]=':';
    buf[12]=(rr/10)+'0'; buf[13]='.'; buf[14]=(rr%10)+'0'; buf[15]='\0';
    display_text(0, 10, buf);
    /* Bottom: battery + state */
    buf[0]='B'; buf[1]='A'; buf[2]='T'; buf[3]=':';
    buf[4]=(battery/10)+'0'; buf[5]=(battery%10)+'0'; buf[6]='%'; buf[7]='\0';
    display_text(0, 54, buf);
    display_update();
}

void display_dsc_curve(const float *temp_data, const float *hf_data,
                        uint32_t count, uint32_t max_points) {
    if (count < 2 || max_points < 2) return;
    /* Plot area: x=0..127, y=20..52 (32 pixels high) */
    float t_min = temp_data[0], t_max = temp_data[count-1];
    float hf_min = 1e30f, hf_max = -1e30f;
    for (uint32_t i = 0; i < count; i++) {
        if (hf_data[i] < hf_min) hf_min = hf_data[i];
        if (hf_data[i] > hf_max) hf_max = hf_data[i];
    }
    if (t_max - t_min < 1e-6f) t_max = t_min + 1.0f;
    if (hf_max - hf_min < 1e-6f) { hf_min -= 1.0f; hf_max += 1.0f; }

    /* Draw axis */
    display_draw_hline(0, 20, 128);
    display_draw_hline(0, 52, 128);
    display_draw_vline(0, 20, 32);

    /* Plot heat-flow curve */
    for (uint16_t x = 0; x < 128; x++) {
        uint32_t idx = (uint32_t)((float)x / 127.0f * (float)(count - 1));
        if (idx >= count) idx = count - 1;
        float frac_t = (temp_data[idx] - t_min) / (t_max - t_min);
        float frac_hf = (hf_data[idx] - hf_min) / (hf_max - hf_min);
        int16_t y = 52 - (int16_t)(frac_hf * 32.0f);
        if (y < 20) y = 20;
        if (y > 52) y = 52;
        display_set_pixel(x, y, 1);
    }
    display_update();
}

void display_peak_markers(int16_t *peak_indices, uint8_t num_peaks,
                           uint32_t max_points) {
    for (uint8_t i = 0; i < num_peaks && i < 8; i++) {
        int16_t x = (int16_t)((float)peak_indices[i] / (float)max_points * 127.0f);
        if (x < 0) x = 0;
        if (x > 127) x = 127;
        display_draw_vline(x, 20, 32);
    }
    display_update();
}

void display_match(const char *name, float confidence) {
    char buf[24];
    buf[0]='M'; buf[1]='A'; buf[2]='T'; buf[3]='C'; buf[4]='H'; buf[5]=':';
    buf[6]='\0';
    display_clear();
    display_text(0, 0, buf);
    display_text(0, 12, name);
    /* Confidence bar */
    int conf_w = (int)(confidence * 100);
    display_text(0, 30, "CONF:");
    for (int i = 0; i < conf_w / 2 && i < 64; i++)
        display_draw_hline(36 + i, 32, 1);
    display_update();
}

void display_idle(void) {
    display_clear();
    display_text(8, 0, "THERMO TRACE");
    display_text(8, 14, "POCKET DSC");
    display_text(0, 30, "READY");
    display_text(0, 48, "Press A to start");
    display_update();
}

void display_message(const char *line1, const char *line2, const char *line3) {
    display_clear();
    if (line1) display_text(0, 0, line1);
    if (line2) display_text(0, 12, line2);
    if (line3) display_text(0, 24, line3);
    display_update();
}

void display_set_progress(float frac) {
    /* Draw a progress bar at bottom of screen */
    int bar_w = (int)(frac * 120.0f);
    display_draw_hline(4, 60, 120);
    display_draw_hline(4, 62, 120);
    for (int i = 0; i < bar_w; i++) {
        display_set_pixel(4 + i, 61, 1);
    }
    display_update();
}