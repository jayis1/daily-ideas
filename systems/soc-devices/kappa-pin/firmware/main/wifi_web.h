/*
 * kappa-pin / firmware / main / wifi_web.h
 * Wi-Fi softAP + HTTP server for web UI and CSV download
 *
 * MIT License.
 */
#ifndef WIFI_WEB_H
#define WIFI_WEB_H

#include <stdbool.h>
#include "measurement.h"

/* Wi-Fi AP credentials */
#define WIFI_AP_SSID     "KappaPin-XXXX"
#define WIFI_AP_PASS     ""    /* open AP for easy access */
#define WIFI_AP_CHANNEL  1
#define WIFI_AP_MAX_CONN 4

/* Initialize Wi-Fi AP + HTTP server */
void wifi_web_init(void);

/* Update the web UI with latest result (called after measurement) */
void wifi_web_update_result(const meas_result_t *r);

/* Push a live sample to connected web clients (via SSE) */
void wifi_web_push_sample(const meas_sample_t *s);

/* Check if any web client is connected */
bool wifi_web_has_clients(void);

/* Get AP IP address string */
const char *wifi_web_get_ip(void);

#endif /* WIFI_WEB_H */