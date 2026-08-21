/*
 * proto.h — frame protocol shared between stm32/esp_link.c and esp32/proto.c
 */
#ifndef FERRO_WEAVE_PROTO_H
#define FERRO_WEAVE_PROTO_H

#include <stdint.h>
#include <stddef.h>

#define ESP_FRAME_SWEEP_RESULT 0x01
#define ESP_FRAME_STATUS       0x02
#define ESP_FRAME_CMD          0x03
#define ESP_FRAME_ACK          0x04

#define PROTO_SYNC  0xA5
#define PROTO_TAIL  0x5A

/* On-wire frame: [SYNC][type][len_hi][len_lo][payload][crc8][TAIL] */
typedef struct {
    uint8_t  type;
    uint16_t len;
    uint8_t  payload[8192];
} proto_frame_t;

/* Decode one frame from a byte stream. Returns 1 on complete frame,
 * 0 if more bytes needed, -1 on error. Consumed bytes are removed. */
int proto_decode(const uint8_t *in, int in_len, proto_frame_t *out,
                 int *consumed);

uint8_t proto_crc8(const uint8_t *p, int n);

#endif /* FERRO_WEAVE_PROTO_H */