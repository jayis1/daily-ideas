/*
 * wifi.h — Wi-Fi AP+STA, HTTP /events.json, /stream SSE, TCP socket
 */
#ifndef BOLT_COMPASS_WIFI_H
#define BOLT_COMPASS_WIFI_H

#include "types.h"

void wifi_init(void);

/* Push a sferic event to all connected SSE/TCP clients. */
void wifi_stream_sferic(const stroke_t *st);

#endif /* BOLT_COMPASS_WIFI_H */