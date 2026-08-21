#!/usr/bin/env python3
"""
Ping Caliper — report.py

Render an inspection PDF from downloaded Ping Caliper logs: a readings
table with location, thickness, material, flaw flags, and A-scan
thumbnails (if available).

Usage:
    python report.py --input ./logs/ --output inspection_report.pdf \\
        --title "API 570 Pipe Survey" --inspector "Jane Doe" \\
        --location "Refinery Unit 12"

Requires: reportlab, matplotlib (optional, for A-scan thumbnails)
    pip install reportlab matplotlib
"""

import argparse
import csv
import os
import struct
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                      TableStyle, PageBreak, Image)
    from reportlab.lib.enums import TA_CENTER
    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False


def load_logs(input_dir):
    csv_path = os.path.join(input_dir, "PINGLOG.csv")
    records = []
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    return records


def load_ascan(input_dir):
    """Load the latest A-scan binary, if present."""
    bin_path = os.path.join(input_dir, "ASCAN_latest.bin")
    if not os.path.exists(bin_path):
        return None
    with open(bin_path, "rb") as f:
        data = f.read()
    if len(data) < 4:
        return None
    count, _ = struct.unpack_from("<HH", data, 0)
    samples = struct.unpack_from(f"<{count}H", data, 4)
    return samples


def make_thumbnail(samples, path, velocity=5920):
    """Render an A-scan PNG thumbnail (requires matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    n = len(samples)
    sample_ns = 200.0   # 5 Msps
    depth_mm = np.arange(n) * (velocity * sample_ns * 1e-9 * 0.5 * 1000.0)
    fig, ax = plt.subplots(figsize=(3, 1.5), dpi=100)
    ax.fill_between(depth_mm, samples, color="black")
    ax.set_xlabel("Depth (mm)")
    ax.set_ylabel("Amplitude")
    ax.set_title("A-scan")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def build_pdf(records, ascan_thumb, output, title, inspector, location):
    if not HAVE_REPORTLAB:
        print("reportlab not installed. Install with: pip install reportlab")
        print("Falling back to text output.")
        with open(output.replace(".pdf", ".txt"), "w") as f:
            f.write(f"{title}\nInspector: {inspector}\nLocation: {location}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n\n")
            f.write("idx,thickness_mm,valid,flaw,material,battery\n")
            for r in records:
                f.write(f"{r.get('idx','')},{r.get('thickness_mm','')},"
                        f"{r.get('valid','')},{r.get('flaw_detected','')},"
                        f"{r.get('material','')},{r.get('battery_pct','')}\n")
        return

    doc = SimpleDocTemplate(output, pagesize=landscape(letter),
                              rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                              topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.1 * inch))
    meta_style = ParagraphStyle("meta", parent=styles["Normal"], fontSize=10)
    story.append(Paragraph(f"<b>Inspector:</b> {inspector}", meta_style))
    story.append(Paragraph(f"<b>Location:</b> {location}", meta_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            meta_style))
    story.append(Paragraph(f"<b>Instrument:</b> Ping Caliper v1.0", meta_style))
    story.append(Spacer(1, 0.2 * inch))

    if ascan_thumb and os.path.exists(ascan_thumb):
        story.append(Image(ascan_thumb, width=4 * inch, height=2 * inch))
        story.append(Spacer(1, 0.1 * inch))

    # Readings table
    header = ["#", "Thickness (mm)", "TOF (ns)", "Velocity (m/s)",
              "Valid", "Flaw", "Flaw depth (mm)", "Material", "Battery (%)"]
    rows = [header]
    for i, r in enumerate(records):
        rows.append([
            str(i + 1),
            r.get("thickness_mm", ""),
            r.get("tof_ns", ""),
            r.get("velocity_mps", ""),
            r.get("valid", ""),
            "YES" if r.get("flaw_detected") == "1" else "",
            r.get("flaw_depth_mm", ""),
            r.get("material", ""),
            r.get("battery_pct", ""),
        ])
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    # Summary stats
    n = len(records)
    valid = sum(1 for r in records if r.get("valid") == "1")
    flaws = sum(1 for r in records if r.get("flaw_detected") == "1")
    thicknesses = [float(r["thickness_mm"]) for r in records
                   if r.get("thickness_mm") and r.get("valid") == "1"]
    summary = (f"<b>Summary:</b> {n} readings, {valid} valid, "
               f"{flaws} flaws flagged")
    if thicknesses:
        summary += (f", thickness range {min(thicknesses):.2f}–"
                    f"{max(thicknesses):.2f} mm")
    story.append(Paragraph(summary, meta_style))

    doc.build(story)
    print(f"Wrote {output}")


def main():
    p = argparse.ArgumentParser(description="Ping Caliper inspection report generator")
    p.add_argument("--input", default="./logs", help="Input logs directory")
    p.add_argument("--output", default="inspection_report.pdf", help="Output PDF")
    p.add_argument("--title", default="Ping Caliper Inspection Report")
    p.add_argument("--inspector", default="Unknown")
    p.add_argument("--location", default="Unknown")
    p.add_argument("--velocity", type=int, default=5920,
                    help="Velocity for A-scan depth axis (m/s)")
    args = p.parse_args()

    records = load_logs(args.input)
    print(f"Loaded {len(records)} records from {args.input}")
    if not records:
        print("No records. Nothing to report.")
        return

    ascan = load_ascan(args.input)
    thumb = None
    if ascan:
        thumb = make_thumbnail(ascan, os.path.join(args.input, "ascan_thumb.png"),
                                args.velocity)
    build_pdf(records, thumb, args.output, args.title, args.inspector, args.location)


if __name__ == "__main__":
    main()