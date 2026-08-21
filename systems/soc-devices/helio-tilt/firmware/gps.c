/*
 * gps.c — NEO-M9N GPS NMEA parsing
 *
 * UART2 at 38400 baud. Parses GGA, RMC, and ZDA sentences for
 * position, time, and fix status. PPS on PC4 for time sync.
 *
 * NMEA 4.1 sentences:
 *   $GPGGA: fix data (lat, lon, elevation, satellites)
 *   $GPRMC: minimum nav data (time, date, status, lat, lon)
 *   $GPZDA: UTC time + date
 */

#include "gps.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static gps_data_t gps_data;
static volatile uint32_t pps_ms = 0;
static volatile bool pps_received = false;

/* ---- UART2 RX ring buffer ---- */
#define GPS_BUF_SIZE 512
static char    rx_buf[GPS_BUF_SIZE];
static volatile uint16_t rx_head = 0;
static volatile uint16_t rx_tail = 0;
static char    line_buf[GPS_NMEA_BUF_SIZE];
static uint16_t line_len = 0;

/* ---- NMEA field parser ---- */
static int nmea_field_count(const char *s)
{
    int count = 1;
    for (const char *p = s; *p; p++)
        if (*p == ',') count++;
    return count;
}

static const char *nmea_field(const char *s, int field)
{
    int idx = 0;
    for (const char *p = s; *p && idx < field; p++) {
        if (*p == ',') idx++;
        if (idx == field) return p + 1;
    }
    return s + strlen(s);
}

static double nmea_parse_lat(const char *val, char hemi)
{
    if (!*val) return 0.0;
    double raw = atof(val);
    double deg = (int)(raw / 100.0);
    double min = raw - deg * 100.0;
    double lat = deg + min / 60.0;
    if (hemi == 'S') lat = -lat;
    return lat;
}

static double nmea_parse_lon(const char *val, char hemi)
{
    if (!*val) return 0.0;
    double raw = atof(val);
    double deg = (int)(raw / 100.0);
    double min = raw - deg * 100.0;
    double lon = deg + min / 60.0;
    if (hemi == 'W') lon = -lon;
    return lon;
}

/* ---- Parse $GPGGA ---- */
static void parse_gga(const char *s)
{
    /* $GPGGA,hhmmss.sss,llll.llll,N,yyyyy.yyyy,E,f,nn,h.h,m.m,M,... */
    const char *time_f  = nmea_field(s, 1);
    const char *lat_f   = nmea_field(s, 2);
    const char *lat_h   = nmea_field(s, 3);
    const char *lon_f   = nmea_field(s, 4);
    const char *lon_h   = nmea_field(s, 5);
    const char *fix_f   = nmea_field(s, 6);
    const char *sats_f  = nmea_field(s, 7);
    const char *ele_f   = nmea_field(s, 9);

    if (*fix_f >= '1') {
        gps_data.fix_valid = true;
        gps_data.latitude = nmea_parse_lat(lat_f, *lat_h);
        gps_data.longitude = nmea_parse_lon(lon_f, *lon_h);
        gps_data.elevation_m = atof(ele_f);
        gps_data.satellites = atoi(sats_f);

        /* Time from GGA */
        if (*time_f) {
            double t = atof(time_f);
            gps_data.hour = (int)(t / 10000.0);
            gps_data.min  = (int)((t / 100.0)) % 100;
            gps_data.sec  = (int)t % 100;
            gps_data.time_valid = true;
        }
    } else {
        gps_data.fix_valid = false;
    }
}

/* ---- Parse $GPRMC ---- */
static void parse_rmc(const char *s)
{
    /* $GPRMC,hhmmss.sss,A,llll.llll,N,yyyyy.yyyy,E,spd,course,ddmmyy,... */
    const char *status = nmea_field(s, 2);
    const char *date_f = nmea_field(s, 9);

    if (*status == 'A') {
        gps_data.fix_valid = true;
        if (*date_f) {
            int dmy = atoi(date_f);
            gps_data.day   = dmy / 10000;
            gps_data.month = (dmy / 100) % 100;
            gps_data.year  = 2000 + (dmy % 100);
        }
    } else {
        gps_data.fix_valid = false;
    }
}

