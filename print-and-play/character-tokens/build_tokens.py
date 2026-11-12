#!/usr/bin/env python3
"""Compose 30 mm Georgian character discs from the selected card medallions."""

import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/character-tokens"
DECK = ROOT / "print-and-play/character-deck"
SPEC = json.loads((HERE / "production-spec.json").read_text())
COPY = json.loads((DECK / "display-copy.ka.json").read_text())
PORTRAITS = json.loads((DECK / "portrait-manifest.json").read_text())["portraits"]
MM = 72 / 25.4
PAL = SPEC["palette"]

sys.path.insert(0, str(DECK))
from prepare_georgian_fonts import prepare

FONTS = prepare(ROOT)
for family, style in (("Geo", "Regular"), ("GeoBold", "Bold"), ("GeoDisplay", "Display")):
    pdfmetrics.registerFont(TTFont(family, str(FONTS / f"Georgian-{style}.ttf")))
for family, filename in (("Latin", "Arial.ttf"), ("LatinBold", "Arial Bold.ttf")):
    pdfmetrics.registerFont(TTFont(family, "/System/Library/Fonts/Supplemental/" + filename))


def runs(text, font):
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    fallback = "Latin" if font == "Geo" else "LatinBold"
    result = []
    for char in text:
        family = font if ord(char) in cmap else fallback
        assert ord(char) in pdfmetrics.getFont(family).face.charToGlyph, char
        if result and result[-1][0] == family:
            result[-1] = (family, result[-1][1] + char)
        else:
            result.append((family, char))
    return result


def width(text, size, font="Geo"):
    return sum(pdfmetrics.stringWidth(s, f, size) for f, s in runs(text, font)) / MM


def draw_text(c, text, x, y, size, font="Geo", ink=None, align="center"):
    w = width(text, size, font)
    left = x - w / 2 if align == "center" else x
    c.setFillColor(colors.HexColor(ink or PAL["green"]))
    cursor = left
    for family, s in runs(text, font):
        c.setFont(family, size)
        c.drawString(cursor * MM, y * MM, s)
        cursor += pdfmetrics.stringWidth(s, family, size) / MM
    return [left, y - size / MM * .28, left + w, y + size / MM]


def wrapped(text, max_width, size, font="Geo"):
    words = text.split()
    lines = []
    for word in words:
        trial = (lines[-1] + " " + word) if lines else word
        if lines and width(trial, size, font) <= max_width:
            lines[-1] = trial
        else:
            lines.append(word)
    return lines


def token_name(text):
    """Use one legible line, or two naturally separated name parts."""
    if width(text, 7, "GeoBold") <= 17.3:
        return [text], 7
    parts = text.replace("-", "- ").split()
    choices = [(" ".join(parts[:i]).replace("- ", "-"),
                " ".join(parts[i:]).replace("- ", "-"))
               for i in range(1, len(parts))]
    if choices:
        lines = min(choices, key=lambda pair: max(width(pair[0], 6.2, "GeoBold") / 18.5,
                                                  width(pair[1], 6.2, "GeoBold") / 14.5))
        if width(lines[0], 6.2, "GeoBold") <= 18.5 and width(lines[1], 6.2, "GeoBold") <= 14.5:
            return list(lines), 6.2
    size = min(7, 7 * 17.3 / width(text, 7, "GeoBold"))
    assert size >= 6, (text, "Name too long for a legible disc")
    return [text], size


