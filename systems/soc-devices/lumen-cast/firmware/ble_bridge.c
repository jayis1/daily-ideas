/**
 * lumen_cast/firmware/ble_bridge.c — UART protocol to ESP32-C3 bridge
 *
 * Binary frame protocol between STM32G491 and ESP32-C3:
 *   [SYNC1=0xAA][SYNC2=0x55][TYPE][LEN_LO][LEN_HI][PAYLOAD...][CRC8]
 *
 * Frame types:
 *   0x01 RESULT     STM32→ESP32  Photometric result (128 bytes)
 *   0x02 SCAN_DATA  STM32→ESP32  Live scan samples (chunked)
 *   0x03 IES_FILE   STM32→ESP32  IES LM-63 photometric file content
 *   0x04 LDT_FILE   STM32→ESP32  EULUMDAT file content
 *   0x05 DEVICE_INFO STM32→ESP32 Firmware version, battery, scan count
 *   0x06 TIME_SYNC  ESP32→STM32  NTP epoch time (4 bytes)
 *   0x07 CAL_UPDATE ESP32→STM32  Calibration factor update (4 bytes float)
 */

#include "main.h"
#include <string.h>

#define TAG "BLE"
#define UART_BAUD  115200
#define MAX_PAYLOAD 256

/* ── CRC8 (polynomial 0x07, init 0x00) ─────────────────────────────── */

static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ── UART init ─────────────────────────────────────────────────────── */

int ble_bridge_init(void)
{
    /* USART1 on PA9(TX)/PA10(RX), 115200 8N1 */
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    GPIOA->MODER &= ~(3 << (PIN_USART1_TX * 2));
    GPIOA->MODER |= (2 << (PIN_USART1_TX * 2));  /* AF */
    GPIOA->AFR[1] &= ~(0xF << ((PIN_USART1_TX - 8) * 4));
    GPIOA->AFR[1] |= (7 << ((PIN_USART1_TX - 8) * 4));  /* AF7 = USART1 */

    GPIOA->MODER &= ~(3 << (PIN_USART1_RX * 2));
    GPIOA->MODER |= (2 << (PIN_USART1_RX * 2));
    GPIOA->AFR[1] &= ~(0xF << ((PIN_USART1_RX - 8) * 4));
    GPIOA->AFR[1] |= (7 << ((PIN_USART1_RX - 8) * 4));

    USART1->BRR = 170000000 / UART_BAUD;  /* APB2 = 170 MHz */
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_RXNEIE | USART_CR1_UE;

    LOGI(TAG, "BLE bridge UART init: USART1 @ %d baud", UART_BAUD);
    return 0;
}

/* ── Frame transmission ────────────────────────────────────────────── */

static void ble_send_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    if (len > MAX_PAYLOAD) len = MAX_PAYLOAD;

    /* Header */
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = 0xAA;
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = 0x55;
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = type;
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = len & 0xFF;
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = (len >> 8) & 0xFF;

    /* Payload */
    for (uint16_t i = 0; i < len; i++) {
        while (!(USART1->ISR & USART_ISR_TXE));
        USART1->TDR = payload[i];
    }

    /* CRC8 over type + length + payload */
    uint8_t crc_buf[3 + MAX_PAYLOAD];
    crc_buf[0] = type;
    crc_buf[1] = len & 0xFF;
    crc_buf[2] = (len >> 8) & 0xFF;
    memcpy(crc_buf + 3, payload, len);
    uint8_t crc = crc8(crc_buf, 3 + len);

    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = crc;
}

/* ── Frame receivers ───────────────────────────────────────────────── */

void ble_bridge_send_result(const photo_result_t *r)
{
    uint8_t buf[128];
    memset(buf, 0, sizeof(buf));
    memcpy(buf, r, sizeof(photo_result_t));
    ble_send_frame(0x01, buf, sizeof(photo_result_t) + 4);
}

void ble_bridge_send_scan_data(const scan_buffer_t *s)
{
    /* Send last 10 samples as a chunk */
    int start = s->n_samples - 10;
    if (start < 0) start = 0;
    int count = s->n_samples - start;
    int len = count * sizeof(photo_sample_t);
    if (len > MAX_PAYLOAD) len = MAX_PAYLOAD;

    ble_send_frame(0x02, (uint8_t *)&s->samples[start], len);
}

/* ── IES LM-63 file generation ─────────────────────────────────────── */
/*
 * IES LM-63-2002 format:
 *   IESNA:LM-63-2002
 *   [Keyword] Value
 *   ...
 *   TILT=NONE
 *   <n_lamps> <lumens/lamp> <multiplier> <n_vert_angles> <n_horz_angles>
 *   <photometric_type> <units_type> <width> <length> <height>
 *   <ballast_factor> <future_use> <input_watts>
 *   <vert_angles...>
 *   <horz_angles...>
 *   <candela_values[horz][vert]...>
 */

