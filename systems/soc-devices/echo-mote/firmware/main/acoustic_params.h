/**
 * acoustic_params.h — Room acoustic parameter computation
 *
 * Computes RT60, C50, C80, D50, and frequency response from
 * an impulse response and octave-band filtered versions.
 */

#ifndef ACOUSTIC_PARAMS_H
#define ACOUSTIC_PARAMS_H

#include <stdint.h>

/* Octave band center frequencies */
#define NUM_OCTAVE_BANDS 6
#define OCTAVE_CENTERS  { 125, 250, 500, 1000, 2000, 4000 }

/* Maximum room modes detectable */
#define MAX_ROOM_MODES 8

/* Acoustic results structure */
typedef struct {
    /* RT60 per octave band (seconds) */
    float rt60[NUM_OCTAVE_BANDS];

    /* RT20, RT30 per octave band (seconds) */
    float rt20[NUM_OCTAVE_BANDS];
    float rt30[NUM_OCTAVE_BANDS];

    /* Broadband RT60 */
    float rt60_broadband;

    /* Clarity indices per octave band (dB) */
    float c50[NUM_OCTAVE_BANDS];
    float c80[NUM_OCTAVE_BANDS];
    float d50[NUM_OCTAVE_BANDS];

    /* Frequency response (1/3 octave, 31 bands from 20 Hz to 20 kHz) */
    #define NUM_THIRD_OCT 31
    float freq_response_mag[NUM_THIRD_OCT];  /* dB */
    float freq_response_phase[NUM_THIRD_OCT]; /* degrees */

    /* Room modes */
    int num_modes;
    struct {
        float freq;       /* Hz */
        float decay_time; /* seconds */
        uint8_t type;     /* 0=axial, 1=tangential, 2=oblique */
    } room_modes[MAX_ROOM_MODES];

    /* Inter-aural cross-correlation */
    float iacc;

    /* NC curve (background noise) */
    #define NUM_NC_BANDS 16
    float nc_bands[NUM_NC_BANDS];  /* dB SPL per 1/3-octave */
    float nc_rating;                /* NC-XX rating */

    /* Metadata */
    float speed_of_sound;
    float temperature;
    float humidity;
} acoustic_results_t;

/**
 * Compute RT60 from impulse response using Schroeder backward integration.
 *
 * @param ir            Impulse response (float, normalized)
 * @param num_samples   Number of samples
 * @param sample_rate   Sample rate in Hz
 * @param speed_of_sound Speed of sound in m/s
 * @param results       Output: filled rt60, rt20, rt30 fields
 * @return 0 on success
 */
int acoustic_params_compute_rt60(const float *ir, uint32_t num_samples,
                                   uint32_t sample_rate,
                                   float speed_of_sound,
                                   acoustic_results_t *results);

/**
 * Compute frequency response from impulse response.
 *
 * @param ir            Impulse response (float, normalized)
 * @param num_samples   Number of samples
 * @param sample_rate   Sample rate in Hz
 * @param results       Output: filled freq_response fields
 * @return 0 on success
 */
int acoustic_params_compute_freq_response(const float *ir, uint32_t num_samples,
                                            uint32_t sample_rate,
                                            acoustic_results_t *results);

/**
 * Compute clarity indices (C50, C80, D50) from impulse response.
 *
 * @param ir            Impulse response (float, normalized)
 * @param num_samples   Number of samples
 * @param sample_rate   Sample rate in Hz
 * @param results       Output: filled c50, c80, d50 fields
 * @return 0 on success
 */
int acoustic_params_compute_clarity(const float *ir, uint32_t num_samples,
                                      uint32_t sample_rate,
                                      acoustic_results_t *results);

#endif /* ACOUSTIC_PARAMS_H */