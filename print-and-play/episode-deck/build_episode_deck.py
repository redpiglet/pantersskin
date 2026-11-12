#!/usr/bin/env python3
"""Build the complete Georgian episode deck and exact A4 duplex editions."""

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

rl_config.useA85 = False
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/episode-deck"
SPEC = json.loads((HERE / "production-spec.json").read_text())
SOURCE = json.loads((HERE / "episode-cards.ka.json").read_text())
EPISODES = SOURCE["episodes"]
DECK = ROOT / "print-and-play/character-deck"
PORTRAITS = {p["character_id"]: p for p in json.loads((DECK / "portrait-manifest.json").read_text())["portraits"]}
MAP = json.loads((ROOT / "print-and-play/foldable-realm-map/map-data.ka.json").read_text())
ROUTES = {r["id"]: r for r in MAP["routes"]}
ILLUSTRATION_PATH = ROOT / SPEC["front"]["illustration_manifest"]
SCENES = {}
MM = 72 / 25.4
PAL = SPEC["palette"]
sys.path.insert(0, str(DECK))
from prepare_georgian_fonts import prepare

for name, style in (("Geo", "Regular"), ("GeoBold", "Bold"), ("GeoDisplay", "Display")):
    pdfmetrics.registerFont(TTFont(name, str(prepare(ROOT) / f"Georgian-{style}.ttf")))
for name, file in (("Latin", "Arial.ttf"), ("LatinBold", "Arial Bold.ttf")):
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + file))


class LayoutError(ValueError):
    pass


