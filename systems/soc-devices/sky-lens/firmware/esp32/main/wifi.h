/* wifi.h — AP+STA, captive portal, HTTP /events /skymap /lifetime */
#ifndef WIFI_H
#define WIFI_H
#include "sky_lens.h"

void wifi_init(void);
void wifi_send_event(const event_t *ev);
bool wifi_connected(void);

#endif