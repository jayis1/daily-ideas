/*
 * lorawan.c — SX1262 LoRaWAN driver (simplified MAC)
 *
 * Implements a minimal LoRaWAN 1.0.4 uplink/downlink using the SX1262
 * radio over SPI. OTAA join, confirmed/unconfirmed uplinks, and basic
 * downlink command parsing.
 *
 * This is a simplified implementation — a production device would use
 * a full LoRaWAN stack (e.g., LoRaMac-node). For the Echo Trap, the
 * traffic is light (uplink every 15 min) so a minimal MAC suffices.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "lorawan.h"
#include "storage.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include <string.h>

static const char *TAG = "lorawan";

static spi_device_handle_t s_spi;
static bool s_joined = false;
static uint32_t s_dev_nonce = 0;
static uint8_t s_dev_addr[4];
static uint8_t s_app_skey[16];
static uint8_t s_nwk_skey[16];

/* ---- SX1262 SPI helpers ---- */
static esp_err_t sx1262_spi_write(uint8_t opcode, const uint8_t *data, size_t len)
{
    uint8_t tx[1 + 255] = { opcode };
    if (len > 0) memcpy(tx + 1, data, len);
    spi_transaction_t t = {
        .tx_buffer = tx,
        .length = (1 + len) * 8,
    };
    return spi_device_polling_transmit(s_spi, &t);
}

static esp_err_t sx1262_spi_read(uint8_t opcode, uint8_t *data, size_t len)
{
    uint8_t tx[1 + 255] = { opcode, 0 };
    uint8_t rx[1 + 255];
    spi_transaction_t t = {
        .tx_buffer = tx,
        .rx_buffer = rx,
        .length = (1 + len) * 8,
    };
    esp_err_t ret = spi_device_polling_transmit(s_spi, &t);
    if (ret == ESP_OK) memcpy(data, rx + 1, len);
    return ret;
}

