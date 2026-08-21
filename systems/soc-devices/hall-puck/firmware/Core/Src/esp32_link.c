/*
 * hall-puck / firmware / Core / Src / esp32_link.c
 * UART bridge to ESP32-C3 companion (BLE + WiFi)
 *
 * Protocol: framed binary over UART1 @ 460800 baud
 * Frame format:
 *   [0xA5] [type] [len_hi] [len_lo] [payload...] [checksum] [0x5A]
 *
 * MIT License.
 */
#include "esp32_link.h"
#include "measurement.h"
#include "main.h"
#include <string.h>

#define UART_BAUDRATE   460800
#define UART_BUF_SIZE   256

#define FRAME_SOF       0xA5
#define FRAME_EOF       0x5A

static uint8_t rx_buf[UART_BUF_SIZE];
static volatile uint16_t rx_head = 0;
static uint16_t rx_tail = 0;
static bool connected = false;
static esp_cmd_callback_t cmd_callback = NULL;

/* UART1 handle */
extern UART_HandleTypeDef huart1;

static uint8_t calc_checksum(const uint8_t *data, int len)
{
    uint8_t cs = 0;
    for (int i = 0; i < len; i++) cs ^= data[i];
    return cs;
}

static void uart_send_byte(uint8_t byte)
{
    while (!(USART1->ISR & USART_ISR_TXE));
    USART1->TDR = byte;
}

static void uart_send_bytes(const uint8_t *data, int len)
{
    for (int i = 0; i < len; i++) {
        uart_send_byte(data[i]);
    }
}

static void send_frame(uint8_t type, const uint8_t *payload, int len)
{
    if (len > 250) len = 250;

    uint8_t header[4] = { FRAME_SOF, type, (len >> 8) & 0xFF, len & 0xFF };
    uart_send_bytes(header, 4);

    if (len > 0) {
        uart_send_bytes(payload, len);
    }

    uint8_t cs = calc_checksum(header + 1, 3);
    if (len > 0) {
        for (int i = 0; i < len; i++) cs ^= payload[i];
    }

    uart_send_byte(cs);
    uart_send_byte(FRAME_EOF);
}

/* ---- Public API ---- */
void esp32_link_init(void)
{
    /* Configure USART1: PA9 (TX), PA10 (RX), 460800 baud, 8N1 */
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    /* Configure PA9 as AF7 (USART1_TX), PA10 as AF7 (USART1_RX) */
    GPIOA->MODER &= ~(3 << (UART_TX_PIN * 2) | 3 << (UART_RX_PIN * 2));
    GPIOA->MODER |= (2 << (UART_TX_PIN * 2) | 2 << (UART_RX_PIN * 2));  /* AF mode */
    GPIOA->AFR[1] &= ~(0xF << ((UART_TX_PIN - 8) * 4) | 0xF << ((UART_RX_PIN - 8) * 4));
    GPIOA->AFR[1] |= (7 << ((UART_TX_PIN - 8) * 4) | 7 << ((UART_RX_PIN - 8) * 4));  /* AF7 */

    /* USART1 config: 460800 baud, 8N1, enable TX + RX */
    USART1->BRR = (SystemCoreClock + UART_BAUDRATE / 2) / UART_BAUDRATE;
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_RXNEIE | USART_CR1_UE;

    /* Enable USART1 interrupt in NVIC */
    NVIC_EnableIRQ(USART1_IRQn);

    connected = false;
}

void esp32_link_set_cmd_callback(esp_cmd_callback_t cb)
{
    cmd_callback = cb;
}

void esp32_link_send_result(const meas_result_t *r)
{
    /* Pack result into 28-byte payload */
    uint8_t payload[28];
    int idx = 0;

    memcpy(&payload[idx], &r->sheet_resistance, 4); idx += 4;
    memcpy(&payload[idx], &r->hall_coefficient, 4); idx += 4;
    memcpy(&payload[idx], &r->carrier_conc, 4); idx += 4;
    memcpy(&payload[idx], &r->mobility, 4); idx += 4;
    memcpy(&payload[idx], &r->resistivity, 4); idx += 4;
    payload[idx++] = (uint8_t)r->carrier_type;
    payload[idx++] = r->status;

    int16_t temp_x100 = (int16_t)(r->temperature_c * 100);
    memcpy(&payload[idx], &temp_x100, 2); idx += 2;
    memcpy(&payload[idx], &r->b_field_t, 4); idx += 4;

    send_frame(ESP_FRAME_RESULT, payload, idx);
}

