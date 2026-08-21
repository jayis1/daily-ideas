/*
 * dent-scope / firmware/esp32-c3/main/main.c
 * ESP32-C3 BLE GATT + Wi-Fi captive portal for Dent Scope uplink
 *
 * Receives P-h data points + results from STM32G474 over UART (115200)
 * and streams via BLE notifications + serves a web page on Wi-Fi AP.
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gatt/ble_svc_gatt.h"
#include "host/ble_uuid.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "lwip/inet.h"

static const char *TAG = "dent-scope-esp32";

#define UART_NUM       UART_NUM_1
#define UART_RX_PIN    18
#define UART_TX_PIN    19
#define UART_BAUD      115200
#define BUF_SIZE       1024

/* BLE UUIDs */
#define UUID_DENT_SCOPE_SERVICE  0x8801
#define UUID_DENT_SCOPE_DATA     0x8802
#define UUID_DENT_SCOPE_RESULT   0x8803
#define UUID_DENT_SCOPE_CMD      0x8804

static uint8_t ble_data_buf[24];
static uint16_t ble_data_conn_handle = BLE_HS_CONN_HANDLE_NONE;
static bool ble_notify_enabled = false;

/* Latest result */
static char latest_result[256];

/* ---- UART protocol parser ---- */
static void parse_frame(uint8_t *frame, int len)
{
    if (len < 6) return;
    if (frame[0] != 0xAA || frame[1] != 0x55) return;
    uint8_t type = frame[2];
    uint16_t plen = frame[3] | (frame[4] << 8);
    if (len < plen + 6) return;

    switch (type) {
    case 0x01: /* data point */
        if (plen == 12 && ble_notify_enabled) {
            ble_gattc_notify(ble_data_conn_handle,
                             ble_svc_gatt_handle(UUID_DENT_SCOPE_DATA),
                             frame + 5, 12);
        }
        break;
    case 0x02: /* result */
        if (plen == 21) {
            memcpy(ble_data_buf, frame + 5, 21);
            float HV, E, eta, Pmax;
            memcpy(&HV, &frame[5], 4);
            memcpy(&E, &frame[9], 4);
            memcpy(&eta, &frame[13], 4);
            memcpy(&Pmax, &frame[17], 4);
            int8_t mat = frame[20];
            snprintf(latest_result, sizeof(latest_result),
                     "{\"HV\":%.1f,\"E_GPa\":%.1f,\"eta\":%.2f,\"Pmax_mN\":%.0f,\"material\":%d}",
                     HV, E, eta, Pmax, mat);
            ESP_LOGI(TAG, "Result: %s", latest_result);
        }
        break;
    default:
        break;
    }
}

static void uart_task(void *arg)
{
    uint8_t *buf = malloc(BUF_SIZE);
    uint8_t frame[256];
    int fidx = 0;
    bool in_frame = false;
    int frame_len = 0;

    uart_config_t cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_param_config(UART_NUM, &cfg);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, -1, -1);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);

    while (1) {
        int len = uart_read_bytes(UART_NUM, buf, BUF_SIZE, pdMS_TO_TICKS(10));
        for (int i = 0; i < len; i++) {
            uint8_t b = buf[i];
            if (!in_frame) {
                if (fidx == 0 && b == 0xAA) { frame[fidx++] = b; }
                else if (fidx == 1 && b == 0x55) { frame[fidx++] = b; in_frame = true; }
                else fidx = 0;
            } else {
                if (fidx < sizeof(frame)) frame[fidx++] = b;
                if (fidx == 5) frame_len = frame[3] | (frame[4] << 8);
                if (fidx >= frame_len + 6) {
                    parse_frame(frame, fidx);
                    fidx = 0;
                    in_frame = false;
                }
            }
        }
    }
}

