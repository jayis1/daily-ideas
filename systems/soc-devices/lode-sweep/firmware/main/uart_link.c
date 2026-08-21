/*
 * lode-sweep / firmware / uart_link.c
 * Binary UART framing between STM32G474 (DSP) and ESP32-C3 (radio/GPS).
 *
 * Protocol (little-endian, 460800 baud, 8N1):
 *
 *   STM32 → ESP32 (result frame):
 *     0xAA 0x55 | len(2) | type=0x01 | class(1) | conf(4f) | depth(4f)
 *     | signal(4f) | tilt(4f) | decay[16](16f) | lat(4f) | lon(4f)
 *     | hdop(4f) | unix_ts(4) | crc16(2)
 *
 *   ESP32 → STM32 (GPS frame, async):
 *     0xAA 0x55 | len(2) | type=0x02 | lat(4f) | lon(4f) | hdop(4f)
 *     | fix(1) | unix_ts(4) | crc16(2)
 *
 *   ESP32 → STM32 (command):
 *     0xAA 0x55 | len(2) | type=0x03 | cmd(1) | arg(1) | crc16(2)
 *      cmd: 0=IDLE 1=ACTIVE 2=DRIFT 3=SLEEP 4=SET_SENS(arg) 5=SET_DISC(arg)
 */
#include "main.h"

#define SYNC0 0xAA
#define SYNC1 0x55

static uint8_t rxbuf[64];
static uint8_t rxpos = 0;

/* GPS data received from ESP32 */
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
    /* USART2 @ 460800 baud, 8N1, DMA TX/RX.  Placeholder. */
    rxpos = 0;
}

/* Send a result frame to ESP32. */
void uart_link_send_result(const sweep_result_t *r)
{
    static uint8_t tx[4 + 1 + 1 + 4*4 + NUM_GATES*4 + 4*3 + 4 + 2];
    uint16_t p = 0;
    tx[p++] = SYNC0; tx[p++] = SYNC1;
    uint16_t len_pos = p; p += 2;
    tx[p++] = 0x01;                        /* type = result */
    tx[p++] = r->target_class;
    memcpy(&tx[p], &r->confidence, 4);      p += 4;
    memcpy(&tx[p], &r->depth_cm, 4);        p += 4;
    memcpy(&tx[p], &r->signal_strength, 4); p += 4;
    memcpy(&tx[p], &r->tilt_deg, 4);        p += 4;
    for (int i = 0; i < NUM_GATES; i++) {
        memcpy(&tx[p], &r->decay[i], 4);    p += 4;
    }
    memcpy(&tx[p], &r->lat, 4);     p += 4;
    memcpy(&tx[p], &r->lon, 4);     p += 4;
    memcpy(&tx[p], &r->hdop, 4);    p += 4;
    memcpy(&tx[p], &r->unix_ts, 4); p += 4;

    uint16_t body_len = p - 4;
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
    if (gps_rx.fix) {
        g_ctx.last.lat    = gps_rx.lat;
        g_ctx.last.lon    = gps_rx.lon;
        g_ctx.last.hdop   = gps_rx.hdop;
        g_ctx.last.unix_ts = gps_rx.ts;
        g_ctx.gps_fix = true;
    }
}

/* Called by ESP32 GPS parser (via UART in real build). */
void uart_link_set_gps(float lat, float lon, float hdop, bool fix, uint32_t ts)
{
    gps_rx.lat = lat; gps_rx.lon = lon; gps_rx.hdop = hdop;
    gps_rx.fix = fix; gps_rx.ts = ts;
}