/* nvs_flash.h — stub for host simulation */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef int nvs_handle_t;
typedef int esp_err_t;
#define ESP_OK          0
#define ESP_FAIL        -1
#define ESP_ERR_NVS_NOT_FOUND  0x1042
#define ESP_ERR_NVS_NO_FREE_PAGES 0x1045
#define ESP_ERR_NVS_NEW_VERSION_FOUND 0x1046

#define NVS_READWRITE 1

static inline esp_err_t nvs_flash_init(void) { return ESP_OK; }
static inline esp_err_t nvs_flash_erase(void) { return ESP_OK; }
static inline esp_err_t nvs_open(const char *ns, int mode, nvs_handle_t *h) {
    (void)ns; (void)mode; *h = 1; return ESP_OK;
}
static inline void nvs_close(nvs_handle_t h) { (void)h; }
static inline esp_err_t nvs_get_blob(nvs_handle_t h, const char *key, void *out, size_t *len) {
    (void)h; (void)key; (void)out; (void)len; return ESP_ERR_NVS_NOT_FOUND;
}
static inline esp_err_t nvs_set_blob(nvs_handle_t h, const char *key, const void *val, size_t len) {
    (void)h; (void)key; (void)val; (void)len; return ESP_OK;
}
static inline esp_err_t nvs_commit(nvs_handle_t h) { (void)h; return ESP_OK; }