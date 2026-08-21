#!/usr/bin/env python3
"""
Spectra Charm — Reference Spectrum Generator

Generates synthetic absorbance spectra for common compounds
and uploads them to the device's SPI flash library.

Usage:
    python3 generate_library.py --output library.bin
    python3 generate_library.py --upload --wifi 192.168.4.1

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import struct
import json
import numpy as np

WAVELENGTH_START = 340.0
WAVELENGTH_END = 700.0
SPECTRUM_POINTS = 128

# Compound database with spectral characteristics
# Each entry: (name, molar_absorptivity, peak_wavelengths_nm, peak_absorptances_normalized)
COMPOUND_DB = {
    1:  ("Potassium Permanganate",   2500,   [525, 545, 310],       [1.0, 0.85, 0.35]),
    2:  ("Potassium Dichromate",     3700,   [350, 440, 370],       [1.0, 0.28, 0.65]),
    3:  ("Copper Sulfate",           23,     [800, 610],            [1.0, 0.55]),
    4:  ("Cobalt Chloride",          500,    [510, 630],            [0.4, 1.0]),
    5:  ("Nickel Sulfate",           2.5,    [395, 720, 650],       [1.0, 0.6, 0.3]),
    6:  ("Iron Sulfate",             2.8,    [510, 305],            [0.3, 1.0]),
    7:  ("Nitrate (reagent)",         4800,   [543, 220],            [1.0, 0.9]),
    8:  ("Phosphate (reagent)",       23500,  [880, 420],            [1.0, 0.2]),
    9:  ("Chlorophyll",              90000,  [430, 662, 450],       [1.0, 0.8, 0.55]),
    10: ("Tartrazine (Yellow 5)",    23000,  [425, 257],            [1.0, 0.7]),
    11: ("Allura Red (Red 40)",      26000,  [504, 425],            [1.0, 0.35]),
    12: ("Brilliant Blue FCF",       83000,  [629, 310],            [1.0, 0.4]),
    13: ("Fluorescein",              88000,  [494, 460],            [1.0, 0.6]),
    14: ("Rhodamine B",              107000, [554, 350],            [1.0, 0.15]),
    15: ("Quinine",                  10000,  [347, 250],            [1.0, 0.5]),
}

# Extended compounds (16-50)
EXTENDED_COMPOUNDS = {
    16: ("Caffeine",           10100, [273, 205], [1.0, 0.8]),
    17: ("Aspirin",            5600,  [229, 276], [1.0, 0.4]),
    18: ("Acetaminophen",      13700, [243, 289], [1.0, 0.35]),
    19: ("Riboflavin",         12500, [266, 370, 445], [0.8, 0.6, 1.0]),
    20: ("Beta-Carotene",      140000, [450, 478], [1.0, 0.65]),
    21: ("Curcumin",           56000,  [420, 460], [1.0, 0.7]),
    22: ("Methylene Blue",     71000,  [664, 610], [1.0, 0.4]),
    23: ("Indigo Carmine",     12000,  [610, 288], [1.0, 0.3]),
    24: ("Sunset Yellow",      21000,  [482, 257], [1.0, 0.6]),
    25: ("Erythrosine B",      62000,  [526, 370], [1.0, 0.3]),
    26: ("Fast Green FCF",     88000,  [624, 422], [1.0, 0.2]),
    27: ("Phenol Red",         28000,  [559, 430], [1.0, 0.5]),
    28: ("Bromothymol Blue",   36000,  [616, 430], [1.0, 0.4]),
    29: ("Cresol Red",         37000,  [572, 434], [1.0, 0.3]),
    30: ("Congo Red",          20000,  [497, 340], [1.0, 0.4]),
    31: ("Malachite Green",    78000,  [617, 425], [1.0, 0.3]),
    32: ("Crystal Violet",     87000,  [590, 420], [1.0, 0.2]),
    33: ("Eosin Y",           65000,  [517, 345], [1.0, 0.3]),
    34: ("Rose Bengal",        95000,  [549, 350], [1.0, 0.2]),
    35: ("Hemoglobin (oxy)",   14000,  [415, 541, 577], [1.0, 0.5, 0.45]),
    36: ("Cytochrome C",       11000,  [410, 530, 550], [1.0, 0.3, 0.35]),
    37: ("Vitamin B12",        27000,  [361, 528], [1.0, 0.15]),
    38: ("Chlorophyll B",      56000,  [453, 645], [1.0, 0.65]),
    39: ("Anthocyanin",        25000,  [520, 280], [1.0, 0.7]),
    40: ("NADH",               6220,   [340, 259], [1.0, 0.8]),
    41: ("NAD+",               16900,  [260], [1.0]),
    42: ("ATP",                15400,  [259], [1.0]),
    43: ("DNA (260nm)",        6600,   [260], [1.0]),
    44: ("RNA (260nm)",        7700,   [260], [1.0]),
    45: ("BSA (280nm)",        43800,  [280], [1.0]),
    46: ("Tryptophan",         5500,   [280, 218], [1.0, 0.8]),
    47: ("Tyrosine",           1400,   [274, 222], [1.0, 0.7]),
    48: ("Phenylalanine",      195,    [257], [1.0]),
    49: ("Ferric Chloride",     4300,   [300, 420], [1.0, 0.2]),
    50: ("Potassium Ferricyanide", 1000, [420, 302], [1.0, 0.5]),
}


def gaussian(x, center, fwhm=30.0):
    """Gaussian function for spectral peak generation."""
    sigma = fwhm / 2.3548
    return np.exp(-((x - center) ** 2) / (2 * sigma ** 2))


def generate_spectrum(peak_wavelengths, peak_absorbances, wavelengths=None):
    """Generate a synthetic absorbance spectrum from peak data."""
    if wavelengths is None:
        wavelengths = np.linspace(WAVELENGTH_START, WAVELENGTH_END, SPECTRUM_POINTS)

    spectrum = np.zeros_like(wavelengths)
    for wl, ab in zip(peak_wavelengths, peak_absorbances):
        fwhm = 25.0 + 5.0 * (wl / 700.0)  # Broader peaks at longer wavelengths
        spectrum += ab * gaussian(wavelengths, wl, fwhm)

    return spectrum


def generate_library_binary(all_compounds, output_file):
    """Generate binary library file for SPI flash programming."""
    data = bytearray()

    # Header
    magic = 0x5343484D  # "SCHM"
    num = len(all_compounds)
    data += struct.pack('<IHH', magic, num, 0)  # magic, count, reserved
    data += struct.pack('<I', 0)  # CRC placeholder

    for comp_id, (name, molar_abs, peak_wls, peak_abs) in all_compounds.items():
        entry = bytearray(512)
        idx = 0

        struct.pack_into('<H', entry, idx, comp_id); idx += 2
        name_bytes = name.encode('utf-8')[:31]
        entry[idx] = len(name_bytes); idx += 1
        entry[idx:idx+len(name_bytes)] = name_bytes; idx += 32
        struct.pack_into('<f', entry, idx, molar_abs); idx += 4
        entry[idx] = len(peak_wls); idx += 1

        for wl in peak_wls[:8]:
            struct.pack_into('<f', entry, idx, wl); idx += 4
        for ab in peak_abs[:8]:
            struct.pack_into('<f', entry, idx, ab); idx += 4

        data += entry

    with open(output_file, 'wb') as f:
        f.write(data)
    print(f"Library written to {output_file} ({len(data)} bytes, {num} compounds)")


def generate_library_json(all_compounds, output_file):
    """Generate JSON library file for human readability."""
    library = []
    wavelengths = np.linspace(WAVELENGTH_START, WAVELENGTH_END, SPECTRUM_POINTS)

    for comp_id, (name, molar_abs, peak_wls, peak_abs) in sorted(all_compounds.items()):
        spectrum = generate_spectrum(peak_wls, peak_abs, wavelengths)
        entry = {
            "id": comp_id,
            "name": name,
            "molar_absorptivity": molar_abs,
            "peak_wavelengths": peak_wls,
            "peak_absorbances": peak_abs,
            "full_spectrum": spectrum.tolist(),
        }
        library.append(entry)

    with open(output_file, 'w') as f:
        json.dump(library, f, indent=2)
    print(f"JSON library written to {output_file} ({len(library)} compounds)")


def upload_to_device(all_compounds, host):
    """Upload library entries to device via WiFi API."""
    import requests

    for comp_id, (name, molar_abs, peak_wls, peak_abs) in sorted(all_compounds.items()):
        payload = {
            "name": name,
            "num_key_points": len(peak_wls),
            "molar_absorptivity": molar_abs,
            "key_wavelengths": peak_wls,
            "key_absorbances": peak_abs,
        }
        try:
            r = requests.post(f"http://{host}/api/v1/library", json=payload, timeout=10)
            print(f"  [{comp_id:3d}] {name}: {r.status_code} {r.text.strip()}")
        except Exception as e:
            print(f"  [{comp_id:3d}] {name}: ERROR - {e}")


def main():
    parser = argparse.ArgumentParser(description="Spectra Charm Reference Library Generator")
    parser.add_argument("--output", default="library.bin", help="Binary output file")
    parser.add_argument("--json", default=None, help="JSON output file")
    parser.add_argument("--upload", action="store_true", help="Upload to device")
    parser.add_argument("--wifi", default="192.168.4.1", help="Device WiFi IP")
    parser.add_argument("--extended", action="store_true", help="Include extended compounds")
    args = parser.parse_args()

    all_compounds = dict(COMPOUND_DB)
    if args.extended:
        all_compounds.update(EXTENDED_COMPOUNDS)

    print(f"Generating library with {len(all_compounds)} compounds...")

    generate_library_binary(all_compounds, args.output)

    if args.json:
        generate_library_json(all_compounds, args.json)

    if args.upload:
        print(f"Uploading to device at {args.wifi}...")
        upload_to_device(all_compounds, args.wifi)
        print("Upload complete!")


if __name__ == "__main__":
    main()