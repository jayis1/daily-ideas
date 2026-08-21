/* library.c — Reference library management (NVS flash storage)
 *
 * The reference library is stored as a blob in NVS flash. It contains up to
 * LIBRARY_MAX_ENTRIES (50) entries, each with a label and 48-feature vector.
 *
 * NVS storage layout:
 *   Namespace: "taste_bead"
 *   Key "count": uint16_t — number of entries
 *   Key "entries": blob — array of library_entry_t
 */

#include "library.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include <string.h>

static const char *TAG = "library";

static library_entry_t g_entries[LIBRARY_MAX_ENTRIES];
static int g_count = 0;
static nvs_handle_t g_nvs_handle;

esp_err_t library_init(void)
{
    esp_err_t ret = nvs_open(LIBRARY_NVS_NAMESPACE, NVS_READWRITE, &g_nvs_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = library_load();
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "No existing library, starting empty");
        g_count = 0;
    }

    ESP_LOGI(TAG, "Library loaded: %d/%d entries", g_count, LIBRARY_MAX_ENTRIES);
    return ESP_OK;
}

int library_count(void)
{
    return g_count;
}

esp_err_t library_get(int index, library_entry_t *entry)
{
    if (index < 0 || index >= g_count) return ESP_ERR_INVALID_ARG;
    if (entry == NULL) return ESP_ERR_INVALID_ARG;
    memcpy(entry, &g_entries[index], sizeof(library_entry_t));
    return ESP_OK;
}

esp_err_t library_add(const char *label,
                       const float features[NUM_FEATURES],
                       int *out_index)
{
    if (label == NULL || features == NULL) return ESP_ERR_INVALID_ARG;
    if (g_count >= LIBRARY_MAX_ENTRIES) {
        ESP_LOGE(TAG, "Library full (%d entries)", LIBRARY_MAX_ENTRIES);
        return ESP_ERR_NO_MEM;
    }

    /* Check for duplicate label */
    int existing = library_find_by_label(label);
    if (existing >= 0) {
        ESP_LOGW(TAG, "Label '%s' already exists (index %d), updating", label, existing);
        library_update(existing, features);
        if (out_index) *out_index = existing;
        return library_save();
    }

    int idx = g_count;
    strncpy(g_entries[idx].label, label, LIBRARY_MAX_NAME_LEN - 1);
    g_entries[idx].label[LIBRARY_MAX_NAME_LEN - 1] = '\0';
    memcpy(g_entries[idx].features, features, sizeof(float) * NUM_FEATURES);
    g_entries[idx].timestamp_us = esp_timer_get_time();
    g_entries[idx].measurement_count = 1;
    g_count++;

    if (out_index) *out_index = idx;
    ESP_LOGI(TAG, "Added '%s' at index %d (total: %d)", label, idx, g_count);

    return library_save();
}

esp_err_t library_delete(int index)
{
    if (index < 0 || index >= g_count) return ESP_ERR_INVALID_ARG;

    /* Shift remaining entries down */
    for (int i = index; i < g_count - 1; i++) {
        memcpy(&g_entries[i], &g_entries[i + 1], sizeof(library_entry_t));
    }
    g_count--;
    memset(&g_entries[g_count], 0, sizeof(library_entry_t));

    ESP_LOGI(TAG, "Deleted index %d (total: %d)", index, g_count);
    return library_save();
}

esp_err_t library_clear(void)
{
    g_count = 0;
    memset(g_entries, 0, sizeof(g_entries));
    ESP_LOGI(TAG, "Library cleared");
    return library_save();
}

esp_err_t library_save(void)
{
    /* Save count */
    esp_err_t ret = nvs_set_u16(g_nvs_handle, "count", (uint16_t)g_count);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS set count failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Save entries as blob */
    size_t blob_size = g_count * sizeof(library_entry_t);
    if (blob_size > 0) {
        ret = nvs_set_blob(g_nvs_handle, "entries", g_entries, blob_size);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "NVS set blob failed: %s", esp_err_to_name(ret));
            return ret;
        }
    } else {
        /* Remove blob if library empty */
        nvs_erase_key(g_nvs_handle, "entries");
    }

    ret = nvs_commit(g_nvs_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS commit failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "Library saved (%d entries, %d bytes)", g_count, (int)blob_size);
    return ESP_OK;
}

esp_err_t library_load(void)
{
    /* Load count */
    uint16_t count = 0;
    esp_err_t ret = nvs_get_u16(g_nvs_handle, "count", &count);
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        g_count = 0;
        return ESP_ERR_NOT_FOUND;
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS get count failed: %s", esp_err_to_name(ret));
        return ret;
    }

    if (count > LIBRARY_MAX_ENTRIES) {
        ESP_LOGE(TAG, "Stored count %d exceeds max %d, truncating", count, LIBRARY_MAX_ENTRIES);
        count = LIBRARY_MAX_ENTRIES;
    }

    /* Load entries blob */
    size_t required_size = 0;
    ret = nvs_get_blob(g_nvs_handle, "entries", NULL, &required_size);
    if (ret == ESP_ERR_NVS_NOT_FOUND || required_size == 0) {
        g_count = 0;
        return ESP_OK;
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS get blob size failed: %s", esp_err_to_name(ret));
        return ret;
    }

    if (required_size != count * sizeof(library_entry_t)) {
        ESP_LOGW(TAG, "Blob size mismatch: %d != %d", (int)required_size,
                 (int)(count * sizeof(library_entry_t)));
    }

    ret = nvs_get_blob(g_nvs_handle, "entries", g_entries, &required_size);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS get blob failed: %s", esp_err_to_name(ret));
        return ret;
    }

    g_count = count;
    return ESP_OK;
}

int library_find_by_label(const char *label)
{
    if (label == NULL) return -1;
    for (int i = 0; i < g_count; i++) {
        if (strcmp(g_entries[i].label, label) == 0) return i;
    }
    return -1;
}

esp_err_t library_update(int index, const float features[NUM_FEATURES])
{
    if (index < 0 || index >= g_count) return ESP_ERR_INVALID_ARG;
    if (features == NULL) return ESP_ERR_INVALID_ARG;

    /* Running average: new = old × (n-1)/n + new × 1/n */
    int n = g_entries[index].measurement_count + 1;
    for (int i = 0; i < NUM_FEATURES; i++) {
        g_entries[index].features[i] =
            (g_entries[index].features[i] * (n - 1) + features[i]) / n;
    }
    g_entries[index].measurement_count = n;
    g_entries[index].timestamp_us = esp_timer_get_time();

    ESP_LOGI(TAG, "Updated '%s' (avg of %d measurements)",
             g_entries[index].label, n);
    return library_save();
}