void ble_bridge_send_ies_file(const scan_buffer_t *s)
{
    /* Generate IES file content in chunks */
    static char ies_buf[4096];
    int pos = 0;

    const scan_config_t *cfg = &s->config;

    /* Header */
    pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos,
        "IESNA:LM-63-2002\r\n"
        "[TEST] LUMEN_CAST_%04d\r\n"
        "[MANUFAC] Unknown\r\n"
        "[TDATE] %lu\r\n"
        "[LUMCAT] LM_%04d\r\n"
        "[LUMINAIRE] Lumen Cast Scan\r\n"
        "TILT=NONE\r\n",
        s->timestamp & 0xFFFF, (unsigned long)s->timestamp,
        s->timestamp & 0xFFFF);

    /* Compute total flux for the file */
    float flux = 0;
    for (int i = 0; i < s->n_samples; i++)
        flux += s->samples[i].candela;
    if (s->n_samples > 0) flux /= s->n_samples;
    flux *= 4.0f * 3.14159f;

    /* Numeric header line */
    int n_vert = cfg->az_steps;
    int n_horz = cfg->el_steps;

    pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos,
        "1 %.1f 1.0 %d %d 1 1 0 0 0 1.0 1.0 0\r\n",
        flux, n_vert, n_horz);

    /* Vertical angles (azimuth 0–360) */
    for (int i = 0; i < n_vert && pos < (int)sizeof(ies_buf) - 20; i++) {
        float angle = cfg->az_start + i *
            (cfg->az_end - cfg->az_start) / n_vert;
        pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "%.1f ", angle);
        if ((i + 1) % 10 == 0) pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "\r\n");
    }
    pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "\r\n");

    /* Horizontal angles (elevation) */
    for (int j = 0; j < n_horz && pos < (int)sizeof(ies_buf) - 20; j++) {
        float angle = cfg->el_start + j *
            (cfg->el_end - cfg->el_start) / (n_horz > 1 ? n_horz - 1 : 1);
        pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "%.1f ", angle);
    }
    pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "\r\n");

    /* Candela values: for each horizontal angle, all vertical angles */
    for (int j = 0; j < n_horz; j++) {
        for (int i = 0; i < n_vert && pos < (int)sizeof(ies_buf) - 20; i++) {
            int idx = j * n_vert + i;
            if (idx < s->n_samples) {
                pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos,
                    "%.1f ", s->samples[idx].candela);
            }
            if ((i + 1) % 10 == 0)
                pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "\r\n");
        }
        pos += snprintf(ies_buf + pos, sizeof(ies_buf) - pos, "\r\n");
    }

    /* Send in chunks */
    int offset = 0;
    while (offset < pos) {
        int chunk = pos - offset;
        if (chunk > MAX_PAYLOAD) chunk = MAX_PAYLOAD;
        ble_send_frame(0x03, (uint8_t *)ies_buf + offset, chunk);
        offset += chunk;
    }

    LOGI(TAG, "IES file sent: %d bytes", pos);
}

/* ── Incoming frame parsing ────────────────────────────────────────── */

static uint8_t rx_buf[MAX_PAYLOAD + 8];
static int rx_pos = 0;
static int rx_len = 0;
static bool rx_in_frame = false;

void ble_bridge_poll(void)
{
    while (USART1->ISR & USART_ISR_RXNE) {
        uint8_t byte = (uint8_t)USART1->RDR;

        if (!rx_in_frame) {
            if (rx_pos == 0 && byte == 0xAA) {
                rx_pos = 1;
            } else if (rx_pos == 1 && byte == 0x55) {
                rx_in_frame = true;
                rx_pos = 0;
                rx_len = 0;
            } else {
                rx_pos = 0;
            }
        } else {
            if (rx_pos < MAX_PAYLOAD + 8)
                rx_buf[rx_pos++] = byte;

            if (rx_pos == 3) {
                rx_len = rx_buf[1] | (rx_buf[2] << 8);
            }

            if (rx_pos >= 6 + rx_len) {
                /* Complete frame: verify CRC */
                uint8_t crc = crc8(rx_buf, 3 + rx_len);
                if (crc == rx_buf[3 + rx_len]) {
                    uint8_t type = rx_buf[0];
                    if (type == 0x06 && rx_len == 4) {
                        /* TIME_SYNC: update RTC */
                        uint32_t epoch = rx_buf[3] | (rx_buf[4] << 8) |
                                         (rx_buf[5] << 16) | (rx_buf[6] << 24);
                        ds3231_set_time(epoch);
                        LOGI(TAG, "Time synced: %lu", (unsigned long)epoch);
                    } else if (type == 0x07 && rx_len == 4) {
                        /* CAL_UPDATE */
                        float factor;
                        memcpy(&factor, &rx_buf[3], 4);
                        g_cal_factor = factor;
                        flashlog_save_cal_factor(factor);
                        LOGI(TAG, "Cal updated: %.4f", factor);
                    }
                }
                rx_in_frame = false;
                rx_pos = 0;
            }
        }
    }
}

/* Helper to save cal factor (called from ble_bridge) */
extern void flashlog_save_cal_factor(float factor);