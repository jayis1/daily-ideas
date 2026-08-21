/*
 * wifi.c — Wi-Fi AP+STA, HTTP /sweep.json, TCP stream (ESP-IDF)
 *
 * In AP mode the device exposes a captive portal at 192.168.4.1 for
 * entering the specimen geometry (N1, N2, l_e, A2, A_core, rho) and
 * sweep parameters. In STA mode it joins a lab Wi-Fi and serves the
 * last sweep as JSON at http://ferro-weave.local/sweep.json plus a raw
 * TCP frame stream on port 7788 for live plotting.
 */
#include "wifi.h"
#include <string.h>

static uint8_t g_last_json[4096];
static int     g_last_json_len = 0;

void wifi_init(void)
{
    /* ESP-IDF: esp_netif_init, esp_event_loop, esp_wifi_init,
     *          wifi_init_config_t, AP+STA mode, start. */
}

void wifi_set_last_sweep(const uint8_t *json, int len)
{
    if (len > (int)sizeof(g_last_json)) len = sizeof(g_last_json);
    memcpy(g_last_json, json, len);
    g_last_json_len = len;
}

void wifi_start_stream(void)
{
    /* Listen on port 7788, accept one client, push sweep frames as they
     * arrive from the STM32. */
}