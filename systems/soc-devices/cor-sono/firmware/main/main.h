/*
 * cor-sono / firmware / main.h
 * Pocket Smart Stethoscope — main header
 * ESP32-S3-WROOM-1, ESP-IDF v5.2+
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define SAMPLE_RATE       4000   /* Hz, both channels */
#define BLOCK_SAMPLES     80     /* 20 ms at 4 kHz */
#define BLOCK_BYTES       (BLOCK_SAMPLES * 2 * sizeof(int16_t))  /* stereo int16 */
#define AUDIO_RING_MS     2000   /* 2 s ring buffer */
#define AUDIO_RING_LEN    ((SAMPLE_RATE * AUDIO_RING_MS / 1000))

#define N_CLASSES         8
#define CLASS_CONF_THRESH 60     /* % */

/* Measurement modes */
typedef enum {
    MODE_HEART = 0,
    MODE_LUNG,
    MODE_MIXED
} corsono_mode_t;

/* Device state machine */
typedef enum {
    ST_IDLE = 0,
    ST_ARMING,
    ST_LISTEN,
    ST_RECORD,
    ST_RESULT
} corsono_state_t;

/* Classification labels (must match training) */
typedef enum {
    CL_NORMAL = 0,
    CL_S3,
    CL_S4,
    CL_SYS_MURMUR,
    CL_DIA_MURMUR,
    CL_CRACKLES,
    CL_WHEEZE,
    CL_RUB
} class_id_t;

extern const char *const CLASS_NAMES[N_CLASSES];

/* System context shared across modules */
typedef struct {
    corsono_state_t state;
    corsono_mode_t  mode;
    int             volume_db;      /* 0–30 */
    int             heart_rate;     /* BPM */
    int             class_id;
    int             confidence;     /* 0–100 */
    int             battery_pct;
    bool            charging;
    bool            sd_present;
} corsono_ctx_t;

extern corsono_ctx_t g_ctx;

/* Module inits */
void audio_init(void);
void anc_init(void);
void pcg_init(void);
void classifier_init(void);
void oled_init(void);
void sd_logger_init(void);
void ble_stream_init(void);
void wifi_web_init(void);
void buttons_init(void);

/* Module tasks */
void audio_task(void *arg);
void pcg_task(void *arg);

/* Utility */
uint64_t millis(void);
int clampi(int v, int lo, int hi);