/* ---- Parse $GPZDA ---- */
static void parse_zda(const char *s)
{
    /* $GPZDA,hhmmss.sss,dd,mm,yyyy,zz,zz */
    const char *time_f = nmea_field(s, 1);
    const char *day_f  = nmea_field(s, 2);
    const char *mon_f  = nmea_field(s, 3);
    const char *yr_f   = nmea_field(s, 4);

    if (*time_f) {
        double t = atof(time_f);
        gps_data.hour = (int)(t / 10000.0);
        gps_data.min  = (int)((t / 100.0)) % 100;
        gps_data.sec  = (int)t % 100;
        gps_data.time_valid = true;
    }
    if (*day_f && *mon_f && *yr_f) {
        gps_data.day   = atoi(day_f);
        gps_data.month = atoi(mon_f);
        gps_data.year  = atoi(yr_f);
    }
}

/* ---- Public API ---- */

void gps_parse_nmea(const char *sentence)
{
    if (!sentence || sentence[0] != '$') return;

    if (strncmp(sentence, "$GPGGA", 6) == 0 ||
        strncmp(sentence, "$GNGGA", 6) == 0)
        parse_gga(sentence);
    else if (strncmp(sentence, "$GPRMC", 6) == 0 ||
             strncmp(sentence, "$GNRMC", 6) == 0)
        parse_rmc(sentence);
    else if (strncmp(sentence, "$GPZDA", 6) == 0 ||
             strncmp(sentence, "$GNZDA", 6) == 0)
        parse_zda(sentence);
}

void gps_init(void)
{
    memset(&gps_data, 0, sizeof(gps_data));

    /* Enable GPS power (PC11 high) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (11u * 2u))) | (1u << (11u * 2u));
    GPIOC->ODR |= (1u << 11);    /* GPS on */

    /* UART2 on PC2 (TX) / PC3 (RX), AF7 */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (2u * 2u))) | (2u << (2u * 2u));
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (3u * 2u))) | (2u << (3u * 2u));
    GPIOC->AFR[0] = (GPIOC->AFR[0] & ~(0xFu << 8))  | (7u << 8);   /* PC2 AF7 */
    GPIOC->AFR[0] = (GPIOC->AFR[0] & ~(0xFu << 12)) | (7u << 12);  /* PC3 AF7 */

    RCC->APB1ENR1 |= RCC_APB1ENR1_USART2EN;
    USART2->BRR = (SYSCLK_FREQ / 2) / GPS_BAUD;   /* APB1 = SYSCLK/2 */
    USART2->CR1 = USART_CR1_RE | USART_CR1_RXNEIE | USART_CR1_UE;

    /* PPS input on PC4 (exti) */
    GPIOC->MODER &= ~(3u << (4u * 2u));   /* Input */
    GPIOC->PUPDR |= (2u << (4u * 2u));    /* Pull-down */

    /* Enable USART2 IRQ */
    NVIC_EnableIRQ(USART2_IRQn);
}

void gps_get_data(gps_data_t *data)
{
    __disable_irq();
    *data = gps_data;
    __enable_irq();
}

bool gps_has_fix(void)
{
    return gps_data.fix_valid;
}

int gps_wait_fix(uint32_t timeout_s)
{
    uint32_t start = 0;  /* Would use SysTick millis */
    while (!gps_has_fix()) {
        if (start > timeout_s * 1000) return -1;
        /* spin; in real firmware, yield to RTOS or WFI */
    }
    return 0;
}

uint32_t gps_get_pps_ms(void)
{
    return pps_ms;
}

/* ---- UART2 ISR ---- */
void USART2_IRQHandler(void)
{
    if (USART2->ISR & USART_ISR_RXNE) {
        char c = (char)(USART2->RDR & 0xFF);
        if (c == '\n') {
            line_buf[line_len] = 0;
            gps_parse_nmea(line_buf);
            line_len = 0;
        } else if (c != '\r' && line_len < GPS_NMEA_BUF_SIZE - 1) {
            line_buf[line_len++] = c;
        }
    }
}

/* ---- PPS ISR (EXTI4) ---- */
void EXTI4_IRQHandler(void)
{
    if (EXTI->PR1 & (1u << 4)) {
        EXTI->PR1 = (1u << 4);
        pps_received = true;
        /* pps_ms = millis(); — would update with SysTick counter */
    }
}