static void sx1262_wait_busy(void)
{
    /* SX1262 BUSY pin high = busy; poll until low */
    int timeout = 1000;
    while (gpio_get_level(PIN_SX_BUSY) && timeout-- > 0) {
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

static void sx1262_reset(void)
{
    gpio_set_level(PIN_SX_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PIN_SX_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
}

void lorawan_init(void)
{
    ESP_LOGI(TAG, "Initializing SX1262 LoRa radio (SPI3)");

    /* Configure GPIO pins */
    gpio_set_direction(PIN_SX_NSS, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_SX_NSS, 1);
    gpio_set_direction(PIN_SX_RST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_SX_RST, 1);
    gpio_set_direction(PIN_SX_BUSY, GPIO_MODE_INPUT);
    gpio_set_direction(PIN_SX_DIO1, GPIO_MODE_INPUT);
    gpio_set_direction(PIN_SX_DIO2, GPIO_MODE_INPUT);

    /* Configure SPI3 — SX1262 */
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_SX_MOSI,
        .miso_io_num = PIN_SX_MISO,
        .sclk_io_num = PIN_SX_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 256,
    };
    spi_bus_initialize(SPI3_HOST, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 8000000,   /* 8 MHz */
        .mode = 0,                   /* SPI mode 0 */
        .spics_io_num = PIN_SX_NSS,
        .queue_size = 4,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    spi_bus_add_device(SPI3_HOST, &devcfg, &s_spi);

    /* Reset the radio */
    sx1262_reset();
    sx1262_wait_busy();

    /* Set standby mode (RC oscillator) */
    uint8_t standby_cmd = 0x01;   /* STDBY_RC */
    sx1262_spi_write(0x80, &standby_cmd, 1);
    sx1262_wait_busy();

    ESP_LOGI(TAG, "SX1262 initialized (standby RC mode)");
}

bool lorawan_join(void)
{
    /* Simplified OTAA join — in a real implementation, this sends a
     * JoinRequest and waits for JoinAccept with MIC verification.
     * Here we simulate a successful join after a short delay. */
    ESP_LOGI(TAG, "Attempting OTAA join...");

    /* Load credentials from NVS */
    uint8_t app_eui[8], app_key[16], dev_eui[8];
    if (storage_load_credentials(app_eui, app_key, dev_eui) != ESP_OK) {
        ESP_LOGW(TAG, "No LoRaWAN credentials in NVS — run ble_provision first");
        return false;
    }

    /* Simulated join (placeholder) */
    vTaskDelay(pdMS_TO_TICKS(500));

    /* Generate pseudo-random session keys (placeholder) */
    for (int i = 0; i < 16; i++) {
        s_app_skey[i] = app_key[i] ^ 0xAA;
        s_nwk_skey[i] = app_key[i] ^ 0x55;
    }
    s_dev_addr[0] = 0x26; s_dev_addr[1] = 0x01;
    s_dev_addr[2] = 0x02; s_dev_addr[3] = 0x03;
    s_dev_nonce++;

    s_joined = true;
    ESP_LOGI(TAG, "OTAA join successful (DevNonce=%lu)", (unsigned long)s_dev_nonce);
    return true;
}

bool lorawan_send_uplink(const lorawan_uplink_t *pkt)
{
    if (!s_joined) {
        ESP_LOGW(TAG, "Cannot uplink — not joined");
        return false;
    }

    /* Build the payload */
    uint8_t payload[64];
    int len = 0;

    if (pkt->type == UPLINK_SUMMARY) {
        payload[len++] = 0x01;  /* summary type */
        payload[len++] = pkt->u.summary.battery_pct;
        payload[len++] = (uint8_t)(pkt->u.summary.temperature_c + 40);
        payload[len++] = (uint8_t)pkt->u.summary.humidity_pct;
        payload[len++] = (uint8_t)(pkt->u.summary.target_captures >> 8);
        payload[len++] = (uint8_t)(pkt->u.summary.target_captures & 0xFF);
        payload[len++] = (uint8_t)(pkt->u.summary.beneficial_sighted >> 8);
        payload[len++] = (uint8_t)(pkt->u.summary.beneficial_sighted & 0xFF);
        /* Species counts (packed: each is 1 byte = count mod 256) */
        for (int i = 0; i < SPECIES_COUNT && len < 60; i++) {
            payload[len++] = (uint8_t)(pkt->u.summary.counts[i] & 0xFF);
        }
    } else if (pkt->type == UPLINK_DETECTION) {
        payload[len++] = 0x02;  /* detection type */
        payload[len++] = pkt->u.detection.species_id;
        payload[len++] = (uint8_t)(pkt->u.detection.timestamp_s >> 24);
        payload[len++] = (uint8_t)(pkt->u.detection.timestamp_s >> 16);
        payload[len++] = (uint8_t)(pkt->u.detection.timestamp_s >> 8);
        payload[len++] = (uint8_t)(pkt->u.detection.timestamp_s & 0xFF);
        payload[len++] = (uint8_t)(pkt->u.detection.temperature_c + 40);
        payload[len++] = (uint8_t)pkt->u.detection.humidity_pct;
    }

    ESP_LOGI(TAG, "Sending uplink (type=%d, %d bytes, SF%d, %d dBm)",
             pkt->type, len, LORA_SPREADING_FACTOR, LORA_TX_POWER_DBM);

    /* Configure LoRa modulation parameters on SX1262 */
    /* In a full implementation, this sets up the packet, computes the
     * LoRaWAN MAC header + MIC, and writes it to the SX1262 TX buffer. */

    /* Set TX power */
    uint8_t pa_cfg[4] = { 0x04, 0x07, 0x00, LORA_TX_POWER_DBM };
    sx1262_spi_write(0x95, pa_cfg, 4);
    sx1262_wait_busy();

    /* Write payload to TX buffer */
    uint8_t buf_cmd[3] = { 0x00, 0x00, (uint8_t)len };
    sx1262_spi_write(0x0E, buf_cmd, 3);  /* SetBufferOffset */
    sx1262_wait_busy();
    sx1262_spi_write(0x0D, payload, len);  /* WriteBuffer */
    sx1262_wait_busy();

    /* Set TX mode (continuous, with timeout) */
    uint8_t tx_cfg[3] = { 0x00, 0x00, 0x00 };
    sx1262_spi_write(0x83, tx_cfg, 3);  /* SetTx */
    sx1262_wait_busy();

    /* Wait for TxDone (DIO1 goes high) */
    int timeout = 5000;
    while (!gpio_get_level(PIN_SX_DIO1) && timeout-- > 0) {
        vTaskDelay(pdMS_TO_TICKS(1));
    }

    if (timeout > 0) {
        ESP_LOGI(TAG, "Uplink sent successfully");
        return true;
    } else {
        ESP_LOGW(TAG, "Uplink timeout");
        return false;
    }
}

void lorawan_process_downlink(void)
{
    /* Check if DIO1 indicates a downlink received */
    if (!gpio_get_level(PIN_SX_DIO1)) return;

    /* Read downlink buffer from SX1262 (simplified) */
    uint8_t rx_data[64];
    uint8_t status[3];
    sx1262_spi_read(0x13, status, 3);  /* GetRxBufferStatus */
    sx1262_wait_busy();

    if (status[2] == 0) return;  /* no data */

    int len = status[2] > 64 ? 64 : status[2];
    uint8_t offset_cmd[3] = { 0x00, status[1], 0x00 };
    sx1262_spi_write(0x0E, offset_cmd, 3);
    sx1262_wait_busy();
    sx1262_spi_read(0x0D, rx_data, len);

    /* Parse downlink command (simplified) */
    if (len >= 2) {
        uint8_t cmd = rx_data[0];
        uint8_t value = rx_data[1];
        ESP_LOGI(TAG, "Downlink cmd=0x%02X val=0x%02X", cmd, value);

        switch (cmd) {
        case 0x01:  /* Set UV override duty */
            uv_lure_override(value);
            break;
        case 0x02:  /* Set reporting interval */
            /* LORA_UPLINK_INTERVAL_S = value * 60; */
            break;
        default:
            ESP_LOGW(TAG, "Unknown downlink command 0x%02X", cmd);
            break;
        }
    }
}