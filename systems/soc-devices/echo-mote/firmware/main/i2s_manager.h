/**
 * i2s_manager.h — Dual I²S bus manager for Echo Mote
 *
 * I²S0: Shared bus for speaker TX (MAX98357A) and left mic RX (ICS-43434)
 * I²S1: Right mic RX (ICS-43434)
 *
 * Provides DMA-based capture and playback with large PSRAM buffers.
 */

#ifndef I2S_MANAGER_H
#define I2S_MANAGER_H

#include <stdint.h>
#include <stddef.h>

/**
 * Initialize both I²S buses with default configuration.
 * I2S0: 48kHz, 16-bit, stereo (TX speaker, RX mic L)
 * I2S1: 48kHz, 16-bit, mono (RX mic R)
 */
int i2s_manager_init(void);

/**
 * Start capturing audio from both microphones.
 * Allocates DMA buffers in PSRAM.
 *
 * @param sample_rate  Sample rate in Hz (typically 48000)
 * @return 0 on success
 */
int i2s_manager_start_capture(uint32_t sample_rate);

/**
 * Stop capturing and retrieve recorded samples.
 * Caller must free the returned buffers.
 *
 * @param captured_l  Output: left channel samples (caller frees)
 * @param captured_r  Output: right channel samples (caller frees)
 * @param num_samples Output: number of samples per channel
 * @return 0 on success
 */
int i2s_manager_read_captured(int16_t *captured_l, int16_t *captured_r,
                                uint32_t num_samples);

/**
 * Write PCM data to the speaker (I2S0 TX).
 * Non-blocking; writes to DMA ring buffer.
 *
 * @param data   PCM int16 samples
 * @param len    Length in bytes
 * @return Number of bytes written
 */
int i2s_manager_write_speaker(const uint8_t *data, size_t len);

/**
 * Stop all I²S capture/playback and free DMA buffers.
 */
void i2s_manager_stop_capture(void);

#endif /* I2S_MANAGER_H */