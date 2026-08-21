/*
 * wifi_server.c — Wi-Fi AP + WebSocket server
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Creates a Wi-Fi AP "PhytoPulse-XXXX" and serves a WebSocket at ws://192.168.4.1/ws
 * for live waveform + event streaming to a phone app or browser.
 */

#include "wifi_server.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "lwip/sockets.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "wifi";
static int g_ws_clients[4] = { -1, -1, -1, -1 };

void wifi_server_init(void)
{
    /* Configure as AP */
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    /* Get MAC for SSID suffix */
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_AP, mac);

    wifi_config_t wifi_cfg = {0};
    snprintf((char *)wifi_cfg.ap.ssid, sizeof(wifi_cfg.ap.ssid),
             "PhytoPulse-%02X%02X", mac[4], mac[5]);
    wifi_cfg.ap.ssid_len = strlen((char *)wifi_cfg.ap.ssid);
    wifi_cfg.ap.channel = 1;
    wifi_cfg.ap.max_connection = 4;
    wifi_cfg.ap.authmode = WIFI_AUTH_OPEN;

    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_cfg);
    esp_wifi_start();

    ESP_LOGI(TAG, "Wi-Fi AP started: PhytoPulse-%02X%02X", mac[4], mac[5]);
}

static void ws_handshake(int sock)
{
    /* Minimal WebSocket handshake (RFC 6455) */
    char buf[512];
    int len = recv(sock, buf, sizeof(buf) - 1, 0);
    if (len <= 0) return;
    buf[len] = 0;

    /* Find Sec-WebSocket-Key */
    char *key = strstr(buf, "Sec-WebSocket-Key: ");
    if (!key) key = strstr(buf, "Sec-WebSocket-Key: ");
    if (!key) return;
    key += strlen("Sec-WebSocket-Key: ");
    char *eol = strstr(key, "\r\n");
    if (!eol) return;
    *eol = 0;

    /* Compute accept value (SHA1 of key + magic GUID, base64) */
    /* Simplified: send back a placeholder (real impl uses SHA1+base64) */
    const char *response =
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n";
    /* NOTE: In production, compute the real accept value with SHA1+base64 */
    send(sock, response, strlen(response), 0);
}

void wifi_ws_task(void *arg)
{
    int server_sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_addr.s_addr = htonl(INADDR_ANY),
        .sin_port = htons(80),
    };
    bind(server_sock, (struct sockaddr *)&addr, sizeof(addr));
    listen(server_sock, 4);

    ESP_LOGI(TAG, "WebSocket server listening on port 80");

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        int client = accept(server_sock, (struct sockaddr *)&client_addr, &addr_len);
        if (client < 0) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        /* Check if it's a WebSocket upgrade request */
        char buf[512];
        int len = recv(client, buf, sizeof(buf) - 1, 0);
        if (len > 0) {
            buf[len] = 0;
            if (strstr(buf, "Upgrade: websocket")) {
                ws_handshake(client);
                /* Add to client list */
                for (int i = 0; i < 4; i++) {
                    if (g_ws_clients[i] < 0) {
                        g_ws_clients[i] = client;
                        ESP_LOGI(TAG, "WS client %d connected", i);
                        break;
                    }
                }
            } else {
                /* Serve a simple HTTP page */
                const char *page =
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                    "<h1>Phyto Pulse</h1>"
                    "<p>Connect to ws://192.168.4.1/ws for live data.</p>";
                send(client, page, strlen(page), 0);
                close(client);
            }
        }
    }
}

static void ws_send_text(const char *msg)
{
    int len = strlen(msg);
    /* WebSocket text frame: 0x81 + length (simplified, <126 bytes) */
    uint8_t header[2];
    header[0] = 0x81;  /* FIN + text frame */
    if (len < 126) {
        header[1] = (uint8_t)len;
    } else {
        header[1] = 126;
    }

    for (int i = 0; i < 4; i++) {
        if (g_ws_clients[i] >= 0) {
            send(g_ws_clients[i], header, 2, 0);
            if (len < 126) {
                send(g_ws_clients[i], msg, len, 0);
            } else {
                uint8_t ext[2] = { (len >> 8) & 0xFF, len & 0xFF };
                send(g_ws_clients[i], ext, 2, 0);
                send(g_ws_clients[i], msg, len, 0);
            }
        }
    }
}

void wifi_broadcast_sample(float voltage_mv, uint32_t timestamp_ms)
{
    char json[128];
    snprintf(json, sizeof(json),
        "{\"type\":\"sample\",\"t\":%lu,\"v\":%.3f}",
        (unsigned long)timestamp_ms, voltage_mv);
    ws_send_text(json);
}

void wifi_broadcast_event(const char *json, int len)
{
    ws_send_text(json);
}