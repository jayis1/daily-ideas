#!/usr/bin/env python3
"""
render_stroke.py — Render a 2D trajectory to a 32×32 grayscale image

Used for visualizing what the CNN "sees" and for debugging trajectory
reconstruction.

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import numpy as np
import sys

def render_trajectory(points, size=32, pen_width=1.5, margin=2):
    """Render a list of (x, y) points to a grayscale image.

    Args:
        points: list of (x, y) tuples, normalized 0.0-1.0
        size: output image dimension (square)
        pen_width: pen width in pixels
        margin: margin in pixels

    Returns:
        numpy array of shape (size, size), dtype uint8
    """
    img = np.zeros((size, size), dtype=np.uint8)
    if len(points) < 2:
        return img

    def to_pixel(xy):
        """Convert normalized (0-1) coordinates to pixel coordinates."""
        px = int(xy[0] * (size - 2 * margin) + margin)
        py = int(xy[1] * (size - 2 * margin) + margin)
        return (max(0, min(size-1, px)), max(0, min(size-1, py)))

    # Bresenham line drawing with pen width
    for i in range(len(points) - 1):
        x0, y0 = to_pixel(points[i])
        x1, y1 = to_pixel(points[i + 1])

        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            # Draw with pen width
            r = int(pen_width)
            for py_off in range(-r, r + 1):
                for px_off in range(-r, r + 1):
                    dist = np.sqrt(px_off**2 + py_off**2)
                    if dist <= pen_width:
                        px, py = x0 + px_off, y0 + py_off
                        if 0 <= px < size and 0 <= py < size:
                            intensity = int(255 * max(0, 1.0 - dist / pen_width))
                            img[py, px] = max(img[py, px], intensity)

            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    # Simple 3×3 Gaussian blur for anti-aliasing
    from scipy.ndimage import gaussian_filter
    img = gaussian_filter(img, sigma=0.5).astype(np.uint8)

    return img


def load_trajectory(filepath):
    """Load trajectory from a text file (one point per line: x y)."""
    points = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                x, y = float(parts[0]), float(parts[1])
                points.append((x, y))
    return points


def main():
    parser = argparse.ArgumentParser(description="Render stroke trajectory to image")
    parser.add_argument("input", help="Input trajectory file (x y per line)")
    parser.add_argument("--output", "-o", help="Output image file (PNG or NPZ)")
    parser.add_argument("--size", type=int, default=32, help="Image size (default: 32)")
    parser.add_argument("--display", action="store_true", help="Display with matplotlib")
    args = parser.parse_args()

    points = load_trajectory(args.input)
    if not points:
        print("Error: No points loaded from input file")
        sys.exit(1)

    print(f"Loaded {len(points)} trajectory points")
    img = render_trajectory(points, size=args.size)

    if args.output:
        if args.output.endswith('.npz') or args.output.endswith('.npy'):
            np.save(args.output, img)
        else:
            try:
                from PIL import Image
                Image.fromarray(img).save(args.output)
            except ImportError:
                np.save(args.output.replace('.png', '.npy'), img)
        print(f"Saved to {args.output}")

    if args.display:
        try:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(10, 5))

            # Plot trajectory
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            axes[0].plot(xs, ys, 'b-', linewidth=1)
            axes[0].set_title("Trajectory (2D)")
            axes[0].set_aspect('equal')
            axes[0].invert_yaxis()

            # Plot rendered image
            axes[1].imshow(img, cmap='gray', vmin=0, vmax=255)
            axes[1].set_title(f"Rendered {args.size}×{args.size}")

            plt.tight_layout()
            plt.show()
        except ImportError:
            print("matplotlib not available; skipping display")


if __name__ == "__main__":
    main()