#!/usr/bin/env python3
"""
generate_chirp.py — Generate custom inverse chirp filter for Echo Mote.

Generates a logarithmic swept sine (forward chirp) and computes the
inverse filter for impulse response deconvolution. Outputs the inverse
chirp as a binary file that can be loaded by the firmware.

Usage:
    python3 generate_chirp.py --fmin 20 --fmax 20000 --duration 5 --sample-rate 48000
    python3 generate_chirp.py --output inverse_chirp.bin
"""

import argparse
import numpy as np
import struct


def generate_log_chirp(fmin, fmax, duration, sample_rate):
    """Generate a logarithmic swept sine (exponential chirp)."""
    t = np.arange(0, duration, 1.0 / sample_rate)
    ratio = fmax / fmin

    # Logarithmic frequency sweep
    phase = 2 * np.pi * fmin * duration / np.log(ratio) * (ratio ** (t / duration) - 1)
    chirp = np.sin(phase)

    # Apply fade-in (50 ms) and fade-out (20 ms)
    fade_in_samples = int(sample_rate * 0.05)
    fade_out_samples = int(sample_rate * 0.02)

    fade_in = np.linspace(0, 1, fade_in_samples)
    fade_out = np.linspace(1, 0, fade_out_samples)

    chirp[:fade_in_samples] *= fade_in
    chirp[-fade_out_samples:] *= fade_out

    return chirp


def compute_inverse_filter(forward_chirp, sample_rate):
    """Compute the inverse filter for impulse response deconvolution."""
    # Zero-pad to next power of 2
    n = len(forward_chirp)
    fft_len = 1
    while fft_len < n:
        fft_len <<= 1

    # Forward FFT
    X = np.fft.fft(forward_chirp, fft_len)

    # Inverse filter: 1 / X with regularization
    eps = 1e-6
    H_inv = np.conj(X) / (np.abs(X) ** 2 + eps)

    # Inverse FFT to get time-domain inverse filter
    inv_filter = np.real(np.fft.ifft(H_inv))

    # Time-reverse (required for proper convolution)
    inv_filter = inv_filter[::-1]

    # Trim to original length
    inv_filter = inv_filter[:n]

    return inv_filter.astype(np.float32)


def main(args):
    print(f"Generating log chirp: {args.fmin}–{args.fmax} Hz, {args.duration}s @ {args.sample_rate} Hz")

    # Generate forward chirp
    forward = generate_log_chirp(args.fmin, args.fmax, args.duration, args.sample_rate)
    print(f"Forward chirp: {len(forward)} samples ({len(forward) / args.sample_rate:.2f} s)")

    # Compute inverse filter
    inverse = compute_inverse_filter(forward, args.sample_rate)
    print(f"Inverse filter: {len(inverse)} samples")

    # Save as binary float32
    output_file = args.output or "inverse_chirp.bin"
    with open(output_file, "wb") as f:
        f.write(inverse.tobytes())
    print(f"Saved inverse chirp to {output_file} ({len(inverse) * 4} bytes)")

    # Also save forward chirp as WAV (for verification)
    if args.save_forward:
        try:
            import wave
            wav_file = args.save_forward
            forward_int16 = (forward * 32767 * 0.25).astype(np.int16)  # -12 dBFS
            with wave.open(wav_file, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(args.sample_rate)
                wf.writeframes(forward_int16.tobytes())
            print(f"Saved forward chirp WAV to {wav_file}")
        except ImportError:
            print("wave module not available, skipping WAV export")

    # Print some stats
    print(f"\nChirp statistics:")
    print(f"  Peak amplitude: {np.max(np.abs(forward)):.4f}")
    print(f"  RMS amplitude:  {np.sqrt(np.mean(forward ** 2)):.4f}")
    print(f"  Inverse peak:   {np.max(np.abs(inverse)):.6f}")
    print(f"  Inverse RMS:    {np.sqrt(np.mean(inverse.astype(np.float64) ** 2)):.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Echo Mote inverse chirp filter")
    parser.add_argument("--fmin", type=float, default=20, help="Start frequency (Hz)")
    parser.add_argument("--fmax", type=float, default=20000, help="End frequency (Hz)")
    parser.add_argument("--duration", type=float, default=5.0, help="Chirp duration (seconds)")
    parser.add_argument("--sample-rate", type=int, default=48000, help="Sample rate (Hz)")
    parser.add_argument("--output", default=None, help="Output binary file path")
    parser.add_argument("--save-forward", default=None, help="Save forward chirp as WAV")
    args = parser.parse_args()
    main(args)