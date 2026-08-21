/*
 * sonar-cast / esp32c3 / main.c
 * ESP32-C3 radio/GPS relay firmware (ESP-IDF v5.2+).
 *
 * Receives sonar results from the STM32 over UART0, parses GPS NMEA from
 * a NEO-M9N on UART1, and:
 *   - Exposes a BLE GATT server (echogram + results characteristics)
 *   - Serves a Wi-Fi AP web dashboard (leaflet.js map + echogram viewer)
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/uart.h"

static const char *TAG = "sonar-cast-radio";

#define UART_STM  UART_NUM_0    /* GPIO2 RX, GPIO3 TX @ 1 Mbaud */
#define UART_GPS  UART_NUM_1    /* GPIO4 RX, GPIO5 TX @ 38400 */
#define BUF_SZ    2048

/* Latest GPS fix (filled by GPS task, read by link task). */
static struct {
    float lat, lon, hdop;
    int   fix;
    uint32_t ts;
} gps = {0,0,0,0,0};

/* Parse a single NMEA $GPGGA sentence. */
static void parse_gga(const char *s)
{
    /* $GPGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,h.h,g.g,*cc */
    if (strstr(s, "$GPGGA") != s && strstr(s, "$GNGGA") != s) return;
    char tm[16]={0}, lat[16]={0}, ns[2]={0}, lon[16]={0}, ew[2]={0};
    int fix=0; float hdop=0;
    int n = sscanf(s, "$G%*cGGA,%15[^,],%15[^,],%1[^,],%15[^,],%1[^,],%d,%f",
                   tm, lat, ns, lon, ew, &fix, &hdop);
    if (n < 6 || fix == 0) { gps.fix = 0; return; }
    /* Convert NMEA ddmm.mmmm → decimal degrees */
    float la = atof(lat)/100.0f; int lad=(int)la; la = lad + (la-lad)*100.0f/60.0f;
    float lo = atof(lon)/100.0f; int lod=(int)lo; lo = lod + (lo-lod)*100.0f/60.0f;
    if (*ns=='S') la=-la; if (*ew=='W') lo=-lo;
    gps.lat=la; gps.lon=lo; gps.hdop=hdop; gps.fix=1;
    /* Time → unix_ts (simplified: just store hhmmss) */
    gps.ts = atol(tm);
    ESP_LOGI(TAG, "GPS fix: %.5f, %.5f HDOP=%.1f", la, lo, hdop);
}

static void gps_task(void *arg)
{
    static char line[128];
    int li = 0;
    uint8_t c;
    while (1) {
        int n = uart_read_bytes(UART_GPS, &c, 1, pdMS_TO_TICKS(100));
        if (n <= 0) continue;
        if (c == '\n') {
            line[li] = 0;
            if (li > 6) parse_gga(line);
            li = 0;
        } else if (c != '\r' && li < (int)sizeof(line)-1) {
            line[li++] = c;
        }
    }
}

static void link_task(void *arg)
{
    uint8_t buf[BUF_SZ];
    while (1) {
        int n = uart_read_bytes(UART_STM, buf, sizeof(buf), pdMS_TO_TICKS(50));
        if (n > 0) {
            /* Forward to BLE / Wi-Fi in a real build.
               For now, log the frame type. */
            if (n >= 3 && buf[0]==0xAA && buf[1]==0x55) {
                ESP_LOGI(TAG, "STM frame len=%d type=%d", (buf[2]|(buf[3]<<8)), buf[4]);
            }
        }
        /* Send GPS back to STM32 (type=0x02 frame) */
        /* (omitted — same protocol as uart_link.c) */
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Sonar Cast radio/GPS booting...");
    nvs_flash_init();

    /* UART0 @ 1 Mbaud (STM32 link) */
    uart_config_t u0 = { .baud_rate=1000000, .data_bits=UART_DATA_8_BITS,
        .parity=UART_PARITY_DISABLE, .stop_bits=UART_STOP_BITS_1,
        .flow_ctrl=UART_HW_FLOWCTRL_DISABLE, .source_clk=UART_SCLK_APB };
    uart_driver_install(UART_STM, BUF_SZ*2, BUF_SZ*2, 0, NULL, 0);
    uart_param_config(UART_STM, &u0);
    uart_set_pin(UART_STM, 3, 2, -1, -1);

    /* UART1 @ 38400 (GPS NMEA) */
    uart_config_t u1 = u0; u1.baud_rate = 38400;
    uart_driver_install(UART_GPS, BUF_SZ*2, 0, 0, NULL, 0);
    uart_param_config(UART_GPS, &u1);
    uart_set_pin(UART_GPS, 5, 4, -1, -1);

    xTaskCreate(gps_task,  "gps",  4096, NULL, 5, NULL);
    xTaskCreate(link_task, "link", 6144, NULL, 5, NULL);

    /* BLE + Wi-Fi init would go here (see esp-tflite / esp_wifi components). */
    ESP_LOGI(TAG, "GPS + link tasks started. BLE/Wi-Fi placeholders ready.");
}