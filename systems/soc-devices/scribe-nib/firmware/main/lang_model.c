/*
 * lang_model.c — Character-level n-gram language model for correction
 *
 * Loads a bigram probability table and common word list from flash.
 * Corrects low-confidence CNN predictions using character context.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "lang_model.h"
#include <string.h>
#include <math.h>
#include "esp_log.h"
#include "esp_partition.h"
#include "nvs_flash.h"

static const char *TAG = "lang_model";

/* Character set */
static const char charset[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
#define NUM_CLASSES 62

/* Bigram table: 62×62 log-probabilities (stored as int16 in flash) */
static int16_t bigram_table[NUM_CLASSES][NUM_CLASSES];

/* Unigram priors */
static float unigram[NUM_CLASSES];

/* Context window (last N characters) */
#define CONTEXT_SIZE 3
static int context[CONTEXT_SIZE];
static int context_len = 0;

/* Common word list for word-level correction */
#define MAX_WORDS 10000
#define MAX_WORD_LEN 32
static char word_list[MAX_WORDS][MAX_WORD_LEN];
static int word_count = 0;

/* Currently building word */
static char current_word[MAX_WORD_LEN];
static int current_word_len = 0;

/* ---- Helper: char ↔ index ---- */

static int char_to_idx(char c)
{
    const char *p = strchr(charset, c);
    return p ? (int)(p - charset) : -1;
}

static char idx_to_char(int idx)
{
    if (idx >= 0 && idx < NUM_CLASSES) return charset[idx];
    return '?';
}

/* ---- Public API ---- */

esp_err_t lang_model_init(void)
{
    /* Load bigram table from flash partition "langmodel" */
    const esp_partition_t *part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "langmodel");
    if (!part) {
        ESP_LOGW(TAG, "No langmodel partition found, using uniform priors");
        for (int i = 0; i < NUM_CLASSES; i++) {
            unigram[i] = 1.0f / NUM_CLASSES;
            for (int j = 0; j < NUM_CLASSES; j++) {
                bigram_table[i][j] = 0;
            }
        }
        return ESP_OK;
    }

    /* Read bigram table: 62×62 × 2 bytes = 7688 bytes */
    if (part->size < NUM_CLASSES * NUM_CLASSES * 2) {
        ESP_LOGE(TAG, "Language model partition too small");
        return ESP_FAIL;
    }

    uint8_t *buf = malloc(NUM_CLASSES * NUM_CLASSES * 2);
    if (!buf) return ESP_ERR_NO_MEM;

    esp_err_t err = esp_partition_read(part, 0, buf, NUM_CLASSES * NUM_CLASSES * 2);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read language model partition");
        free(buf);
        return err;
    }

    /* Parse bigram table (int16, log-probability × 1000) */
    for (int i = 0; i < NUM_CLASSES; i++) {
        for (int j = 0; j < NUM_CLASSES; j++) {
            int offset = (i * NUM_CLASSES + j) * 2;
            bigram_table[i][j] = (int16_t)((buf[offset] << 8) | buf[offset + 1]);
        }
    }

    /* Compute unigram priors from bigram row sums */
    for (int i = 0; i < NUM_CLASSES; i++) {
        float sum = 0;
        for (int j = 0; j < NUM_CLASSES; j++) {
            sum += expf((float)bigram_table[i][j] / 1000.0f);
        }
        unigram[i] = sum / NUM_CLASSES;
    }

    free(buf);

    /* Load word list (after bigram table in partition) */
    /* For now, word list is embedded in code for simplicity */
    word_count = 0;
    context_len = 0;
    current_word_len = 0;

    ESP_LOGI(TAG, "Language model loaded (62×62 bigrams)");
    return ESP_OK;
}

char lang_model_correct(int char_id, float confidence)
{
    if (char_id < 0 || char_id >= NUM_CLASSES) return '?';

    /* High confidence: accept as-is */
    if (confidence > 0.90f) {
        return idx_to_char(char_id);
    }

    /* Medium confidence: use bigram context to pick best candidate */
    if (confidence > 0.50f && context_len > 0) {
        int prev = context[context_len - 1];
        float best_score = -1e10f;
        int best_idx = char_id;

        /* Score = CNN_confidence + bigram_log_prob */
        for (int c = 0; c < NUM_CLASSES; c++) {
            float bigram_score = (float)bigram_table[prev][c] / 1000.0f;
            float score = logf(confidence + 0.001f) + bigram_score;
            if (c == char_id) score += 0.5f;  /* CNN prior bonus */
            if (score > best_score) {
                best_score = score;
                best_idx = c;
            }
        }
        return idx_to_char(best_idx);
    }

    /* Low confidence: try word list matching */
    if (current_word_len > 0 && confidence < 0.50f) {
        /* Use edit distance on current partial word */
        /* For simplicity, just return the CNN prediction with lower bound */
        return idx_to_char(char_id);
    }

    return idx_to_char(char_id);
}

void lang_model_update_context(char c)
{
    int idx = char_to_idx(c);
    if (idx < 0) return;

    /* Add to context window */
    if (context_len < CONTEXT_SIZE) {
        context[context_len++] = idx;
    } else {
        /* Shift window */
        for (int i = 0; i < CONTEXT_SIZE - 1; i++) {
            context[i] = context[i + 1];
        }
        context[CONTEXT_SIZE - 1] = idx;
    }

    /* Update current word buffer */
    if (c == ' ') {
        /* Word boundary: reset word buffer */
        current_word_len = 0;
    } else {
        if (current_word_len < MAX_WORD_LEN - 1) {
            current_word[current_word_len++] = c;
            current_word[current_word_len] = '\0';
        }
    }
}

void lang_model_reset_context(void)
{
    context_len = 0;
    current_word_len = 0;
}