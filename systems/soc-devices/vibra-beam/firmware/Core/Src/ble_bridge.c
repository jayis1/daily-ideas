/*
 * ble_bridge.c — ESP32-C3 UART bridge for BLE/Wi-Fi streaming
 *
 * Protocol (simple framed):
 *   0xAA <type> <len_hi> <len_lo> <payload...> <crc8>
 * Types:
 *   0x01 RESULT   (measure_result_t)
 *   0x02 FFT      (fft_result_t summary + bins)
 *   0x03 STREAM   (phase_block_t velocity excerpt)
 *   0x10 CMD     (incoming commands from app → set params)
 */

#include "ble_bridge.h"
#include "stm32g4xx_hal.h"
#include "config.h"
#include <string.h>

extern UART_HandleTypeDef huart2;

#define SYNC_BYTE 0xAA

static uint8_t s_tx_buf[256];

static uint8_t crc8(const uint8_t *p, uint32_t n)
{
    uint8_t c = 0;
    for (uint32_t i = 0; i < n; i++) c ^= p[i];
    return c;
}

static void send_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    s_tx_buf[0] = SYNC_BYTE;
    s_tx_buf[1] = type;
    s_tx_buf[2] = (len >> 8) & 0xFF;
    s_tx_buf[3] = len & 0xFF;
    if (len) memcpy(&s_tx_buf[4], payload, len);
    s_tx_buf[4 + len] = crc8(s_tx_buf, 4 + len);
    HAL_UART_Transmit(&huart2, s_tx_buf, 5 + len, 100);
}

void ble_bridge_init(void)
{
    /* UART already initialized in main; nothing else needed */
}

void ble_bridge_send_result(const measure_result_t *r)
{
    send_frame(0x01, (const uint8_t *)r, sizeof(*r));
}

void ble_bridge_send_fft(const fft_result_t *fft)
{
    /* Send summary + first 128 bins to keep frame small */
    struct {
        float freq_peak_hz;
        float mag_peak;
        float thd_pct;
        float snr_db;
        float bin_hz;
        uint16_t n_bins;
        float bins[128];
    } pkt;
    pkt.freq_peak_hz = fft->freq_peak_hz;
    pkt.mag_peak     = fft->mag_peak;
    pkt.thd_pct      = fft->thd_pct;
    pkt.snr_db       = fft->snr_db;
    pkt.bin_hz       = fft->bin_hz;
    pkt.n_bins       = 128;
    for (int i = 0; i < 128; i++) pkt.bins[i] = fft->mag[i];
    send_frame(0x02, (const uint8_t *)&pkt, sizeof(pkt));
}

void ble_bridge_send_stream(const phase_block_t *pb, uint32_t t_ms)
{
    /* Send a downsampled velocity excerpt (64 samples) */
    struct {
        uint32_t t_ms;
        uint16_t n;
        float vel[64];
    } pkt;
    pkt.t_ms = t_ms;
    pkt.n = 64;
    uint32_t step = (pb->n > 64) ? pb->n / 64 : 1;
    for (uint32_t i = 0, j = 0; i < pb->n && j < 64; i += step, j++) {
        pkt.vel[j] = pb->vel_mms[i];
    }
    send_frame(0x03, (const uint8_t *)&pkt, sizeof(pkt));
}

void ble_bridge_handle_commands(acq_params_t *params)
{
    /* Non-blocking RX: check for incoming command frame */
    static uint8_t rx[32];
    static uint32_t rx_len = 0;

    uint8_t b;
    while (HAL_UART_Receive(&huart2, &b, 1, 0) == HAL_OK) {
        if (rx_len < sizeof(rx)) rx[rx_len++] = b;
        if (rx_len >= 5 && rx[0] == SYNC_BYTE) {
            uint16_t len = (rx[2] << 8) | rx[3];
            if (rx_len == 5 + len) {
                if (rx[4 + len] == crc8(rx, 4 + len)) {
                    /* Parse command */
                    switch (rx[1]) {
                    case 0x10:  /* SET_PARAM */
                        if (len >= 1) {
                            uint8_t id = rx[4];
                            float val = 0;
                            if (len >= 5) memcpy(&val, &rx[5], 4);
                            switch (id) {
                            case 0: params->laser_mw     = val; break;
                            case 1: params->vel_lp_fc_hz = val; break;
                            case 2: params->audio_gain   = val; break;
                            case 3: params->audio_shift  = val; break;
                            case 4: params->imu_compensate = (uint8_t)val; break;
                            case 5: params->ble_stream     = (uint8_t)val; break;
                            default: break;
                            }
                        }
                        break;
                    default: break;
                    }
                }
                rx_len = 0;
            }
        }
    }
}