/**
 * wifi_uplink.c — Wi-Fi Uplink via ESP32-C3 AT Commands
 * 
 * Manages UART communication with ESP32-C3 module running
 * the ESP-AT firmware for Wi-Fi connectivity and MQTT publishing.
 */

#include "wifi_uplink.h"
#include "stm32l4xx_hal.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

extern UART_HandleTypeDef huart1;  /* USART1: ESP32-C3 */

static wifi_config_t s_wifi_config = {0};
static wifi_mqtt_config_t s_mqtt_config = {0};
static bool s_wifi_connected = false;
static bool s_mqtt_connected = false;
static char s_tx_buf[512];
static char s_rx_buf[256];

/* AT command response parser */
static bool send_at_command(const char *cmd, const char *expected, uint32_t timeout_ms);
static bool wait_for_response(const char *expected, uint32_t timeout_ms);

/*----------------------------------------------------------------------------*/

int wifi_uplink_init(void) {
    /* Enable ESP32-C3 power */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_SET);
    HAL_Delay(500);  /* Wait for ESP32-C3 boot */
    
    /* Test AT communication */
    if (!send_at_command("AT\r\n", "OK", 2000)) {
        return -1;
    }
    
    /* Reset to known state */
    if (!send_at_command("AT+RST\r\n", "ready", 5000)) {
        return -2;
    }
    HAL_Delay(1000);
    
    /* Configure UART for transparent mode */
    if (!send_at_command("AT+UART_CUR=115200,8,1,0,0\r\n", "OK", 1000)) {
        return -3;
    }
    
    /* Set station mode */
    if (!send_at_command("AT+CWMODE=1\r\n", "OK", 1000)) {
        return -4;
    }
    
    /* Disable echo */
    if (!send_at_command("ATE0\r\n", "OK", 1000)) {
        /* Non-critical */
    }
    
    return 0;
}

/*----------------------------------------------------------------------------*/

int wifi_configure(const wifi_config_t *config) {
    if (!config) return -1;
    
    s_wifi_config = *config;
    
    /* Configure Wi-Fi credentials */
    snprintf(s_tx_buf, sizeof(s_tx_buf), 
             "AT+CWJAP=\"%s\",\"%s\"\r\n",
             config->ssid, config->password);
    
    if (!send_at_command(s_tx_buf, "WIFI GOT IP", 15000)) {
        return -2;
    }
    
    s_wifi_connected = true;
    return 0;
}

/*----------------------------------------------------------------------------*/

int wifi_connect(uint32_t timeout_ms) {
    if (s_wifi_config.ssid[0] == '\0') {
        return -1;  /* No credentials configured */
    }
    
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+CWJAP=\"%s\",\"%s\"\r\n",
             s_wifi_config.ssid, s_wifi_config.password);
    
    if (!send_at_command(s_tx_buf, "WIFI GOT IP", timeout_ms)) {
        s_wifi_connected = false;
        return -2;
    }
    
    s_wifi_connected = true;
    return 0;
}

/*----------------------------------------------------------------------------*/

void wifi_disconnect(void) {
    send_at_command("AT+CWQAP\r\n", "OK", 2000);
    s_wifi_connected = false;
}

/*----------------------------------------------------------------------------*/

bool wifi_is_connected(void) {
    /* Quick check with AT+CIPSTATUS */
    if (send_at_command("AT+CIPSTATUS\r\n", "STATUS:", 1000)) {
        s_wifi_connected = true;
    } else {
        s_wifi_connected = false;
    }
    return s_wifi_connected;
}

/*----------------------------------------------------------------------------*/

int wifi_mqtt_configure(const wifi_mqtt_config_t *config) {
    if (!config) return -1;
    
    s_mqtt_config = *config;
    
    /* Configure MQTT broker */
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+MQTTUSERCFG=0,1,\"%s\",\"%s\",\"%s\",0,0,\"\"\r\n",
             config->device_id,
             config->username ? config->username : "",
             config->password ? config->password : "");
    
    if (!send_at_command(s_tx_buf, "OK", 2000)) {
        return -2;
    }
    
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+MQTTCONNCFG=0,0,0,0,0,\"\","  "0,0,60,0\r\n");
    send_at_command(s_tx_buf, "OK", 1000);
    
    return 0;
}

/*----------------------------------------------------------------------------*/

