/**
 * wifi_server.h — Wi-Fi HTTP REST API server for Refracto Bead
 */
#ifndef WIFI_SERVER_H
#define WIFI_SERVER_H

#include "uart_protocol.h"

void wifi_server_init(void);
void wifi_server_notify_result(const ri_result_t *result);

#endif /* WIFI_SERVER_H */