void esp32_link_send_point(const meas_point_t *p, int idx)
{
    uint8_t payload[20];
    int off = 0;

    payload[off++] = (uint8_t)p->config;
    payload[off++] = (uint8_t)idx;

    float v_uv = p->voltage_uv;
    float i_ma = p->current_ma;
    float b_t = p->b_field_t;
    float t_c = p->temperature_c;

    memcpy(&payload[off], &v_uv, 4); off += 4;
    memcpy(&payload[off], &i_ma, 4); off += 4;
    memcpy(&payload[off], &b_t, 4); off += 4;
    memcpy(&payload[off], &t_c, 4); off += 4;

    send_frame(ESP_FRAME_POINT, payload, off);
}

void esp32_link_send_state(meas_state_t state)
{
    uint8_t payload = (uint8_t)state;
    send_frame(ESP_FRAME_STATE, &payload, 1);
}

void esp32_link_send_info(const char *fw_version, float b_field, uint32_t cal_date)
{
    uint8_t payload[40];
    int off = 0;

    /* Firmware version string (8 bytes) */
    strncpy((char *)&payload[off], fw_version, 8);
    off += 8;

    memcpy(&payload[off], &b_field, 4); off += 4;
    memcpy(&payload[off], &cal_date, 4); off += 4;

    send_frame(ESP_FRAME_INFO, payload, off);
}

/* ---- Frame parser (called from poll) ---- */
static void process_frame(uint8_t type, const uint8_t *payload, int len)
{
    switch (type) {
    case ESP_FRAME_ACK:
        connected = true;
        break;
    case ESP_FRAME_CMD:
        if (cmd_callback && len >= 1) {
            cmd_callback(payload[0], &payload[1], len - 1);
        }
        break;
    default:
        break;
    }
}

static int parse_frame(void)
{
    /* Look for SOF in rx_buf */
    /* Simplified parser — production would use proper ring buffer */
    static enum { WAIT_SOF, READ_TYPE, READ_LEN_HI, READ_LEN_LO,
                  READ_PAYLOAD, READ_CHECKSUM, READ_EOF } parse_state = WAIT_SOF;
    static uint8_t frame_type = 0;
    static uint16_t frame_len = 0;
    static uint8_t frame_payload[256];
    static int payload_idx = 0;
    static uint8_t expected_cs = 0;

    while (rx_tail != rx_head) {
        uint8_t byte = rx_buf[rx_tail];
        rx_tail = (rx_tail + 1) % UART_BUF_SIZE;

        switch (parse_state) {
        case WAIT_SOF:
            if (byte == FRAME_SOF) parse_state = READ_TYPE;
            break;
        case READ_TYPE:
            frame_type = byte;
            expected_cs = byte;
            parse_state = READ_LEN_HI;
            break;
        case READ_LEN_HI:
            frame_len = (byte << 8);
            expected_cs ^= byte;
            parse_state = READ_LEN_LO;
            break;
        case READ_LEN_LO:
            frame_len |= byte;
            expected_cs ^= byte;
            payload_idx = 0;
            parse_state = (frame_len > 0) ? READ_PAYLOAD : READ_CHECKSUM;
            break;
        case READ_PAYLOAD:
            frame_payload[payload_idx++] = byte;
            expected_cs ^= byte;
            if (payload_idx >= frame_len) parse_state = READ_CHECKSUM;
            break;
        case READ_CHECKSUM:
            if (byte == expected_cs) {
                parse_state = READ_EOF;
            } else {
                parse_state = WAIT_SOF;  /* checksum error */
            }
            break;
        case READ_EOF:
            if (byte == FRAME_EOF) {
                process_frame(frame_type, frame_payload, frame_len);
            }
            parse_state = WAIT_SOF;
            break;
        }
    }

    return 0;
}

void esp32_link_poll(void)
{
    parse_frame();
}

bool esp32_link_is_connected(void)
{
    return connected;
}

/* ---- USART1 interrupt handler ---- */
void USART1_IRQHandler(void)
{
    if (USART1->ISR & USART_ISR_RXNE) {
        uint8_t byte = USART1->RDR;
        uint16_t next = (rx_head + 1) % UART_BUF_SIZE;
        if (next != rx_tail) {
            rx_buf[rx_head] = byte;
            rx_head = next;
        }
    }
}