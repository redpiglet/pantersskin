#!/usr/bin/env python3
"""Build two exact-size, two-page Georgian rules/setup sheets.

All printed gameplay content comes from data/rulebook.ka.json. Expanded
background/examples stay in the data; the two-page sheet uses its core fields.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/rulebook"
SOURCE_PATH = ROOT / "data/rulebook.ka.json"
PALETTE_PATH = ROOT / "print-and-play/episode-deck/production-spec.json"
SOURCE = json.loads(SOURCE_PATH.read_text())
META = SOURCE["meta"]
# These aliases only select source fields; they do not rewrite their content.
COPY = {
    "title_ka": META["title_ka"], "subtitle_ka": META["subtitle_ka"],
    "overview_ka": SOURCE["overview"]["summary_ka"],
    "turn_steps_ka": [s["instruction_ka"] for s in SOURCE["gameplay_loop"]],
    "setup_steps_ka": [s["instruction_ka"] for s in SOURCE["setup_steps"]],
    "actions": [{**s,"text_ka":s["instruction_ka"]} for s in SOURCE["token_actions"]],
    "flashback_ka": SOURCE["flashback_rules"]["description_ka"],
    "scale_ka": SOURCE["scale_rules"]["explanation_ka"],
    "win_ka": SOURCE["victory"]["condition_ka"],
    "print_ka": SOURCE["print_production"]["general_instructions_ka"][0],
    "edition_ka": META["poem_basis_ka"], "art_ka": META["art_basis_ka"],
}
PAL = json.loads(PALETTE_PATH.read_text())["palette"]
MM = 72 / 25.4
rl_config.useA85 = False
sys.path.insert(0, str(ROOT / "print-and-play/character-deck"))
from prepare_georgian_fonts import prepare


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def register_fonts():
    fonts = prepare(ROOT)
    for name, suffix in (("Geo", "Regular"), ("GeoBold", "Bold"), ("GeoDisplay", "Display")):
        pdfmetrics.registerFont(TTFont(name, str(fonts / f"Georgian-{suffix}.ttf")))
    for name, filename in (("Symbols", "Arial.ttf"), ("SymbolsBold", "Arial Bold.ttf")):
        pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + filename))
    return fonts


def clean(text):
    text = str(text).replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    if re.search(r"[A-Za-z\u2460-\u2473]", text):
        raise ValueError(f"Non-Georgian printed copy: {text}")
    return text


def runs(text, font):
    result = []
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    for char in clean(text):
        family = font if ord(char) in cmap else ("Symbols" if font == "Geo" else "SymbolsBold")
        if ord(char) not in pdfmetrics.getFont(family).face.charToGlyph:
            raise ValueError(("Missing glyph", char, hex(ord(char))))
        if result and result[-1][0] == family:
            result[-1] = (family, result[-1][1] + char)
        else:
            result.append((family, char))
    return result


def text_width(text, size, font="Geo"):
    return sum(pdfmetrics.stringWidth(s, f, size) for f, s in runs(text, font)) / MM


def make_paragraph(text, w, size, font="Geo", ink="ink", leading=None, align=0, label=None):
    markup = "<br/>".join("".join(f'<font name="{f}">{escape(s)}</font>' for f, s in runs(line, font))
                              for line in clean(text).split("\n"))
    if label:
        markup="".join(f'<font name="{f}">{escape(s)}</font>' for f,s in runs(label+". ","GeoBold"))+markup
    p = Paragraph(markup, ParagraphStyle("rules", fontName=font, fontSize=size,
        leading=leading or size * 1.22, textColor=colors.HexColor(PAL.get(ink, ink)),
        alignment=align, splitLongWords=False, spaceShrinkage=0, spaceAfter=0, spaceBefore=0))
    # ReportLab's mixed-font word breaker can consume a fraction of a point
    # beyond its wrapped width. Reserve 0.5pt inside the declared text box.
    reserve = .5
    _, height = p.wrap(w * MM - reserve, 5000)
    for word in clean(text).split():
        if text_width(word, size, font) > w + .01:
            raise ValueError(("Unbreakable text overflow", word, w, size))
    # Check every actual line, including ReportLab's unbreakable-word handling.
    for line in p.blPara.lines:
        if (line[0] if isinstance(line, tuple) else line.extraSpace) < -reserve:
            raise ValueError(("Paragraph line exceeds width", text))
    return p, height / MM


def tint(key, fraction=.10):
    base, ink = colors.HexColor(PAL["ivory"]), colors.HexColor(PAL.get(key, key))
    return colors.Color(*(getattr(base, k) * (1 - fraction) + getattr(ink, k) * fraction
                          for k in ("red", "green", "blue")))


class Page:
    def __init__(self, c, size, number):
        self.c, self.size, self.number = c, size, number
        self.spec = SOURCE["print_production"]["formats"][size]
        self.w, self.h = self.spec["width_mm"], self.spec["height_mm"]
        self.m = self.spec["margins_mm"]
        self.iw = self.w - 2 * self.m
        self.body, self.small = self.spec["body_font_pt"], self.spec["min_font_pt"]
        # The expanded source is set at its8pt permitted minimum in compact
        # format; the large edition retains the10.4pt body recommendation.
        if size=="A5":
            self.body=self.small
        self.heading = 12.4 if size == "A4" else 9
        self.gap = 2.1 if size == "A4" else 1.2
        self.text_boxes, self.graphic_boxes, self.sections = [], [], []
        self.table = None
        self.c.setFillColor(colors.HexColor(PAL["ivory"]))
        self.c.rect(0, 0, self.w * MM, self.h * MM, fill=1, stroke=0)

    def check(self, box, label):
        if box[0] < 8 - .01 or box[1] < 8 - .01 or box[2] > self.w - 8 + .01 or box[3] > self.h - 8 + .01:
            raise ValueError(("Outside safe area", self.size, self.number, label, box))

    def para(self, text, x, top, w, size=None, font="Geo", ink="ink", align=0, role="body", leading=None,label=None):
        size = self.body if size is None else size
        p, h = make_paragraph(text, w, size, font, ink, leading, align,label)
        box = [x, top - h, x + w, top]
        self.check(box, clean(text))
        p.drawOn(self.c, x * MM, (top - h) * MM)
        self.text_boxes.append({"text": clean((label+". " if label else "")+text), "bbox_mm": box, "size_pt": size, "role": role})
        return top - h

    def rect(self, x, y, w, h, fill=None, stroke="gold", weight=.18, radius=0):
        box = [x - weight / 2, y - weight / 2, x + w + weight / 2, y + h + weight / 2]
        self.check(box, "rectangle")
        self.c.setFillColor(fill if isinstance(fill, colors.Color) else colors.HexColor(PAL.get(fill, fill) if fill else PAL["ivory"]))
        self.c.setStrokeColor(colors.HexColor(PAL.get(stroke, stroke) if stroke else PAL["ivory"]))
        self.c.setLineWidth(weight * MM)
        self.c.roundRect(x * MM, y * MM, w * MM, h * MM, radius * MM, fill=int(fill is not None), stroke=int(stroke is not None))
        self.graphic_boxes.append({"kind": "rect", "bbox_mm": box})

    def line(self, x0, y0, x1, y1, ink="gold", weight=.18):
        box = [min(x0, x1) - weight / 2, min(y0, y1) - weight / 2,
               max(x0, x1) + weight / 2, max(y0, y1) + weight / 2]
        self.check(box, "line")
        self.c.setStrokeColor(colors.HexColor(PAL.get(ink, ink)))
        self.c.setLineWidth(weight * MM)
        self.c.line(x0 * MM, y0 * MM, x1 * MM, y1 * MM)
        self.graphic_boxes.append({"kind": "line", "bbox_mm": box})

    def circle(self, x, y, r, fill=None, stroke="gold", weight=.2):
        box = [x-r-weight/2, y-r-weight/2, x+r+weight/2, y+r+weight/2]
        self.check(box, "circle")
        self.c.setFillColor(fill if isinstance(fill, colors.Color) else colors.HexColor(PAL.get(fill, fill) if fill else PAL["ivory"]))
        self.c.setStrokeColor(colors.HexColor(PAL.get(stroke, stroke) if stroke else PAL["ivory"]))
        self.c.setLineWidth(weight * MM)
        self.c.circle(x*MM, y*MM, r*MM, fill=int(fill is not None), stroke=int(stroke is not None))
        self.graphic_boxes.append({"kind": "circle", "bbox_mm": box})

    def arrow(self, x0, y0, x1, y1, ink="green"):
        import math
        self.line(x0, y0, x1, y1, ink, .28)
        angle = math.atan2(y1-y0, x1-x0)
        for sign in (-1, 1):
            a = angle + sign * .55
            self.line(x1, y1, x1 - 1.6 * math.cos(a), y1 - 1.6 * math.sin(a), ink, .28)

    def token(self, x, y, r=2, face=None):
        self.circle(x, y, r, "green", "gold", .24)
        self.circle(x, y, r * .32, "ivory", None)
        if face:
            self.line(x + face * r * .55, y-r*.5, x + face * (r+.8), y, "gold", .3)
            self.line(x + face * r * .55, y+r*.5, x + face * (r+.8), y, "gold", .3)

    def section(self, title, x, top, w):
        bottom = self.para(title, x, top, w, self.heading, "GeoBold", "green", role="heading")
        self.line(x, bottom-.7, x+w, bottom-.7, weight=.15)
        return bottom - (2.3 if self.size == "A4" else 1.4)

    def header(self, page_title):
        top = self.h - self.m
        if self.number == 2:
            size = 20 if self.size == "A4" else 12
            y = self.para(COPY["title_ka"], self.m, top, self.iw*.62, size,
                          "GeoDisplay", "green", role="title")
            self.para("მომზადება • 2 / 2", self.m+self.iw*.62, top-1,
                      self.iw*.38, self.small, "GeoBold", "muted", 2, role="header")
            self.line(self.m,y-1.5,self.w-self.m,y-1.5,weight=.3)
            return y-3.2
        self.para(f"{page_title} • {self.number} / 2", self.m, top, self.iw, self.small,
                  "GeoBold", "muted", role="header")
        title_size = 26 if self.size == "A4" else 16
        y = top - (7 if self.size == "A4" else 5)
        y = self.para(COPY["title_ka"], self.m, y, self.iw, title_size, "GeoDisplay", "green", role="title")
        y = self.para(COPY["subtitle_ka"], self.m, y-1, self.iw, self.heading, "GeoBold", "gold", role="subtitle")
        self.line(self.m, y-1.5, self.w-self.m, y-1.5, weight=.3)
        return y - (4 if self.size == "A4" else 3)

    def steps(self, texts, x, y, w):
        for n, text in enumerate(texts, 1):
            bottom_n = self.para(f"{n}.", x, y, 5, self.body, "GeoBold", "gold")
            bottom = self.para(text, x+5.4, y, w-5.4)
            y = min(bottom_n, bottom) - self.gap
        return y

    def action_icon(self, kind, x, y):
        if kind == "move":
            self.circle(x+3, y, 2.6, tint("gold"), "gold")
            self.circle(x+13, y, 2.6, tint("gold"), "gold")
            self.token(x+3, y, 1.3)
            self.arrow(x+6.5, y, x+9.5, y)
        elif kind == "group":
            self.token(x+5, y, 2.3)
            self.token(x+9.6, y, 2.3)
        elif kind == "face":
            self.token(x+3.5, y, 2, 1)
            self.token(x+12, y, 2, -1)
        elif kind == "remove":
            self.rect(x+.5, y-4, 8, 8, None, "gold", .16, 1)
            self.token(x+4.5, y, 1.8)
            self.arrow(x+7, y, x+13.5, y)
            self.circle(x+14.8, y, 1.1, None, "muted")
        else:
            self.rect(x+4, y-3.7, 7.5, 7.4, None, "gold", .16, 1)
            self.token(x+7.75, y, 1.7)
            self.arrow(x+.5, y+2.2, x+3.2, y+2.2)
            self.arrow(x+12.3, y-2, x+15.2, y-2)

    def action_list(self, x, top, w):
        y = top
        for a in COPY["actions"]:
            icon_h = 9
            title_bottom = self.para(a["title_ka"], x+16.5, y, w-16.5, self.body, "GeoBold", "green")
            bottom = self.para(a["text_ka"], x+16.5, title_bottom-.45, w-16.5)
            if a["kind"] == "remove":
                # The source puts the five named removals in a separate note.
                bottom = self.para(a["rule_note_ka"],x,bottom-.7,w,self.small,ink="muted")
            self.action_icon(a["kind"], x, y-4.4)
            y = min(bottom, y-icon_h) - self.gap
        return y

    def modes(self, x, top, w):
        labels = [(s["label_ka"],s["color_role"]) for s in SOURCE["flashback_rules"]["modes"]]
        h = 5.5 if self.size == "A4" else 4.7
        gap = 2
        widths = [text_width(t, self.small, "GeoBold") + 4 for t, _ in labels]
        start=x
        for (label, ink), bw in zip(labels, widths):
            if x+bw > start+w+.01:
                top-=h+1
                x=start
            self.rect(x, top-h, bw, h, tint(ink, .15), None, radius=1)
            self.para(label, x+1, top-.65, bw-2, self.small, "GeoBold", ink, 1)
            x += bw+gap
        return top-h-1.2

    def timeline(self, x, top, w,show_label=True):
        # Same circle/tick language as the cards, using source episode06.
        example=SOURCE["episodes"][5]
        if show_label:
            self.para(f'მაგალითი: ეპიზოდი {example["episode_number"]} • თავები {example["chapter_span_ka"]}',
                      x,top,w,self.small,"GeoBold","muted")
        cy = top - ((6 if self.size == "A4" else 5.2) if show_label else 1)
        pitch = (w-3)/64
        radius = min(.72, pitch*.30)
        for chapter in range(1, META["total_chapters"]+1):
            xx = x+1.5+(chapter-1)*pitch
            self.circle(xx, cy, radius, "green" if chapter in example["chapters"] else None, "green", .13)
            if chapter in (1, 65) or chapter % 5 == 0:
                length = 1.3 if chapter % 10 == 0 else .65
                self.line(xx, cy-radius-.4, xx, cy-radius-.4-length, "gold", .13)
            if chapter in (1, 10, 20, 30, 40, 50, 60, 65):
                labelw = 5 if chapter != 1 else 3
                left = max(x, min(xx-labelw/2, x+w-labelw))
                self.para(str(chapter), left, cy-2.5, labelw, self.small, "Geo", "muted", 1)
        return cy-6.2

    def finish(self):
        return {"page": self.number, "text_boxes": self.text_boxes,
                "graphic_boxes": self.graphic_boxes, "sections": self.sections,
                **({"table": self.table} if self.table else {})}


def rules_page(p):
    if p.size=="A5":
        return compact_rules_page(p)
    y = p.header("წესები")
    y = p.para(COPY["overview_ka"], p.m, y, p.iw) - (3 if p.size == "A4" else 2)
    gap = 6 if p.size == "A4" else 4
    leftw = (p.iw-gap)*.50
    rightx, rightw = p.m+leftw+gap, p.iw-leftw-gap
    columns_top = y
    ly = p.section("ერთი ეპიზოდის სვლა", p.m, y, leftw)
    ry = p.section("ნიშნების მოქმედებები", rightx, y, rightw)
    ly = p.steps(COPY["turn_steps_ka"], p.m, ly, leftw)
    ry = p.action_list(rightx, ry, rightw)
    p.sections += [{"kind":"turns", "bbox_mm":[p.m,ly,p.m+leftw,columns_top]},
                   {"kind":"actions", "bbox_mm":[rightx,ry,rightx+rightw,columns_top]}]
    ly=p.section(SOURCE["flashback_rules"]["title_ka"],p.m,ly-1,leftw)
    ly=p.modes(p.m,ly,leftw)
    ly=p.para(COPY["flashback_ka"],p.m,ly,leftw)
    ry=p.section(SOURCE["scale_rules"]["title_ka"],rightx,ry-1,rightw)
    ry=p.para(COPY["scale_ka"],rightx,ry,rightw)
    ly-=2
    title=SOURCE["victory"]["title_ka"]
    titleh=make_paragraph(title,leftw-4,p.heading,"GeoBold")[1]
    winh=make_paragraph(COPY["win_ka"],leftw-4,p.body)[1]
    totalh=titleh+winh+4
    p.rect(p.m,ly-totalh,leftw,totalh,tint("green",.08),"gold",.18,1.2)
    wy=p.para(title,p.m+2,ly-1.3,leftw-4,p.heading,"GeoBold","green")
    p.para(COPY["win_ka"],p.m+2,wy-.7,leftw-4)
    p.sections.append({"kind":"final_positions","bbox_mm":[p.m,ly-totalh,p.m+leftw,ly]})
    y=min(ly-totalh,ry)-2
    return p.timeline(p.m,y,p.iw)


def compact_rules_page(p):
    """Full-width copy avoids wasting space on repeated short wrapped lines."""
    y=p.header("წესები")
    y=p.para(COPY["overview_ka"],p.m,y,p.iw)-1
    y=p.section("ერთი ეპიზოდის სვლა",p.m,y,p.iw)
    oldgap=p.gap
    p.gap=.2
    y=p.steps(COPY["turn_steps_ka"],p.m,y,p.iw)
    p.gap=oldgap
    y=p.section("ნიშნების მოქმედებები",p.m,y-.3,p.iw)
    for a in COPY["actions"]:
        # A reduced vector icon, with source title and instruction on one run.
        p.c.saveState()
        p.c.translate(p.m*MM,(y-3.7)*MM)
        p.c.scale(.72,.72)
        # Use a local drawing canvas while retaining the world-coordinate
        # graphic bounds for the independent PDF verifier.
        before=len(p.graphic_boxes)
        originalcheck=p.check
        p.check=lambda *args:None
        p.action_icon(a["kind"],0,0)
        p.check=originalcheck
        for box in p.graphic_boxes[before:]:
            box["bbox_mm"]=[p.m+box["bbox_mm"][0]*.72,y-3.7+box["bbox_mm"][1]*.72,
                            p.m+box["bbox_mm"][2]*.72,y-3.7+box["bbox_mm"][3]*.72]
            p.check(box["bbox_mm"],"compact action icon")
        p.c.restoreState()
        bottom=p.para(a["text_ka"],p.m+12,y,p.iw-12,label=a["title_ka"])
        if a["kind"]=="remove":
            bottom=p.para(a["rule_note_ka"],p.m+12,bottom-.3,p.iw-12,p.small,ink="muted")
        y=min(bottom,y-7)-.3
    y=p.section(SOURCE["flashback_rules"]["title_ka"],p.m,y,p.iw)
    y=p.modes(p.m,y,p.iw)
    y=p.para(COPY["flashback_ka"],p.m,y,p.iw)-.5
    top=y
    y=p.section(SOURCE["scale_rules"]["title_ka"],p.m,y,p.iw*.53)
    example=SOURCE["episodes"][5]
    p.para(f'ეპიზოდი {example["episode_number"]} • თავები {example["chapter_span_ka"]}',
           p.m+p.iw*.55,top,p.iw*.45,p.small,"GeoBold","muted",2)
    y=p.para(COPY["scale_ka"],p.m,y,p.iw)-.2
    y=p.timeline(p.m,y,p.iw,False)-.3
    title=SOURCE["victory"]["title_ka"]
    th=make_paragraph(title,p.iw-4,p.heading,"GeoBold")[1]
    bh=make_paragraph(COPY["win_ka"],p.iw-4,p.body)[1]
    h=th+bh+3
    p.rect(p.m,y-h,p.iw,h,tint("green",.08),"gold",.18,1.2)
    wy=p.para(title,p.m+2,y-1,p.iw-4,p.heading,"GeoBold","green")
    p.para(COPY["win_ka"],p.m+2,wy-.5,p.iw-4)
    return y-h


def episode_table(p, top):
    y = p.section("ეპიზოდების სწრაფი ცნობარი", p.m, top, p.iw)
    # One table,24 rows. Values (except abbreviated titles) come from the JSON.
    cols = [p.m, p.m+p.iw*.065, p.m+p.iw*.565, p.m+p.iw*.865, p.w-p.m]
    size = p.small if p.size == "A5" else 9.4
    pad = .1 if p.size == "A5" else .7
    headerh = size/MM*1.22+2*pad
    tabletop = y
    p.rect(p.m, y-headerh, p.iw, headerh, "green", None)
    for i, title in enumerate(("ეპ.", "მოკლე სათაური", "სამეფო", "თავები")):
        p.para(title, cols[i]+pad, y-pad, cols[i+1]-cols[i]-2*pad,
               size, "GeoBold", "ivory", 1 if i in (0,3) else 0, role="table_header")
    y -= headerh
    rows = []
    previous_act = None
    for e in SOURCE["episodes"]:
        num = e["episode_number"]
        title = e["short_title_ka"]
        realm = f'{e["primary_realm"]["number"]} {e["primary_realm"]["name_ka"]}'
        chapters = e["chapters"]
        span = str(chapters[0]) if len(chapters)==1 else f"{chapters[0]}-{chapters[-1]}"
        cells = [str(num), title, realm, span]
        heights = [make_paragraph(s, cols[i+1]-cols[i]-2*pad, size, "GeoBold" if i==0 else "Geo")[1]
                   for i,s in enumerate(cells)]
        rowh = max(heights)+2*pad
        if num % 2:
            p.rect(p.m, y-rowh, p.iw, rowh, tint("gold", .07), None)
        if previous_act is not None and e["act_number"] != previous_act:
            p.line(p.m, y, p.w-p.m, y, "gold", .28)
        for i, text in enumerate(cells):
            p.para(text, cols[i]+pad, y-(rowh-heights[i])/2, cols[i+1]-cols[i]-2*pad,
                   size, "GeoBold" if i==0 else "Geo", "green" if i in (0,2) else "ink",
                   1 if i in (0,3) else 0, role="table_cell")
        rows.append({"episode_number":num, "short_title_ka":title, "bbox_mm":[p.m,y-rowh,p.w-p.m,y],
                     "primary_realm":e["primary_realm"], "chapters":chapters})
        y -= rowh
        previous_act = e["act_number"]
    p.line(p.m, y, p.w-p.m, y, "gold", .24)
    p.table = {"bbox_mm":[p.m,y,p.w-p.m,tabletop], "columns_mm":cols, "rows":rows}
    return y


def setup_page(p):
    y = p.header("მომზადება და ცნობარი")
    # A horizontal seven-realm sketch leaves the full width for all six source
    # setup instructions. The realms have no edges or invented route graph.
    rx=p.w-p.m-43
    for index,realm in enumerate(SOURCE["realms"]):
        xx=rx+index*6.1
        p.rect(xx,y-4.4,4.8,4.8,tint("gold",.12),"gold",.16,.4)
        p.para(str(realm["number"]),xx+.4,y-.2,4,p.small,"GeoBold","green",1)
        if index==0:
            p.token(xx+.1,y-3.8,.75)
    y = p.section("მომზადება", p.m, y, p.iw-48)
    originalgap=p.gap
    p.gap=.4 if p.size=="A5" else 1.5
    y=p.steps(COPY["setup_steps_ka"],p.m,y,p.iw)
    p.gap=originalgap
    components="; ".join(f'{s["quantity"]} {s["name_ka"]} • {s["dimensions"]}'
                         for s in SOURCE["components"] if s["id"]!="rulebook_sheet")+"."
    y=p.para(components,p.m,y-.5,p.iw,p.small,ink="muted")-1
    y = episode_table(p, y)
    y-=1.2
    # A short print/source block stays at the body minimum; no microprint.
    p.line(p.m,y,p.w-p.m,y,"gold",.2)
    y-=1.2
    for key in ("print_ka", "edition_ka", "art_ka"):
        y = p.para(COPY[key], p.m, y, p.iw, p.small) - .7
    return y


def check_source():
    assert META["token_mode"] == "character_tokens_only_21"
    assert META["total_episodes"] == 24
    assert [e["episode_number"] for e in SOURCE["episodes"]] == list(range(1,25))
    assert [c for e in SOURCE["episodes"] for c in e["chapters"]] == list(range(1,66))
    assert META["total_stanzas"] == 1669 and META["total_acts"]==5
    assert len(SOURCE["gameplay_loop"])==6 and len(SOURCE["setup_steps"])==6
    assert len(SOURCE["characters_manifest"])==META["total_character_tokens"]==21
    assert [r["number"] for r in SOURCE["realms"]]==list(range(1,8))
    assert all(e["mode"]=="recollection" for e in SOURCE["episodes"][5:12])


def render_previews(pdfs):
    pdftoppm = shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"
    previews = []
    for size, path in pdfs.items():
        prefix = OUT / f"preview-{size.lower()}"
        subprocess.run([pdftoppm, "-r", "150", "-png", str(path), str(prefix)], check=True,
                       capture_output=True)
        for number in (1,2):
            preview = Path(f"{prefix}-{number}.png")
            with Image.open(preview) as im:
                im.verify()
            previews.append(preview)
    # Pillow creates a convenient contact sheet; page PNGs remain full150dpi.
    thumbs = []
    for path in previews:
        with Image.open(path) as im:
            thumb = im.convert("RGB")
            thumb.thumbnail((630,900), Image.Resampling.LANCZOS)
            thumbs.append(ImageOps.expand(thumb, border=8, fill="#203D37"))
    sheet = Image.new("RGB", (max(im.width for im in thumbs)*2+36,
                              max(im.height for im in thumbs)*2+36), "#ddd8ca")
    cw, ch = (sheet.width-36)//2, (sheet.height-36)//2
    for i, im in enumerate(thumbs):
        sheet.paste(im, (12+(i%2)*(cw+12),12+(i//2)*(ch+12)))
    contact = OUT / "preview-all.png"
    sheet.save(contact)
    return previews+[contact]


def file_info(path):
    return {"path":str(path.relative_to(ROOT)), "bytes":path.stat().st_size, "sha256":sha(path)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fonts = register_fonts()
    check_source()
    layout = {"coordinate_system":"millimetres, origin bottom left", "minimum_safe_margin_mm":8,
              "design_margin_mm":9, "editions":{}}
    pdfs = {}
    for size, dims in (("A4",(210,297)), ("A5",(148,210))):
        path = OUT / f"pantersskin-rulebook-ka-{size.lower()}.pdf"
        c = canvas.Canvas(str(path), pagesize=tuple(v*MM for v in dims), pageCompression=1,
                          invariant=1)
        c.setTitle(COPY["title_ka"]+" - "+COPY["subtitle_ka"])
        c.setAuthor("შოთა რუსთაველი")
        reports = []
        for number, draw in ((1,rules_page),(2,setup_page)):
            p = Page(c,size,number)
            bottom = draw(p)
            if bottom < 8:
                raise ValueError(("Page overflow",size,number,bottom))
            report=p.finish()
            report["content_bottom_mm"]=bottom
            reports.append(report)
            c.showPage()
        c.save()
        layout["editions"][size]={"file":path.name,"size_mm":list(dims),"pages":reports}
        pdfs[size]=path
    (OUT/"layout-report.json").write_text(json.dumps(layout,ensure_ascii=False,indent=2)+"\n")
    previews=render_previews(pdfs)
    # The verifier independently parses actual PDF text, fonts, and paths.
    from verify_rulebook import verify
    validation=verify(OUT)
    if validation.get("status") != "independent_source_content_and_pdf_geometry_passed":
        raise ValueError(("Independent verification did not pass", validation))
    files=list(pdfs.values())+previews+[OUT/"layout-report.json",OUT/"validation.json"]
    manifest={"title_ka":COPY["subtitle_ka"],"language":"ka","status":"verified",
      "source":file_info(SOURCE_PATH),"palette_source":file_info(PALETTE_PATH),
      "builder":file_info(Path(__file__)),
      "verifier":file_info(HERE/"verify_rulebook.py"),
      "documentation":file_info(HERE/"README.md"),
      "linked_components":{s["id"]:s["file_path"] for s in SOURCE["components"]},
      "content_selection":{"verbatim_core_fields":["meta.title_ka","meta.subtitle_ka",
         "overview.summary_ka","setup_steps[].instruction_ka","gameplay_loop[].instruction_ka",
         "token_actions[].title_ka","token_actions[].instruction_ka","token_actions[kind=remove].rule_note_ka",
         "flashback_rules.description_ka","flashback_rules.modes[].label_ka","scale_rules.explanation_ka",
         "victory.condition_ka","meta.poem_basis_ka","meta.art_basis_ka",
         "print_production.general_instructions_ka[0]","episodes[].short_title_ka"],
         "supplemental_reference_fields_not_duplicated":True,
         "legacy_rulebook_copy_used":False},
      "formats_mm":{"A4":[210,297],"A5":[148,210]},"pages_per_pdf":2,
      "minimum_safe_margin_mm":8,"design_margin_mm":9,
      "minimum_body_font_pt":{"A4":10.4,"A5":8},"minimum_any_font_pt":{"A4":9,"A5":8},
      "print_scale_percent":100,"duplex_flip":"long_edge",
      "palette":PAL,"fonts":[file_info(fonts/f"Georgian-{s}.ttf") for s in ("Regular","Bold","Display")],
      "source_interpretations":SOURCE["source_interpretations"],"files":[file_info(p) for p in files]}
    (OUT/"build-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":"passed","pdfs":[str(p) for p in pdfs.values()],
                      "bottom_mm":{s:[p["content_bottom_mm"] for p in e["pages"]]
                                   for s,e in layout["editions"].items()}},ensure_ascii=False))


if __name__ == "__main__":
    main()