def image_readers():
    images = {}
    for item in PORTRAITS:
        path = ROOT / item["asset"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
        with Image.open(path) as source:
            image = source.convert("RGBA")
            assert image.width == image.height
            image.thumbnail((SPEC["embedded_image_max_px"],) * 2, Image.Resampling.LANCZOS)
            images[item["character_id"]] = ImageReader(image)
    return images


def disc(c, item, cx, cy, images):
    cid = item["character_id"]
    radius = SPEC["diameter_mm"] / 2
    c.saveState()
    c.setFillColor(colors.HexColor(PAL["ivory"]))
    c.circle(cx * MM, cy * MM, radius * MM, fill=1, stroke=0)
    clip = c.beginPath()
    clip.circle(cx * MM, cy * MM, radius * MM)
    c.clipPath(clip, stroke=0)
    d = SPEC["portrait_diameter_mm"]
    c.drawImage(images[cid], (cx - d / 2) * MM, (cy - d / 2) * MM,
                width=d * MM, height=d * MM, mask="auto")

    # Keep the painted gold rim intact. The name field stays inside its inner edge.
    c.saveState()
    inner = c.beginPath()
    inner.circle(cx * MM, cy * MM, SPEC["name_band_clip_radius_mm"] * MM)
    c.clipPath(inner, stroke=0)
    c.setFillColor(colors.HexColor(PAL["ivory"]))
    top = cy + SPEC["name_band_top_offset_mm"]
    c.rect((cx - radius) * MM, (cy - radius) * MM,
           radius * 2 * MM, (top - (cy - radius)) * MM, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor(PAL["gold"]))
    c.setLineWidth(.16 * MM)
    c.line((cx - radius) * MM, top * MM, (cx + radius) * MM, top * MM)
    lines, size = token_name(COPY[cid]["short_name"])
    offsets = [-9] if len(lines) == 1 else [-7.8, -10.2]
    boxes = [draw_text(c, text, cx, cy + offset, size, "GeoBold")
             for text, offset in zip(lines, offsets)]
    for box in boxes:
        for bx in (box[0], box[2]):
            for by in (box[1], box[3]):
                assert math.hypot(bx - cx, by - cy) <= SPEC["name_band_clip_radius_mm"] - .15, (cid, box)
    c.restoreState()
    c.restoreState()
    # The centre of this fine continuous contour is the exact 30 mm cut line.
    c.setStrokeColor(colors.HexColor(PAL["green"]))
    c.setLineWidth(.12 * MM)
    c.circle(cx * MM, cy * MM, radius * MM, fill=0, stroke=1)
    return {"character_id": cid, "name_ka": COPY[cid]["name"],
            "token_name_ka": COPY[cid]["short_name"], "name_lines": lines,
            "name_size_pt": size, "name_boxes_mm": boxes,
            "center_mm": [cx, cy], "diameter_mm": radius * 2,
            "art_status": item["status"], "art_source": item["asset"],
            "art_sha256": item["sha256"]}


def sheet(c, items, kind, images, page_number):
    painted = kind == "painted_portraits"
    draw_text(c, "პერსონაჟთა ფიშკები", 105, 278, 23, "GeoDisplay")
    subtitle = "მოხატული პორტრეტები" if painted else "დამატებითი პერსონაჟები / სილუეტები"
    draw_text(c, f"{subtitle} / {len(items)} ფიშკა / დიამეტრი: 30 მმ", 105, 267, 10.5)
    draw_text(c, "A4 / ბეჭდვა 100%-ზე / ერთ მხარეს", 105, 257, 9, ink=PAL["muted"])
    c.setStrokeColor(colors.HexColor(PAL["gold"]))
    c.setLineWidth(.2 * MM)
    c.line(18 * MM, 250 * MM, 192 * MM, 250 * MM)

    records = []
    columns = SPEC["columns"]
    for start in range(0, len(items), columns):
        row = items[start:start + columns]
        cy = SPEC["first_row_center_y_mm"] - (start // columns) * SPEC["row_pitch_mm"]
        for col, item in enumerate(row):
            cx = 105 + (col - (len(row) - 1) / 2) * SPEC["column_pitch_mm"]
            record = disc(c, item, cx, cy, images)
            name = COPY[item["character_id"]]["name"]
            lines = wrapped(name, 34, 7.8)
            assert len(lines) <= 2, name
            for i, line in enumerate(lines):
                draw_text(c, line, cx, cy - 20 - i * 3.2, 7.8)
            record.update(page=page_number, sheet_kind=kind)
            records.append(record)

    draw_text(c, "დააწებეთ თხელ მუყაოზე და ამოჭერით გარე წრეზე.", 18, 27, 9, align="left")
    draw_text(c, "ფიშკები რუკაზე პერსონაჟების გადაადგილებისთვის გამოიყენეთ.", 18, 21, 8.5, align="left", ink=PAL["muted"])
    draw_text(c, "საკონტროლო სიგრძე: 30 მმ", 174, 26, 7.2, ink=PAL["muted"])
    c.setStrokeColor(colors.HexColor(PAL["green"]))
    c.setLineWidth(.22 * MM)
    c.line(159 * MM, 19 * MM, 189 * MM, 19 * MM)
    for x in (159, 189):
        c.line(x * MM, 17.5 * MM, x * MM, 20.5 * MM)
    return records


def build(path, groups, images):
    c = canvas.Canvas(str(path), pagesize=tuple(n * MM for n in SPEC["paper_mm"]), pageCompression=1)
    c.setTitle("პერსონაჟთა ფიშკები / 30 მმ")
    c.setAuthor("ვეფხისტყაოსნის პროექტი")
    records = []
    for index, (kind, items) in enumerate(groups, 1):
        records += sheet(c, items, kind, images, index)
        c.showPage()
    c.save()
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert len(PORTRAITS) == len({p["character_id"] for p in PORTRAITS}) == 35
    painted = [p for p in PORTRAITS if p["status"] != "generic_silhouette"]
    silhouettes = [p for p in PORTRAITS if p["status"] == "generic_silhouette"]
    assert len(painted) == 21 and len(silhouettes) == 14
    images = image_readers()
    all_path = OUT / "pantersskin-character-tokens-ka-30mm-a4.pdf"
    painted_path = OUT / "pantersskin-character-tokens-ka-painted-21-30mm-a4.pdf"
    records = build(all_path, [("painted_portraits", painted), ("generic_silhouettes", silhouettes)], images)
    build(painted_path, [("painted_portraits", painted)], images)
    manifest = {"date": "2026-11-09", "language": "ka", "diameter_mm": 30,
                "painted_tokens": 21, "silhouette_tokens": 14, "total_tokens": 35,
                "paper_mm": SPEC["paper_mm"], "print_scale": "100% / actual size",
                "print_sides": "single-sided", "printed_image_dpi": round(600 / (29 / 25.4), 1),
                "portrait_source": "print-and-play/character-deck/portrait-manifest.json",
                "portrait_processing": "Same centred full medallions as the cards; thumbnails embedded at up to 600 px. Original assets unchanged.",
                "name_placement": "Georgian short names inside the circular cut line; full names on the sheet below each disc.",
                "tokens": records,
                "pdfs": [{"path": str(p.relative_to(ROOT)), "pages": n,
                          "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p, n in ((all_path, 2), (painted_path, 1))]}
    (OUT / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for path in (all_path, painted_path):
        print(path.resolve())


if __name__ == "__main__":
    main()
