/*
 * wifi_server.h — Wi-Fi AP + WebSocket server for Phyto Pulse
 */

#ifndef WIFI_SERVER_H
#define WIFI_SERVER_H

void wifi_server_init(void);
void wifi_ws_task(void *arg);
void wifi_broadcast_sample(float voltage_mv, uint32_t timestamp_ms);
void wifi_broadcast_event(const char *json, int len);

#endif /* WIFI_SERVER_H */