/**
 * wifi_server.h — Wi-Fi HTTP REST API server
 */

#ifndef WIFI_SERVER_H
#define WIFI_SERVER_H

#include <stdint.h>
#include <stdbool.h>
#include "acoustic_params.h"

/**
 * Connect to Wi-Fi and start the HTTP API server.
 */
int wifi_server_start(const char *ssid, const char *password);

/**
 * Stop the Wi-Fi server and disconnect.
 */
void wifi_server_stop(void);

/**
 * Check if Wi-Fi server is active and connected.
 */
bool wifi_server_is_active(void);

/**
 * Post measurement results to the HTTP API endpoint.
 * Called after each measurement to make results available via REST.
 */
int wifi_server_post_results(uint32_t mode, const acoustic_results_t *results);

#endif /* WIFI_SERVER_H */