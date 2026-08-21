/*
 * pyro-balance / Core/Src/esp32_link.c — UART protocol to ESP32-C3.
 * Frame: [0xAA][len_lo][len_hi][cmd][payload...][crc8]
 */
#include "esp32_link.h"
#include "tga.h"
#include <stdio.h>

extern UART_HandleTypeDef huart1;

#define RX_BUF 128
static uint8_t rxb[RX_BUF]; static uint16_t rx_len=0;
static uint8_t cmd_buf[64]; static uint16_t cmd_avail=0;

void esp32_link_init(void) {
    HAL_UART_Receive_IT(&huart1, rxb, 1);
}

static uint8_t crc8(const uint8_t* d, int n) {
    uint8_t c=0; for (int i=0;i<n;i++) c ^= d[i];
    return c;
}
static void send_frame(uint8_t cmd, const uint8_t* p, uint16_t n) {
    uint8_t hdr[4] = {0xAA, n&0xFF, (n>>8)&0xFF, cmd};
    uint8_t buf[140];
    memcpy(buf, hdr, 4);
    if (n) memcpy(buf+4, p, n);
    buf[4+n] = crc8(buf, 4+n);
    HAL_UART_Transmit(&huart1, buf, 5+n, 200);
}

void esp32_send_point(float temp_c,float mass_mg,float mass_pct,float dtg,uint32_t t_ms){
    uint8_t b[20];
    memcpy(b+0,&t_ms,4);
    memcpy(b+4,&temp_c,4);
    memcpy(b+8,&mass_mg,4);
    memcpy(b+12,&mass_pct,4);
    memcpy(b+16,&dtg,4);
    send_frame(0x01, b, 20);
}
void esp32_send_status(const pb_status_t* s) { send_frame(0x02, (uint8_t*)s, sizeof(*s)); }
void esp32_send_log(const char* msg){ send_frame(0x03, (uint8_t*)msg, strlen(msg)); }

void esp32_send_result(const tga_run_t* run){
    /* send compact result: step_count + steps + residual */
    uint8_t b[2 + TGA_MAX_STEPS*sizeof(tga_step_t) + 4];
    b[0] = run->step_count;
    b[1] = 0;
    memcpy(b+2, run->steps, run->step_count*sizeof(tga_step_t));
    memcpy(b+2+run->step_count*sizeof(tga_step_t), &run->residual_pct, 4);
    send_frame(0x04, b, 2 + run->step_count*sizeof(tga_step_t) + 4);
}

void esp32_link_poll(void) { /* IT-driven; nothing here */ }

bool esp32_cmd_pending(void) { return cmd_avail > 0; }
int esp32_get_cmd(uint8_t* buf, uint16_t len) {
    if (!cmd_avail) return 0;
    int n = (len < cmd_avail) ? len : cmd_avail;
    memcpy(buf, cmd_buf, n); cmd_avail = 0;
    return n;
}

/* UART RX callback (IT mode) */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef* h) {
    if (h->Instance == huart1.Instance) {
        /* simplistic: accumulate into cmd_buf */
        if (rx_len < RX_BUF) {
            uint8_t b = rxb[0];
            if (b == 0xAA || rx_len) {
                cmd_buf[rx_len++] = b;
                if (rx_len >= 4 && rx_len >= (cmd_buf[1] | (cmd_buf[2]<<8)) + 5) {
                    cmd_avail = rx_len; rx_len = 0;
                }
            }
        } else rx_len = 0;
        HAL_UART_Receive_IT(&huart1, rxb, 1);
    }
}