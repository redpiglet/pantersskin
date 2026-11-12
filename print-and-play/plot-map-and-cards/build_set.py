#!/usr/bin/env python3
"""Create an explanatory plot map and twelve character cards.

Map copy and card copy are kept in JSON. Portrait PNGs are embedded unchanged.
Produces a four-page A4 packet and a one-page A3 overview.
"""

import json
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output" / "pdf"
TMP = ROOT / "tmp" / "pdfs" / "plot-map-and-cards"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
MAP = json.loads((HERE / "map.json").read_text())
CARDS = json.loads((HERE / "cards.json").read_text())

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
for name, file in [
    ("Body", "Arial.ttf"), ("BodyBold", "Arial Bold.ttf"),
    ("BodyItalic", "Arial Italic.ttf"),
    ("Title", "Georgia.ttf"), ("TitleBold", "Georgia Bold.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="BodyItalic")

INK = colors.HexColor("#282D29")
MUTED = colors.HexColor("#62675F")
ACCENT = colors.HexColor("#814A3A")
LINE = colors.HexColor("#B7BDB2")
WASH = colors.HexColor("#F1F3ED")
BOUNDS = []
PW, PH = A4


def clean(value):
    return value.replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")


def text(c, value, x, y, size=10, font="Body", color=INK, align="left"):
    c.setFillColor(color)
    c.setFont(font, size)
    if align == "right":
        c.drawRightString(x, y, clean(value))
    elif align == "center":
        c.drawCentredString(x, y, clean(value))
    else:
        c.drawString(x, y, clean(value))


def paragraph(c, value, x, top, width, size=10.4, leading=13.6, color=INK):
    style = ParagraphStyle("p", fontName="Body", fontSize=size, leading=leading, textColor=color)
    p = Paragraph(clean(value), style)
    _, height = p.wrap(width, 2000)
    bottom = top - height
    assert bottom >= 33, (value[:45], bottom)
    p.drawOn(c, x, bottom)
    BOUNDS.append({"text": value, "x": x, "top": top, "bottom": bottom, "width": width})
    return bottom


def rule(c, x1, y1, x2, y2, color=LINE, width=0.65):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)


def footer(c, label):
    rule(c, 36, 30, PW - 36, 30)
    text(c, "PANTHER'S SKIN  /  EXPLANATORY MAP + CHARACTER CARDS", 36, 17, 7.2, color=MUTED)
    text(c, label, PW - 36, 17, 7.2, color=MUTED, align="right")


def arrow_down(c, x, y1, y2):
    rule(c, x, y1, x, y2, ACCENT, 1)
    c.setFillColor(ACCENT)
    p = c.beginPath()
    p.moveTo(x, y2 - 1)
    p.lineTo(x - 3.7, y2 + 5)
    p.lineTo(x + 3.7, y2 + 5)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def milestone(c, item, top, height):
    x, width = 70, PW - 106
    bottom = top - height
    memory = item["kind"] == "recollection"
    c.saveState()
    c.setFillColor(WASH if memory else colors.white)
    c.setStrokeColor(ACCENT if memory else LINE)
    c.setLineWidth(0.8)
    if memory:
        c.setDash(4, 3)
    c.roundRect(x, bottom, width, height, 4, fill=1, stroke=1)
    c.restoreState()

    c.setFillColor(colors.white)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.circle(47, top - 21, 13, stroke=1, fill=1)
    text(c, str(item["number"]), 47, top - 25, 11, "BodyBold", ACCENT, "center")

    text(c, item["title"], x + 12, top - 22, 14.2, "TitleBold")
    text(c, item["realm"], x + 12, top - 37, 7.5, "BodyBold", ACCENT)
    text(c, "CH. " + item["chapters"], x + width - 12, top - 37, 7.5, color=MUTED, align="right")
    y = paragraph(c, item["body"], x + 12, top - 45, width - 24, 10.1, 12.6)
    if memory:
        y = paragraph(c, "<b>Earlier events:</b> " + item["sequence"].replace(">", " / "),
                      x + 12, y - 8, width - 24, 8.8, 11.8, ACCENT)
        y = paragraph(c, item["extra"], x + 12, y - 7, width - 24, 9.5, 12.4)
    cast_top = bottom + 20
    assert y >= cast_top + 6, (item["number"], y, cast_top)
    paragraph(c, item["cast"], x + 12, cast_top, width - 24, 8.1, 10.5, MUTED)


def map_panel(c, panel):
    text(c, "THE KNIGHT IN THE PANTHER'S SKIN  /  PLOT MAP", 36, PH - 40, 8.2, "BodyBold", ACCENT)
    titles = ["From Arabia to Gulansharo", "From captivity to reunion"]
    text(c, titles[panel], 36, PH - 77, 23, "TitleBold")
    paragraph(c,
        "Follow the numbered path in the order the poem tells its story. "
        "Dashed boxes explain earlier events recounted later.",
        36, PH - 95, PW - 72, 9.7, 13.1, MUTED)
    rule(c, 36, PH - 129, PW - 36, PH - 129, ACCENT, 0.85)
    top = PH - 148
    heights = ([98, 98, 158, 110, 98], [154, 109, 109, 100, 106])[panel]
    items = MAP["milestones"][panel * 5:panel * 5 + 5]
    for index, (item, height) in enumerate(zip(items, heights)):
        milestone(c, item, top, height)
        if index < 4:
            next_top = top - height - 12
            arrow_down(c, 47, top - 36, next_top - 5)
        top -= height + 12
    if panel == 0:
        text(c, "CONTINUE WITH 6 ON THE RIGHT-HAND PANEL  >", 70, 57, 8, "BodyBold", ACCENT)
    else:
        text(c, "Choose character cards. Follow their map numbers and connections.", 70, 49, 8.4, color=MUTED)
    footer(c, f"MAP PANEL {panel + 1} OF 2")


def character_card(c, card, x, bottom, width, height, index):
    top = bottom + height
    c.setStrokeColor(LINE)
    c.setLineWidth(0.75)
    c.roundRect(x, bottom, width, height, 3, fill=0, stroke=1)
    image = ROOT / "assets" / "characters" / f"{card['id']}.png"
    assert image.exists(), image
    c.drawImage(ImageReader(str(image)), x + 12, top - 67, width=49, height=49,
                preserveAspectRatio=True, mask="auto")
    name_size = 15.8 if card["id"] == "nestan" else 17
    text(c, card["name"], x + 72, top - 26, name_size, "TitleBold")
    role_bottom = paragraph(c, card["role"], x + 72, top - 36, width - 84, 9, 11.4, MUTED)
    text(c, card["realm"].upper(), x + 12, top - 77, 7.7, "BodyBold", ACCENT)
    text(c, f"CARD {index:02}", x + width - 12, top - 77, 7.4, color=MUTED, align="right")
    y = paragraph(c, card["thread"], x + 12, top - 88, width - 24, 9.4, 12.1)
    y = paragraph(c, "<b>Connections:</b> " + "; ".join(card["connections"]) + ".",
                  x + 12, y - 6, width - 24, 8.6, 11)
    assert y > bottom + 43, (card["name"], y, bottom)
    rule(c, x + 12, bottom + 38, x + width - 12, bottom + 38)
    text(c, "MAP " + " / ".join(str(n) for n in card["stops"]), x + 12, bottom + 23,
         8.7, "BodyBold", ACCENT)
    text(c, "Chapters " + card["chapters"], x + 12, bottom + 10, 7.6, color=MUTED)


def card_sheet(c, sheet):
    text(c, "CUT ON THE OUTLINES  /  SINGLE-SIDED CHARACTER CARDS", 36, PH - 40, 8.2, "BodyBold", ACCENT)
    text(c, "People whose stories connect", 36, PH - 77, 23, "TitleBold")
    paragraph(c, "Keep the cards beside the map. Their numbers show where to follow each person; "
              "their connections explain how the cast fits together.",
              36, PH - 95, PW - 72, 9.7, 13.1, MUTED)
    rule(c, 36, PH - 129, PW - 36, PH - 129, ACCENT, 0.85)
    cardw = (PW - 84) / 2
    cardh = 209
    for index, card in enumerate(CARDS[sheet * 6:sheet * 6 + 6]):
        x = 36 + (index % 2) * (cardw + 12)
        top = PH - 144 - (index // 2) * (cardh + 12)
        character_card(c, card, x, top - cardh, cardw, cardh, sheet * 6 + index + 1)
    footer(c, f"CHARACTER SHEET {sheet + 1} OF 2")


def metadata(c, title):
    c.setTitle(title)
    c.setAuthor("Pantersskin project")
    c.setSubject("Explanatory map of the poem's plot with twelve character reference cards")


packet = OUT / "panthers-skin-plot-map-and-cards.pdf"
c = canvas.Canvas(str(packet), pagesize=A4, pageCompression=1)
metadata(c, "Panther's Skin: plot map and character cards")
for panel in range(2):
    map_panel(c, panel)
    c.showPage()
for sheet in range(2):
    card_sheet(c, sheet)
    c.showPage()
c.save()

overview = OUT / "panthers-skin-plot-map-a3.pdf"
c = canvas.Canvas(str(overview), pagesize=landscape(A3), pageCompression=1)
metadata(c, "Panther's Skin: complete plot map - A3")
map_panel(c, 0)
c.saveState()
c.translate(PW, 0)
map_panel(c, 1)
c.restoreState()
c.showPage()
c.save()

(TMP / "text-bounds.json").write_text(json.dumps(BOUNDS, indent=2))
print(packet)
print(overview)
