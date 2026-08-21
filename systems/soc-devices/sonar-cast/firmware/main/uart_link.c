/*
 * sonar-cast / firmware / uart_link.c
 * Binary UART framing between STM32G474 (DSP) and ESP32-C3 (radio/GPS).
 *
 * Protocol (little-endian, 1 Mbaud, 8N1):
 *
 *   STM32 → ESP32 (result frame):
 *     0xAA 0x55 | len(2) | type=0x01 | depth(4f) | depth_pres(4f)
 *     | bottom(1) | bottom_conf(4f) | fish_count(1)
 *     | fish[depth(4f),length(4f),ts(4f)] × fish_count
 *     | temp(4f) | sspeed(4f) | tilt(4f) | echogram[128] | crc16(2)
 *
 *   ESP32 → STM32 (GPS frame, async):
 *     0xAA 0x55 | len(2) | type=0x02 | lat(4f) | lon(4f) | hdop(4f)
 *     | fix(1) | unix_ts(4) | crc16(2)
 *
 *   ESP32 → STM32 (command):
 *     0xAA 0x55 | len(2) | type=0x03 | cmd(1) | arg(4) | crc16(2)
 *      cmd: 0=IDLE 1=ACTIVE 2=DRIFT 3=SLEEP 4=SET_RATE(arg=Hz)
 */
#include "main.h"

#define SYNC0 0xAA
#define SYNC1 0x55

static uint8_t rxbuf[64];
static uint8_t rxpos = 0;

/* GPS data received from ESP32 (updated by uart_link_poll). */
static struct {
    float lat, lon, hdop;
    bool  fix;
    uint32_t ts;
} gps_rx = { 0, 0, 0, false, 0 };

/* CRC16-CCITT (0x1021). */
static uint16_t crc16(const uint8_t *p, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)p[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : (crc << 1);
    }
    return crc;
}

void uart_link_init(void)
{
    /* USART2 @ 1 Mbaud, 8N1, DMA TX/RX.  Placeholder. */
    rxpos = 0;
}

/* Send a result frame to ESP32. */
void uart_link_send_result(const sonar_result_t *r)
{
    /* Build frame in a static buffer (single-threaded pinger). */
    static uint8_t tx[4 + 1 + 4 + 4 + 1 + 4 + 1 + MAX_FISH_PER_PING * 12
                      + 4 + 4 + 4 + ECHO_BIN_COUNT + 2];
    uint16_t p = 0;
    tx[p++] = SYNC0; tx[p++] = SYNC1;
    uint16_t len_pos = p; p += 2;          /* fill length later */
    tx[p++] = 0x01;                        /* type = result */
    memcpy(&tx[p], &r->depth_m, 4);      p += 4;
    memcpy(&tx[p], &r->depth_pres_m, 4); p += 4;
    tx[p++] = r->bottom_type;
    memcpy(&tx[p], &r->bottom_conf, 4); p += 4;
    tx[p++] = r->fish_count;
    for (uint8_t i = 0; i < r->fish_count; i++) {
        memcpy(&tx[p], &r->fish_depths[i], 4);  p += 4;
        memcpy(&tx[p], &r->fish_lengths[i], 4); p += 4;
        memcpy(&tx[p], &r->fish_ts[i], 4);      p += 4;
    }
    memcpy(&tx[p], &r->temp_c, 4);       p += 4;
    memcpy(&tx[p], &r->sound_speed, 4);  p += 4;
    memcpy(&tx[p], &r->tilt_deg, 4);     p += 4;
    memcpy(&tx[p], r->echogram, ECHO_BIN_COUNT); p += ECHO_BIN_COUNT;

    uint16_t body_len = p - 4;   /* excluding sync + len */
    tx[len_pos]     = body_len & 0xFF;
    tx[len_pos + 1] = (body_len >> 8) & 0xFF;

    uint16_t crc = crc16(&tx[4], body_len);
    tx[p++] = crc & 0xFF;
    tx[p++] = (crc >> 8) & 0xFF;

    /* HAL_UART_Transmit_DMA(USART2, tx, p) — placeholder. */
    (void)p;
}

/* Non-blocking poll: parse any incoming GPS / command frames. */
void uart_link_poll(void)
{
    /* In real HW: read USART2 DMA ring, sync on 0xAA 0x55, parse len,
       verify CRC, dispatch by type.  Placeholder: expose gps_rx. */
    if (gps_rx.fix) {
        g_ctx.last.lat    = gps_rx.lat;
        g_ctx.last.lon    = gps_rx.lon;
        g_ctx.last.hdop   = gps_rx.hdop;
        g_ctx.last.unix_ts = gps_rx.ts;
        g_ctx.gps_fix = true;
    }
}

/* Called by ESP32 GPS parser (in the real build, this is populated via UART). */
void uart_link_set_gps(float lat, float lon, float hdop, bool fix, uint32_t ts)
{
    gps_rx.lat = lat; gps_rx.lon = lon; gps_rx.hdop = hdop;
    gps_rx.fix = fix; gps_rx.ts = ts;
}