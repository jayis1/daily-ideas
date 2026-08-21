/*
 * esp_link.c — UART protocol to the ESP32-C3 co-processor
 *
 * A simple SLIP-like framing: each frame is
 *   [0xA5][type][len_hi][len_lo][payload...][crc8][0x5A]
 * Payload is binary for SWEEP_RESULT (geometry + result struct + H/B
 * arrays as int16 Q15) and ASCII for STATUS / CMD.
 */
#include "esp_link.h"
#include <string.h>
#include <stdio.h>

#define UART_BAUD 115200

static uint8_t crc8(const uint8_t *p, int n)
{
    uint8_t c = 0;
    for (int i = 0; i < n; i++) {
        c ^= p[i];
        for (int j = 0; j < 8; j++)
            c = (c & 0x80) ? (c << 1) ^ 0x07 : (c << 1);
    }
    return c;
}

void esp_link_init(void)
{
    /* UART1 at 115200 8N1, DMA TX, interrupt RX. */
}

static void uart_send(const uint8_t *p, int n)
{
    /* HAL_UART_Transmit_DMA in firmware; fwrite in sim. */
    (void)p; (void)n;
}

static void send_frame(uint8_t type, const uint8_t *payload, int len)
{
    uint8_t hdr[4] = { 0xA5, type, (uint8_t)(len >> 8), (uint8_t)(len & 0xFF) };
    uint8_t crc = crc8(payload, len);
    uint8_t tail[2] = { crc, 0x5A };
    uart_send(hdr, 4);
    uart_send(payload, len);
    uart_send(tail, 2);
}

int esp_link_send_sweep(const sweep_params_t *sp, const geom_t *g,
                        const float *H, const float *B, int n,
                        const bh_result_t *r)
{
    /* Pack into a compact binary payload:
     *   sweep_params_t (16 B) + geom_t (28 B) + bh_result_t (40 B)
     *   + n × (int16 H, int16 B)  */
    if (n > 4096) n = 4096;
    int plen = 16 + 28 + 40 + n * 4;
    uint8_t buf[16 + 28 + 40 + 4096 * 4];
    if (plen > (int)sizeof(buf)) return -1;
    int o = 0;
    memcpy(buf + o, sp, 16);  o += 16;
    memcpy(buf + o, g,  28);  o += 28;
    memcpy(buf + o, r,  40);  o += 40;
    for (int i = 0; i < n; i++) {
        int16_t h = (int16_t)(H[i] * 1e-2f);   /* scale to int16 */
        int16_t b = (int16_t)(B[i] * 1e4f);
        memcpy(buf + o, &h, 2); o += 2;
        memcpy(buf + o, &b, 2); o += 2;
    }
    send_frame(ESP_FRAME_SWEEP_RESULT, buf, plen);
    return 0;
}

int esp_link_send_status(const char *s)
{
    if (!s) return -1;
    send_frame(ESP_FRAME_STATUS, (const uint8_t *)s, (int)strlen(s));
    return 0;
}

int esp_link_poll_cmd(char *cmd, size_t maxlen)
{
    /* Firmware: check a ring buffer filled by the UART RX ISR. */
    (void)cmd; (void)maxlen;
    return 0;
}