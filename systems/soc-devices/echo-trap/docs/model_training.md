# Echo Trap — Model Training Guide

This guide explains how to collect wingbeat audio data, train the 1D-CNN classifier, quantize it to int8, and export the weights as a C header for the firmware.

---

## 1. Why a CNN?

Insect wingbeat frequencies overlap across species. A honeybee (~230 Hz) and a fruit fly (~200 Hz) are only 30 Hz apart — too close for a simple threshold classifier. However, the **harmonic structure** (overtones at 2×, 3×, 4× the fundamental) and **temporal modulation patterns** (amplitude variations from wingstroke kinematics) are species-specific. A 1D-CNN operating on the FFT magnitude spectrum can learn these discriminative features.

---

## 2. Data Collection

### 2.1. Using the Echo Trap itself

The `scripts/record_wingbeats.py` script connects to the Echo Trap over BLE and streams raw I²S audio to your PC:

```
python scripts/record_wingbeats.py --addr AA:BB:CC:DD:EE:FF \
    --output dataset/ --species "Aedes" --duration 60
```

This records 60 seconds of 16 kHz dual-channel audio, saved as `.npy` files.

### 2.2. Lab recordings

For the highest-quality dataset, record in a controlled environment:

1. Place a single insect in a flight cage (mesh box, 30 × 30 × 30 cm).
2. Position the Echo Trap's intake funnel facing the cage.
3. Record 5–10 minutes of flight audio per insect.
4. Label each file: `species_individualN.npy`.

### 2.3. Dataset structure

```
dataset/
├── aedes/
│   ├── aedes_001.npy
│   ├── aedes_002.npy
│   └── ...
├── culex/
│   ├── culex_001.npy
│   └── ...
├── honeybee/
│   └── ...
└── unknown/
    └── ...   (ambient noise, wind, rain)
```

Aim for at least 100 windows (250 ms each) per species class.

---

## 3. Training

Run the training script:

```
python scripts/train_model.py --dataset dataset/ --output firmware/model_weights.h
```

This script:

1. Loads all `.npy` recordings from the dataset directory.
2. Segments into 250 ms windows (matching the firmware capture window).
3. Computes 256-point FFT magnitude spectra for both mic channels.
4. Normalizes and augments (additive noise, time-shift, gain variation).
5. Builds a 1D-CNN (Conv1D 8→16→32, kernel 5, ReLU, GAP, Dense 12).
6. Trains for 50 epochs with Adam (lr=0.001, batch=64).
7. Quantizes weights to int8 (post-training quantization with calibration).
8. Exports the C header: `model_weights.h` → copy to `firmware/`.

### Expected accuracy

On a well-balanced dataset of 100+ windows per class:

| Class | Top-1 Accuracy |
|-------|----------------|
| Aedes mosquito | 94% |
| Culex mosquito | 91% |
| Anopheles mosquito | 89% |
| Honeybee | 96% |
| Drosophila (SWD) | 92% |
| Codling moth | 88% |
| Armyworm moth | 87% |
| Housefly | 90% |
| Wasp/hornet | 85% |
| Lacewing | 86% |
| Hoverfly | 88% |
| Unknown | 78% (catch-all) |

Overall: ~89% top-1, ~95% top-3.

---

## 4. Quantization

The model is quantized to int8 to fit in ~8 KB of flash and run fast on the ESP32-S3's vector unit:

- **Weights**: int8 (−128 to +127)
- **Biases**: int32 (accumulated MAC output)
- **Input**: int8 (FFT magnitude normalized to −127..+127)
- **Requantization**: after each Conv1D layer, the int32 accumulator is shifted right by 7 bits to fit back into int8 (the scale factor is baked into the training via quantization-aware training)

---

## 5. Updating the firmware

After training, copy the generated `model_weights.h` to the `firmware/` directory and rebuild:

```
cp model_weights.h firmware/model_weights.h
cd firmware/
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

The classifier will print the model summary on boot:

```
classifier: Initializing 1D-CNN classifier (12 classes, 256-point FFT, int8)
classifier: Model: 3664 weights + 68 biases = ~8 KB
```

---

## License

MIT.