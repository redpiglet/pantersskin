#!/usr/bin/env python3
"""Build the English or Georgian character deck from the selected portraits."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

rl_config.useA85 = False

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SETTINGS = json.loads((HERE / "deck-settings.json").read_text())
parser = argparse.ArgumentParser()
parser.add_argument("--language", choices=["en", "ka"], default="en")
parser.add_argument("--card-size", choices=["A6", "A5"], default=SETTINGS["card_size"])
parser.add_argument("--check-layout", action="store_true", help="Check every text block without writing PDFs")
parser.add_argument("--overviews", action="store_true", help="Also create full-cast overview PDFs")
parser.add_argument("--painted-only", action="store_true", help="Include only characters with finished painted portraits")
ARGS = parser.parse_args()
LANG = ARGS.language
SIZE = ARGS.card_size
PREFIX = "pantersskin-character-cards" + ("-ka" if LANG == "ka" else "")
OUT = ROOT / "output" / (("character-cards-ka" if LANG == "ka" else "character-cards") + ("-a5" if SIZE == "A5" else ""))
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((ROOT / "data/character-cards.json").read_text())
COPY = json.loads((HERE / ("display-copy.ka.json" if LANG == "ka" else "display-copy.json")).read_text())
UI = json.loads((HERE / "locale.ka.json").read_text()) if LANG == "ka" else {
    "deck_title": "THE KNIGHT IN THE PANTHER'S SKIN", "project": "PANTERSSKIN",
    "character_notes": "CHARACTER NOTES", "story": "Story", "interpretation": "Interpretation",
    "interacted_with": "Interacted with", "chapter_appearances": "CHAPTERS",
    "appears": "appears", "absent": "absent", "portrait_pending": "PORTRAIT PENDING",
    "front": "front", "back": "back", "fronts": "fronts", "backs": "backs",
    "empty_frame": "The framing narrator stands outside the characters' encounters.",
    "empty_story": "No depicted encounters with the carded cast.",
    "sheet": "SHEET", "language": "English", "latest_portrait": "Latest selected portrait",
    "placeholder_note": "Portrait pending / silhouette placeholder", "all_contacts": "relationships with portraits",
    "print_instruction": "A6 / 105 x 148 mm / print at 100% / landscape / duplex: flip on short edge",
    "overview": "ALL 35 CHARACTER",
}
MANIFEST = json.loads((HERE / "portrait-manifest.json").read_text())
CARDS = DATA["characters"]
BY_ID = {c["id"]: c for c in CARDS}
assert len(CARDS) == len(BY_ID) == len(COPY) == 35

MM = 72 / 25.4
CARD_MM = [148, 210] if SIZE == "A5" else [105, 148]
PCW, PCH = (n * MM for n in CARD_MM)
LAYOUT_SCALE = CARD_MM[0] / 105
# Preserve the approved proportions with a uniform scale, adjusting only logical height.
CW, CH = PCW / LAYOUT_SCALE, PCH / LAYOUT_SCALE
MAX_IMAGE_PX = 1200 if SIZE == "A5" else 900
if LANG == "ka":
    orientation = "ვერტიკალურად" if SIZE == "A5" else "თარაზულად"
    flip = "გრძელ" if SIZE == "A5" else "მოკლე"
    UI["print_instruction"] = f"{SIZE} / {CARD_MM[0]} × {CARD_MM[1]} მმ / ბეჭდვა 100%-ზე / {orientation} / ორმხრივად: გადაბრუნება {flip} კიდეზე"
else:
    orientation = "portrait" if SIZE == "A5" else "landscape"
    flip = "long" if SIZE == "A5" else "short"
    UI["print_instruction"] = f"{SIZE} / {CARD_MM[0]} x {CARD_MM[1]} mm / print at 100% / {orientation} / duplex: flip on {flip} edge"
IVORY = colors.HexColor("#F8F5EC")
GREEN = colors.HexColor("#203D37")
INK = colors.HexColor("#303B34")
GOLD = colors.HexColor("#A58958")
MUTED = colors.HexColor("#647168")
FONTS = Path("/System/Library/Fonts/Supplemental")
if LANG == "ka":
    from prepare_georgian_fonts import prepare
    font_cache = prepare(ROOT)
    font_files = {"Body": font_cache / "Georgian-Regular.ttf",
                  "BodyBold": font_cache / "Georgian-Bold.ttf",
                  "BodyItalic": font_cache / "Georgian-Regular.ttf",
                  "Display": font_cache / "Georgian-Display.ttf",
                  "DisplayBold": font_cache / "Georgian-Display.ttf"}
else:
    font_files = {name: FONTS / filename for name, filename in [
        ("Body", "Arial.ttf"), ("BodyBold", "Arial Bold.ttf"),
        ("BodyItalic", "Arial Italic.ttf"),
        ("Display", "Georgia.ttf"), ("DisplayBold", "Georgia Bold.ttf")]}
for name, path in font_files.items():
    pdfmetrics.registerFont(TTFont(name, str(path)))
if LANG == "ka":
    for name, filename in [("Latin", "Arial.ttf"), ("LatinBold", "Arial Bold.ttf"),
                           ("LatinItalic", "Arial Italic.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="BodyItalic")

SHORT_NAMES = {
    "queen_india": "Indian Queen", "khvarazmsha": "Prince of Khwarazm",
    "khvarazmshah": "King of Khwarazm", "chashnagiri": "Chashnagir",
    "eldest_hunting_brother": "Eldest brother",
    "middle_hunting_brother": "Middle brother",
    "youngest_hunting_brother": "Youngest brother",
    "khatavian_informant": "Khatavian informant", "tariel_surgeon": "Surgeon",
    "usen_gardener": "Usen's gardener", "fatman_messenger": "Messenger",
    "kadji_informant": "Kadji informant", "sea_kings_son": "Sea King's son",
}
IMAGES = {}
# Generic silhouettes are front artwork, not finished likenesses for contact galleries.
PAINTED_PORTRAIT_IDS = set()
SILHOUETTE_IDS = set()
for item in MANIFEST["portraits"]:
    card = BY_ID[item["character_id"]]
    assert card["portrait"]["existing_asset"] == item["asset"]
    if item["asset"]:
        path = ROOT / item["asset"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        # Keep more than 300 dpi at the large medallion's actual printed size.
        # Only the embedded PDF payload is resized; original artwork is untouched.
        with Image.open(path) as original:
            payload = original.copy()
        if max(payload.size) > MAX_IMAGE_PX:
            payload.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX), Image.Resampling.LANCZOS)
        IMAGES[item["character_id"]] = ImageReader(payload)
        if item["status"] == "generic_silhouette":
            assert card["portrait"]["status"] == "generic_silhouette"
            SILHOUETTE_IDS.add(item["character_id"])
        else:
            PAINTED_PORTRAIT_IDS.add(item["character_id"])


def visible_contacts(card):
    ids = card["interacted_with"]
    if SETTINGS["relationships"]["show_only_with_portraits"]:
        return [cid for cid in ids if cid in PAINTED_PORTRAIT_IDS]
    return ids


def plain(s):
    return s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")


def card_name(card):
    return COPY[card["id"]].get("name", card["name"]["en"])


def font_runs(s, font):
    """Native Georgian fonts omit digits; embed Arial just for missing glyphs."""
    if LANG != "ka":
        return [(font, s)]
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    fallback = "LatinBold" if "Bold" in font or "Display" in font else \
               "LatinItalic" if "Italic" in font else "Latin"
    runs = []
    for char in s:
        selected = font if ord(char) in cmap else fallback
        assert ord(char) in pdfmetrics.getFont(selected).face.charToGlyph, (font, char, hex(ord(char)))
        if runs and runs[-1][0] == selected:
            runs[-1] = (selected, runs[-1][1] + char)
        else:
            runs.append((selected, char))
    return runs


def text_width(s, font, size):
    return sum(pdfmetrics.stringWidth(run, family, size) for family, run in font_runs(s, font))


def paragraph(s, width, size=10, leading=12, font="Body", centered=False, color=INK):
    markup = "<br/>".join("".join(escape(run) if family == font else
                                  f'<font name="{family}">{escape(run)}</font>'
                                  for family, run in font_runs(line, font))
                           for line in plain(s).split("\n"))
    p = Paragraph(markup, ParagraphStyle(
        "card", fontName=font, fontSize=size, leading=leading,
        textColor=color, alignment=1 if centered else 0,
    ))
    _, height = p.wrap(width, 2000)
    return p, height


class Renderer:
    def __init__(self, c):
        self.c = c
        self.metrics = {}

    def text(self, s, x, y, size=10, font="Body", color=INK, align="left"):
        self.c.setFillColor(color)
        s = plain(s)
        width = text_width(s, font, size)
        x -= width / 2 if align == "center" else width if align == "right" else 0
        for family, run in font_runs(s, font):
            self.c.setFont(family, size)
            self.c.drawString(x, y, run)
            x += pdfmetrics.stringWidth(run, family, size)

    def spaced(self, s, cx, y, size=7.2, spacing=1.05, color=GREEN):
        self.c.saveState()
        if LANG == "ka":
            spacing = min(spacing, .5)
        width = text_width(s, "Body", size) + (len(s) - 1) * spacing
        if width > CW - 36:
            size *= (CW - 36) / width
            spacing *= (CW - 36) / width
            width = text_width(s, "Body", size) + (len(s) - 1) * spacing
        t = self.c.beginText(cx - width / 2, y)
        t.setCharSpace(spacing)
        t.setFillColor(color)
        for family, run in font_runs(s, "Body"):
            t.setFont(family, size)
            t.textOut(run)
        self.c.drawText(t)
        self.c.restoreState()

    def para(self, s, x, top, width, **kwargs):
        p, height = paragraph(s, width, **kwargs)
        p.drawOn(self.c, x, top - height)
        return top - height

    def rule(self, x1, y1, x2, y2, color=GOLD, width=.55):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.line(x1, y1, x2, y2)

    def base(self):
        self.c.setFillColor(IVORY)
        self.c.setStrokeColor(GREEN)
        self.c.setLineWidth(.8)
        self.c.roundRect(0, 0, CW, CH, 11, fill=1, stroke=1)
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(.45)
        self.c.roundRect(6, 6, CW - 12, CH - 12, 7, fill=0, stroke=1)

    def portrait(self, cid, cx, bottom, diameter):
        if ARGS.check_layout:
            return
        self.c.saveState()
        path = self.c.beginPath()
        path.circle(cx, bottom + diameter / 2, diameter / 2)
        self.c.clipPath(path, stroke=0)
        if cid in IMAGES:
            self.c.drawImage(IMAGES[cid], cx - diameter / 2, bottom,
                             width=diameter, height=diameter,
                             preserveAspectRatio=True, mask="auto")
        else:
            self.c.setFillColor(colors.HexColor("#E8E6DD"))
            self.c.rect(cx - diameter / 2, bottom, diameter, diameter, fill=1, stroke=0)
            self.c.setFillColor(colors.HexColor("#A9B0A6"))
            self.c.circle(cx, bottom + diameter * .65, diameter * .15, fill=1, stroke=0)
            self.c.ellipse(cx - diameter * .32, bottom - diameter * .04,
                           cx + diameter * .32, bottom + diameter * .44, fill=1, stroke=0)
        self.c.restoreState()
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(.5 if diameter < 50 else .8)
        self.c.circle(cx, bottom + diameter / 2, diameter / 2, fill=0, stroke=1)

    def label(self, s, y):
        self.text(s.upper(), 18, y, 7.9, "BodyBold", GREEN)
        return y - 11

    def front(self, card):
        cid = card["id"]
        copy = COPY[cid]
        self.base()
        self.spaced(copy["realm_label"], CW / 2, CH - 24)
        self.portrait(cid, CW / 2, 183, 195)
        if cid not in PAINTED_PORTRAIT_IDS:
            # Keep the pending label readable below dark generated silhouettes.
            pending_y = 174 if cid in SILHOUETTE_IDS else 197
            self.spaced(UI["portrait_pending"], CW / 2, pending_y, 6, .7, MUTED)

        # A fixed title area accommodates both short names and unnamed roles.
        name = card_name(card).upper()
        if LANG == "ka" and "-" in name and text_width(name, "DisplayBold", 31) > CW - 36:
            name = name.replace("-", "-\n")
        for size in [31, 29, 27, 25, 23, 21, 20]:
            p, height = paragraph(name, CW - 36, size, size + 2,
                                  "DisplayBold", centered=True, color=GREEN)
            if height <= 52:
                break
        assert height <= 52, (cid, "front title")
        p.drawOn(self.c, 18, 116 + (52 - height) / 2)
        self.rule(57, 108, CW / 2 - 6, 108)
        self.rule(CW / 2 + 6, 108, CW - 57, 108)
        path = self.c.beginPath()
        path.moveTo(CW / 2, 110)
        path.lineTo(CW / 2 + 2, 108)
        path.lineTo(CW / 2, 106)
        path.lineTo(CW / 2 - 2, 108)
        path.close()
        self.c.setFillColor(GOLD)
        self.c.drawPath(path, fill=1, stroke=0)
        role_bottom = self.para(copy["role"], 18, 98, CW - 36,
                                size=10.6, leading=12.3, font="BodyBold",
                                centered=True, color=GREEN)
        assert role_bottom >= 71, (cid, "front role", role_bottom)
        desc = copy.get("short_description", card["front"]["short_description"])
        p, height = paragraph(desc, CW - 36, 10.1, 12.2, centered=True)
        if height > 40:
            p, height = paragraph(desc, CW - 36, 9.6, 11.7, centered=True)
        assert height <= 40, (cid, "front description", height)
        p.drawOn(self.c, 18, 61 - height)
        self.spaced(UI["deck_title"], CW / 2, 12, 5.5, .55, MUTED)
        self.metrics.setdefault(cid, {}).update(front_title_pt=size,
                                               front_description_bottom_pt=61 - height)

    def strip(self, card):
        mask = card["chapter_presence"]
        assert mask["status"] == "reviewed_draft"
        assert len(mask["binary"]) == 65
        assert mask["binary"] == [int(n in mask["included_chapters"]) for n in range(1, 66)]
        radius, pitch, gap = 1.6, 3.88809, .8
        width = radius * 2 + 64 * pitch + 12 * gap
        left = (CW - width) / 2 + radius
        centers = {n: left + (n - 1) * pitch + ((n - 1) // 5) * gap for n in range(1, 66)}
        self.rule(18, 44, CW - 18, 44)
        self.text(UI["chapter_appearances"].upper(), 18, 33, 7.2, "BodyBold", GREEN)
        if SETTINGS["chapter_strip"]["show_legend"]:
            for x, label, filled in [(CW - 87, UI["appears"], True), (CW - 43, UI["absent"], False)]:
                self.c.setStrokeColor(GREEN)
                self.c.setFillColor(GREEN if filled else IVORY)
                self.c.setLineWidth(.3)
                self.c.circle(x, 35, 1.4, fill=1, stroke=1)
                self.text(label, x + 4.2, 32.9, 6.8, color=MUTED)
        for n in range(1, 66):
            self.c.setFillColor(GREEN if mask["binary"][n - 1] else IVORY)
            self.c.setStrokeColor(GREEN)
            self.c.setLineWidth(.27)
            self.c.circle(centers[n], 21.5, radius, fill=1, stroke=1)
            if n in (1, 65) or n % 5 == 0:
                major = n in (1, 65) or n % 10 == 0
                self.rule(centers[n], 18.2, centers[n], 18.2 - (2.8 if major else 1.5),
                          GREEN, .35 if major else .25)
        for n in (1, 10, 20, 30, 40, 50, 60, 65):
            x, align = (centers[n] - radius, "left") if n == 1 else \
                       (centers[n] + radius, "right") if n == 65 else (centers[n], "center")
            self.text(str(n), x, 9.6, 6.2, color=MUTED, align=align)

    def gallery(self, card, top):
        ids = visible_contacts(card)
        assert len(ids) == len(set(ids)) and card["id"] not in ids
        if not ids:
            message = UI["empty_frame"] if card["section"] == "frame" else UI["empty_story"]
            return self.para(message, 18, top, CW - 36, size=9.5,
                             leading=12, font="BodyItalic", color=MUTED)
        columns = min(4, len(ids)) if len(ids) <= 8 else 5
        dense = len(ids) > 10
        cell_width = (CW - 36) / columns
        rows = math.ceil(len(ids) / columns)
        preferred_diameter, preferred_row = (36, 56) if dense else (38, 59)
        row_height = min(preferred_row, (top - 50) / rows)
        diameter = min(preferred_diameter, row_height - 19)
        assert diameter >= 23, (card["id"], "interaction portraits too small")
        for index, target in enumerate(ids):
            assert card["id"] in BY_ID[target]["interacted_with"], (card["id"], target)
            row, col = divmod(index, columns)
            row_count = min(columns, len(ids) - row * columns)
            inset = (columns - row_count) * cell_width / 2
            cx = 18 + inset + (col + .5) * cell_width
            image_top = top - row * row_height
            self.portrait(target, cx, image_top - diameter, diameter)
            target_name = COPY[target].get("short_name", SHORT_NAMES.get(target, card_name(BY_ID[target])))
            if LANG == "ka":
                target_name = " ".join(word.replace("-", "-\n")
                                       if "-" in word and text_width(word, "Body", 7) > cell_width - 2
                                       else word for word in target_name.split(" "))
            bottom = self.para(target_name,
                               cx - cell_width / 2 + 1, image_top - diameter - 3,
                               cell_width - 2, size=7, leading=7.5,
                               centered=True, color=GREEN)
            assert bottom >= image_top - row_height + 1, (card["id"], target, "gallery label")
        return top - rows * row_height

    def back(self, card):
        cid, copy = card["id"], COPY[card["id"]]
        self.base()
        self.spaced(UI["character_notes"].upper(), CW / 2, CH - 24)
        name_size = min(25, 25 * (CW - 36) / text_width(card_name(card), "DisplayBold", 25))
        assert name_size >= 17, (cid, "back name")
        self.text(card_name(card), 18, CH - 49, name_size, "DisplayBold", GREEN)
        self.rule(18, CH - 58, CW - 18, CH - 58)
        y = self.label(UI["story"], CH - 70)
        y = self.para(copy["overview"], 18, y, CW - 36, size=10, leading=12) - 10
        y = self.label(UI["interpretation"], y)
        for insight in copy["insights"]:
            y = self.para(insight, 18, y, CW - 36, size=9.7, leading=11.7,
                          font="BodyItalic") - 6
        y = self.label(UI["interacted_with"], y - 10)
        gallery_top = y
        y = self.gallery(card, y)
        assert y > 49, (cid, "footer overlap", y)
        self.strip(card)
        self.metrics.setdefault(cid, {}).update(
            back_name_pt=round(name_size, 2), interaction_count=len(card["interacted_with"]),
            visible_interaction_ids=visible_contacts(card),
            interaction_top_pt=round(gallery_top, 2), content_bottom_pt=round(y, 2),
            chapter_count=len(card["chapter_presence"]["included_chapters"]),
            portrait=card["portrait"]["existing_asset"],
        )

    def cropmarks(self, x, y):
        self.c.saveState()
        self.c.setStrokeColor(colors.HexColor("#A5ADA5"))
        self.c.setLineWidth(.3)
        for xx, yy, sx, sy in [(x, y, -1, -1), (x + PCW, y, 1, -1),
                              (x, y + PCH, -1, 1), (x + PCW, y + PCH, 1, 1)]:
            self.c.line(xx + sx * 3, yy, xx + sx * 8, yy)
            self.c.line(xx, yy + sy * 3, xx, yy + sy * 8)
        self.c.restoreState()

    def placed(self, card, side, x=0, y=0, scale=1):
        self.c.saveState()
        self.c.translate(x, y)
        self.c.scale(scale * LAYOUT_SCALE, scale * LAYOUT_SCALE)
        getattr(self, side)(card)
        self.c.restoreState()


def new_pdf(path, pagesize, title):
    c = canvas.Canvas(str(path), pagesize=pagesize, pageCompression=1)
    c.setTitle("ვეფხისტყაოსანი / პერსონაჟების ბარათები" if LANG == "ka" else title)
    c.setAuthor("ვეფხისტყაოსნის პროექტი" if LANG == "ka" else "Pantersskin project")
    c.setSubject("ქართული ბარათები / პორტრეტები, ურთიერთობები და თავებში გამოჩენა" if LANG == "ka" else
                 f"English {SIZE} character cards, selected latest portraits, interaction gallery and 65-chapter scale")
    return c, Renderer(c)


def main():
    deck_cards = [c for c in CARDS if c["id"] in PAINTED_PORTRAIT_IDS] if ARGS.painted_only else CARDS
    if ARGS.check_layout:
        r = Renderer(canvas.Canvas(io.BytesIO(), pagesize=(PCW, PCH)))
        for card in deck_cards:
            r.front(card)
            r.back(card)
        print(json.dumps(r.metrics, ensure_ascii=False, indent=2))
        return
    pdfs = []
    suffix = "-painted-21" if ARGS.painted_only else ""
    edition_prefix = PREFIX + ("-a5" if SIZE == "A5" else "") + suffix
    path = OUT / f"{PREFIX}-{SIZE.lower()}{suffix}.pdf"
    c, r = new_pdf(path, (PCW, PCH), f"Pantersskin: {len(deck_cards)} {SIZE} character cards, front then back")
    for card in deck_cards:
        for side in ("front", "back"):
            c.bookmarkPage(card["id"] + "-" + side)
            c.addOutlineEntry(card_name(card) + " / " + UI[side], card["id"] + "-" + side, 0)
            r.placed(card, side)
            c.showPage()
    c.save()
    metrics = r.metrics
    pdfs.append({"file": str(path.relative_to(ROOT)), "pages": 2 * len(deck_cards), "page_size_mm": CARD_MM})

    page = A4 if SIZE == "A5" else landscape(A4)
    pw, ph = page
    gap = 10 * MM
    per_sheet = 1 if SIZE == "A5" else 2
    bottom = (ph - PCH) / 2
    if per_sheet == 1:
        slots = [(pw - PCW) / 2]
    else:
        left = (pw - 2 * PCW - gap) / 2
        slots = [left, left + PCW + gap]
    path = OUT / f"{edition_prefix}-a4-duplex.pdf"
    c, r = new_pdf(path, page, "Pantersskin: A4 duplex print sheets")
    sheets = []
    for start in range(0, len(deck_cards), per_sheet):
        pair = deck_cards[start:start + per_sheet]
        sheet = start // per_sheet + 1
        sheet_ids = [card["id"] for card in pair]
        if per_sheet == 1:
            sheets.append({"sheet": sheet, "front_center": sheet_ids[0], "back_center": sheet_ids[0]})
        else:
            sheets.append({"sheet": sheet, "front_left": sheet_ids[0],
                           "front_right": sheet_ids[1] if len(pair) > 1 else None,
                           "back_left": sheet_ids[1] if len(pair) > 1 else None,
                           "back_right": sheet_ids[0]})
        for side in ("front", "back"):
            for index, card in enumerate(pair):
                position = 0 if per_sheet == 1 else index if side == "front" else 1 - index
                r.placed(card, side, slots[position], bottom)
                r.cropmarks(slots[position], bottom)
                r.text(card_name(card) + " / " + UI[side], slots[position] + PCW / 2,
                       bottom - 17, 7, color=MUTED, align="center")
            r.text(f"{UI['project']} / {UI['sheet']} {sheet:02d} / {UI[side+'s'].upper()}", 30, ph - 25,
                   8, "BodyBold", MUTED)
            r.text(UI["print_instruction"],
                   pw / 2, 25, 8, color=MUTED, align="center")
            c.showPage()
    c.save()
    pdfs.append({"file": str(path.relative_to(ROOT)), "pages": 2 * math.ceil(len(deck_cards) / per_sheet),
                 "page_size_mm": [210, 297] if SIZE == "A5" else [297, 210],
                 "duplex_flip": "long_edge" if SIZE == "A5" else "short_edge",
                 "back_mapping": "same centered position" if SIZE == "A5" else "left-right mirrored",
                 "cards_per_sheet": per_sheet, "sheets": sheets})

    page = landscape(A3) if SIZE == "A5" else landscape(A4)
    pw, ph = page
    left, bottom = (pw - 2 * PCW - gap) / 2, (ph - PCH) / 2
    slots = [left, left + PCW + gap]
    path = OUT / f"{edition_prefix}-review.pdf"
    c, r = new_pdf(path, page, "Pantersskin: character fronts and backs, side by side")
    for index, card in enumerate(deck_cards, 1):
        r.text(f"{index:02d} / {card_name(card)}", 30, ph - 30, 14, "DisplayBold", GREEN)
        for position, side in enumerate(("front", "back")):
            r.placed(card, side, slots[position], bottom)
            r.text(UI[side].upper(), slots[position] + PCW / 2, bottom + PCH + 12,
                   8, "BodyBold", MUTED, "center")
        note = UI["latest_portrait"] if card["id"] in PAINTED_PORTRAIT_IDS else UI["placeholder_note"]
        r.text(note + f" / {UI['language']} / {SIZE} / {UI['all_contacts']}", pw / 2, 35,
               8, color=MUTED, align="center")
        c.showPage()
    c.save()
    pdfs.append({"file": str(path.relative_to(ROOT)), "pages": len(deck_cards),
                 "page_size_mm": [420, 297] if SIZE == "A5" else [297, 210]})

    # One overview page per side, useful for visual inspection of the entire cast.
    scale, cols, rows = .5, 7, math.ceil(len(deck_cards) / 7)
    gutter, margin = 13, 22
    overview_size = (cols * (PCW * scale + gutter) + margin * 2 - gutter,
                     rows * (PCH * scale + gutter) + margin * 2 + 30 - gutter)
    for side in (("front", "back") if ARGS.overviews else ()):
        path = OUT / f"{edition_prefix}-{side}s-overview.pdf"
        c, r = new_pdf(path, overview_size, "Pantersskin: complete cast / " + side + "s")
        r.text(UI["project"] + " / " + UI["overview"] + " / " + UI[side+"s"].upper(), margin,
               overview_size[1] - 21, 13, "BodyBold", GREEN)
        for index, card in enumerate(deck_cards):
            row, col = divmod(index, cols)
            x = margin + col * (PCW * scale + gutter)
            y = overview_size[1] - 43 - (row + 1) * PCH * scale - row * gutter
            r.placed(card, side, x, y, scale)
        c.save()

    build = {"date": "2026-11-08", "language": LANG, "card_count": len(deck_cards),
             "sides": 2, "card_size_mm": CARD_MM, "layout_scale": LAYOUT_SCALE,
             "portraits_available": len(PAINTED_PORTRAIT_IDS),
             "front_assets_available": len([c for c in deck_cards if c["id"] in IMAGES]),
             "generic_silhouette_assets": len([c for c in deck_cards if c["id"] in SILHOUETTE_IDS]),
             "silhouette_placeholders": len([c for c in deck_cards if c["id"] not in IMAGES]),
             "portrait_pending_fronts": len([c for c in deck_cards if c["id"] not in PAINTED_PORTRAIT_IDS]),
             "embedded_portrait_max_px": MAX_IMAGE_PX,
             "large_portrait_print_dpi": round(MAX_IMAGE_PX / (195 * LAYOUT_SCALE) * 72, 1),
             "settings": SETTINGS,
             "source": "data/character-cards.json", "display_copy": str((HERE / ("display-copy.ka.json" if LANG == "ka" else "display-copy.json")).relative_to(ROOT)),
             "portrait_manifest": "print-and-play/character-deck/portrait-manifest.json",
             "chapter_audit": "data/character-chapter-presence.json",
             "pdfs": pdfs, "layout_metrics": metrics}
    manifest_name = "build-manifest-painted-21.json" if ARGS.painted_only else "build-manifest.json"
    (OUT / manifest_name).write_text(json.dumps(build, ensure_ascii=False, indent=2) + "\n")
    for item in pdfs:
        print(item["file"])


if __name__ == "__main__":
    main()
