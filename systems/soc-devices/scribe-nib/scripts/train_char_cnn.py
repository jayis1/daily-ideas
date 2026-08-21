#!/usr/bin/env python3
"""
train_char_cnn.py — Train the 62-class character recognition CNN for Scribe Nib

Uses IAM Online Handwriting Database or custom samples to train
a depthwise-separable CNN that runs on ESP32-S3 in ~4ms.

Output: quantized INT8 TFLite model (~92KB)

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import os
import sys
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser(description="Train Scribe Nib character CNN")
    parser.add_argument("--data", required=True, help="Path to training data directory")
    parser.add_argument("--output", default="model/char_cnn.tflite", help="Output TFLite model path")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--quantize", choices=["int8", "float16", "none"], default="int8")
    parser.add_argument("--augment", action="store_true", help="Enable data augmentation")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    return parser.parse_args()


def load_data(data_dir):
    """Load handwriting samples from directory.

    Expected structure:
        data_dir/
        ├── 0/  (digit samples as .npy or .png)
        ├── 1/
        ├── ...
        ├── A/
        ├── B/
        ├── ...
        ├── a/
        ├── b/
        └── ...

    Each sample should be a 32×32 grayscale image.
    """
    import tensorflow as tf

    charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    images = []
    labels = []

    for class_idx, char in enumerate(charset):
        char_dir = os.path.join(data_dir, char)
        if not os.path.isdir(char_dir):
            print(f"Warning: missing directory for '{char}'")
            continue

        for fname in os.listdir(char_dir):
            fpath = os.path.join(char_dir, fname)
            if fname.endswith('.npy'):
                img = np.load(fpath)
            elif fname.endswith('.png') or fname.endswith('.jpg'):
                img = tf.keras.preprocessing.image.load_img(
                    fpath, color_mode='grayscale', target_size=(32, 32))
                img = np.array(img)
            else:
                continue

            # Ensure 32×32 grayscale
            if img.shape != (32, 32):
                img = tf.image.resize(img[..., np.newaxis], (32, 32)).numpy().squeeze()
            if img.ndim == 3:
                img = img.squeeze()

            images.append(img.astype(np.float32) / 255.0)
            labels.append(class_idx)

    images = np.array(images, dtype=np.float32)[..., np.newaxis]  # Add channel dim
    labels = np.array(labels, dtype=np.int32)

    print(f"Loaded {len(images)} samples across {len(set(labels))} classes")
    return images, labels


def build_model():
    """Build the depthwise-separable CNN for 62-class character recognition.

    Architecture:
        Input (32×32×1)
        → Conv2D(3×3, 32) + BN + ReLU
        → DepthwiseConv2D(3×3, stride=2) + BN + ReLU    → 16×16×32
        → Conv2D(1×1, 64) + BN + ReLU                    → 16×16×64
        → DepthwiseConv2D(3×3, stride=2) + BN + ReLU    → 8×8×64
        → Conv2D(1×1, 128) + BN + ReLU                   → 8×8×128
        → GlobalAvgPool                                    → 128
        → Dense(128, ReLU)
        → Dense(62, Softmax)
    """
    import tensorflow as tf

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(32, 32, 1)),

        # Block 1
        tf.keras.layers.Conv2D(32, (3, 3), padding='same', use_bias=False),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.ReLU(),

        tf.keras.layers.DepthwiseConv2D((3, 3), strides=2, padding='same', use_bias=False),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.ReLU(),

        # Block 2 (pointwise expansion)
        tf.keras.layers.Conv2D(64, (1, 1), padding='same', use_bias=False),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.ReLU(),

        tf.keras.layers.DepthwiseConv2D((3, 3), strides=2, padding='same', use_bias=False),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.ReLU(),

        # Block 3 (pointwise expansion)
        tf.keras.layers.Conv2D(128, (1, 1), padding='same', use_bias=False),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.ReLU(),

        # Classifier
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(62, activation='softmax'),
    ])

    return model


def augment_data(images, labels):
    """Apply data augmentation: rotation, scaling, translation."""
    import tensorflow as tf

    datagen = tf.keras.preprocessing.image.ImageDataGenerator(
        rotation_range=15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        shear_range=5,
        fill_mode='constant',
        cval=0.0,
    )
    return datagen, images, labels


def quantize_model(model, representative_dataset, output_path):
    """Convert to INT8 quantized TFLite model."""
    import tensorflow as tf

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"Quantized INT8 model saved to {output_path} ({size_kb:.1f} KB)")
    return tflite_model


def representative_data_gen(images, num_samples=500):
    """Generate representative dataset for INT8 quantization calibration."""
    indices = np.random.choice(len(images), min(num_samples, len(images)), replace=False)
    for idx in indices:
        img = images[idx]
        # Scale to INT8 range [-128, 127]
        img_scaled = (img * 255.0 - 128.0).astype(np.float32)
        yield [img_scaled[np.newaxis, ...]]


def main():
    args = parse_args()

    try:
        import tensorflow as tf
    except ImportError:
        print("Error: TensorFlow is required. Install with: pip install tensorflow")
        sys.exit(1)

    print(f"TensorFlow version: {tf.__version__}")
    print(f"GPU available: {tf.config.list_physical_devices('GPU')}")

    # Load data
    images, labels = load_data(args.data)

    # Split into train/val
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        images, labels, test_size=0.15, random_state=42, stratify=labels)

    # Build model
    model = build_model()
    model.summary()

    # Compile
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=args.lr),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # Callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3),
        tf.keras.callbacks.ModelCheckpoint('model/best.h5', save_best_only=True),
    ]

    # Train
    if args.augment:
        datagen, X_train, y_train = augment_data(X_train, y_train)
        model.fit(
            datagen.flow(X_train, y_train, batch_size=args.batch_size),
            epochs=args.epochs,
            validation_data=(X_val, y_val),
            callbacks=callbacks,
        )
    else:
        model.fit(
            X_train, y_train,
            batch_size=args.batch_size,
            epochs=args.epochs,
            validation_data=(X_val, y_val),
            callbacks=callbacks,
        )

    # Evaluate
    val_loss, val_acc = model.evaluate(X_val, y_val)
    print(f"\nValidation accuracy: {val_acc:.4f}")

    # Quantize and save
    if args.quantize == "int8":
        rep_gen = lambda: representative_data_gen(X_train)
        quantize_model(model, rep_gen, args.output)
    elif args.quantize == "float16":
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
        tflite_model = converter.convert()
        with open(args.output, 'wb') as f:
            f.write(tflite_model)
        print(f"Float16 model saved to {args.output} ({len(tflite_model)/1024:.1f} KB)")
    else:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        tflite_model = converter.convert()
        with open(args.output, 'wb') as f:
            f.write(tflite_model)
        print(f"Float32 model saved to {args.output} ({len(tflite_model)/1024:.1f} KB)")

    print("\nDone! Copy the .tflite file to firmware/components/model/")


if __name__ == "__main__":
    main()