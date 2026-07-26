#!/usr/bin/env python3
"""Generate a static SVG 'screenshot' of the aurora for the README."""
import html
import math
import random

WIDTH = 120
HEIGHT = 32
CELL = 8

AURORA_CHARS = " .:-=+*#%@"
STAR_CHARS = ".+*"

PALETTES = {
    "green": [(0.0,(5,46,26)),(0.45,(26,242,115)),(0.75,(140,255,191)),(1.0,(217,242,255))],
    "violet": [(0.0,(26,5,51)),(0.45,(140,38,242)),(0.75,(217,115,255)),(1.0,(242,230,255))],
    "sunset": [(0.0,(51,8,13)),(0.45,(255,89,38)),(0.75,(255,191,77)),(1.0,(255,242,217))],
    "rainbow": [(0.0,(13,13,51)),(0.3,(26,230,128)),(0.55,(77,128,255)),(0.8,(242,102,217)),(1.0,(255,242,255))],
    "ice": [(0.0,(5,26,51)),(0.45,(77,191,255)),(0.75,(191,242,255)),(1.0,(255,255,255))],
}

def smoothstep(t): return t*t*(3-2*t)

def value_noise_1d(grid, x):
    n = len(grid)
    i0 = int(math.floor(x)) % n
    i1 = (i0 + 1) % n
    t = smoothstep(x - math.floor(x))
    return grid[i0]*(1-t) + grid[i1]*t

def value_noise_2d(grid, x, y):
    h = len(grid); w = len(grid[0])
    xi = math.floor(x); yi = math.floor(y)
    fx = smoothstep(x - xi); fy = smoothstep(y - yi)
    i0,j0 = xi%w, yi%h; i1,j1 = (i0+1)%w, (j0+1)%h
    v00=grid[j0][i0]; v10=grid[j0][i1]; v01=grid[j1][i0]; v11=grid[j1][i1]
    top=v00*(1-fx)+v10*fx; bot=v01*(1-fx)+v11*fx
    return top*(1-fy)+bot*fy

def fractal_noise_1d(grid, x, octaves=3):
    total=amp=freq=norm=0.0
    for _ in range(octaves):
        total += value_noise_1d(grid, x*freq)*amp
        norm += amp; amp *= 0.5; freq *= 2.0
    return total/norm if norm else 0.0

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))

def palette_color(name, t):
    stops = PALETTES[name]; t = clamp(t)
    for i in range(len(stops)-1):
        t0,c0 = stops[i]; t1,c1 = stops[i+1]
        if t0 <= t <= t1:
            lt = (t-t0)/(t1-t0) if t1>t0 else 0.0
            return (int(c0[0]+(c1[0]-c0[0])*lt), int(c0[1]+(c1[1]-c0[1])*lt), int(c0[2]+(c1[2]-c0[2])*lt))
    return stops[-1][1]

def make_mountains(width, base_row, seed, n=3):
    rng = random.Random(seed); heights=[0.0]*width
    for r in range(n):
        amp=(r+1)*2.2; wl=rng.uniform(width*0.25, width*0.8); ph=rng.uniform(0,6.28)
        grid=[rng.random() for _ in range(64)]
        for x in range(width):
            heights[x] += (fractal_noise_1d(grid, x/wl+ph)-0.5)*amp
    return [int(base_row - heights[x] - 1) for x in range(width)]

