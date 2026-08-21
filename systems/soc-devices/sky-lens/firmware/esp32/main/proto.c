/*
 * proto.c — event frame protocol (shared with the companion app)
 *
 * Binary event frame:
 *   [0-1]  magic 0x534C ('SL')
 *   [2-5]  seq (uint32 LE)
 *   [6-13] ts_us (uint64 LE)
 *   [14-15] h0_mv (int16 LE)
 *   [16-17] h1_mv (int16 LE)
 *   [18-21] dt_ps (int32 LE)
 *   [22-25] zenith_deg (float LE)
 *   [26-29] az_deg (float LE)
 *   [30-45] quaternion (4× float LE)
 *   [46-49] p_hpa (float LE)
 *   [50-53] t_c (float LE)
 *   [54]    flags
 *   [55]    checksum (XOR of bytes 0..54)
 *
 * Total: 56 bytes.
 */
#include "proto.h"
#include "sky_lens.h"
#include <string.h>

#define FRAME_LEN 56

void proto_pack_event(const event_t *ev, uint8_t *buf, int *len)
{
    uint8_t *p = buf;
    p[0] = 0x53; p[1] = 0x4C;   /* 'SL' */
    /* seq */
    uint32_t seq = ev->seq;
    memcpy(p+2, &seq, 4);
    /* ts_us */
    uint64_t ts = ev->ts_us;
    memcpy(p+6, &ts, 8);
    /* h0, h1 */
    int16_t h0 = ev->h0_mv, h1 = ev->h1_mv;
    memcpy(p+14, &h0, 2);
    memcpy(p+16, &h1, 2);
    /* dt_ps */
    int32_t dt = ev->dt_ps;
    memcpy(p+18, &dt, 4);
    /* zenith, az */
    float zen = ev->zenith_deg, az = ev->az_deg;
    memcpy(p+22, &zen, 4);
    memcpy(p+26, &az, 4);
    /* quaternion */
    float qw = ev->q_w, qx = ev->q_x, qy = ev->q_y, qz = ev->q_z;
    memcpy(p+30, &qw, 4);
    memcpy(p+34, &qx, 4);
    memcpy(p+38, &qy, 4);
    memcpy(p+42, &qz, 4);
    /* P, T */
    float pv = ev->p_hpa, tv = ev->t_c;
    memcpy(p+46, &pv, 4);
    memcpy(p+50, &tv, 4);
    /* flags */
    p[54] = ev->flags;
    /* checksum */
    uint8_t cks = 0;
    for (int i = 0; i < 55; i++) cks ^= p[i];
    p[55] = cks;

    *len = FRAME_LEN;
}

bool proto_unpack_event(const uint8_t *buf, int len, event_t *ev)
{
    if (len < FRAME_LEN) return false;
    if (buf[0] != 0x53 || buf[1] != 0x4C) return false;
    /* Verify checksum */
    uint8_t cks = 0;
    for (int i = 0; i < 55; i++) cks ^= buf[i];
    if (cks != buf[55]) return false;

    memset(ev, 0, sizeof(*ev));
    memcpy(&ev->seq,       buf+2,  4);
    memcpy(&ev->ts_us,    buf+6,  8);
    memcpy(&ev->h0_mv,    buf+14, 2);
    memcpy(&ev->h1_mv,    buf+16, 2);
    memcpy(&ev->dt_ps,    buf+18, 4);
    memcpy(&ev->zenith_deg, buf+22, 4);
    memcpy(&ev->az_deg,   buf+26, 4);
    memcpy(&ev->q_w,      buf+30, 4);
    memcpy(&ev->q_x,      buf+34, 4);
    memcpy(&ev->q_y,      buf+38, 4);
    memcpy(&ev->q_z,      buf+42, 4);
    memcpy(&ev->p_hpa,    buf+46, 4);
    memcpy(&ev->t_c,      buf+50, 4);
    ev->flags = buf[54];
    return true;
}