def clean(text):
    # Localize bare identifiers where they carry the route instruction; hide
    # redundant parenthetical IDs without changing the verified source files.
    replacements = {
        "გზით india_khataeti": "„ტარიელის ლაშქრობის გზით“",
        "გზით india_mulgazanzar": "ზღვითა და ხმელეთით მულღაზანზარისკენ",
        "გზით cave_mulgazanzar / india_cave „გაჭრა და ხეტიალი“": "გზით „გაჭრა და ხეტიალი“",
        "გზით arabia_cave": "„ავთანდილის ძიების გზით“",
        "გზით mulgazanzar_gulansharo": "სანაპირო და საზღვაო გზით",
        ", gulansharo_cave": ""
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    text = re.sub(r"\s*\([a-z][a-z0-9_]*(?:\s*[,/→]\s*[a-z][a-z0-9_]*)*\)", "", text)
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")
    for i in range(20):
        text = text.replace(chr(0x2460 + i), str(i + 1))
    assert not re.search(r"[A-Za-z]", text), ("Non-Georgian printed copy", text)
    return text


def runs(text, font="Geo"):
    result = []
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    fallback = "Latin" if font == "Geo" else "LatinBold"
    for char in text:
        family = font if ord(char) in cmap else fallback
        assert ord(char) in pdfmetrics.getFont(family).face.charToGlyph, (char, hex(ord(char)))
        if result and result[-1][0] == family:
            result[-1] = (family, result[-1][1] + char)
        else:
            result.append((family, char))
    return result


def width(text, size, font="Geo"):
    return sum(pdfmetrics.stringWidth(s, f, size) for f, s in runs(clean(text), font)) / MM


def tint(ink, amount=.10):
    a, b = colors.HexColor(PAL["ivory"]), colors.HexColor(ink)
    return colors.Color(*(getattr(a, k) * (1 - amount) + getattr(b, k) * amount for k in ("red", "green", "blue")))


def paragraph(text, w, size, leading=None, font="Geo", ink=None, align=0):
    text = clean(text)
    markup = "<br/>".join("".join(f'<font name="{family}">{escape(s)}</font>'
                                   for family, s in runs(line, font)) for line in text.split("\n"))
    p = Paragraph(markup, ParagraphStyle("episode", fontName=font, fontSize=size,
                  leading=leading or size * 1.22, textColor=colors.HexColor(ink or PAL["ink"]),
                  alignment=align, splitLongWords=False, spaceBefore=0, spaceAfter=0))
    pw, ph = p.wrap(w * MM, 5000)
    # ReportLab permits an unsplittable word wider than its assigned width.
    if any(width(word, size, font) > w + .02 for word in text.replace("\n", " ").split()):
        raise LayoutError(("Unbreakable word", text, w, size))
    return p, ph / MM


def profile(size, compression, side=None):
    compact = size == "A6"
    values = {"margin": 6.5 if compact else 9,
            "body": max(7.5, 8.1 - .2 * compression) if compact else max(9.4, 10.6 - .3 * compression),
            "small": 6.8 if compact else 8.6,
            "section": 7.3 if compact else 9.3,
            "chapter": max(6.7, 7.5 - .25 * compression) if compact else max(8, 9.2 - .3 * compression),
            "roster": max(6.2, 7 - .25 * compression) if compact else max(7.2, 8.3 - .25 * compression),
            "title": max(11.7, 14.5 - .7 * compression) if compact else max(18, 22 - compression),
            "back_title": max(10.8, 12.8 - .45 * compression) if compact else max(16, 18.5 - .6 * compression),
            "gap": max(.8, 1.8 - .25 * compression) if compact else max(1.5, 3 - .4 * compression),
            "compact": compact}
    if side == "front":
        values.update(front=True,
                      title=max(11.6, 12.8 - .3 * compression) if compact else max(17, 18.5 - .35 * compression),
                      body=max(7.5, 7.9 - .15 * compression) if compact else max(9.4, 10.6 - .3 * compression),
                      small=6.6 if compact else 8.4,
                      realm_meta=6.3 if compact else 7.8,
                      gap=max(.7, 1.2 - .15 * compression) if compact else max(1, 2.2 - .3 * compression))
    return values


class Card:
    def __init__(self, c, e, size, p, images=None, draw=False):
        self.c, self.e, self.size, self.p, self.images, self.draw = c, e, size, p, images or {}, draw
        self.w, self.h = SPEC["card_sizes_mm"][size]
        self.m = p["margin"]
        self.iw = self.w - 2 * self.m
        self.boxes, self.sections = [], []
        self.font_sizes = []

    def text(self, text, x, y, size, font="Geo", ink=None, align="left"):
        text = clean(text)
        tw = width(text, size, font)
        x -= tw / 2 if align == "center" else tw if align == "right" else 0
        box = [x, y - size / MM * .28, x + tw, y + size / MM]
        self.boxes.append({"text": text, "bbox_mm": box, "size_pt": size})
        self.font_sizes.append(size)
        if self.draw:
            self.c.setFillColor(colors.HexColor(ink or PAL["ink"]))
            for family, s in runs(text, font):
                self.c.setFont(family, size)
                self.c.drawString(x * MM, y * MM, s)
                x += pdfmetrics.stringWidth(s, family, size) / MM
        return box

    def para(self, text, x, top, w, size, font="Geo", ink=None, align=0, leading=None):
        p, height = paragraph(text, w, size, leading, font, ink, align)
        self.boxes.append({"text": clean(text), "bbox_mm": [x, top - height, x + w, top], "size_pt": size})
        self.font_sizes.append(size)
        if self.draw:
            p.drawOn(self.c, x * MM, (top - height) * MM)
        return top - height

    def line(self, x0, y0, x1, y1, ink=None, weight=.22, dash=()):
        if self.draw:
            self.c.setStrokeColor(colors.HexColor(ink or PAL["gold"]))
            self.c.setLineWidth(weight * MM)
            self.c.setDash([x * MM for x in dash])
            self.c.line(x0 * MM, y0 * MM, x1 * MM, y1 * MM)
            self.c.setDash()

    def rect(self, x, y, w, h, fill=None, stroke=None, radius=1.6):
        if self.draw:
            self.c.setFillColor(fill if isinstance(fill, colors.Color) else colors.HexColor(fill or PAL["ivory"]))
            self.c.setStrokeColor(colors.HexColor(stroke or PAL["gold"]))
            self.c.setLineWidth(.2 * MM)
            self.c.roundRect(x * MM, y * MM, w * MM, h * MM, radius * MM,
                             fill=int(fill is not None), stroke=int(stroke is not None))

    def section(self, kind, top, bottom):
        if bottom > top:
            raise LayoutError((kind, top, bottom))
        self.sections.append({"kind": kind, "bbox_mm": [self.m, bottom, self.w - self.m, top]})

    def base(self):
        self.rect(0, 0, self.w, self.h, PAL["ivory"], None, 0)
        self.rect(1, 1, self.w - 2, self.h - 2, None, PAL["green"], 2.7)
        self.rect(2.5, 2.5, self.w - 5, self.h - 5, None, PAL["gold"], 1.8)
        if self.draw:
            for x in (4.3, self.w - 4.3):
                for y in (4.3, self.h - 4.3):
                    p = self.c.beginPath()
                    p.moveTo(x * MM, (y + .7) * MM)
                    for a, b in ((x + .7, y), (x, y - .7), (x - .7, y)):
                        p.lineTo(a * MM, b * MM)
                    p.close()
                    self.c.setFillColor(colors.HexColor(PAL["gold"]))
                    self.c.drawPath(p, fill=1, stroke=0)

    def header(self, back=False):
        top = self.h - self.m
        compact = self.p["compact"]
        badge_h, badge_w = (4.6, 31) if compact else (5.7, 40)
        self.rect(self.m, top - badge_h, badge_w, badge_h, PAL["green"], None)
        self.text(f"ეპიზოდი {self.e['episode_number']:02d} / 24", self.m + badge_w / 2,
                  top - badge_h + (1.2 if compact else 1.5), 7 if compact else 9,
                  "GeoBold", PAL["ivory"], "center")
        mode_size = 6.4 if compact else 8
        mode_w = self.iw - badge_w - 2
        mode_w = min(mode_w, width(self.e["mode_label_ka"], mode_size, "GeoBold") + 4)
        mode_height = paragraph(self.e["mode_label_ka"], mode_w - 2, mode_size,
                                font="GeoBold", align=1)[1]
        mode_h = max(badge_h, mode_height + 1.4)
        mode_x = self.w - self.m - mode_w
        mode_ink = PAL["green"] if self.e["mode"] == "present" else PAL["gold"]
        self.rect(mode_x, top - mode_h, mode_w, mode_h, tint(mode_ink, .13), None)
        self.para(self.e["mode_label_ka"], mode_x + 1, top - (mode_h - mode_height) / 2,
                  mode_w - 2, mode_size, "GeoBold", PAL["green"], 1)
        y = top - max(badge_h, mode_h) - (2 if back else 1.3)
        if not back:
            act = re.sub(r"^კარი [IVX]+", f"კარი {self.e['act_number']}", self.e["act_title_ka"])
            y = self.para(act, self.m, y, self.iw, self.p["small"], "GeoBold", PAL["muted"])
            y -= 1
            label = f"{self.e['chapter_range_label_ka']} • სტრ. {self.e['stanza_range']}"
            pill_h = self.p["small"] / MM * 1.3 + 1.6
            self.rect(self.m, y - pill_h, self.iw, pill_h, tint(PAL["gold"], .12), None)
            self.text(label, self.w / 2, y - pill_h + 1, self.p["small"], "GeoBold", PAL["green"], "center")
            y -= pill_h + self.p["gap"]
        self.section("header", top, y)
        return y

    def title(self, top, back=False):
        y = self.para(self.e["title_ka"], self.m, top, self.iw,
                      self.p["back_title"] if back else self.p["title"], "GeoDisplay", PAL["green"])
        divider_gap = 1.4 if back else 1
        self.line(self.m, y - divider_gap, self.w - self.m, y - divider_gap)
        bottom = y - divider_gap - self.p["gap"]
        self.section("title", top, bottom)
        return bottom

    def realm_context(self, top):
        """Compact geographical context; no route keys or journey-line graphics."""
        r = self.e["primary_realm"]
        fs = 8.7 if self.p["compact"] else 10.4
        h = fs / MM * 1.15 + 2.4
        self.rect(self.m, top - h, self.iw, h, tint(r["color"], .13), None)
        self.text(f"{r['number']}. {r['name_ka']}", self.m + 2, top - h + 1.3, fs, "GeoBold", r["color"])
        y = top - h - 1.1
        context = []
        names = [f"{x['number']}. {x['name_ka']}" for x in self.e["secondary_realms"]]
        if names:
            context.append("ასევე: " + " / ".join(names))
        if self.e["frame_realm"]:
            frame = self.e["frame_realm"]
            context.append(f"თხრობის ჩარჩო: {frame['number']}. {frame['name_ka']}")
        if context:
            y = self.para(" • ".join(context), self.m + 1, y, self.iw - 2,
                          self.p["realm_meta"], ink=PAL["muted"])
            y -= .7
        self.section("realm_context", top, y)
        return y

    def box_height(self, text):
        fs = self.p["body"]
        padding = 3.4 if self.p.get("front") and self.p["compact"] else 5
        return paragraph(text, self.iw - 6, fs)[1] + self.p["section"] / MM * 1.3 + padding

    def callout(self, label, text, top, kind):
        h = self.box_height(text)
        self.rect(self.m, top - h, self.iw, h, tint(PAL["green"], .06), PAL["gold"])
        compact_front = self.p.get("front") and self.p["compact"]
        y = top - (1.4 if compact_front else 2)
        y = self.para(label, self.m + 3, y, self.iw - 6, self.p["section"], "GeoBold", PAL["green"])
        y = self.para(text, self.m + 3, y - (.75 if compact_front else 1.1), self.iw - 6, self.p["body"])
        if y < top - h + 1:
            raise LayoutError((kind, "callout overflow"))
        self.section(kind, top, top - h)
        return top - h

    def episode_scene(self, top, available):
        """Full-width selected painting, with its complete vellum edges visible."""
        selected = SCENES[self.e["id"]]
        frame_w, frame_h = SPEC["front"]["scene_frame_mm"][self.size]
        assert abs(frame_w - self.iw) < .01
        if available + .01 < frame_h:
            raise LayoutError((self.e["episode_number"], self.size, "Full-width scene needs more room", available, frame_h))
        top -= (available - frame_h) / 2
        bottom = top - frame_h
        pixels_w, pixels_h = selected["pixel_dimensions"]
        scale = min(frame_w / pixels_w, frame_h / pixels_h)
        image_w, image_h = pixels_w * scale, pixels_h * scale
        x, y = self.m + (frame_w - image_w) / 2, bottom + (frame_h - image_h) / 2
        if self.draw:
            self.c.drawImage(self.images[self.e["id"]], x * MM, y * MM,
                             width=image_w * MM, height=image_h * MM)
        self.rect(self.m, bottom, frame_w, frame_h, None, PAL["gold"], radius=0)
        self.section("episode_scene", top, bottom)
        return {"scene_asset": selected["asset"], "scene_asset_sha256": selected["sha256"],
                "scene_bbox_mm": [self.m, bottom, self.m + frame_w, top],
                "scene_image_bbox_mm": [x, y, x + image_w, y + image_h],
                "scene_frame_size_mm": [frame_w, frame_h],
                "scene_effective_dpi": round(pixels_w / (image_w / 25.4), 1)}

    def quote_footer_height(self):
        fs = 8.8 if self.p["compact"] else 11.5
        return paragraph(self.e["quote"]["line_ka"], self.iw - 2, fs, font="GeoDisplay")[1] + 6

    def front(self):
        self.base()
        y = self.title(self.header())
        y = self.realm_context(y) - self.p["gap"]
        action_h = self.box_height(self.e["token_action_ka"])
        quote_h = self.quote_footer_height()
        bottom = self.m
        available = y - bottom - action_h - quote_h - 2 * self.p["gap"]
        scene = self.episode_scene(y, available)
        action_top = bottom + quote_h + self.p["gap"] + action_h
        y = self.callout("ნიშნების გადაადგილება რუკაზე", self.e["token_action_ka"], action_top, "token_action")
        y -= self.p["gap"]
        self.line(self.m, y, self.w - self.m, y)
        top = y
        fs = 8.8 if self.p["compact"] else 11.5
        y = self.para(self.e["quote"]["line_ka"], self.m + 1, y - 2, self.iw - 2, fs, "GeoDisplay", PAL["green"])
        self.text(self.e["quote"]["locator_label_ka"], self.w - self.m, y - 3,
                  self.p["small"], ink=PAL["muted"], align="right")
        self.section("quote_footer", top, y - 4)
        if y - 4 < self.m - .1:
            raise LayoutError(("Front bottom", y))
        return {**scene, "content_bottom_mm": y - 4}

    def body_section(self, label, text, top):
        y = self.para(label, self.m, top, self.iw, self.p["section"], "GeoBold", PAL["green"])
        return self.para(text, self.m, y - 1, self.iw, self.p["body"])

    def chapter_titles(self, top):
        y = self.para("პოემის თავები", self.m, top, self.iw, self.p["section"], "GeoBold", PAL["green"])
        y -= .8
        for ch in self.e["chapter_titles_ka"]:
            y = self.para(f"{ch['chapter']}. {ch['title_ka']}", self.m, y, self.iw, self.p["chapter"])
            y -= .5 if self.p["compact"] else .8
        self.section("chapter_titles", top, y)
        return y

    def full_stanza(self, top):
        lines = self.e["quote"]["full_stanza_ka"].splitlines()
        assert len(lines) == 4
        max_fs = 8.2 if self.p["compact"] else 10.4
        stanza_size = min(max_fs, *(max_fs * (self.iw - 2) / width(s, max_fs) for s in lines))
        if stanza_size < (6.8 if self.p["compact"] else 8.4):
            raise LayoutError(("Stanza type too small", stanza_size))
        y = self.para("სტროფი", self.m, top, self.iw, self.p["section"], "GeoBold", PAL["green"])
        y -= 1
        for line in lines:
            y = self.para(line, self.m + 1, y, self.iw - 2, stanza_size, leading=stanza_size * 1.28)
        self.text(self.e["quote"]["locator_label_ka"], self.w - self.m, y - 2.8,
                  self.p["small"], ink=PAL["muted"], align="right")
        y -= 3.6
        self.section("full_stanza", top, y)
        return y, stanza_size

    def roster(self, top):
        y = self.para("მონაწილე პერსონაჟები", self.m, top, self.iw, self.p["section"], "GeoBold", PAL["green"])
        y -= 1
        fs = self.p["roster"]
        chip_h = fs / MM * 1.25 + 1.8
        x, rows = self.m, 1
        for ch in self.e["all_chapter_characters"]:
            name = ch["short_name_ka"]
            chip_w = width(name, fs) + 4.2
            if chip_w > self.iw:
                raise LayoutError(("Roster chip", name))
            if x + chip_w > self.w - self.m + .01:
                x, y, rows = self.m, y - chip_h - .8, rows + 1
            painted = ch["has_painted_portrait"]
            self.rect(x, y - chip_h, chip_w, chip_h,
                      PAL["green"] if painted else None, PAL["green"], 1.3)
            self.text(name, x + chip_w / 2, y - chip_h + .9, fs,
                      ink=PAL["ivory"] if painted else PAL["green"], align="center")
            x += chip_w + .9
        y -= chip_h + 1.1
        key_size = 5.9 if self.p["compact"] else 7.3
        y = self.para("მუქი ფონი: მოხატული პორტრეტი / კონტური: დამატებითი პერსონაჟი",
                      self.m, y, self.iw, key_size, ink=PAL["muted"])
        self.section("character_roster", top, y)
        return y, rows

    def timeline(self):
        scale = self.w / 105
        radius = 1.6 / MM * scale
        pitch = 3.88809 / MM * scale
        gap = .8 / MM * scale
        tw = 2 * radius + 64 * pitch + 12 * gap
        left = (self.w - tw) / 2 + radius
        centers = {n: left + (n - 1) * pitch + ((n - 1) // 5) * gap for n in range(1, 66)}
        rule_y, label_y, circle_y, tick_y, number_y = (v / MM * scale for v in (44, 33, 21.5, 18.2, 9.6))
        self.line(self.m, rule_y, self.w - self.m, rule_y)
        self.text("თავებში 1-65", self.m, label_y, 7.2 * scale, "GeoBold", PAL["green"])
        for n in range(1, 66):
            active = n in self.e["chapters"]
            if self.draw:
                self.c.setFillColor(colors.HexColor(PAL["green"] if active else PAL["ivory"]))
                self.c.setStrokeColor(colors.HexColor(PAL["green"]))
                self.c.setLineWidth(.27 * scale)
                self.c.circle(centers[n] * MM, circle_y * MM, radius * MM, fill=1, stroke=1)
            if n in (1, 65) or n % 5 == 0:
                major = n in (1, 65) or n % 10 == 0
                self.line(centers[n], tick_y, centers[n], tick_y - (2.8 if major else 1.5) / MM * scale,
                          PAL["green"], (.35 if major else .25) / MM * scale)
        for n in (1, 10, 20, 30, 40, 50, 60, 65):
            x, align = (centers[n] - radius, "left") if n == 1 else (centers[n] + radius, "right") if n == 65 else (centers[n], "center")
            self.text(str(n), x, number_y, 6.2 * scale, ink=PAL["muted"], align=align)
        self.section("timeline", rule_y, 2.7 * scale)
        return rule_y

    def back(self):
        self.base()
        y = self.title(self.header(back=True), back=True)
        y = self.chapter_titles(y) - self.p["gap"]
        top = y
        y = self.body_section("ეპიზოდის შინაარსი", self.e["summary_ka"], y)
        self.section("summary", top, y)
        y = self.callout("სვლის მიზანი", self.e["objective_ka"], y - self.p["gap"], "objective")
        y, stanza_size = self.full_stanza(y - self.p["gap"])
        y, rows = self.roster(y - self.p["gap"])
        timeline_top = self.timeline()
        if y < timeline_top + (1.5 if self.p["compact"] else 2.5):
            raise LayoutError(("Back timeline overlap", self.e["episode_number"], self.size, y, timeline_top))
        return {"content_bottom_mm": y, "stanza_size_pt": stanza_size, "roster_rows": rows,
                "highlighted_chapters": self.e["chapters"], "chapter_circle_count": 65}

    def validate(self):
        for b in self.boxes:
            x0, y0, x1, y1 = b["bbox_mm"]
            if not (2.6 <= x0 < x1 <= self.w - 2.6 and 2.6 <= y0 < y1 <= self.h - 2.6):
                raise LayoutError(("Text outside safe card area", self.e["episode_number"], self.size, b))
        for a, b in zip(self.sections, self.sections[1:]):
            if b["bbox_mm"][3] > a["bbox_mm"][1] + .01:
                raise LayoutError(("Section overlap", a, b))


def choose_layout(e, size, side):
    failures = []
    for compression in range(5):
        try:
            card = Card(None, e, size, profile(size, compression, side))
            metrics = getattr(card, side)()
            card.validate()
            return compression, metrics, card
        except LayoutError as error:
            failures.append(str(error))
    raise LayoutError({"episode": e["episode_number"], "size": size, "side": side, "failures": failures})


def verify_sources():
    assert len(EPISODES) == 24
    assert [e["episode_number"] for e in EPISODES] == list(range(1, 25))
    assert [ch for e in EPISODES for ch in e["chapters"]] == list(range(1, 66))
    assert [st for e in EPISODES for st in range(e["stanza_start"], e["stanza_end"] + 1)] == list(range(1, 1670))
    with (HERE / "episode-cards.ka.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 24
    scalar_keys = ("id", "act_title_ka", "chapter_range_label_ka", "stanza_range", "mode", "mode_label_ka", "title_ka", "summary_ka", "token_action_ka", "objective_ka")
    for e, row in zip(EPISODES, rows):
        assert int(row["episode_number"]) == e["episode_number"]
        assert all(row[key] == e[key] for key in scalar_keys)
        assert row["quote_full_stanza_ka"] == e["quote"]["full_stanza_ka"].replace("\n", " / ")
        assert len(e["quote"]["full_stanza_ka"].splitlines()) == 4
        assert e["quote"]["chapter"] in e["chapters"]
        assert e["stanza_start"] <= e["quote"]["stanza_number"] <= e["stanza_end"]
        for route in e["routes_used"]:
            assert route["kind"] == ROUTES[route["id"]]["kind"]
        for ch in e["all_chapter_characters"]:
            assert ch["has_painted_portrait"] == (PORTRAITS[ch["id"]]["status"] != "generic_silhouette")
    return {"episodes": 24, "chapters": list(range(1, 66)), "stanzas": [1, 1669], "csv_rows": len(rows)}


def load_scene_manifest(episodes=None,illustration_path=None):
    episodes = EPISODES if episodes is None else episodes
    illustration_path=Path(illustration_path) if illustration_path else ILLUSTRATION_PATH
    selected = json.loads(illustration_path.read_text())["selected_paintings"]
    assert len(selected) >= len(episodes)
    assert len({item["id"] for item in selected}) == len(selected)
    SCENES.clear()
    for e in episodes:
        matches = [item for item in selected if item["id"] == e["id"]]
        assert len(matches) == 1, (e["id"], "Expected exactly one selected painting")
        item = matches[0]
        assert item["episode_number"] == e["episode_number"]
        path = ROOT / item["asset"]
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        with Image.open(path) as image:
            pixels = list(image.size)
        expected = item.get("pixel_dimensions", item.get("export_pixels", item["native_pixels"]))
        assert pixels == expected and abs(pixels[0] / pixels[1] / 1.6 - 1) < .01
        SCENES[e["id"]] = {"episode_number": e["episode_number"], "id": e["id"],
                             "asset": item["asset"], "sha256": item["sha256"], "pixel_dimensions": pixels}
    assert len(SCENES) == len(episodes)


def load_images():
    """Embed native selected episode paintings; no character-image thumbnails."""
    images = {}
    for eid, item in SCENES.items():
        path = ROOT / item["asset"]
        with Image.open(path) as original:
            images[eid] = ImageReader(original.convert("RGB"))
    return images


def make_forms(c, size, layouts, images):
    w, h = SPEC["card_sizes_mm"][size]
    for e in EPISODES:
        for side in ("front", "back"):
            compression = layouts[size][e["id"]][side]["compression"]
            c.beginForm(f"{e['id']}_{side}", 0, 0, w * MM, h * MM)
            card = Card(c, e, size, profile(size, compression, side), images, True)
            getattr(card, side)()
            card.validate()
            c.endForm()


def new_pdf(path, paper_mm):
    c = canvas.Canvas(str(path), pagesize=tuple(v * MM for v in paper_mm), pageCompression=1)
    c.setTitle("ეპიზოდების დასტა / ვეფხისტყაოსანი")
    c.setAuthor("ვეფხისტყაოსნის პროექტი")
    c.setSubject("24 ეპიზოდი / 65 თავი / ქართული დასაბეჭდი ბარათები")
    return c


def crop_and_calibration(c, size):
    """Use the only free space: exact packed layouts have a 1 mm gutter."""
    c.setStrokeColor(colors.HexColor(PAL["muted"]))
    c.setLineWidth(.12 * MM)
    if size == "A5":
        for y in (0, 210):
            c.line(148 * MM, y * MM, 149 * MM, y * MM)
        # Gutter edges and paper edges define the two exact A5 trim rectangles.
        for y in (2, 208):
            for x in (148, 149):
                c.line(x * MM, (y - 1) * MM, x * MM, (y + 1) * MM)
        c.line(148.5 * MM, 90 * MM, 148.5 * MM, 120 * MM)
        for y in (90, 120):
            c.line(148.15 * MM, y * MM, 148.85 * MM, y * MM)
    else:
        for x in (0, 105, 210):
            c.line(x * MM, 148 * MM, x * MM, 149 * MM)
        for x in (2, 208):
            c.line((x - 1) * MM, 148 * MM, (x + 1) * MM, 148 * MM)
            c.line((x - 1) * MM, 149 * MM, (x + 1) * MM, 149 * MM)
        c.line(90 * MM, 148.5 * MM, 120 * MM, 148.5 * MM)
        for x in (90, 120):
            c.line(x * MM, 148.15 * MM, x * MM, 148.85 * MM)


def export_single(layouts, images):
    path = OUT / "pantersskin-episode-cards-ka-a5-single.pdf"
    c = new_pdf(path, SPEC["card_sizes_mm"]["A5"])
    make_forms(c, "A5", layouts, images)
    order = []
    for e in EPISODES:
        for side in ("front", "back"):
            page = len(order) + 1
            mark = f"{e['id']}-{side}"
            c.bookmarkPage(mark)
            c.addOutlineEntry(f"{e['episode_number']:02d}. {e['title_ka']} / " + ("წინა" if side == "front" else "უკანა"), mark, 0)
            c.doForm(f"{e['id']}_{side}")
            c.showPage()
            order.append({"page": page, "episode_number": e["episode_number"], "id": e["id"], "side": side})
    c.save()
    return {"file": str(path.relative_to(ROOT)), "pages": 48, "page_size_mm": [148, 210], "page_order": order}


def export_imposed(size, layouts, images):
    spec = SPEC["imposition"][size]
    path = OUT / f"pantersskin-episode-cards-ka-{size.lower()}-a4-duplex.pdf"
    c = new_pdf(path, spec["paper_mm"])
    make_forms(c, size, layouts, images)
    sheet_records = []
    count = spec["cards_per_sheet"]
    for start in range(0, 24, count):
        group = EPISODES[start:start + count]
        sheet = start // count + 1
        pages = []
        for side in ("front", "back"):
            indexes = list(range(count)) if side == "front" else spec["back_slot_order"]
            slots = []
            for slot, (index, (x, y)) in enumerate(zip(indexes, spec["slot_origins_mm"])):
                episode = group[index]
                c.saveState()
                c.translate(x * MM, y * MM)
                c.doForm(f"{episode['id']}_{side}")
                c.restoreState()
                slots.append({"slot": slot, "origin_mm": [x, y], "episode_number": episode["episode_number"], "id": episode["id"], "rotation_degrees": 0})
            crop_and_calibration(c, size)
            page_number = (sheet - 1) * 2 + (1 if side == "front" else 2)
            mark = f"sheet-{sheet}-{side}"
            c.bookmarkPage(mark)
            c.addOutlineEntry(f"ფურცელი {sheet} / " + ("წინა" if side == "front" else "უკანა"), mark, 0)
            c.showPage()
            pages.append({"page": page_number, "side": side, "slots": slots})
        sheet_records.append({"sheet": sheet, "pages": pages})
    c.save()
    return {"file": str(path.relative_to(ROOT)), "pages": spec["pdf_pages"], "sheets": spec["sheets"],
            "page_size_mm": spec["paper_mm"], "card_size_mm": SPEC["card_sizes_mm"][size],
            "duplex_flip": spec["duplex_flip"], "back_mapping": "horizontal position swap, upright lettering",
            "borderless_required_for_full_edge_art": True, "calibration_bar_mm": 30, "sheet_order": sheet_records}


def render_previews(a5_single_only=False):
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise RuntimeError("PNG proof rendering requires Poppler pdftoppm.")
    plans = [("a5-single", 35, "preview-a5-front", 130),
             ("a5-single", 36, "preview-a5-back", 130),
             ("a5-single", 14, "preview-a5-six-chapters-back", 130),
             ("a5-a4-duplex", 17, "preview-a5-imposition-front", 100),
             ("a5-a4-duplex", 18, "preview-a5-imposition-back", 100),
             ("a6-a4-duplex", 9, "preview-a6-dense-fronts", 130),
             ("a6-a4-duplex", 10, "preview-a6-dense-backs", 130),
             ("a6-a4-duplex", 11, "preview-a6-imposition-front", 130),
             ("a6-a4-duplex", 12, "preview-a6-imposition-back", 130)]
    if a5_single_only:
        plans = [plan for plan in plans if plan[0] == "a5-single"]
    outputs = []
    for edition, page, name, dpi in plans:
        pdf = OUT / f"pantersskin-episode-cards-ka-{edition}.pdf"
        prefix = OUT / name
        subprocess.run([renderer, "-f", str(page), "-l", str(page), "-singlefile", "-r", str(dpi),
                        "-png", str(pdf), str(prefix)], check=True)
        path = prefix.with_suffix(".png")
        outputs.append({"file": str(path.relative_to(ROOT)), "source_pdf": str(pdf.relative_to(ROOT)),
                        "source_page": page, "dpi": dpi, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return outputs


class StorytellingFrontCard(Card):
    """Keep the large painting and put the complete quatrain below the action."""

    def front(self):
        self.base()
        y=self.title(self.header())
        y=self.realm_context(y)-self.p["gap"]
        action_h=self.box_height(self.e["token_action_ka"])
        lines=self.e["quote"]["full_stanza_ka"].splitlines()
        fs=min(9.5,*(9.5*(self.iw-2)/width(s,9.5) for s in lines))
        label_h=paragraph("სტროფი",self.iw,self.p["section"],font="GeoBold")[1]
        stanza_h=sum(paragraph(s,self.iw-2,fs,leading=fs*1.25)[1] for s in lines)
        quote_h=label_h+stanza_h+6.8
        available=y-self.m-action_h-quote_h-2*self.p["gap"]
        scene=self.episode_scene(y,available)
        action_top=self.m+quote_h+self.p["gap"]+action_h
        y=self.callout("ნიშნების გადაადგილება რუკაზე",self.e["token_action_ka"],action_top,"token_action")-self.p["gap"]
        self.line(self.m,y,self.w-self.m,y)
        top=y
        y=self.para("სტროფი",self.m,y-1.2,self.iw,self.p["section"],"GeoBold",PAL["green"])-.5
        for line in lines:
            y=self.para(line,self.m+1,y,self.iw-2,fs,leading=fs*1.25)
        self.text(self.e["quote"]["locator_label_ka"],self.w-self.m,y-2.7,self.p["small"],ink=PAL["muted"],align="right")
        self.section("quote_footer",top,y-3.6)
        return {**scene,"content_bottom_mm":y-3.6,"full_stanza_side":"front","stanza_size_pt":fs}


class StorytellingCard(Card):
    """Selected-episode prototype with the new complete per-character inputs."""

    def box_height(self, text):
        return paragraph(text,self.iw-6,self.p["body"])[1]+self.p["section"]/MM*1.3+4.3

    def storytelling_inputs(self, top):
        inputs=self.e.get("character_inputs_ka",[])
        y=self.para("პერსონაჟთა სვლები",self.m,top,self.iw,self.p["section"],"GeoBold",PAL["green"])-.8
        for index,item in enumerate(inputs):
            if index:
                self.line(self.m,y-.4,self.w-self.m,y-.4,weight=.14)
                y-=1.5
            y=self.para(f'{item["name_ka"]} • {item["role_ka"]}',self.m,y,self.iw,
                        self.p["role_title"],"GeoBold",PAL["green"])-.5
            for label,key in (("მოქმედება","action_ka"),("სათქმელი","dialogue_ka"),("მინიშნება","cue_ka")):
                y=self.para(f'{label}: {item[key]}',self.m,y,self.iw,self.p["role_body"])-.2
        self.section("character_inputs",top,y)
        # Named role headings serve as the roster. Keep any additional source
        # participants even when the selected card has no instruction for them.
        covered={item["character_id"] for item in inputs}
        others=[ch["name_ka"] for ch in self.e["all_chapter_characters"] if ch["id"] not in covered]
        if others:
            top=y-1
            y=self.para("ასევე მონაწილეობენ: "+" • ".join(others),self.m,top,self.iw,self.p["role_body"])
            self.section("additional_roster",top,y)
        return y

    def timeline(self):
        count=SOURCE["total_episodes"]
        radius,group_gap=.8,1.0
        boundaries={act["act_number"]:[] for act in SOURCE["acts"]}
        for e in EPISODES:
            boundaries[e["act_number"]].append(e["episode_number"])
        ends={max(numbers) for numbers in boundaries.values()}
        pitch=(self.iw-2*radius-group_gap*(len(ends)-1))/(count-1)
        x=self.m+radius
        self.line(self.m,17.5,self.w-self.m,17.5)
        self.text("ეპიზოდებში 1-24",self.m,13.3,8.2,"GeoBold",PAL["green"])
        for number in range(1,count+1):
            if self.draw:
                self.c.setFillColor(colors.HexColor(PAL["green"] if number==self.e["episode_number"] else PAL["ivory"]))
                self.c.setStrokeColor(colors.HexColor(PAL["green"]))
                self.c.setLineWidth(.22*MM)
                self.c.circle(x*MM,9.0*MM,radius*MM,fill=1,stroke=1)
            self.line(x,7.8,x,7.0 if number%5==0 or number in (1,count) else 7.4,PAL["green"],.13)
            self.text(str(number),x,3.8,8.0,ink=PAL["muted"],align="center")
            x+=pitch+(group_gap if number in ends and number<count else 0)
        self.section("timeline",17.5,2.8)
        return 17.5

    def back(self):
        self.base()
        y=self.title(self.header(back=True),back=True)
        y=self.chapter_titles(y)-self.p["gap"]
        top=y
        y=self.body_section("ეპიზოდის შინაარსი",self.e["summary_ka"],y)
        self.section("summary",top,y)
        y=self.callout("სვლის მიზანი",self.e["objective_ka"],y-self.p["gap"],"objective")
        y=self.storytelling_inputs(y-self.p["gap"])
        timeline_top=self.timeline()
        if y<timeline_top+2:
            raise LayoutError(("Storytelling inputs overlap timeline",self.e["episode_number"],y,timeline_top))
        return {"content_bottom_mm":y,"full_stanza_side":"front",
                "character_input_count":len(self.e.get("character_inputs_ka",[])),
                "timeline_unit":"episodes","circle_count":SOURCE["total_episodes"],
                "highlighted_episodes":[self.e["episode_number"]]}


def storytelling_profile(compression):
    p=profile("A5",compression,"back")
    p.update(body=max(8.4,9.4-.2*compression),small=8.0,section=8.8,chapter=8.4,
             back_title=14.0,gap=max(.8,1.2-.1*compression),
             role_title=9.1,role_body=max(8.2,9.0-.2*compression))
    return p


def build_selected_episodes(numbers, previews=False,variant=None,illustration_path=None):
    """Write a separate sample, leaving every existing full-deck PDF intact."""
    numbers=sorted(set(numbers))
    if not numbers or any(n<1 or n>SOURCE["total_episodes"] for n in numbers):
        raise ValueError("Episode selection must be within1..24")
    selected=[e for e in EPISODES if e["episode_number"] in numbers]
    illustration_path=Path(illustration_path) if illustration_path else ILLUSTRATION_PATH
    if not illustration_path.is_absolute():
        illustration_path=ROOT/illustration_path
    if variant and not re.fullmatch(r"[a-z0-9][a-z0-9-]*",variant):
        raise ValueError("Variant must be a lowercase ASCII label")
    verify_sources()
    load_scene_manifest(selected,illustration_path)
    tag="-".join(f"{n:02d}" for n in numbers)
    out=(OUT/variant if variant else OUT)/f"episodes-{tag}"
    out.mkdir(parents=True,exist_ok=True)
    failures=[]
    # One shared back profile keeps the selected cards consistent.
    for compression in range(7):
        try:
            backs={}
            for e in selected:
                p=storytelling_profile(compression)
                card=StorytellingCard(None,e,"A5",p)
                metrics=card.back();card.validate()
                backs[e["id"]]={"compression":compression,"profile":p,**metrics,
                                 "sections":card.sections,"text_boxes":card.boxes}
            break
        except LayoutError as error:
            failures.append(str(error))
    else:
        raise LayoutError({"selected_episodes":numbers,"failures":failures})
    layouts={"A5":{}}
    for e in selected:
        compression=0
        card=StorytellingFrontCard(None,e,"A5",profile("A5",compression,"front"))
        metrics=card.front();card.validate()
        layouts["A5"][e["id"]]={"front":{"compression":compression,"profile":profile("A5",compression,"front"),
            **metrics,"sections":card.sections,"text_boxes":card.boxes},"back":backs[e["id"]]}
    images=load_images()
    pdf=out/f"pantersskin-episode-cards-ka-a5-episodes-{tag}.pdf"
    c=new_pdf(pdf,SPEC["card_sizes_mm"]["A5"])
    c.setSubject(f'{len(selected)} ეპიზოდი / ქართული დასაბეჭდი ბარათები')
    order=[]
    for e in selected:
        for side in ("front","back"):
            form=f'{e["id"]}_{side}'
            c.beginForm(form,0,0,148*MM,210*MM)
            p=layouts["A5"][e["id"]][side]["profile"]
            card=(StorytellingFrontCard if side=="front" else StorytellingCard)(c,e,"A5",p,images,True)
            getattr(card,side)();card.validate();c.endForm()
            c.doForm(form);c.showPage()
            order.append({"page":len(order)+1,"episode_number":e["episode_number"],"id":e["id"],"side":side})
    c.save()
    proof_records=[]
    if previews:
        renderer=shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"
        for record in order:
            prefix=out/f'episode-{record["episode_number"]:02d}-{record["side"]}'
            subprocess.run([renderer,"-f",str(record["page"]),"-l",str(record["page"]),"-singlefile",
                            "-r","150","-png",str(pdf),str(prefix)],check=True,capture_output=True)
            path=prefix.with_suffix(".png")
            proof_records.append({"file":str(path.relative_to(ROOT)),"source_page":record["page"],
                                  "bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
        thumb_w,thumb_h,gutter=500,710,12
        rows=(len(order)+1)//2
        sheet=Image.new("RGB",(2*thumb_w+3*gutter,rows*thumb_h+(rows+1)*gutter),PAL["ivory"])
        for index,proof in enumerate(proof_records):
            with Image.open(ROOT/proof["file"]) as image:
                image=image.convert("RGB")
                image.thumbnail((thumb_w,thumb_h),Image.Resampling.LANCZOS)
                sheet.paste(image,(gutter+(index%2)*(thumb_w+gutter),gutter+(index//2)*(thumb_h+gutter)))
        contact=out/f"preview-episodes-{tag}.png"
        sheet.save(contact)
        proof_records.append({"file":str(contact.relative_to(ROOT)),"source_pages":list(range(1,len(order)+1)),
                              "bytes":contact.stat().st_size,"sha256":hashlib.sha256(contact.read_bytes()).hexdigest()})
    manifest={"language":"ka","scope":"selected_episodes_only","episode_numbers":numbers,
        "artwork_variant":variant or "manuscript",
        "episode_count":len(selected),"source_json":str((HERE/"episode-cards.ka.json").relative_to(ROOT)),
        "source_hashes":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (HERE/"episode-cards.ka.json",ROOT/"data/episode-cards.json",HERE/"episode-cards.ka.csv")},
        "builder_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_copy_unchanged":True,"full_deck_exports_unchanged":True,
        "illustration_source":str(illustration_path.relative_to(ROOT)),
        "illustration_manifest_sha256":hashlib.sha256(illustration_path.read_bytes()).hexdigest(),
        "scene_assets":list(SCENES.values()),
        "front_design":{**SPEC["front"],"illustration_manifest":str(illustration_path.relative_to(ROOT))},
        "timeline":{"unit":"episodes","count":24,"heading_ka":"ეპიზოდებში 1-24",
                    "highlight_rule":"this episode number","act_groups":[[1,5],[6,12],[13,16],[17,19],[20,24]]},
        "character_inputs_printed_verbatim":True,"character_input_headers_serve_as_roster":True,
        "layout_metrics":layouts,"pdfs":[{"file":str(pdf.relative_to(ROOT)),"pages":len(order),
            "page_size_mm":[148,210],"page_order":order,"bytes":pdf.stat().st_size,
            "sha256":hashlib.sha256(pdf.read_bytes()).hexdigest()}],"previews":proof_records,
        "print_note":"100% / actual size; native A5; front followed by matching back; duplex long edge."}
    manifest["verification"]={"status":"independent_selected_episode_verification_passed",
                              "report":str((out/"validation.json").relative_to(ROOT))}
    (out/"build-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    from verify_episode_sample import verify
    checked=verify(out,numbers,illustration_path=illustration_path)
    assert checked["status"]==manifest["verification"]["status"]
    print(pdf.resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-layout", action="store_true", help="Validate both sizes without exporting PDFs")
    parser.add_argument("--previews", action="store_true", help="Also render sample PNG proofs using Poppler")
    parser.add_argument("--previews-only", action="store_true", help="Refresh PNG proofs for existing PDFs")
    parser.add_argument("--a5-single-only", action="store_true", help="Build and verify only the native A5 front/back PDF")
    parser.add_argument("--episodes",nargs="+",type=int,help="Build only these A5 episodes with the updated character storytelling inputs")
    parser.add_argument("--illustrations",type=Path,help="Alternate illustration manifest for selected episodes")
    parser.add_argument("--variant",help="Save a selected-episode artwork variant in its own folder")
    args = parser.parse_args()
    if args.episodes:
        if args.check_layout or args.previews_only:
            parser.error("--episodes exports a separate selected-card sample; use --previews to render it")
        build_selected_episodes(args.episodes,args.previews,args.variant,args.illustrations)
        return
    if args.illustrations or args.variant:
        parser.error("--illustrations and --variant are available with --episodes")
    if args.previews_only:
        manifest_path = OUT / "build-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["previews"] = render_previews(args.a5_single_only)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print("PNG proofs refreshed for the existing PDFs.")
        return
    coverage = verify_sources()
    load_scene_manifest()
    layouts = {}
    for size in (("A5",) if args.a5_single_only else ("A5", "A6")):
        layouts[size] = {}
        for e in EPISODES:
            sides = {}
            for side in ("front", "back"):
                compression, metrics, card = choose_layout(e, size, side)
                sides[side] = {"compression": compression, **metrics,
                               "profile": profile(size, compression, side), "sections": card.sections,
                               "text_boxes": card.boxes}
            layouts[size][e["id"]] = sides
    OUT.mkdir(parents=True, exist_ok=True)
    if args.check_layout:
        (OUT / "layout-preflight.json").write_text(json.dumps(layouts, ensure_ascii=False, indent=2) + "\n")
        print(("A5" if args.a5_single_only else "Both sizes") + ": 24 fronts and 24 backs passed layout preflight.")
        return
    images = load_images()
    outputs = [export_single(layouts, images)]
    if not args.a5_single_only:
        outputs += [export_imposed("A5", layouts, images), export_imposed("A6", layouts, images)]
    for item in outputs:
        path = ROOT / item["file"]
        item.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest = {"date": SPEC["date"], "language": "ka", "episode_count": 24,
                "edition": "a5_single_only" if args.a5_single_only else "all_editions",
                "source_coverage": coverage, "source_json": str((HERE / "episode-cards.ka.json").relative_to(ROOT)),
                "source_csv": str((HERE / "episode-cards.ka.csv").relative_to(ROOT)),
                "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "episode-cards.ka.json", HERE / "episode-cards.ka.csv")},
                "source_copy_unchanged": True, "print_cleanup": "Internal Latin route IDs removed; act numerals localized to Arabic digits; hyphens normalized.",
                "fonts": {"body": "Geo", "bold": "GeoBold", "display": "GeoDisplay", "numeral_fallback": "Arial"},
                "illustration_source": str(ILLUSTRATION_PATH.relative_to(ROOT)),
                "illustration_manifest_sha256": hashlib.sha256(ILLUSTRATION_PATH.read_bytes()).hexdigest(),
                "scene_assets": list(SCENES.values()), "embedded_character_portrait_ids": [],
                "front_design": SPEC["front"],
                "painted_character_ids": sorted(cid for cid, p in PORTRAITS.items() if p["status"] != "generic_silhouette"),
                "timeline": SPEC["timeline"], "pdfs": outputs, "layout_metrics": layouts,
                "print_note": ("Native A5 pages, exact148x210mm, front then matching back; print at100% / actual size."
                               if args.a5_single_only else SPEC["packed_printing"]), "physical_print_test": False}
    if args.previews:
        manifest["previews"] = render_previews(args.a5_single_only)
    manifest_path = OUT / "build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    verify_args = [sys.executable, str(HERE / "verify_episode_deck.py"), "--report", str(OUT / "validation.json")]
    if args.a5_single_only:
        verify_args.append("--a5-single-only")
    subprocess.run(verify_args,
                   check=True, stdout=subprocess.PIPE, text=True)
    manifest["verification"] = {"status": "passed", "report": "output/episode-deck/validation.json",
                                "checks": ["exact sizes and page counts", "complete Georgian content in both sizes",
                                           "actual upright duplex placements", "65 actual circles and correct chapter fill masks on every back",
                                           "30mm calibration bars and frame paths", "manifest maps and PDF hashes"],
                                "physical_print_test": False}
    if args.a5_single_only:
        manifest["verification"]["checks"] = ["exact A5 sizes and48 pages", "complete current Georgian content",
                                               "front/back page order and upright text",
                                               "65 actual circles and correct chapter fill masks on every back",
                                               "frame paths", "manifest page map and PDF hash"]
    manifest["verification"]["checks"] += ["one native selected scene image on each front, matched by decoded RGB pixels",
                                             "no portrait medallions, clipped artwork or route-line dash patterns"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for item in outputs:
        print((ROOT / item["file"]).resolve())


if __name__ == "__main__":
    main()
