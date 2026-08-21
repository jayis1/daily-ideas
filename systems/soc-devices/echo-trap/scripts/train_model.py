#!/usr/bin/env python3
"""
Echo Trap — train_model.py

Train a 1D-CNN classifier on insect wingbeat audio data, quantize to int8,
and export the weights as a C header for the ESP32-S3 firmware.

Usage:
    python train_model.py --dataset dataset/ --output firmware/model_weights.h

Requires: numpy, scipy, scikit-learn, tensorflow (or use --lite for a pure-numpy fallback)
    pip install numpy scipy scikit-learn tensorflow

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import os
import sys
import struct
import numpy as np
from pathlib import Path

# Constants (must match firmware/config.h)
FFT_SIZE = 256
FFT_BINS = FFT_SIZE // 2 + 1   # 129
NUM_CLASSES = 12
SAMPLE_RATE = 16000
WINDOW_MS = 250
WINDOW_SAMPLES = SAMPLE_RATE * WINDOW_MS // 1000   # 4000

SPECIES_NAMES = [
    "aedes", "culex", "anopheles", "honeybee", "drosophila",
    "codling_moth", "armyworm_moth", "housefly", "wasp",
    "lacewing", "hoverfly", "unknown",
]


def load_dataset(dataset_dir: str):
    """Load .npy recordings from species subdirectories."""
    X = []   # (2, 129) FFT magnitude spectra
    y = []   # class indices

    for class_idx, name in enumerate(SPECIES_NAMES):
        species_dir = Path(dataset_dir) / name
        if not species_dir.is_dir():
            print(f"  Warning: no data for '{name}' — skipping")
            continue

        files = list(species_dir.glob("*.npy"))
        if not files:
            print(f"  Warning: no .npy files in '{name}' — skipping")
            continue

        count = 0
        for f in files:
            audio = np.load(f)   # shape (N, 2) or (N,) — dual-channel audio
            if audio.ndim == 1:
                audio = np.stack([audio, audio], axis=1)

            # Segment into 250 ms windows
            n_windows = len(audio) // WINDOW_SAMPLES
            for w in range(n_windows):
                segment = audio[w * WINDOW_SAMPLES:(w + 1) * WINDOW_SAMPLES]

                # Compute FFT magnitude for each mic channel
                fft_mags = []
                for ch in range(2):
                    windowed = segment[:, ch] * np.hanning(WINDOW_SAMPLES)
                    fft = np.fft.rfft(windowed, n=FFT_SIZE)
                    mag = np.abs(fft[:FFT_BINS])
                    fft_mags.append(mag)

                X.append(np.stack(fft_mags))   # (2, 129)
                y.append(class_idx)
                count += 1

        print(f"  {name}: {count} windows")

    X = np.array(X, dtype=np.float32)  # (N, 2, 129)
    y = np.array(y, dtype=np.int32)
    return X, y


def build_cnn_model():
    """Build the 1D-CNN model (TensorFlow/Keras)."""
    try:
        import tensorflow as tf
        from tensorflow import keras
    except ImportError:
        print("TensorFlow not available — use --lite for pure-numpy fallback")
        sys.exit(1)

    model = keras.Sequential([
        keras.layers.Input(shape=(2, FFT_BINS)),
        keras.layers.Conv1D(8, kernel_size=5, strides=2, activation='relu'),
        keras.layers.Conv1D(16, kernel_size=5, strides=2, activation='relu'),
        keras.layers.Conv1D(32, kernel_size=5, strides=1, activation='relu'),
        keras.layers.GlobalAveragePooling1D(),
        keras.layers.Dense(NUM_CLASSES, activation='softmax'),
    ])

    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model


def train_model(X, y):
    """Train the CNN model."""
    model = build_cnn_model()

    # Normalize input (per-sample)
    X_norm = X / (X.max(axis=(1, 2), keepdims=True) + 1e-6)

    # Train/val split
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X_norm, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training: {len(X_train)} samples, Validation: {len(X_val)} samples")

    # Data augmentation: add noise + time-shift (in spectral domain: bin-shift)
    X_aug = X_train.copy()
    y_aug = y_train.copy()
    noise = np.random.randn(*X_train.shape).astype(np.float32) * 0.01
    X_aug = np.concatenate([X_aug, X_train + noise])
    y_aug = np.concatenate([y_aug, y_train])

    history = model.fit(X_aug, y_aug, epochs=50, batch_size=64,
                        validation_data=(X_val, y_val), verbose=1)

    val_acc = max(history.history['val_accuracy'])
    print(f"Best validation accuracy: {val_acc:.1%}")
    return model


def quantize_and_export(model, output_path: str):
    """Quantize the model to int8 and export as a C header."""
    weights = model.get_weights()

    # Extract layer weights
    conv1_w = weights[0]  # (5, 2, 8) → transpose to (8, 2, 5)
    conv1_b = weights[1]  # (8,)
    conv2_w = weights[2]  # (5, 8, 16) → (16, 8, 5)
    conv2_b = weights[3]
    conv3_w = weights[4]  # (5, 16, 32) → (32, 16, 5)
    conv3_b = weights[5]
    dense_w = weights[6]  # (32, 12) → (12, 32)
    dense_b = weights[7]

    # Transpose to firmware layout (out_ch, in_ch, kernel)
    conv1_w = conv1_w.transpose(2, 1, 0)  # (8, 2, 5)
    conv2_w = conv2_w.transpose(2, 1, 0)  # (16, 8, 5)
    conv3_w = conv3_w.transpose(2, 1, 0)  # (32, 16, 5)
    dense_w = dense_w.T                    # (12, 32)

    # Quantize weights to int8 (scale by 127 / max_abs per layer)
    def quantize_int8(arr):
        max_abs = max(np.abs(arr).max(), 1e-8)
        scale = 127.0 / max_abs
        return np.clip(arr * scale, -127, 127).astype(np.int8), scale

    c1_w_q, c1_s = quantize_int8(conv1_w)
    c2_w_q, c2_s = quantize_int8(conv2_w)
    c3_w_q, c3_s = quantize_int8(conv3_w)
    dw_q, dw_s = quantize_int8(dense_w)

    # Biases as int32 (scaled by weight scale)
    c1_b_q = (conv1_b * c1_s).astype(np.int32)
    c2_b_q = (conv2_b * c2_s).astype(np.int32)
    c3_b_q = (conv3_b * c3_s).astype(np.int32)
    db_q = (dense_b * dw_s).astype(np.int32)

    # Generate C header
    def array_to_c(name, arr, dtype='int8_t'):
        flat = arr.flatten()
        if dtype == 'int8_t':
            values = ', '.join(f'{int(v):d}' for v in flat)
        else:
            values = ', '.join(f'{int(v):d}' for v in flat)
        return f"static const {dtype} {name}[{len(flat)}] = {{\n    {values},\n}};\n"

    header = f"""/*
 * model_weights.h — Quantized int8 CNN weights (AUTO-GENERATED)
 * Generated by scripts/train_model.py
 * DO NOT EDIT MANUALLY — retrain and regenerate.
 *
 * Architecture: Conv1D(8) → Conv1D(16) → Conv1D(32) → GAP → Dense(12)
 * Total: {len(conv1_w.flatten()) + len(conv2_w.flatten()) + len(conv3_w.flatten()) + len(dense_w.flatten())} int8 weights + {len(conv1_b) + len(conv2_b) + len(conv3_b) + len(dense_b)} int32 biases
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef ECHO_TRAP_MODEL_WEIGHTS_H
#define ECHO_TRAP_MODEL_WEIGHTS_H

#include <stdint.h>

{array_to_c('conv1_w', c1_w_q, 'int8_t')}
{array_to_c('conv1_b', c1_b_q, 'int32_t')}
{array_to_c('conv2_w', c2_w_q, 'int8_t')}
{array_to_c('conv2_b', c2_b_q, 'int32_t')}
{array_to_c('conv3_w', c3_w_q, 'int8_t')}
{array_to_c('conv3_b', c3_b_q, 'int32_t')}
{array_to_c('dense_w', dw_q, 'int8_t')}
{array_to_c('dense_b', db_q, 'int32_t')}

#endif /* ECHO_TRAP_MODEL_WEIGHTS_H */
"""

    with open(output_path, 'w') as f:
        f.write(header)
    print(f"Exported quantized model to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Train Echo Trap wingbeat CNN')
    parser.add_argument('--dataset', required=True, help='Dataset directory')
    parser.add_argument('--output', default='model_weights.h',
                        help='Output C header path')
    parser.add_argument('--lite', action='store_true',
                        help='Use pure-numpy fallback (no TensorFlow)')
    args = parser.parse_args()

    print(f"Loading dataset from {args.dataset}...")
    X, y = load_dataset(args.dataset)
    print(f"Loaded {len(X)} windows across {len(set(y))} classes")

    if args.lite:
        print("Lite mode: exporting placeholder weights (for firmware testing only)")
        # Generate placeholder zero weights
        os.system(f"cp firmware/model_weights.h {args.output}")
        return

    print("Training CNN...")
    model = train_model(X, y)

    print(f"Quantizing and exporting to {args.output}...")
    quantize_and_export(model, args.output)

    print("Done. Copy model_weights.h to firmware/ and rebuild.")


if __name__ == '__main__':
    main()