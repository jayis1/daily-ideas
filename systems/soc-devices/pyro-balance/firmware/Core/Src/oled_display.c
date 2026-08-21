/*
 * pyro-balance / Core/Src/oled_display.c — SSD1306 128x64 SPI driver.
 */
#include "oled_display.h"
#include "tga.h"

extern SPI_HandleTypeDef hspi1;

static void spi_tx(const uint8_t* d, uint16_t n) {
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, (uint8_t*)d, n, 100);
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
}
static void cmd(uint8_t c){ HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET); spi_tx(&c,1); }
static void data(uint8_t d){ HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_SET); spi_tx(&d,1); }

static uint8_t fb[128*8]; /* 128×64 / 8 vertical */

void oled_init(void) {
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
    HAL_Delay(10);
    cmd(0xAE); /* display off */
    cmd(0xD5); cmd(0x80);
    cmd(0xA8); cmd(0x3F);
    cmd(0xD3); cmd(0x00);
    cmd(0x40);
    cmd(0x8D); cmd(0x14);
    cmd(0x20); cmd(0x00);
    cmd(0xA1); cmd(0xC8);
    cmd(0xDA); cmd(0x12);
    cmd(0xD9); cmd(0xF1);
    cmd(0xDB); cmd(0x40);
    cmd(0x81); cmd(0xCF);
    cmd(0xD6); cmd(0x00);
    cmd(0xA4); cmd(0xA6);
    cmd(0xAF);
}
void oled_clear(void) { memset(fb,0,sizeof(fb)); }
static void flush(void){
    for (uint8_t p=0;p<8;p++){ cmd(0xB0|p); cmd(0x00); cmd(0x10);
        HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_SET);
        HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
        HAL_SPI_Transmit(&hspi1,&fb[p*128],128,200);
        HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
    }
}
static void px(int x,int y,int on){ if(x<0||x>127||y<0||y>63)return; if(on) fb[(y>>3)*128+x]|=(1<<(y&7)); else fb[(y>>3)*128+x]&=~(1<<(y&7)); }

/* tiny 5×7 font */
static const uint8_t font[96][5]={
 {0,0,0,0,0},{0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},{0x7F,0x41,0x41,0x41,0x22},
 /* ... truncated; in production embed full font */
 {0,0,0,0,0},{0,0,0,0,0},{0,0,0,0,0},{0,0,0,0,0},{0,0,0,0,0},{0x7F,0x41,0x41,0x41,0x3E}, /* 'O' placeholder */
};
static void text_at(uint8_t col, uint8_t row, const char* s){
    for (; *s; s++, col+=6) {
        int idx = *s - 32;
        if (idx < 0 || idx >= 96) idx = 0;
        for (int i=0;i<5;i++){
            uint8_t b = font[idx][i];
            for (int j=0;j<7;j++) px(col+i,row+j,(b>>j)&1);
        }
    }
}
void oled_text(uint8_t line,const char* s){ oled_clear(); text_at(0,line*9,s); flush(); }
void oled_invert(bool on){ cmd(on?0xA7:0xA6); }

void oled_draw_tg(const tga_run_t* run, float cur_temp, float cur_mass_pct){
    oled_clear();
    /* top status line */
    char buf[24];
    snprintf(buf,sizeof(buf),"T:%5.1fC  M:%5.1f%%",cur_temp,cur_mass_pct);
    text_at(0,0,buf);
    /* TG curve: x=temp 0..600, y=mass% 0..110 → plot area y=10..63, x=0..127 */
    if (run && run->n > 1) {
        for (uint32_t i=0;i<run->n;i++){
            int x = (int)(run->temp_c[i] / 600.0f * 127.0f);
            int y = 63 - (int)(run->mass_pct[i] / 110.0f * 53.0f);
            if (x<0)x=0; if(x>127)x=127; if(y<10)y=10; if(y>63)y=63;
            px(x,y,1);
        }
    }
    /* border */
    for (int x=0;x<128;x++){px(x,9,1);px(x,63,1);}
    for (int y=9;y<64;y++){px(0,y,1);px(127,y,1);}
    flush();
}

void oled_status(const pb_status_t* s){
    oled_clear();
    char buf[24];
    snprintf(buf,sizeof(buf),"State: %d  T:%5.1f",(int)s->state,s->temp_c);
    text_at(0,0,buf);
    snprintf(buf,sizeof(buf),"Mass: %6.2fmg",s->mass_mg);
    text_at(0,18,buf);
    snprintf(buf,sizeof(buf),"Target:%5.1f Rate:%4d",s->target_c,s->heating_rate/10);
    text_at(0,36,buf);
    flush();
}