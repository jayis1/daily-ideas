/* stubs/esp_log.h — stub for host simulation */
#ifndef ESP_LOG_H
#define ESP_LOG_H
#include <stdio.h>
#define ESP_LOGI(tag, fmt, ...)  fprintf(stderr, "[I][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define ESP_LOGE(tag, fmt, ...)  fprintf(stderr, "[E][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define ESP_LOGD(tag, fmt, ...)  ((void)0)
#define ESP_ERROR_CHECK(x)       do { if ((x) != 0) { fprintf(stderr, "err\n"); } } while (0)
#endif