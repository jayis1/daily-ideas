Sky Lens — Schematic Notes
==========================

This directory contains the KiCad 7 schematic and PCB files for the
Sky Lens pocket cosmic-ray muon telescope.

Files:
  sky-lens.kicad_sch    — main schematic (top-level, net list in comments)
  sky-lens.kicad_pcb     — PCB layout (70×100 mm, 4-layer)
  sky-lens.kicad-project.json — project metadata

The schematic is organised into these conceptual blocks (the full
KiCad hierarchical sheets would be expanded in a complete project):

  1. SoC core          — ESP32-S3-WROOM-1, decoupling, USB-C, boot/EN
  2. SiPM bias         — TPS61158 boost to +30V, BIAS_EN, BIAS_MON, bleeder
  3. Analog front end  — 2× OPA2356 TIA, 2× TLV3501 discriminator, peak-hold
  4. ADC               — ADS7946 dual 14-bit SAR + REF5045 4.5V reference
  5. I²C peripherals   — SSD1306 OLED, BMP390, ICM-42688-P, MAX17048
  6. SD card           — microSD on SPI2 (GPIO11-14)
  7. Power             — TP4056 charger, AMS1117-3.3 LDO, LiPo, fuel gauge
  8. User I/O          — buttons, LEDs, buzzer, debug UART

The net list in the kicad_sch file comments captures all essential
connections. A full KiCad project with symbol libraries and a routed
PCB would be generated from this starting point.