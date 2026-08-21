#!/usr/bin/env python3
"""
export_csv.py — Convert SD card vibra.csv to a pandas DataFrame
and optionally export to Parquet/feather for fast analysis.

Usage:
    python3 export_csv.py --input vibra.csv --export out.parquet
"""
import argparse
import pandas as pd

def load(path):
    df = pd.read_csv(path, names=["time_ms", "disp_nm", "vel_mms"])
    df["time_s"] = df["time_ms"] / 1000.0
    return df

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--export", default=None)
    args = ap.parse_args()
    df = load(args.input)
    print(df.describe())
    if args.export:
        if args.export.endswith(".parquet"):
            df.to_parquet(args.export)
        elif args.export.endswith(".feather"):
            df.to_feather(args.export)
        else:
            df.to_csv(args.export, index=False)
        print(f"Exported to {args.export}")