int wifi_mqtt_connect(uint32_t timeout_ms) {
    if (!s_mqtt_config.broker_url) return -1;
    
    /* Parse broker URL to extract host and port */
    /* For simplicity, assume format: mqtt://hostname:port */
    char host[64] = {0};
    uint16_t port = s_mqtt_config.broker_port;
    
    /* Extract hostname from URL */
    const char *start = strstr(s_mqtt_config.broker_url, "://");
    if (start) {
        start += 3;
        const char *end = strchr(start, ':');
        if (!end) end = strchr(start, '/');
        if (!end) end = start + strlen(start);
        size_t len = (end - start) < sizeof(host) - 1 ? (end - start) : sizeof(host) - 1;
        strncpy(host, start, len);
    } else {
        strncpy(host, s_mqtt_config.broker_url, sizeof(host) - 1);
    }
    
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+MQTTCONN=0,\"%s\",%u,0\r\n",
             host, port);
    
    if (!send_at_command(s_tx_buf, "OK", timeout_ms)) {
        s_mqtt_connected = false;
        return -2;
    }
    
    s_mqtt_connected = true;
    return 0;
}

/*----------------------------------------------------------------------------*/

int wifi_push_all(float gravity, float temperature, uint16_t co2_ppm,
                  float ph, float pressure, ferment_stage_t stage,
                  float activity) {
    if (!s_mqtt_connected) return -1;
    
    /* Build JSON payload */
    char json[256];
    snprintf(json, sizeof(json),
             "{\"sg\":%.4f,\"temp\":%.1f,\"co2\":%u,\"ph\":%.2f,"
             "\"pressure\":%.1f,\"stage\":\"%s\",\"activity\":%.0f,"
             "\"trend\":%d}",
             gravity, temperature, co2_ppm, ph, pressure,
             fermentation_stage_str(stage), activity, 0);
    
    /* Build MQTT publish command */
    char topic[64];
    snprintf(topic, sizeof(topic), "brewsense/%s/status", s_mqtt_config.device_id);
    
    size_t json_len = strlen(json);
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+MQTTPUB=0,\"%s\",\"%s\",0,0\r\n",
             topic, json);
    
    if (!send_at_command(s_tx_buf, "OK", 5000)) {
        return -2;
    }
    
    return 0;
}

/*----------------------------------------------------------------------------*/

int wifi_publish_value(const char *topic_suffix, float value) {
    if (!s_mqtt_connected) return -1;
    
    char topic[64];
    snprintf(topic, sizeof(topic), "brewsense/%s/%s",
             s_mqtt_config.device_id, topic_suffix);
    
    char payload[32];
    snprintf(payload, sizeof(payload), "%.4f", value);
    
    snprintf(s_tx_buf, sizeof(s_tx_buf),
             "AT+MQTTPUB=0,\"%s\",\"%s\",0,0\r\n",
             topic, payload);
    
    if (!send_at_command(s_tx_buf, "OK", 3000)) {
        return -2;
    }
    
    return 0;
}

/*----------------------------------------------------------------------------*/

void wifi_mqtt_disconnect(void) {
    send_at_command("AT+MQTTDISCONN=0\r\n", "OK", 2000);
    s_mqtt_connected = false;
}

/*----------------------------------------------------------------------------*/

void wifi_sleep(void) {
    /* Put ESP32-C3 into deep sleep */
    send_at_command("AT+GSLP=0\r\n", "OK", 1000);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_RESET);  /* Power off */
}

void wifi_wake(void) {
    /* Power on ESP32-C3 */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6, GPIO_PIN_SET);
    HAL_Delay(500);
    
    /* Re-initialize AT connection */
    wifi_uplink_init();
}

/*----------------------------------------------------------------------------*/

int8_t wifi_get_rssi(void) {
    if (!s_wifi_connected) return 0;
    
    /* Query RSSI with AT+CWLAP */
    if (send_at_command("AT+CWLAP\r\n", "+CWLAP:", 3000)) {
        /* Parse RSSI from response — simplified */
        /* In production, parse the actual RSSI value from response */
        return -50;  /* Placeholder */
    }
    
    return 0;
}

/*----------------------------------------------------------------------------*/
/* AT Command Helper Functions */
/*----------------------------------------------------------------------------*/

static bool send_at_command(const char *cmd, const char *expected, uint32_t timeout_ms) {
    /* Send AT command via UART */
    HAL_UART_Transmit(&huart1, (uint8_t *)cmd, strlen(cmd), 1000);
    
    /* Wait for expected response */
    return wait_for_response(expected, timeout_ms);
}

static bool wait_for_response(const char *expected, uint32_t timeout_ms) {
    uint32_t start = HAL_GetTick();
    uint16_t rx_idx = 0;
    
    while ((HAL_GetTick() - start) < timeout_ms) {
        uint8_t byte;
        if (HAL_UART_Receive(&huart1, &byte, 1, 10) == HAL_OK) {
            s_rx_buf[rx_idx++] = byte;
            s_rx_buf[rx_idx] = '\0';
            
            if (strstr(s_rx_buf, expected) != NULL) {
                return true;
            }
            
            if (strstr(s_rx_buf, "ERROR") != NULL) {
                return false;
            }
            
            if (rx_idx >= sizeof(s_rx_buf) - 1) {
                rx_idx = 0;  /* Overflow protection */
            }
        }
    }
    
    return false;  /* Timeout */
}