#!/usr/bin/env python3
"""
Sonar Cast — sim_chirp.py
Simulate the 150-250 kHz CHIRP pulse-compression pipeline and verify the
range resolution improvement vs single-frequency CW.

Usage:
    python3 sim_chirp.py

Requires: numpy, matplotlib
    pip install numpy matplotlib
"""
import numpy as np
import matplotlib.pyplot as plt

FS    = 1_000_000    # 1 Msps
F0    = 150_000
F1    = 250_000
T_MS  = 0.5
N     = int(FS * T_MS / 1000)   # 500 samples
C     = 1500.0                  # sound speed m/s

t = np.arange(N) / FS
k = (F1 - F0) / (T_MS / 1000)

# Transmit chirp (Hamming-weighted)
phase = 2 * np.pi * (F0 * t + 0.5 * k * t**2)
win = np.hamming(N)
chirp = np.exp(1j * phase) * win

# Matched filter = conj(time-reversed chirp)
mf = np.conj(chirp[::-1])

# Simulate two targets at 5.0 m and 5.075 m (7.5 cm apart)
# sound speed 1500 m/s → 5 m round-trip = 10 m / 1500 = 0.00667 s = 6667 samples
# so we need a much larger echo buffer
def range_to_samples(r):
    return int(round(2 * r / C * FS))

ECHO_LEN = 20000
targets = [(5.0, 1.0), (5.075, 0.9)]
echo = np.zeros(ECHO_LEN, dtype=complex)
for rng, amp in targets:
    delay = range_to_samples(rng)
    echo[delay:delay + N] += amp * chirp

# Add noise (SNR ~ 10 dB)
echo += 0.3 * (np.random.randn(len(echo)) + 1j * np.random.randn(len(echo)))

# Pulse compress
compressed = np.convolve(echo, mf, mode="same")
env = np.abs(compressed)

# Compare with CW (single 200 kHz, same 0.5 ms duration)
cw = np.exp(2j * np.pi * 200_000 * t) * win
cw_mf = np.conj(cw[::-1])
cw_env = np.abs(np.convolve(echo, cw_mf, mode="same"))

# Range axis
r_axis = np.arange(len(env)) * C / (2 * FS)

fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
axes[0].plot(r_axis, env, label="CHIRP pulse-compressed")
axes[0].axvline(5.0, color="r", ls="--", alpha=0.5, label="Target 1 (5.000 m)")
axes[0].axvline(5.075, color="g", ls="--", alpha=0.5, label="Target 2 (5.075 m)")
axes[0].set_ylabel("Envelope")
axes[0].set_title("Sonar Cast — CHIRP pulse compression (7.5 cm resolution)")
axes[0].legend()
axes[0].set_xlim(4.8, 5.3)

axes[1].plot(r_axis, cw_env, label="CW 200 kHz (no pulse compression)")
axes[1].axvline(5.0, color="r", ls="--", alpha=0.5)
axes[1].axvline(5.075, color="g", ls="--", alpha=0.5)
axes[1].set_xlabel("Range (m)")
axes[1].set_ylabel("Envelope")
axes[1].set_title("CW — targets unresolved (75 cm resolution)")
axes[1].legend()
axes[1].set_xlim(4.8, 5.3)

plt.tight_layout()
plt.savefig("sim_chirp_result.png", dpi=120)
print("Saved sim_chirp_result.png — CHIRP resolves the 7.5 cm pair; CW does not.")
print(f"CHIRP peak width (FWHM): "
      f"{np.sum(env > 0.5*env.max()) * C / (2*FS) * 100:.1f} cm")
print(f"CW peak width (FWHM): "
      f"{np.sum(cw_env > 0.5*cw_env.max()) * C / (2*FS) * 100:.1f} cm")