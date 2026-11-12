#!/usr/bin/env python3
"""Illustrated narrative board, full-size vector PDF and eight printable fold panels."""

import hashlib
import json
import math
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/foldable-realm-map"
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((HERE / "map-data.ka.json").read_text())
PRODUCTION = json.loads((HERE / "production-spec.json").read_text())
MM = 72 / 25.4
W, H = DATA["board_size_mm"]
IVORY = "#F8F5EC"
GREEN = "#203D37"
INK = "#33473E"
GOLD = "#A58958"
MUTED = "#6A786E"
SEA = "#E3ECE8"
LAND = "#F2EDDF"
LAND_ROUTE = "#426650"
SEA_ROUTE = "#50798B"
MIXED_ROUTE = "#94734C"
NARRATIVE_ROUTE = "#8B6C85"
ROUTE_STYLES = {
    "land": {"color": LAND_ROUTE, "dash": None},
    "sea": {"color": SEA_ROUTE, "dash": [3, 2.1]},
    "mixed": {"color": MIXED_ROUTE, "dash": [5, 1.7, .7, 1.7]},
    # A summary of a long, multi-stage journey is distinct from a physical road.
    "narrative": {"color": NARRATIVE_ROUTE, "dash": [.65, 1.65]},
}

sys.path.insert(0, str(ROOT / "print-and-play/character-deck"))
from prepare_georgian_fonts import prepare