/* ---- BLE GATT callbacks ---- */
static int on_data_access(uint16_t conn_handle, uint16_t attr_handle,
                          struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        /* command from phone: forward to STM32 */
        uint8_t cmd[16];
        uint16_t n = OS_MBUF_PKTLEN(ctxt->om);
        os_mbuf_copydata(ctxt->om, 0, n, cmd);
        uart_write_bytes(UART_NUM, (char*)cmd, n);
        return 0;
    } else if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, latest_result, strlen(latest_result));
        return 0;
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static int on_data_subscribe(uint16_t conn_handle, uint16_t attr_handle,
                              struct ble_gap_event *event)
{
    if (event->type == BLE_GAP_EVENT_SUBSCRIBE) {
        ble_notify_enabled = event->subscribe.cur_notify;
        ble_data_conn_handle = conn_handle;
        ESP_LOGI(TAG, "BLE notify %s", ble_notify_enabled ? "ON" : "OFF");
    }
    return 0;
}

static const struct ble_gatt_svc_def gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(UUID_DENT_SCOPE_SERVICE),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = BLE_UUID16_DECLARE(UUID_DENT_SCOPE_DATA),
                .access_cb = on_data_access,
                .flags = BLE_GATT_CHR_F_NOTIFY,
                .val_handle = (uint16_t[]){0},
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_DENT_SCOPE_RESULT),
                .access_cb = on_data_access,
                .flags = BLE_GATT_CHR_F_READ,
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_DENT_SCOPE_CMD),
                .access_cb = on_data_access,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            { 0 }
        }
    },
    { 0 }
};

static void on_stack_reset(int reason)
{
    ESP_LOGI(TAG, "BLE stack reset: %d", reason);
}

static void on_sync(void)
{
    /* start advertising */
    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (uint8_t*)"DentScope";
    fields.name_len = strlen("DentScope");
    ble_gap_adv_set_fields(&fields);
    struct ble_gap_adv_params params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN
    };
    ble_gap_adv_start(BLE_ADDR_ANY, NULL, BLE_HS_FOREVER, &params,
                     (ble_gap_event_fn*)on_data_subscribe);
}

static void ble_host_task(void *param)
{
    nimble_port_run();
    vTaskDelete(NULL);
}

/* ---- Wi-Fi AP + simple HTTP server ---- */
static esp_err_t http_root_handler(httpd_req_t *req)
{
    const char *html = "<!DOCTYPE html><html><head><title>Dent Scope</title>"
        "<meta charset='utf-8'></head><body style='font-family:monospace'>"
        "<h1>Dent Scope</h1>"
        "<p>Latest result:</p><pre id='r'>Waiting...</pre>"
        "<script>"
        "var ws=new WebSocket('ws://192.168.4.1/ws');"
        "ws.onmessage=function(e){document.getElementById('r').innerText=e.data;};"
        "</script></body></html>";
    httpd_resp_send(req, html, strlen(html));
    return ESP_OK;
}

static httpd_handle_t start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_uri_t root = {.uri="/", .method=HTTP_GET, .handler=http_root_handler};
        httpd_register_uri_handler(server, &root);
    }
    return server;
}

static void wifi_init_ap(void)
{
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    wifi_config_t wifi_cfg = {0};
    strcpy((char*)wifi_cfg.ap.ssid, "DentScope");
    strcpy((char*)wifi_cfg.ap.password, "12345678");
    wifi_cfg.ap.ssid_len = strlen("DentScope");
    wifi_cfg.ap.max_connection = 4;
    wifi_cfg.ap.authmode = WIFI_AUTH_WPA2_PSK;
    esp_wifi_set_config(WIFI_IF_AP, &wifi_cfg);
    esp_wifi_start();
    ESP_LOGI(TAG, "Wi-Fi AP: DentScope / 12345678");
}

void app_main(void)
{
    ESP_LOGI(TAG, "Dent Scope ESP32-C3 starting...");

    esp_netif_init();
    esp_event_loop_create_default();
    wifi_init_ap();
    start_webserver();

    /* BLE init */
    nimble_port_init();
    ble_hs_cfg.reset_cb = on_stack_reset;
    ble_hs_cfg.sync_cb = on_sync;
    ble_svc_gatt_init();
    ble_gatts_count_cfg(gatt_svcs);
    ble_gatts_add_svcs(gatt_svcs);

    nimble_port_freertos_init(ble_host_task);

    /* UART task */
    xTaskCreate(uart_task, "uart", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "Ready. BLE: DentScope | Wi-Fi AP: DentScope");
}