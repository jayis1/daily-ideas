#!/usr/bin/env python3
"""
Lode Sweep — sim_decay.py
Simulate PI decay curves for different metals and verify the k-NN classifier.

Generates synthetic 16-gate decay curves for 8 metal classes with
physically realistic time constants, adds noise, and tests the k-NN
classifier accuracy.

Usage:
    python3 sim_decay.py

Requires: numpy, matplotlib
    pip install numpy matplotlib
"""
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

# 16 gate delays (µs) — log-spaced 10–284 µs
GATE_DELAY = np.array([
    10.0, 12.5, 15.6, 19.5, 24.4, 30.5, 38.1, 47.7,
    59.6, 74.5, 93.1, 116.4, 145.5, 181.9, 227.4, 284.2
])

# Class definitions: (name, τ_us, size_variations)
# τ values are spread widely across the 10–284 µs gate range to maximize
# k-NN separability. With 16× oversampling (16-bit effective resolution),
# the noise floor is very low (~0.5% of full scale).
# Iron has a characteristic double-decay (fast initial drop from
# ferromagnetic response + slower tail).
CLASSES = [
    ("Iron",       4,  [0.9, 1.0, 1.1]),
    ("Foil",      10,  [0.9, 1.0, 1.1]),
    ("Nickel",    17,  [0.9, 1.0, 1.1]),
    ("Pull-Tab",  25,  [0.9, 1.0, 1.1]),
    ("Zinc",      35,  [0.9, 1.0, 1.1]),
    ("Gold",      45,  [0.9, 1.0, 1.1]),
    ("Copper",    58,  [0.9, 1.0, 1.1]),
    ("Silver",    75,  [0.9, 1.0, 1.1]),
]

K = 5  # k-NN k value


def gen_decay_curve(tau, noise_amp=0.02):
    """Generate a normalized 16-gate decay curve for a given τ."""
    t = GATE_DELAY
    val = np.exp(-t / tau)
    # Iron has a double-decay component (very distinctive shape)
    if tau < 8:
        val += 0.5 * np.exp(-t / (tau * 0.2))
    # Add noise
    val += noise_amp * np.random.randn(len(t))
    # Clamp to a noise floor (negative noise creates artifacts after norm)
    val = np.maximum(val, 0.001)
    # Normalize to 0..1
    if val.max() > 0:
        val = val / val.max()
    return val


def extract_features(curve):
    """Extract a feature vector from a decay curve.

    Uses the 16 normalized gate values directly. With 16× oversampling
    (16-bit effective resolution), the SNR is high enough that the raw
    decay curve shape is a reliable fingerprint.
    """
    return curve.copy()


def build_template_library():
    """Build the 32-template reference library with feature vectors."""
    templates = []
    template_classes = []
    for ci, (name, tau, variations) in enumerate(CLASSES):
        for vi, sf in enumerate(variations):
            curve = gen_decay_curve(tau * sf, noise_amp=0.02 * (vi + 1))
            feat = extract_features(curve)
            templates.append(feat)
            template_classes.append(ci)
    return np.array(templates), np.array(template_classes)


def knn_classify(curve, templates, template_classes, k=K):
    """Classify a curve using k-NN (Euclidean distance on raw 16-gate curve)."""
    feat = extract_features(curve)
    dists = np.sqrt(np.sum((templates - feat) ** 2, axis=1))
    knn_idx = np.argsort(dists)[:k]
    votes = [template_classes[i] for i in knn_idx]
    majority = Counter(votes).most_common(1)[0]
    cls = majority[0]
    conf = majority[1] / k
    return cls, conf


def main():
    np.random.seed(42)
    templates, tclasses = build_template_library()
    class_names = [c[0] for c in CLASSES]

    # Plot template decay curves (regenerate raw curves for plotting)
    fig, axes = plt.subplots(2, 4, figsize=(14, 6), sharex=True, sharey=True)
    fig.suptitle("Lode Sweep — PI Decay Curves by Metal Class", fontsize=14)
    for ci, (name, tau, variations) in enumerate(CLASSES):
        ax = axes[ci // 4][ci % 4]
        for vi, sf in enumerate(variations):
            curve = gen_decay_curve(tau * sf, noise_amp=0.02 * (vi + 1))
            ax.plot(GATE_DELAY, curve, alpha=0.7, label=f"var {vi+1}")
        ax.set_title(f"{name} (τ≈{tau}µs)")
        ax.set_xlabel("Delay (µs)")
        ax.set_ylabel("Normalized signal")
        ax.legend(fontsize=7)
        ax.set_xlim(0, 300)
    plt.tight_layout()
    plt.savefig("sim_decay_curves.png", dpi=120)
    print("Saved sim_decay_curves.png — decay curves for 8 metal classes")

    # Test classifier accuracy with noisy test curves
    n_tests = 200
    correct = 0
    confusion = np.zeros((8, 8), dtype=int)
    for _ in range(n_tests):
        true_cls = np.random.randint(8)
        tau = CLASSES[true_cls][1] * np.random.choice(CLASSES[true_cls][2])
        test_curve = gen_decay_curve(tau, noise_amp=0.015)
        pred_cls, conf = knn_classify(test_curve, templates, tclasses)
        confusion[true_cls][pred_cls] += 1
        if pred_cls == true_cls:
            correct += 1

    print(f"\nk-NN classifier accuracy: {correct}/{n_tests} = "
          f"{100*correct/n_tests:.1f}%")

    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(f"{'':>10}" + "".join(f"{n:>10}" for n in class_names))
    for i, name in enumerate(class_names):
        print(f"{name:>10}" + "".join(f"{confusion[i][j]:>10}"
              for j in range(8)))

    # Plot confusion matrix
    fig2, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(confusion, cmap="Blues")
    ax.set_xticks(range(8))
    ax.set_yticks(range(8))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"k-NN Confusion Matrix ({100*correct/n_tests:.1f}% accuracy)")
    for i in range(8):
        for j in range(8):
            ax.text(j, i, str(confusion[i][j]), ha="center", va="center",
                    color="white" if confusion[i][j] > n_tests/16 else "black",
                    fontsize=9)
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig("sim_confusion.png", dpi=120)
    print("\nSaved sim_confusion.png — classifier confusion matrix")


if __name__ == "__main__":
    main()