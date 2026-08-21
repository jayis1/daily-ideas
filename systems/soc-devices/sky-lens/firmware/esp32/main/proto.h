/* proto.h — event frame protocol shared with the companion app */
#ifndef PROTO_H
#define PROTO_H
#include "sky_lens.h"

#define PROTO_MAGIC 0x534C   /* 'SL' */

void proto_pack_event(const event_t *ev, uint8_t *buf, int *len);
bool proto_unpack_event(const uint8_t *buf, int len, event_t *ev);

#endif