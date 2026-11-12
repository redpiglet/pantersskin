#!/usr/bin/env python3
"""One actual-size front/back proof, using existing artwork unchanged."""

import argparse
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output" / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("--design", default="design.json", help="Layout specification beside this script")
ARGS = parser.parse_args()
DESIGN = json.loads((HERE / ARGS.design).read_text())
TYPE = DESIGN.get("typography_overrides", {})
DATA = json.loads((ROOT / DESIGN["content_source"]).read_text())
CARD = next(c for c in DATA["characters"] if c["id"] == DESIGN["character_id"])
CHARACTERS = {c["id"]: c for c in DATA["characters"]}
STRIP = DESIGN["back"]["chapter_strip"]
PRESENCE = CARD["chapter_presence"]
if PRESENCE is None or PRESENCE["status"] != "reviewed_draft":
    raise ValueError("Review this character's chapter appearances before rendering a presence strip.")
APPEARS_IN = set(PRESENCE["included_chapters"])
assert len(PRESENCE["binary"]) == STRIP["total_chapters"] == 65
assert PRESENCE["binary"] == [int(n in APPEARS_IN) for n in range(1, 66)]

FONTS = Path("/System/Library/Fonts/Supplemental")
for name, filename in [
    ("Body", "Arial.ttf"), ("BodyBold", "Arial Bold.ttf"),
    ("BodyItalic", "Arial Italic.ttf"),
    ("Display", "Georgia.ttf"), ("DisplayBold", "Georgia Bold.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="BodyItalic")

PALETTE = {k: colors.HexColor(v) for k, v in DESIGN["palette"].items()}
IVORY = PALETTE["ivory"]
GREEN = PALETTE["dark_green"]
INK = PALETTE["body_ink"]
GOLD = PALETTE["antique_gold"]
MUTED = PALETTE["muted_ink"]
MM = 72 / 25.4
CW = DESIGN["card_size_mm"]["width"] * MM
CH = DESIGN["card_size_mm"]["height"] * MM
PAGE = landscape(A4)
PDF = OUT / DESIGN.get("output_filename", f"tariel-character-card-design-v{DESIGN['revision']}.pdf")
C = canvas.Canvas(str(PDF), pagesize=PAGE, pageCompression=1)
C.setTitle("Tariel: front and back character-card design study")
C.setAuthor("Pantersskin project")
C.setSubject(f"One {DESIGN['card_size_mm']['width']} x {DESIGN['card_size_mm']['height']} mm card, both sides at actual size; existing portrait placeholder")


def clean(s):
    return s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")


def text(s, x, y, size=10, font="Body", color=INK, align="left"):
    C.setFillColor(color)
    C.setFont(font, size)
    if align == "center": C.drawCentredString(x, y, clean(s))
    elif align == "right": C.drawRightString(x, y, clean(s))
    else: C.drawString(x, y, clean(s))


def spaced(s, cx, y, size=8, spacing=1.25, color=GREEN):
    C.saveState()
    width = pdfmetrics.stringWidth(s, "Body", size) + (len(s) - 1) * spacing
    t = C.beginText(cx - width / 2, y)
    t.setFont("Body", size)
    t.setCharSpace(spacing)
    t.setFillColor(color)
    t.textOut(s)
    C.drawText(t)
    C.restoreState()


def para(s, x, top, width, size=9.8, leading=12.3, color=INK, font="Body", centered=False):
    p = Paragraph(clean(s), ParagraphStyle(
        "p", fontName=font, fontSize=size, leading=leading,
        textColor=color, alignment=1 if centered else 0,
    ))
    _, height = p.wrap(width, 2000)
    p.drawOn(C, x, top - height)
    return top - height


def line(x1, y1, x2, y2, color=GOLD, width=0.55):
    C.setStrokeColor(color)
    C.setLineWidth(width)
    C.line(x1, y1, x2, y2)


def diamond(cx, cy, size=2.4):
    p = C.beginPath()
    p.moveTo(cx, cy + size)
    p.lineTo(cx + size, cy)
    p.lineTo(cx, cy - size)
    p.lineTo(cx - size, cy)
    p.close()
    C.setFillColor(GOLD)
    C.drawPath(p, fill=1, stroke=0)


def base():
    C.setFillColor(IVORY)
    C.setStrokeColor(GREEN)
    C.setLineWidth(0.8)
    C.roundRect(0, 0, CW, CH, 11, stroke=1, fill=1)
    C.setStrokeColor(GOLD)
    C.setLineWidth(0.45)
    C.roundRect(6, 6, CW - 12, CH - 12, 7, stroke=1, fill=0)


def draw_front():
    base()
    spaced(DESIGN["front"]["realm_label"], CW / 2, CH - 24, 7.2, 1.05, GREEN)
    portrait_size = min(CW - 60, CH - 202)
    C.drawImage(ImageReader(str(ROOT / DESIGN["portrait_asset"])),
                (CW - portrait_size) / 2, 159, width=portrait_size, height=portrait_size,
                preserveAspectRatio=True, mask="auto")
    text(CARD["name"]["en"].upper(), CW / 2, 127, TYPE.get("front_name", 28.5), "DisplayBold", GREEN, "center")
    line(57, 105, CW / 2 - 6, 105)
    line(CW / 2 + 6, 105, CW - 57, 105)
    diamond(CW / 2, 105, 2)
    text(DESIGN["front"]["role_lines"][0], CW / 2, 89, TYPE.get("front_role", 10.4), "BodyBold", GREEN, "center")
    text(DESIGN["front"]["role_lines"][1], CW / 2, 75, TYPE.get("front_epithet", 9.6), "BodyItalic", MUTED, "center")
    bottom = para(CARD["front"]["short_description"], 18, 58, CW - 36,
                  size=TYPE.get("front_description", 9.6), leading=TYPE.get("front_description_leading", 12.1), centered=True)
    assert bottom > 18, bottom
    spaced("THE KNIGHT IN THE PANTHER'S SKIN", CW / 2, 12, 5.5, 0.55, MUTED)


def back_label(label, top):
    text(label.upper(), 18, top, 7.9, "BodyBold", GREEN)
    return top - 11


def chapter_strip():
    """One stable position per chapter; never use source citations as presence."""
    count = STRIP["total_chapters"]
    radius = STRIP["circle_diameter_pt"] / 2
    pitch = STRIP["center_pitch_pt"]
    group = STRIP["group_size"]
    group_gap = STRIP["extra_group_gap_pt"]
    width = 2 * radius + (count - 1) * pitch + ((count - 1) // group) * group_gap
    assert width <= CW - 36, width
    left = (CW - width) / 2 + radius
    centers = {n: left + (n - 1) * pitch + ((n - 1) // group) * group_gap
               for n in range(1, count + 1)}
    line(18, 44, CW - 18, 44)
    text("CHAPTER APPEARANCES", 18, 33, TYPE.get("strip_heading", 6.7), "BodyBold", GREEN)
    # A small binary legend sits on the same line as the label.
    for x, label, filled in [(CW - 87, "appears", True), (CW - 43, "absent", False)]:
        C.setStrokeColor(GREEN)
        C.setFillColor(GREEN if filled else IVORY)
        C.setLineWidth(0.3)
        C.circle(x, 35, 1.4, fill=1, stroke=1)
        text(label, x + 4.2, 32.9, TYPE.get("strip_legend", 6.2), "Body", MUTED)
    for chapter in range(1, count + 1):
        C.setFillColor(GREEN if chapter in APPEARS_IN else IVORY)
        C.setStrokeColor(GREEN)
        C.setLineWidth(0.27)
        C.circle(centers[chapter], 21.5, radius, fill=1, stroke=1)
    ticks = STRIP["ticks"]
    major = set(range(ticks["major_interval"], count + 1, ticks["major_interval"]))
    if ticks["include_endpoints"]:
        major.update((1, count))
    minor = set(range(ticks["minor_interval"], count + 1, ticks["minor_interval"])) - major
    for chapter in sorted(major | minor):
        is_major = chapter in major
        length = ticks["major_length_pt"] if is_major else ticks["minor_length_pt"]
        stroke = ticks["major_stroke_pt"] if is_major else ticks["minor_stroke_pt"]
        line(centers[chapter], ticks["start_y_pt"],
             centers[chapter], ticks["start_y_pt"] - length, GREEN, stroke)
    for chapter in STRIP["index_labels"]:
        index_size = TYPE.get("strip_index", 5.3)
        index_y = TYPE.get("strip_index_y", 10.5)
        if chapter == 1:
            text(str(chapter), centers[chapter] - radius, index_y, index_size, "Body", MUTED)
        elif chapter == count:
            text(str(chapter), centers[chapter] + radius, index_y, index_size, "Body", MUTED, "right")
        else:
            text(str(chapter), centers[chapter], index_y, index_size, "Body", MUTED, "center")


def draw_back():
    base()
    spaced("CHARACTER NOTES", CW / 2, CH - 24, 7.2, 1.05, GREEN)
    text(CARD["name"]["en"], 18, CH - 49, TYPE.get("back_name", 23), "DisplayBold", GREEN)
    line(18, CH - 58, CW - 18, CH - 58)
    y = back_label("Story", CH - 70)
    copy = DESIGN["back"].get("display_copy", {})
    section_gap = DESIGN["back"].get("section_gap_pt", 16)
    y = para(copy.get("overview", CARD["back"]["overview"]), 18, y, CW - 36,
             size=TYPE.get("story", 9.8), leading=TYPE.get("story_leading", 12.3)) - section_gap
    y = back_label("Interpretation", y)
    insights = copy.get("insights", [i["text"] for i in CARD["back"]["insights"]])
    for i, insight in enumerate(insights):
        y = para(insight, 18, y, CW - 36,
                 size=TYPE.get("insight", 9.6), leading=TYPE.get("insight_leading", 12.1), font="BodyItalic")
        if i == 0: y -= 6
    y -= section_gap
    if "interaction_gallery" in DESIGN["back"]:
        y = back_label("Interacted with", y)
        y = interaction_gallery(y)
    else:
        y = back_label("Connections", y)
        for relation in DESIGN["back"]["connections"]:
            y = para(f"<b>{relation['name']}</b>  /  {relation['label']}",
                     18, y, CW - 36, size=TYPE.get("connection", 9.2), leading=TYPE.get("connection_leading", 11.7)) - 3
    assert y > 49, y
    chapter_strip()


def interaction_gallery(top):
    """Every recorded contact, resolving the same portrait used on their own card."""
    config = DESIGN["back"]["interaction_gallery"]
    ids = CARD["interacted_with"]
    assert len(ids) == len(set(ids)) and CARD["id"] not in ids
    if not ids:
        return para("No recorded encounters in this cast.", 18, top, CW - 36,
                    size=9, leading=11, color=MUTED)
    columns = config["columns"]
    rows = (len(ids) + columns - 1) // columns
    cell_width = (CW - 36) / columns
    diameter = config["portrait_diameter_pt"]
    row_height = config["row_height_pt"]
    label_size = config["label_size_pt"]
    label_leading = config["label_leading_pt"]
    labels = config.get("display_names", {})
    for index, character_id in enumerate(ids):
        target = CHARACTERS[character_id]
        row, column = divmod(index, columns)
        # Center the final, partially filled row as a group.
        row_count = min(columns, len(ids) - row * columns)
        inset = (columns - row_count) * cell_width / 2
        cx = 18 + inset + (column + .5) * cell_width
        image_top = top - row * row_height
        image_bottom = image_top - diameter
        asset = target["portrait"]["existing_asset"]
        C.saveState()
        clipping = C.beginPath()
        clipping.circle(cx, image_bottom + diameter / 2, diameter / 2)
        C.clipPath(clipping, stroke=0)
        if asset:
            if not (ROOT / asset).is_file():
                raise FileNotFoundError(asset)
            C.drawImage(ImageReader(str(ROOT / asset)), cx - diameter / 2,
                        image_bottom, width=diameter, height=diameter,
                        preserveAspectRatio=True, mask="auto")
        else:
            C.setFillColor(colors.HexColor("#E8E6DD"))
            C.rect(cx - diameter / 2, image_bottom, diameter, diameter, fill=1, stroke=0)
            C.setFillColor(colors.HexColor("#A9B0A6"))
            C.circle(cx, image_bottom + diameter * .65, diameter * .15, fill=1, stroke=0)
            C.ellipse(cx - diameter * .32, image_bottom - diameter * .04,
                      cx + diameter * .32, image_bottom + diameter * .44, fill=1, stroke=0)
        C.restoreState()
        C.setStrokeColor(GOLD)
        C.setLineWidth(.5)
        C.circle(cx, image_bottom + diameter / 2, diameter / 2, fill=0, stroke=1)
        bottom = para(labels.get(character_id, target["name"]["en"]),
                      cx - cell_width / 2 + 1, image_bottom - 3, cell_width - 2,
                      size=label_size, leading=label_leading, centered=True, color=GREEN)
        assert bottom >= image_top - row_height + 1, (character_id, bottom, image_top - row_height)
    return top - rows * row_height


def cropmarks(x, y):
    C.saveState()
    C.setStrokeColor(colors.HexColor("#B8BDB6"))
    C.setLineWidth(0.35)
    for xx, yy, sx, sy in [(x, y, -1, -1), (x + CW, y, 1, -1),
                            (x, y + CH, -1, 1), (x + CW, y + CH, 1, 1)]:
        C.line(xx + sx * 3, yy, xx + sx * 9, yy)
        C.line(xx, yy + sy * 3, xx, yy + sy * 9)
    C.restoreState()


PW, PH = PAGE
gap = 42
left = (PW - 2 * CW - gap) / 2
bottom = DESIGN.get("proof_bottom_pt", 93)
text("CHARACTER CARD  /  ONE DESIGN EXAMPLE", 42, PH - 33, 8.5, "BodyBold", MUTED)
text("Tariel", 42, PH - 62, 22, "DisplayBold", GREEN)
text(f"Proposed size: {DESIGN['card_size_mm']['width']} x {DESIGN['card_size_mm']['height']} mm. Both sides at actual size on this A4 proof.",
     PW - 42, PH - 56, 9.2, "Body", MUTED, "right")

for i, draw in enumerate([draw_front, draw_back]):
    x = left + i * (CW + gap)
    text("FRONT" if i == 0 else "BACK", x + CW / 2, bottom + CH + 16,
         8.5, "BodyBold", MUTED, "center")
    C.saveState()
    C.translate(x, bottom)
    draw()
    C.restoreState()
    cropmarks(x, bottom)

text("English-only sample. The 65 circles show chapter appearances: filled = appears; outlined = absent. Flashbacks count.",
     PW / 2, 61, 9, "Body", MUTED, "center")
text(DESIGN.get("proof_note", "Existing portrait used as a placeholder. Print at 100% to judge card size, text, and the chapter strip. This is a layout proof."),
     PW / 2, 43, 8.2, "Body", MUTED, "center")
C.save()
print(PDF)
