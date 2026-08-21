/*
 * proto.c — frame protocol decoder (ESP32-C3 side)
 *
 * Mirrors the framing in stm32/esp_link.c:
 *   [0xA5][type][len_hi][len_lo][payload...][crc8][0x5A]
 */
#include "proto.h"
#include <string.h>

uint8_t proto_crc8(const uint8_t *p, int n)
{
    uint8_t c = 0;
    for (int i = 0; i < n; i++) {
        c ^= p[i];
        for (int j = 0; j < 8; j++)
            c = (c & 0x80) ? (c << 1) ^ 0x07 : (c << 1);
    }
    return c;
}

int proto_decode(const uint8_t *in, int in_len, proto_frame_t *out,
                 int *consumed)
{
    *consumed = 0;
    if (in_len < 6) return 0;   /* need at least header+crc+tail */

    /* Find sync byte. */
    int i = 0;
    while (i < in_len && in[i] != PROTO_SYNC) i++;
    if (i >= in_len) { *consumed = in_len; return 0; }
    if (in_len - i < 6) { *consumed = i; return 0; }

    int o = i;
    uint8_t type   = in[o + 1];
    uint16_t len   = ((uint16_t)in[o + 2] << 8) | in[o + 3];
    int total = 6 + len;
    if (in_len - o < total) { *consumed = o; return 0; }

    const uint8_t *payload = &in[o + 4];
    uint8_t crc = in[o + 4 + len];
    uint8_t tail = in[o + 5 + len];
    if (tail != PROTO_TAIL) { *consumed = o + 1; return -1; }
    if (proto_crc8(payload, len) != crc) { *consumed = o + 1; return -1; }

    if (len > sizeof(out->payload)) { *consumed = o + 1; return -1; }
    out->type = type;
    out->len  = len;
    memcpy(out->payload, payload, len);
    *consumed = o + total;
    return 1;
}