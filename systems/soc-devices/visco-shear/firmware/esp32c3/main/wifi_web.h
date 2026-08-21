/*
 * visco-shear / firmware / esp32c3 / main / wifi_web.h
 */
#ifndef WIFI_WEB_H
#define WIFI_WEB_H

#include <stdint.h>
#include <stddef.h>

void wifi_web_init(void);
void wifi_web_push_data(const uint8_t *data, int len);

#endif