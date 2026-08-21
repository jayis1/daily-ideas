/*
 * wifi.h — Wi-Fi AP+STA, HTTP /sweep.json, TCP stream
 */
#ifndef FERRO_WEAVE_WIFI_H
#define FERRO_WEAVE_WIFI_H

#include <stdint.h>

void wifi_init(void);

/* Serve the last sweep as JSON on GET /sweep.json. */
void wifi_set_last_sweep(const uint8_t *json, int len);

/* Start a raw TCP stream on port 7788 that pushes sweep frames live. */
void wifi_start_stream(void);

#endif /* FERRO_WEAVE_WIFI_H */