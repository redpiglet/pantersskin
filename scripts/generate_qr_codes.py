#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate vector SVG QR codes from the reader URLs in data/episode-links.json.

Run with Python 3; no third-party packages are required.
"""

import argparse
from pathlib import Path
import json
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
QR_DIR = ROOT / "assets/qr"
LINKS_PATH = ROOT / "data/episode-links.json"

# --- Galois Field GF(256) Arithmetic ---
EXP = [0] * 512
LOG = [0] * 256
x = 1
for i in range(255):
    EXP[i] = x
    EXP[i + 255] = x
    LOG[x] = i
    x <<= 1
    if x & 256:
        x ^= 0x11D


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def rs_generator(n):
    gen = [1]
    for i in range(n):
        root = EXP[i]
        new_gen = [0] * (len(gen) + 1)
        for j, c in enumerate(gen):
            new_gen[j] ^= c
            new_gen[j + 1] ^= gf_mul(c, root)
        gen = new_gen
    return gen


def rs_encode(data, n_ec):
    gen = rs_generator(n_ec)
    rem = list(data) + [0] * n_ec
    for i in range(len(data)):
        lead = rem[i]
        if lead != 0:
            for j in range(len(gen)):
                rem[i + j] ^= gf_mul(gen[j], lead)
    return rem[-n_ec:]


def encode_data_v4_l(text):
    """Version 4, Level L: 80 data codewords, 20 error correction codewords."""
    data_bytes = text.encode("utf-8")
    if len(data_bytes) > 78:
        raise ValueError(f"URL exceeds the 78-byte Version 4 capacity: {text}")

    # 4-bit mode indicator (0100 for Byte mode) + 8-bit character count indicator
    bits = [0, 1, 0, 0]
    length = len(data_bytes)
    for i in range(7, -1, -1):
        bits.append((length >> i) & 1)
    for b in data_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    # Terminator
    needed = 80 * 8
    pad_zeros = min(4, needed - len(bits))
    bits.extend([0] * pad_zeros)

    # Pad to byte boundary
    while len(bits) % 8 != 0:
        bits.append(0)

    # Codewords
    codewords = []
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        codewords.append(b)

    # Pad bytes
    pads = [0xEC, 0x11]
    pad_idx = 0
    while len(codewords) < 80:
        codewords.append(pads[pad_idx])
        pad_idx ^= 1

    # Error correction
    ec_codewords = rs_encode(codewords, 20)
    all_codewords = codewords + ec_codewords

    final_bits = []
    for cw in all_codewords:
        for i in range(7, -1, -1):
            final_bits.append((cw >> i) & 1)
    return final_bits


def mask_pattern(m, r, c):
    if m == 0:
        return (r + c) % 2 == 0
    if m == 1:
        return r % 2 == 0
    if m == 2:
        return c % 3 == 0
    if m == 3:
        return (r + c) % 3 == 0
    if m == 4:
        return (r // 2 + c // 3) % 2 == 0
    if m == 5:
        return (r * c) % 2 + (r * c) % 3 == 0
    if m == 6:
        return ((r * c) % 2 + (r * c) % 3) % 2 == 0
    if m == 7:
        return ((r + c) % 2 + (r * c) % 3) % 2 == 0
    return False


def get_format_bits(ecl, mask):
    data = (ecl << 3) | mask
    rem = data << 10
    gen = 0x537
    for i in range(14, 9, -1):
        if rem & (1 << i):
            rem ^= gen << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def build_qr_v4_matrix(final_bits, mask_num):
    size = 33
    grid = [[None] * size for _ in range(size)]
    is_func = [[False] * size for _ in range(size)]

    # 1. Finder patterns + separators
    def set_finder(r0, c0):
        for r in range(r0 - 1, r0 + 8):
            for c in range(c0 - 1, c0 + 8):
                if 0 <= r < size and 0 <= c < size:
                    grid[r][c] = False
                    is_func[r][c] = True
        for r in range(r0, r0 + 7):
            for c in range(c0, c0 + 7):
                is_black = (
                    r == r0
                    or r == r0 + 6
                    or c == c0
                    or c == c0 + 6
                    or (r0 + 2 <= r <= r0 + 4 and c0 + 2 <= c <= c0 + 4)
                )
                grid[r][c] = is_black
                is_func[r][c] = True

    set_finder(0, 0)
    set_finder(0, 26)
    set_finder(26, 0)

    # 2. Alignment pattern at (26, 26)
    r0, c0 = 24, 24
    for r in range(r0, r0 + 5):
        for c in range(c0, c0 + 5):
            is_black = (
                r == r0
                or r == r0 + 4
                or c == c0
                or c == c0 + 4
                or (r == r0 + 2 and c == c0 + 2)
            )
            grid[r][c] = is_black
            is_func[r][c] = True

    # 3. Timing patterns
    for i in range(8, 25):
        if not is_func[6][i]:
            grid[6][i] = i % 2 == 0
            is_func[6][i] = True
        if not is_func[i][6]:
            grid[i][6] = i % 2 == 0
            is_func[i][6] = True

    # 4. Dark module
    grid[25][8] = True
    is_func[25][8] = True

    # 5. Reserve format info areas
    for i in range(9):
        is_func[8][i] = True
        is_func[i][8] = True
    for i in range(25, 33):
        is_func[8][i] = True
    for i in range(25, 33):
        is_func[i][8] = True

    # 6. Place data bits with mask
    bit_idx = 0
    c = size - 1
    up = True
    while c > 0:
        if c == 6:
            c -= 1
        cols = [c, c - 1]
        rows = range(size - 1, -1, -1) if up else range(size)
        for r in rows:
            for cc in cols:
                if not is_func[r][cc]:
                    b = final_bits[bit_idx] if bit_idx < len(final_bits) else 0
                    bit_idx += 1
                    if mask_pattern(mask_num, r, cc):
                        b ^= 1
                    grid[r][cc] = bool(b)
        up = not up
        c -= 2

    # 7. Place format bits
    fmt = get_format_bits(1, mask_num)  # Level L = 1
    for i in range(15):
        b = bool((fmt >> i) & 1)
        # Top-left placement
        if i < 6:
            grid[i][8] = b
        elif i < 8:
            grid[i + 1][8] = b
        elif i == 8:
            grid[8][7] = b
        else:
            grid[8][14 - i] = b

        # Split placement
        if i < 8:
            grid[8][size - 1 - i] = b
        else:
            grid[size - 15 + i][8] = b

    return grid


def calculate_penalty(grid):
    size = len(grid)
    penalty = 0

    # Rule 1: 5 or more consecutive same color in row/col
    for r in range(size):
        run_color = None
        run_len = 0
        for c in range(size):
            if grid[r][c] == run_color:
                run_len += 1
            else:
                if run_len >= 5:
                    penalty += 3 + (run_len - 5)
                run_color = grid[r][c]
                run_len = 1
        if run_len >= 5:
            penalty += 3 + (run_len - 5)

    for c in range(size):
        run_color = None
        run_len = 0
        for r in range(size):
            if grid[r][c] == run_color:
                run_len += 1
            else:
                if run_len >= 5:
                    penalty += 3 + (run_len - 5)
                run_color = grid[r][c]
                run_len = 1
        if run_len >= 5:
            penalty += 3 + (run_len - 5)

    # Rule 2: 2x2 same color
    for r in range(size - 1):
        for c in range(size - 1):
            val = grid[r][c]
            if grid[r + 1][c] == val and grid[r][c + 1] == val and grid[r + 1][c + 1] == val:
                penalty += 3

    # Rule 3: 1:1:3:1:1 patterns
    patt1 = [True, False, True, True, True, False, True, False, False, False, False]
    patt2 = [False, False, False, False, True, False, True, True, True, False, True]
    for r in range(size):
        for c in range(size - 10):
            window = [grid[r][c + k] for k in range(11)]
            if window == patt1 or window == patt2:
                penalty += 40
    for c in range(size):
        for r in range(size - 10):
            window = [grid[r + k][c] for k in range(11)]
            if window == patt1 or window == patt2:
                penalty += 40

    # Rule 4: Balance of dark/light
    dark = sum(1 for row in grid for cell in row if cell)
    percent = (dark * 100) // (size * size)
    prev_mult = (percent // 5) * 5
    next_mult = prev_mult + 5
    k = min(abs(percent - 50) // 5, abs(next_mult - 50) // 5)
    penalty += k * 10

    return penalty


def generate_qr_svg(text, quiet_zone=4, scale=8, dark_color="#1A2F2B", bg_color="#FFFFFF"):
    final_bits = encode_data_v4_l(text)
    best_grid = None
    min_penalty = float("inf")

    for m in range(8):
        grid = build_qr_v4_matrix(final_bits, m)
        pen = calculate_penalty(grid)
        if pen < min_penalty:
            min_penalty = pen
            best_grid = grid

    size = len(best_grid)
    total_size = (size + 2 * quiet_zone) * scale

    path_d = []
    for r in range(size):
        for c in range(size):
            if best_grid[r][c]:
                x = (c + quiet_zone) * scale
                y = (r + quiet_zone) * scale
                path_d.append(f"M{x},{y}h{scale}v{scale}h-{scale}z")

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_size} {total_size}" width="100%" height="100%" shape-rendering="crispEdges">',
        f'  <rect width="100%" height="100%" fill="{bg_color}"/>',
        f'  <path d="{" ".join(path_d)}" fill="{dark_color}"/>',
        f"</svg>",
    ]
    return "\n".join(svg)


def load_episode_links(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    episodes = data.get("episodes") if isinstance(data, dict) else None
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("Input must contain a non-empty 'episodes' array")

    links = {}
    for index, episode in enumerate(episodes, start=1):
        if not isinstance(episode, dict):
            raise ValueError(f"Episode entry {index} must be an object")
        number = episode.get("episode_number")
        if type(number) is not int or number < 1:
            raise ValueError(f"Episode entry {index} needs a positive integer episode_number")
        if number in links:
            raise ValueError(f"Duplicate episode_number: {number}")
        url = episode.get("reader_url")
        if not isinstance(url, str) or not url or any(char.isspace() for char in url):
            raise ValueError(f"Episode {number} needs a reader_url without whitespace")
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"Episode {number} needs an absolute HTTP(S) reader_url")
        links[number] = url
    return sorted(links.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=LINKS_PATH, help="Episode links JSON")
    parser.add_argument("--output-dir", type=Path, default=QR_DIR, help="SVG output directory")
    args = parser.parse_args()

    try:
        # Validate and encode every entry before changing any output files.
        codes = [
            (number, generate_qr_svg(url))
            for number, url in load_episode_links(args.input)
        ]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for number, svg_content in codes:
        svg_path = args.output_dir / f"episode-{number:02d}-qr.svg"
        svg_path.write_text(svg_content, encoding="utf-8")

    print(f"Generated {len(codes)} SVG QR codes from {args.input} in {args.output_dir}/")


if __name__ == "__main__":
    main()