font_cache = prepare(ROOT)
for name, file in [("Geo", "Georgian-Regular.ttf"), ("GeoBold", "Georgian-Bold.ttf"),
                   ("GeoDisplay", "Georgian-Display.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(font_cache / file)))
for name, file in [("Latin", "Arial.ttf"), ("LatinBold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + file))


def color(value):
    return colors.HexColor(value) if isinstance(value, str) else value


def runs(s, font):
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    fallback = "Latin" if font == "Geo" else "LatinBold"
    result = []
    for ch in s:
        selected = font if ord(ch) in cmap else fallback
        assert ord(ch) in pdfmetrics.getFont(selected).face.charToGlyph, (ch, hex(ord(ch)))
        if result and result[-1][0] == selected:
            result[-1] = (selected, result[-1][1] + ch)
        else:
            result.append((selected, ch))
    return result


def width(s, size, font):
    return sum(pdfmetrics.stringWidth(text, family, size) for family, text in runs(s, font)) / MM


class Drawing:
    def __init__(self, c):
        self.c = c
        self.label_boxes = []

    def text(self, s, x, y, size=11, font="Geo", ink=INK, align="left", primary=False):
        total = width(s, size, font)
        if align == "center":
            x -= total / 2
        elif align == "right":
            x -= total
        start = x
        self.c.setFillColor(color(ink))
        for family, text in runs(s, font):
            self.c.setFont(family, size)
            self.c.drawString(x * MM, y * MM, text)
            x += pdfmetrics.stringWidth(text, family, size) / MM
        if primary:
            box = [start, y - size / MM * .28, start + total, y + size / MM]
            self.label_boxes.append({"text": s, "bbox_mm": box})
        return total

    def para(self, s, x, top, max_width, size=10.5, leading=14, ink=INK, centered=False):
        markup = "".join(escape(text) if family == "Geo" else
                         f'<font name="{family}">{escape(text)}</font>'
                         for family, text in runs(s, "Geo"))
        p = Paragraph(markup, ParagraphStyle("map", fontName="Geo", fontSize=size,
                      leading=leading, textColor=color(ink), alignment=1 if centered else 0))
        _, h = p.wrap(max_width * MM, 2000)
        p.drawOn(self.c, x * MM, top * MM - h)
        return top - h / MM

    def line(self, x1, y1, x2, y2, ink=GOLD, weight=.25, dash=None):
        self.c.saveState()
        self.c.setStrokeColor(color(ink))
        self.c.setLineWidth(weight * MM)
        self.c.setDash([n * MM for n in dash] if dash else [])
        self.c.line(x1 * MM, y1 * MM, x2 * MM, y2 * MM)
        self.c.restoreState()

    def shape(self, commands, fill=None, stroke=None, weight=.25, dash=None):
        p = self.c.beginPath()
        for command, values in commands:
            values = [n * MM for n in values]
            if command == "M": p.moveTo(*values)
            elif command == "L": p.lineTo(*values)
            elif command == "C": p.curveTo(*values)
            elif command == "Z": p.close()
        self.c.saveState()
        if fill: self.c.setFillColor(color(fill))
        if stroke: self.c.setStrokeColor(color(stroke))
        self.c.setLineWidth(weight * MM)
        self.c.setLineCap(1)
        self.c.setLineJoin(1)
        self.c.setDash([n * MM for n in dash] if dash else [])
        self.c.drawPath(p, fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.c.restoreState()

    def polygon(self, points, fill=None, stroke=None, weight=.25):
        self.shape([("M", points[0])] + [("L", pt) for pt in points[1:]] + [("Z", [])], fill, stroke, weight)

    def rect(self, x, y, w, h, fill=None, stroke=None, radius=0, weight=.25):
        self.c.saveState()
        if fill: self.c.setFillColor(color(fill))
        if stroke: self.c.setStrokeColor(color(stroke))
        self.c.setLineWidth(weight * MM)
        args = [n * MM for n in [x, y, w, h]]
        if radius:
            self.c.roundRect(*args, radius * MM, fill=int(bool(fill)), stroke=int(bool(stroke)))
        else:
            self.c.rect(*args, fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.c.restoreState()

    def circle(self, x, y, r, fill=None, stroke=None, weight=.25):
        self.c.saveState()
        if fill: self.c.setFillColor(color(fill))
        if stroke: self.c.setStrokeColor(color(stroke))
        self.c.setLineWidth(weight * MM)
        self.c.circle(x * MM, y * MM, r * MM, fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.c.restoreState()

    def ellipse(self, x, y, w, h, fill=None, stroke=None, weight=.2):
        self.c.saveState()
        if fill: self.c.setFillColor(color(fill))
        if stroke: self.c.setStrokeColor(color(stroke))
        self.c.setLineWidth(weight * MM)
        self.c.ellipse(x * MM, y * MM, (x + w) * MM, (y + h) * MM,
                       fill=int(bool(fill)), stroke=int(bool(stroke)))
        self.c.restoreState()

    def mountain(self, x, y, w=13, h=13, fill="#D8D4C4"):
        self.polygon([(x - w / 2, y), (x - w * .15, y + h * .7), (x + w * .05, y + h),
                      (x + w / 2, y)], fill, "#A9B1A0", .2)
        self.shape([("M", [x + w * .05, y + h]), ("L", [x - w * .08, y + h * .48]),
                    ("L", [x + w * .2, y + h * .25])], stroke="#A4AA9A", weight=.2)

    def tree(self, x, y, scale=1):
        self.line(x, y, x, y + 10 * scale, "#6C7E64", .25)
        self.polygon([(x - 3 * scale, y + 2 * scale), (x - 1.5 * scale, y + 6 * scale),
                      (x - 2 * scale, y + 6 * scale), (x, y + 12 * scale),
                      (x + 2 * scale, y + 6 * scale), (x + 1.5 * scale, y + 6 * scale),
                      (x + 3 * scale, y + 2 * scale)], "#A3B29B", "#6C7E64", .18)

    def arch(self, x, y, w, h, fill=GREEN, stroke=None):
        self.shape([("M", [x, y]), ("L", [x, y + h * .6]),
                    ("C", [x, y + h * .83, x + w * .28, y + h * .96, x + w / 2, y + h]),
                    ("C", [x + w * .72, y + h * .96, x + w, y + h * .83, x + w, y + h * .6]),
                    ("L", [x + w, y]), ("Z", [])], fill, stroke, .2)

    def dome(self, x, y, w, h, tint):
        self.shape([("M", [x, y]), ("C", [x - 1, y + h * .55, x + w * .32, y + h * .72, x + w / 2, y + h]),
                    ("C", [x + w * .68, y + h * .72, x + w + 1, y + h * .55, x + w, y]),
                    ("Z", [])], tint, GREEN, .28)
        self.line(x + w / 2, y + h, x + w / 2, y + h + 2, GOLD, .3)

    def flag(self, x, y, tint):
        self.line(x, y, x, y + 10, GREEN, .25)
        self.polygon([(x, y + 10), (x + 8, y + 8), (x, y + 6)], tint, GREEN, .18)

    def boat(self, x, y, scale=1):
        self.polygon([(x - 9 * scale, y), (x + 9 * scale, y), (x + 5 * scale, y - 3 * scale),
                      (x - 5 * scale, y - 3 * scale)], "#BEAD89", "#617D82", .25)
        self.line(x, y, x, y + 13 * scale, "#617D82", .3)
        self.polygon([(x - .7 * scale, y + 11 * scale), (x - 7 * scale, y + 2 * scale),
                      (x - .7 * scale, y + 2 * scale)], IVORY, "#6E8D91", .18)
        self.polygon([(x + .7 * scale, y + 11 * scale), (x + 5.5 * scale, y + 3 * scale),
                      (x + .7 * scale, y + 2 * scale)], "#EEE4CA", "#6E8D91", .18)

    def palace(self, x, y, tint, indian=False, coastal=False):
        self.ellipse(x - 33, y - 7, 66, 10, "#DFDFCC")
        self.rect(x - 27, y - 1, 54, 3, "#C9C4AB", GREEN, weight=.3)
        self.rect(x - 22, y + 2, 44, 18, "#E7DCC3", GREEN, weight=.3)
        self.rect(x - 11, y + 2, 22, 24, "#EEE3CC", GREEN, weight=.3)
        self.dome(x - 12, y + 26, 24, 15, tint)
        for dx in [-22, 15]:
            self.rect(x + dx, y + 3, 7, 29, "#E8DCC0", GREEN, weight=.3)
            self.dome(x + dx - .5, y + 32, 8, 9, tint)
            self.arch(x + dx + 2, y + 21, 3, 6, "#7D8A78")
        self.arch(x - 5, y + 2, 10, 15, GREEN)
        for dx in [-16, 13]: self.arch(x + dx, y + 7, 4, 8, "#77866E")
        for dx in [-8, 8]:
            self.line(x + dx, y + 19, x + dx, y + 24, GOLD, .3)
        if indian:
            self.rect(x - 15, y + 20, 30, 2, "#BD9D62", GREEN, weight=.18)
            for dx in [-17, 17]: self.tree(x + dx * 2, y - 1, .85)
        elif coastal:
            for i in range(3): self.line(x - 25, y - 5 - i * 2, x + 25, y - 5 - i * 2, "#A0BAB9", .22)
            self.boat(x - 34, y - 12, .6)
        else:
            for dx in [-36, 35]: self.tree(x + dx, y - 1, .8)

    def cave(self, x, y):
        self.ellipse(x - 37, y - 7, 74, 11, "#DCE0D1")
        self.polygon([(x - 31, y - 1), (x - 28, y + 19), (x - 13, y + 28), (x - 5, y + 22),
                      (x + 3, y + 37), (x + 18, y + 30), (x + 30, y + 8), (x + 31, y - 1)],
                     "#C2C7B9", "#63756A", .4)
        self.polygon([(x + 3, y + 37), (x + 3, y + 14), (x + 18, y + 4), (x + 31, y - 1),
                      (x + 18, y + 30)], "#AAB4A4", "#63756A", .2)
        self.arch(x - 11, y - 1, 24, 22, GREEN, "#667464")
        self.arch(x - 7, y - 1, 17, 17, "#304339")
        self.polygon([(x - 2, y - 1), (x + 5, y + 8), (x + 10, y - 1)], "#B6A47D")
        for dx, dy, s in [(-39, 0, 1), (-31, 12, .7), (37, -1, 1), (28, 21, .7)]:
            self.tree(x + dx, y + dy, s)
        self.shape([("M", [x - 4, y - 1]), ("C", [x - 11, y - 9, x - 18, y - 5, x - 22, y - 13])],
                   stroke="#BBAE87", weight=1.3)

    def citadel(self, x, y, tint):
        self.ellipse(x - 31, y - 7, 62, 10, "#E0D9C7")
        self.rect(x - 25, y, 50, 20, "#DDCCB6", GREEN, weight=.3)
        for dx in [-25, -9, 17]:
            self.rect(x + dx, y, 8, 31 if dx != -9 else 39, "#E5D3BD", GREEN, weight=.3)
            hh = 31 if dx != -9 else 39
            for j in range(3): self.rect(x + dx + j * 3, y + hh, 2, 3, tint, GREEN, weight=.2)
            self.arch(x + dx + 2.4, y + 17, 3, 6, "#70806F")
        self.arch(x - 3, y, 10, 14, GREEN)
        self.flag(x + 21, y + 34, tint)
        for dx in [-36, 33]: self.mountain(x + dx, y - 4, 18, 15, "#DBD0BE")

    def port(self, x, y, tint):
        self.ellipse(x - 35, y - 8, 70, 11, "#D6E0D6")
        for dx, h in [(-25, 15), (-14, 22), (-1, 16), (12, 26), (24, 18)]:
            self.rect(x + dx - 5, y, 11, h, "#E9DCC5", GREEN, weight=.28)
            self.polygon([(x + dx - 6, y + h), (x + dx, y + h + 7), (x + dx + 7, y + h)],
                         tint if dx % 2 else "#AB8B64", GREEN, .25)
            self.arch(x + dx - 1.6, y + 4, 3.5, 6, "#6C8379")
        self.rect(x - 30, y - 3, 62, 3, "#C5BA9D", GREEN, weight=.28)
        for dx in [-28, 26]:
            self.line(x + dx, y - 3, x + dx, y - 16, "#8D806A", .8)
        self.boat(x - 22, y - 17, .7)
        self.boat(x + 18, y - 13, .85)
        self.flag(x + 12, y + 33, tint)

    def fortress(self, x, y, tint):
        self.polygon([(x - 38, y - 8), (x - 21, y + 22), (x + 8, y + 20), (x + 23, y + 13),
                      (x + 40, y - 12)], "#BEBAB8", "#7B7F7C", .35)
        for dx in [-22, -6, 12, 24]:
            self.line(x + dx, y - 5, x + dx * .6, y + 15, "#929590", .35)
        self.rect(x - 29, y + 12, 58, 19, "#DDD6D1", GREEN, weight=.35)
        for dx, height in [(-32, 36), (-6, 49), (25, 39)]:
            self.rect(x + dx, y + 12, 10, height, "#D8D2CD", GREEN, weight=.35)
            for j in range(4): self.rect(x + dx + j * 3, y + 12 + height, 2, 3, tint, GREEN, weight=.2)
            self.arch(x + dx + 3, y + 27, 4, 8, "#697575")
        # Three gates are a visible, source-backed landmark.
        for dx in [-19, 0, 18]:
            self.arch(x + dx - 4, y + 12, 8, 12, GREEN)
            self.line(x + dx, y + 12, x + dx, y + 22, "#8B8679", .3)
        self.flag(x + 30, y + 53, tint)

    def routes(self):
        paths = {
            "arabia_cave": [("M", [113, 306]), ("C", [139, 315, 163, 316, 184, 309])],
            "india_khataeti": [("M", [484, 319]), ("C", [466, 345, 439, 351, 408, 347])],
            "india_mulgazanzar": [("M", [486, 310]), ("C", [456, 296, 468, 262, 435, 234]),
                                      ("C", [393, 200, 306, 195, 247, 164])],
            "cave_mulgazanzar": [("M", [184, 299]), ("C", [159, 275, 168, 225, 181, 191]),
                                      ("C", [186, 178, 189, 173, 194, 170])],
            "mulgazanzar_gulansharo": [("M", [247, 145]), ("C", [276, 152, 312, 152, 343, 145])],
            "gulansharo_kajeti": [("M", [405, 159]), ("C", [431, 184, 464, 187, 488, 160])],
            "mulgazanzar_kajeti": [("M", [238, 127]), ("C", [260, 74, 304, 42, 358, 44]),
                                      ("C", [421, 43, 467, 64, 491, 124])],
            "india_gulansharo": [("M", [481, 307]), ("C", [443, 286, 455, 255, 423, 226]),
                                    ("C", [371, 187, 286, 191, 245, 121]),
                                    ("C", [279, 76, 321, 99, 344, 133])],
            "gulansharo_cave": [("M", [344, 133]), ("C", [315, 172, 289, 185, 278, 219]),
                                   ("C", [268, 250, 263, 279, 251, 295])],
            "arabia_india": [("M", [102, 329]), ("C", [176, 380, 281, 393, 363, 382]),
                              ("C", [422, 376, 466, 351, 489, 325])],
            "india_cave": [("M", [485, 293]), ("C", [414, 273, 344, 260, 259, 282])],
        }
        rendered = [route for route in DATA["routes"] if route["rendered"]]
        assert all(route["id"] in paths for route in rendered), "Missing vector route path"
        for route in DATA["routes"]:
            if not route["rendered"]: continue
            path = paths[route["id"]]
            style = ROUTE_STYLES[route["kind"]]
            ink, dash = style["color"], style["dash"]
            self.shape(path, stroke=IVORY, weight=2.2)
            self.shape(path, stroke=ink, weight=.8, dash=dash)
            for command, values in (path[0], path[-1]):
                px, py = values[-2:]
                self.circle(px, py, 1.3, IVORY, ink, .35)

    def map(self):
        self.rect(0, 0, W, H, IVORY)
        self.rect(9, 9, W - 18, H - 18, SEA, radius=3)
        coast = [("M", [9, 185]), ("C", [60, 205, 105, 171, 145, 190]),
                 ("C", [180, 210, 174, 185, 181, 162]),
                 ("C", [168, 133, 178, 102, 206, 91]),
                 ("C", [246, 91, 263, 127, 252, 177]),
                 ("C", [277, 205, 305, 175, 343, 206]),
                 ("C", [388, 235, 426, 249, 458, 284]),
                 ("C", [484, 314, 512, 296, 508, 266]),
                 ("C", [497, 224, 453, 177, 399, 151]),
                 ("C", [368, 135, 354, 93, 381, 62]),
                 ("C", [418, 35, 461, 65, 504, 51]),
                 ("C", [542, 37, 558, 51, 583, 59]),
                 ("L", [583, 411]), ("L", [9, 411]), ("Z", [])]
        self.shape(coast, LAND, "#91A99B", .45)
        # Fine sea marks and terrain make this a finished map rather than a node diagram.
        for x, y in [(47, 36), (128, 149), (132, 38), (294, 113), (303, 65), (419, 217),
                     (460, 236), (466, 276), (336, 165), (555, 23), (80, 172)]:
            for i in range(3):
                self.shape([("M", [x - 7, y + i * 2]),
                            ("C", [x - 3, y - 1 + i * 2, x + 3, y - 1 + i * 2, x + 7, y + i * 2])],
                           stroke="#A5BDB7", weight=.2)
        rng = random.Random(27)
        for x, y in [(135, 354), (272, 350), (315, 366), (437, 361), (552, 358),
                     (284, 263), (70, 223), (564, 212), (466, 105)]:
            for j in range(5):
                self.mountain(x + j * 5, y + rng.uniform(-3, 3), 11, rng.uniform(10, 17))
        for x, y in [(32, 349), (161, 322), (263, 313), (268, 384), (329, 288),
                     (416, 379), (558, 289), (462, 192), (557, 94), (180, 206)]:
            for j in range(4): self.tree(x + rng.uniform(-5, 8), y + rng.uniform(-3, 5), rng.uniform(.6, 1))
        self.routes()
        self.boat(300, 136, .8)
        self.boat(328, 54, .85)
        self.boat(440, 239, .7)
        for realm in DATA["realms"]:
            x, y, tint = realm["x"], realm["y"], realm["color"]
            icon = realm["icon"]
            if icon == "cave": self.cave(x, y)
            elif icon == "citadel": self.citadel(x, y, tint)
            elif icon == "fortress": self.fortress(x, y, tint)
            elif icon == "port": self.port(x, y, tint)
            else: self.palace(x, y, tint, icon == "indian_palace", icon == "coastal_palace")
            label_y = realm["label_y"]
            label = realm["name_ka"].upper()
            label_width = width(label, 22, "GeoDisplay")
            self.rect(x - label_width / 2 - 5, label_y - 3, label_width + 10, 12, IVORY, radius=3)
            self.text(label, x, label_y, 22, "GeoDisplay", GREEN, "center", True)
            self.line(x - 17, label_y - 5, x + 17, label_y - 5, GOLD, .28)
            self.text(realm["caption_ka"], x, label_y - 12, 11.5, "Geo", MUTED, "center", True)
            self.circle(x - label_width / 2 - 10, label_y + 2, 3.6, IVORY, GOLD, .35)
            self.text(str(realm["number"]), x - label_width / 2 - 10, label_y + .8,
                      10, "GeoBold", GREEN, "center")
        # Title and key each live wholly within one fold panel.
        self.text(DATA["title"].upper(), 25, 390, 30, "GeoDisplay", GREEN, primary=True)
        self.text(DATA["subtitle"], 25, 378, 13, ink=MUTED, primary=True)
        self.line(25, 371, 108, 371, GOLD, .45)
        self.legend()
        self.border()
        for x in DATA["folds"]["vertical_mm"]:
            self.line(x, 4, x, 7.5, GOLD, .35)
            self.line(x, H - 4, x, H - 7.5, GOLD, .35)
        self.line(4, 210, 7.5, 210, GOLD, .35)
        self.line(W - 4, 210, W - 7.5, 210, GOLD, .35)

    def legend(self):
        self.rect(19, 61, 113, 110, IVORY, GOLD, radius=3, weight=.25)
        self.text(DATA["legend"]["heading"].upper(), 28, 153, 16, "GeoBold", GREEN, primary=True)
        active_kinds = {route["kind"] for route in DATA["routes"] if route["rendered"]}
        kinds = [kind for kind in ("land", "sea", "mixed", "narrative") if kind in active_kinds]
        row_step = 12 if len(kinds) > 3 else 16
        for index, kind in enumerate(kinds):
            y = 137 - index * row_step
            ink, dash = ROUTE_STYLES[kind]["color"], ROUTE_STYLES[kind]["dash"]
            self.line(28, y, 48, y, ink, .8, dash)
            self.text(DATA["legend"][kind], 55, y - 1.5, 11.5, ink=INK, primary=True)
        bottom = self.para(DATA["legend"]["note"], 28, 87, 94, 10.2, 14, MUTED)
        assert bottom >= 65
        # A quiet, unoriented rosette; it does not assert real-world bearings.
        for a in range(8):
            angle = a * math.pi / 4
            x, y = 75 + 8 * math.cos(angle), 190 + 8 * math.sin(angle)
            self.line(75, 190, x, y, GOLD, .25)
        self.circle(75, 190, 5, IVORY, GOLD, .25)
        self.circle(75, 190, 1.2, GOLD)

    def border(self):
        self.rect(6, 6, W - 12, H - 12, stroke=GREEN, radius=4, weight=.5)
        self.rect(8, 8, W - 16, H - 16, stroke=GOLD, radius=3, weight=.25)
        for x, y, sx, sy in [(15, 15, 1, 1), (W - 15, 15, -1, 1),
                              (15, H - 15, 1, -1), (W - 15, H - 15, -1, -1)]:
            for a in range(3):
                self.line(x, y, x + sx * (8 + a * 3), y + sy * (2 + a * 2), GOLD, .25)
                self.line(x, y, x + sx * (2 + a * 2), y + sy * (8 + a * 3), GOLD, .25)


def new_pdf(path, size):
    c = canvas.Canvas(str(path), pagesize=size, pageCompression=1)
    c.setTitle("სამეფოთა რუკა / ვეფხისტყაოსანი")
    c.setAuthor("ვეფხისტყაოსნის პროექტი")
    c.setSubject("შვიდი სივრცე / სიუჟეტური გზები / დასაკეცი რუკა")
    return c, Drawing(c)


def cropmarks(d, x, y, w, h):
    for xx, yy, sx, sy in [(x, y, -1, -1), (x + w, y, 1, -1),
                          (x, y + h, -1, 1), (x + w, y + h, 1, 1)]:
        d.line(xx + sx * 2, yy, xx + sx * 6, yy, "#566B60", .18)
        d.line(xx, yy + sy * 2, xx, yy + sy * 6, "#566B60", .18)


def panel_diagram(d, x, y, w, active=None, labels=True):
    h = w * H / W
    for row in range(2):
        for col in range(4):
            number = row * 4 + col + 1
            px, py = x + col * w / 4, y + (1 - row) * h / 2
            d.rect(px, py, w / 4, h / 2, "#D9E6DD" if active == number else IVORY,
                   GREEN, weight=.22)
            if labels:
                d.text(str(number), px + w / 8, py + h / 4 - (2 if w > 100 else .8),
                       17 if w > 100 else 6.5, "GeoBold", GREEN, "center")
    return h


def assembly(d):
    d.rect(0, 0, 210, 297, IVORY)
    d.text("რუკის აწყობა და დაკეცვა", 18, 277, 21, "GeoDisplay", GREEN)
    d.text("გაშლილი: 592 × 420 მმ   /   დაკეცილი: A5", 18, 265, 11.5, ink=MUTED)
    panel_diagram(d, 31, 145, 148)
    d.line(31, 197.5, 179, 197.5, GOLD, .45, [2, 1.5])
    d.text("ზედა რიგი: 1–4   /   ქვედა რიგი: 5–8", 105, 135, 10, ink=MUTED, align="center")
    instructions = [
        "დაბეჭდეთ პირველი რვა გვერდი A4 ფორმატზე, ვერტიკალურად, ერთ მხარეს, მასშტაბით 100%.",
        "მოჭერით პანელები ჭრის ნიშნებზე: თითოეულის ზომაა 148 × 210 მმ. გარშემო არსებული 8 მმ-იანი გამეორებული გამოსახულება მოაჭერით.",
        "შეათავსეთ ზედა რიგი 1–4 და ქვედა რიგი 5–8. კიდეები ერთმანეთს მიაბჯინეთ და რუკის ხაზები გაასწორეთ.",
        "შეერთებები უკანა მხრიდან თხელი, მოქნილი წებოვანი ლენტით დაამაგრეთ. პანელები ამ ხაზებზე უნდა იკეცებოდეს.",
        "ჯერ ქვედა რიგი გადაკეცეთ ზედა რიგის უკან, შუა ჰორიზონტალურ ხაზზე.",
        "მიღებული გრძელი ზოლი ოთხ ნაწილად, აკორდეონივით დაკეცეთ. დახურული რუკა A5 ზომის იქნება.",
    ]
    y = 120
    for i, text in enumerate(instructions, 1):
        d.circle(22, y - 2, 3.2, GREEN)
        d.text(str(i), 22, y - 3.1, 9, "GeoBold", IVORY, "center")
        y = d.para(text, 31, y + 1, 160, size=10.4, leading=14) - 4.4
    assert y > 15, y


def main():
    master = OUT / "samqaro-realm-map-ka-592x420.pdf"
    c, d = new_pdf(master, (W * MM, H * MM))
    d.map()
    boxes = d.label_boxes
    c.save()
    # All important names and captions stay at least 4 mm clear of the folds.
    for label in boxes:
        x0, y0, x1, y1 = label["bbox_mm"]
        for x in DATA["folds"]["vertical_mm"]:
            assert x1 <= x - 4 or x0 >= x + 4, (label["text"], "vertical fold", x)
        for y in DATA["folds"]["horizontal_mm"]:
            assert y1 <= y - 4 or y0 >= y + 4, (label["text"], "horizontal fold", y)

    tiled = OUT / "samqaro-realm-map-ka-a4-print.pdf"
    c, d = new_pdf(tiled, A4)
    panel_records = []
    for index, panel in enumerate(PRODUCTION["home_print"]["panels"], 1):
        x0, y0, x1, y1 = panel["core_world_bbox_mm"]
        c.bookmarkPage(f"panel-{index}")
        c.addOutlineEntry(f"პანელი {index}", f"panel-{index}", 0)
        d.rect(23, 35.5, 164, 226, IVORY)
        c.saveState()
        clipping = c.beginPath()
        clipping.rect(23 * MM, 35.5 * MM, 164 * MM, 226 * MM)
        c.clipPath(clipping, stroke=0)
        c.translate((31 - x0) * MM, (43.5 - y0) * MM)
        d.map()
        c.restoreState()
        cropmarks(d, 31, 43.5, 148, 210)
        d.text(f"სამეფოთა რუკა / პანელი {index} / 8", 16, 278, 14, "GeoBold", GREEN)
        row = "ზედა რიგი" if index <= 4 else "ქვედა რიგი"
        d.text(f"{row} / სვეტი {(index - 1) % 4 + 1}", 16, 268, 10.5, ink=MUTED)
        panel_diagram(d, 163, 265, 29, index)
        d.text("ჭრის ზომა: 148 × 210 მმ", 105, 26, 10, ink=MUTED, align="center")
        d.text("A4 / ბეჭდვა 100%-ზე / ერთ მხარეს", 105, 17, 9, ink=MUTED, align="center")
        c.showPage()
        panel_records.append({"page": index, "world_bbox_mm": [x0, y0, x1, y1],
                              "a4_core_bbox_mm": [31, 43.5, 179, 253.5]})
    c.bookmarkPage("assembly")
    c.addOutlineEntry("აწყობა და დაკეცვა", "assembly", 0)
    assembly(d)
    c.showPage()
    c.save()

    guide = OUT / "samqaro-realm-map-ka-folding-guide.pdf"
    c, d = new_pdf(guide, A4)
    assembly(d)
    c.save()
    files = [master, tiled, guide]
    manifest = {"date": "2026-11-09", "language": "ka", "realm_count": 7,
                "rendered_route_count": sum(r["rendered"] for r in DATA["routes"]),
                "board_size_mm": [W, H], "folded_size_mm": [148, 210],
                "print_panels": panel_records, "a4_print_pages": 9,
                "note": "Eight map panels plus one assembly guide; source geography is schematic.",
                "important_label_boxes": boxes,
                "files": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                           "bytes": p.stat().st_size} for p in files]}
    (OUT / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for path in files: print(path)


if __name__ == "__main__":
    main()
