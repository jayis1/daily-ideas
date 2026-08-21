/*
 * pyro-balance / Core/Inc/esp32_link.h
 */
#ifndef ESP32_LINK_H
#define ESP32_LINK_H
#include "main.h"
void esp32_link_init(void);
void esp32_link_poll(void);
void esp32_send_point(float temp_c, float mass_mg, float mass_pct, float dtg, uint32_t t_ms);
void esp32_send_result(const tga_run_t* run);
void esp32_send_status(const pb_status_t* s);
void esp32_send_log(const char* msg);
bool esp32_cmd_pending(void);
int  esp32_get_cmd(uint8_t* buf, uint16_t len);
#endif