def main():
    rng = random.Random(42)
    noise_grid = [[rng.random() for _ in range(32)] for _ in range(32)]
    curtain_seeds = [rng.random() for _ in range(256)]
    sky_h = max(4, int(HEIGHT*0.62))
    stars = [(rng.randint(0,WIDTH-1), rng.randint(0,sky_h-1),
              rng.uniform(0.25,1.0), rng.uniform(0,6.28)) for _ in range(int(WIDTH*sky_h*0.012))]
    mountains = make_mountains(WIDTH, HEIGHT-3, 42)
    t = 3.0
    palette = "green"

    curtains = [
        {"freq":0.045,"amp":0.22,"speed":0.30,"phase":0.0,"bright":1.0,"color_t":0.55},
        {"freq":0.080,"amp":0.16,"speed":0.55,"phase":1.3,"bright":0.85,"color_t":0.42},
        {"freq":0.033,"amp":0.28,"speed":0.18,"phase":2.7,"bright":0.95,"color_t":0.70},
        {"freq":0.120,"amp":0.10,"speed":0.75,"phase":4.1,"bright":0.70,"color_t":0.30},
    ]
    band_c = sky_h*0.42; band_h = sky_h*0.55

    # build pixel grid: (r,g,b) per cell, default deep night sky
    grid = [[(6,10,20)]*WIDTH for _ in range(HEIGHT)]
    chars = [[" "]*WIDTH for _ in range(HEIGHT)]

    # stars
    for (sx, sy, sb, sp) in stars:
        tw = math.sin(sp + t*1.0)*0.5+0.5
        b = sb * (0.55+0.45*tw)
        c = (int(b*255), int(b*255), int((b*0.95+0.05)*255))
        grid[sy][sx] = c
        chars[sy][sx] = "."

    # aurora
    for x in range(WIDTH):
        col_intensity=0.0; col_color_t=0.0; col_norm=0.0
        for c in curtains:
            n = fractal_noise_1d(curtain_seeds, x*c["freq"]+t*c["speed"]+c["phase"])
            col_intensity += n*c["bright"]; col_color_t += n*c["color_t"]*c["bright"]; col_norm += c["bright"]
        col_intensity = col_intensity/col_norm if col_norm else 0.0
        col_color_t = col_color_t/col_norm if col_norm else 0.0
        for y in range(sky_h):
            shift = (col_intensity-0.5)*band_h*0.5
            local_dy = (y - (band_c+shift))/band_h
            vert = math.exp(-(local_dy*local_dy)*2.6)
            streak = value_noise_2d(noise_grid, x*0.18+t*0.05, y*0.22-t*0.08)
            vert *= 0.6+0.4*streak
            intensity = vert*col_intensity
            if intensity < 0.05: continue
            color_t = clamp(col_color_t*0.6 + (1.0-local_dy)*0.4)
            color_t = clamp(color_t + (streak-0.5)*0.15)
            r,g,b = palette_color(palette, color_t)
            k = clamp(intensity*1.15)
            grid[y][x] = (int(r*k), int(g*k), int(b*k))
            ci = int(clamp(intensity)*(len(AURORA_CHARS)-1))
            chars[y][x] = AURORA_CHARS[ci]

    # mountains
    for x in range(WIDTH):
        top = mountains[x]
        for y in range(top, HEIGHT):
            ridge_h = HEIGHT-3-top
            if y == top:
                if ridge_h > 4:
                    grid[y][x] = (160,175,200); chars[y][x] = "^"
                else:
                    grid[y][x] = (20,24,40); chars[y][x] = "▁"
            else:
                grid[y][x] = (14,18,32); chars[y][x] = "▒"

    # SVG
    svg_w = WIDTH*CELL
    svg_h = HEIGHT*CELL
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">']
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="#06060f"/>')
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r,g,b = grid[y][x]
            parts.append(f'<rect x="{x*CELL}" y="{y*CELL}" width="{CELL}" height="{CELL}" fill="rgb({r},{g},{b})"/>')
            ch = chars[y][x]
            if ch not in (" ", "."):
                # draw char darker/lighter contrast
                parts.append(f'<text x="{x*CELL+CELL/2}" y="{y*CELL+CELL*0.8}" font-family="monospace" font-size="{CELL*0.8}" text-anchor="middle" fill="rgb({min(255,r+80)},{min(255,g+80)},{min(255,b+80)})">{html.escape(ch)}</text>')
            elif ch == ".":
                parts.append(f'<text x="{x*CELL+CELL/2}" y="{y*CELL+CELL*0.8}" font-family="monospace" font-size="{CELL*0.7}" text-anchor="middle" fill="rgb({r},{g},{b})">.</text>')
    parts.append('</svg>')
    print('\n'.join(parts))

if __name__ == "__main__":
    main()