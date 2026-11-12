#!/usr/bin/env python3
"""Build the four-sheet print-and-play packet with ReportLab.

Existing portrait PNGs are embedded unchanged. The board and tokens are vector
art. No network access, repository source changes, or image generation needed.
"""

from pathlib import Path
import json
import math

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf"
TMP = ROOT / "tmp" / "pdfs" / "letter-and-reunion"
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
PDF = OUT / "panthers-skin-letter-and-reunion.pdf"

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
for name, filename in (
    ("Body", "Arial.ttf"),
    ("BodyBold", "Arial Bold.ttf"),
    ("BodyItalic", "Arial Italic.ttf"),
    ("Title", "Georgia.ttf"),
    ("TitleBold", "Georgia Bold.ttf"),
):
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily(
    "Body", normal="Body", bold="BodyBold", italic="BodyItalic", boldItalic="BodyBold"
)

INK = colors.HexColor("#252923")
MUTED = colors.HexColor("#62695E")
LINE = colors.HexColor("#B9BFB2")
FAINT = colors.HexColor("#F3F4EF")
ACCENT = colors.HexColor("#844B3A")
WHITE = colors.white
BOUNDS = []
C = canvas.Canvas(str(PDF), pagesize=A4, pageCompression=1)
C.setTitle("Panther's Skin: The Letter and the Reunion - print-and-play prototype")
C.setAuthor("Pantersskin project")
C.setSubject("Cooperative reenactment of chapters 52-54; four single-sided A4 sheets")


def txt(s, x, y, size=10, font="Body", color=INK, align="left"):
    C.setFont(font, size)
    C.setFillColor(color)
    if align == "center":
        C.drawCentredString(x, y, s)
    elif align == "right":
        C.drawRightString(x, y, s)
    else:
        C.drawString(x, y, s)


def para(s, x, top, width, size=10.3, leading=None, font="Body", color=INK):
    style = ParagraphStyle(
        "p", fontName=font, fontSize=size,
        leading=leading or size * 1.33, textColor=color,
        spaceAfter=0, allowWidows=0, allowOrphans=0,
    )
    p = Paragraph(s, style)
    _, height = p.wrap(width, 2000)
    bottom = top - height
    assert bottom >= 32, (C.getPageNumber(), s[:60], bottom)
    p.drawOn(C, x, bottom)
    BOUNDS.append({"page": C.getPageNumber(), "x": x, "top": top,
                   "bottom": bottom, "width": width, "text": s})
    return bottom


def section(title, text, x, top, width, size=10.1, gap=17):
    txt(title, x, top, 11.5, "BodyBold")
    y = para(text, x, top - 10, width, size)
    return y - gap


def line(x1, y1, x2, y2, color=LINE, width=0.7):
    C.setStrokeColor(color)
    C.setLineWidth(width)
    C.line(x1, y1, x2, y2)


def footer(page, kind, w, h):
    line(34, 29, w - 34, 29)
    txt("PANTHER'S SKIN  /  THE LETTER AND THE REUNION", 34, 16, 7.5, color=MUTED)
    txt(f"PROTOTYPE 0.1  /  {kind}  /  {page} OF 4", w - 34, 16, 7.5, color=MUTED, align="right")


def heading(kicker, title, subtitle, w, h, title_size=27):
    txt(kicker, 36, h - 42, 8.8, "BodyBold", ACCENT)
    txt(title, 36, h - 80, title_size, "TitleBold")
    txt(subtitle, 36, h - 101, 10.3, color=MUTED)
    line(36, h - 116, w - 36, h - 116, ACCENT, 0.9)


def rules_page():
    w, h = A4
    C.setPageSize(A4)
    heading("A COOPERATIVE CHAPTER FOR PEOPLE WHO KNOW THE POEM",
            "The Letter and the Reunion",
            "2-4 players  /  first play: about 15-20 minutes  /  four single-sided A4 sheets", w, h)
    y = para(
        "Avtandil has Nestan's letter. Send news ahead to Pridon, bring the letter to Tariel, "
        "open the chambers with Asmat, and reunite the company with its armor. "
        "<b>The group brings the familiar plot to life through shared actions.</b>",
        36, h - 134, w - 72, 11, 15,
    )
    C.setFillColor(FAINT)
    C.roundRect(36, y - 42, w - 72, 32, 3, fill=1, stroke=0)
    txt("PRINT AT ACTUAL SIZE. PAGE 2 IS LANDSCAPE. CUT ONLY PAGE 3.",
        47, y - 29, 9.1, "BodyBold")
    y -= 65
    gap = 24
    col = (w - 72 - gap) / 2
    lx, rx = 36, 36 + col + gap
    left = y
    right = y

    left = section("1  Choose a voice; share the cast", 
        "Choose a character to voice; unchosen roles are shared. "
        "<b>Any player can activate any character.</b> Rotate the lead player each round and plan together.", lx, left, col)
    left = section("2  Set the opening scene",
        "Put <b>A</b> in Gulansharo, <b>T</b> at the Reeds, <b>AS</b> at the Cave, and <b>P</b> "
        "at Mulghazanzar.<br/>"
        "Put <b>Nestan's letter + veil fringe</b> under Avtandil's card. Leave the notice, "
        "armor, and N aside. Empty all checkboxes; start round 1. Read scene 1 on page 4.",
        lx, left, col)
    left = section("3  Take up to two actions per round",
        "Resolve actions one after the other. Each activates <b>one character</b>. That character "
        "can act only <b>once this round</b>; put an action marker on their card. Presence at a "
        "meeting does not use a character's action. The first action can unlock the second.<br/>"
        "At round end, if <b>N is in transit</b>, advance it <b>one dashed arrow</b>, including the dispatch round. "
        "It reaches Pridon after two round-ends. Retrieve both action markers; advance the round. "
        "You may end early and lose unused actions.", lx, left, col)
    left = section("4  Follow the story gates",
        "<b>Gulansharo:</b> send the notice before Avtandil leaves.<br/>"
        "<b>Reeds:</b> Avtandil and Tariel stay until Tariel receives Nestan's letter.<br/>"
        "<b>Cave:</b> the three stay until the chambers open.<br/>"
        "Travel follows solid arrows, one disc per action. Pridon stays in his kingdom. "
        "Keep carried objects under the carrier's character card.", lx, left, col)
    left = section("5  Complete the reunion",
        "Finish immediately when <b>A, T, and AS</b> have reached Pridon, all three preparation boxes are "
        "marked, and Pridon has his armor. Record this round; read scene 4. Departure is automatic.<br/>"
        "<b>First-play target: 12 rounds. Tighter target: 10.</b> If you take longer, keep playing "
        "and record your round. Beyond 12, count on paper.", lx, left, col, gap=0)

    txt("THE ACTIONS", rx, right, 11.5, "BodyBold", ACCENT)
    right -= 22
    entries = [
        ("A  /  Send notice",
         "At Gulansharo, once. Put notice disc N there. Leave its card aside until N reaches Pridon, "
         "then put the card under Pridon and set N aside."),
        ("A, T, OR AS  /  Travel",
         "Move that disc one solid arrow forward, observing the three gates. Each traveler moves separately."),
        ("T  /  Receive Nestan's letter",
         "At the Reeds with Avtandil. Put the letter + fringe under Tariel's card. Mark Letter received; read scene 2."),
        ("T  /  Open the chambers",
         "At the Cave with Avtandil AND Asmat, after the letter. Mark Chambers opened. Choose A, T, or AS to carry "
         "the armor bundle; put it under their card. The two knights equip themselves. Read scene 3."),
        ("P  /  Read the notice",
         "After it arrives, mark preparation box 1."),
        ("P  /  Gather 300 horsemen",
         "After box 1, mark box 2. This is another action in a later round."),
        ("P  /  Ready the crossing",
         "After box 2, mark box 3. Again, he acts only once per round."),
        ("ARMOR CARRIER  /  Give Pridon his armor",
         "At Mulghazanzar, spend the carrier's action to put the armor under Pridon's card. Pridon does not spend an action."),
    ]
    for title, body in entries:
        right = para(f"<b>{title}</b><br/>{body}", rx, right, col, 10.1, 13.3) - 12
    right = para(
        "<b>Objects:</b> choose the armor carrier when the chambers open; keep that carrier until delivery. "
        "There are no other object transfers.<br/>"
        "<b>One-time events:</b> each action except Travel can happen only once.",
        rx, right, col, 9.4, 12.2, color=MUTED)
    assert min(left, right) > 41, (left, right)
    footer(1, "RULES", w, h)
    C.showPage()


def arrow(x1, y1, x2, y2, dashed=False, color=INK, width=1.2):
    C.saveState()
    C.setStrokeColor(color)
    C.setFillColor(color)
    C.setLineWidth(width)
    if dashed:
        C.setDash(4, 4)
    C.line(x1, y1, x2, y2)
    C.setDash()
    angle = math.atan2(y2 - y1, x2 - x1)
    length, spread = 7, 0.43
    p = C.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - length * math.cos(angle - spread), y2 - length * math.sin(angle - spread))
    p.lineTo(x2 - length * math.cos(angle + spread), y2 - length * math.sin(angle + spread))
    p.close()
    C.drawPath(p, fill=1, stroke=0)
    C.restoreState()


def node(cx, cy, title, note="", start="", gate="", width=166, height=123):
    x, y = cx - width / 2, cy - height / 2
    C.setFillColor(WHITE)
    C.setStrokeColor(INK)
    C.setLineWidth(0.9)
    C.roundRect(x, y, width, height, 6, fill=1, stroke=1)
    txt(title, cx, y + height - 23, 13, "TitleBold", align="center")
    if note:
        txt(note, cx, y + height - 39, 8.2, color=MUTED, align="center")
    if start:
        txt(start, cx, y + height - 65, 11, "BodyBold", ACCENT, align="center")
    if gate:
        para(gate, x + 10, y + 33, width - 20, 8.5, 10.7, color=MUTED)
    return x, y


def checkbox(x, y, label, size=9):
    C.setStrokeColor(INK)
    C.setLineWidth(0.7)
    C.rect(x, y - 1, 8, 8, stroke=1, fill=0)
    txt(label, x + 13, y, size)


def board_page():
    w, h = landscape(A4)
    C.setPageSize((w, h))
    heading("CHAPTER 52-54  /  JOURNEY DIAGRAM",
            "Two letters. One reunion.",
            "Solid arrows: one traveler action. Dashed arrows: notice disc N advances automatically at each round end.",
            w, h, 25)
    xs = [129, 324, 519, 714]
    top, bottom = 399, 224
    halfw, halfh = 83, 61.5
    for a, b in zip(xs, xs[1:]):
        arrow(a + halfw + 3, top, b - halfw - 3, top)
    arrow(xs[3], top - halfh - 3, xs[3], bottom + halfh + 3)
    arrow(xs[3] - halfw - 3, bottom, xs[2] + halfw + 3, bottom)
    arrow(xs[2] - halfw - 3, bottom, xs[1] + halfw + 3, bottom)
    arrow(xs[0], top - halfh - 3, xs[0], bottom + 30, dashed=True, color=ACCENT)
    arrow(xs[0] + 52, bottom, xs[1] - halfw - 3, bottom, dashed=True, color=ACCENT)

    node(xs[0], top, "Gulansharo", "SEND: put notice disc N here", "START A",
         "Send Avtandil's notice<br/>before he leaves.")
    node(xs[1], top, "Sea Landing", "return voyage")
    node(xs[2], top, "Shore Road", "toward the wilderness")
    node(xs[3], top, "Reeds", "receive Nestan's letter here", "START T",
         "A and T stay until<br/>Letter received is marked.")
    node(xs[3], bottom, "Cave", "open the chambers here", "START AS",
         "A, T, and AS stay until<br/>Chambers opened is marked.")
    node(xs[2], bottom, "Riding Road", "the company travels onward")
    node(xs[1], bottom, "Mulghazanzar", "Pridon's kingdom", "START P",
         "All travelers arrive here.<br/>Give Pridon his armor.")

    C.setFillColor(WHITE)
    C.setStrokeColor(ACCENT)
    C.setLineWidth(0.9)
    C.setDash(4, 3)
    C.roundRect(xs[0] - 50, bottom - 28, 100, 56, 5, fill=1, stroke=1)
    C.setDash()
    txt("N AT SEA", xs[0], bottom + 8, 9, "BodyBold", ACCENT, "center")
    txt("after first round-end", xs[0], bottom - 8, 8, color=MUTED, align="center")
    para("Retainers carry the notice. At arrival, set N aside and put its card under Pridon.",
         51, 176, 152, 8.4, 11, color=MUTED)

    line(36, 132, w - 36, 132)
    txt("PRIDON'S PREPARATIONS  /  IN ORDER", 38, 117, 8.5, "BodyBold", ACCENT)
    checkbox(38, 98, "1 Read notice", 8.7)
    checkbox(155, 98, "2 Gather 300", 8.7)
    checkbox(270, 98, "3 Ready crossing", 8.7)
    txt("STORY CHECKS", 470, 117, 8.5, "BodyBold", ACCENT)
    checkbox(470, 98, "Letter received", 8.7)
    checkbox(622, 98, "Chambers opened", 8.7)

    txt("ROUND", 38, 67, 9, "BodyBold")
    for n in range(1, 13):
        x = 100 + (n - 1) * 29
        C.setStrokeColor(ACCENT if n in (10, 12) else LINE)
        C.setLineWidth(1 if n in (10, 12) else 0.6)
        C.rect(x, 57, 25, 23, fill=0, stroke=1)
        txt(str(n), x + 12.5, 64.5, 10, "BodyBold" if n in (10, 12) else "Body", align="center")
    txt("10: tighter target   12: first-play target", 470, 68, 9, "BodyBold")
    txt("FINISH: A + T + AS here, P ready, armor delivered.", 470, 51, 8.6)
    txt("Waypoints, separate piece movements, and timing are game abstractions; see page 4.",
        38, 40, 7.7, color=MUTED)
    footer(2, "BOARD", w, h)
    C.showPage()


CHARACTERS = [
    ("A", "Avtandil", "avtandil", "GULANSHARO", "Send the notice. Bring Nestan's letter to Tariel. Travel to Pridon."),
    ("T", "Tariel", "tariel", "REEDS", "Receive Nestan's letter. Open the chambers with Avtandil and Asmat present."),
    ("AS", "Asmat", "asmat", "CAVE", "Join the journey after the chambers open. Any of the three travelers may carry the armor."),
    ("P", "Pridon", "pridon", "MULGHAZANZAR", "Read the notice, gather 300 horsemen, and ready the crossing. Stay in your kingdom."),
]


def character_card(x, y, w, h, data):
    code, name, image_name, start, job = data
    C.setStrokeColor(INK)
    C.setLineWidth(0.7)
    C.roundRect(x, y, w, h, 3, fill=0, stroke=1)
    image_path = ROOT / "assets" / "characters" / f"{image_name}.png"
    C.drawImage(ImageReader(str(image_path)), x + 12, y + h - 72,
                width=54, height=54, mask="auto", preserveAspectRatio=True)
    txt(name, x + 77, y + h - 28, 17, "TitleBold")
    txt(f"{code}  /  START: {start}", x + 77, y + h - 44, 7.8, "BodyBold", ACCENT)
    para(job, x + 77, y + h - 55, w - 89, 9.2, 12)
    line(x + 12, y + 29, x + w - 12, y + 29)
    txt("CARRIED OBJECTS: TUCK CARDS UNDER HERE", x + 12, y + 15, 7.4, color=MUTED)


def object_card(x, y, w, h, title, subtitle, body, icon):
    C.setStrokeColor(INK)
    C.setLineWidth(0.7)
    C.roundRect(x, y, w, h, 3, fill=0, stroke=1)
    if icon == "letter":
        C.rect(x + 12, y + h - 31, 24, 16, fill=0, stroke=1)
        line(x + 12, y + h - 15, x + 24, y + h - 24, INK)
        line(x + 36, y + h - 15, x + 24, y + h - 24, INK)
    else:
        path = C.beginPath()
        path.moveTo(x + 14, y + h - 15)
        path.lineTo(x + 35, y + h - 15)
        path.lineTo(x + 35, y + h - 26)
        path.curveTo(x + 35, y + h - 34, x + 24, y + h - 38, x + 24, y + h - 38)
        path.curveTo(x + 24, y + h - 38, x + 14, y + h - 34, x + 14, y + h - 26)
        path.close()
        C.drawPath(path, fill=0, stroke=1)
    ptop = para(f"<b>{title}</b>", x + 46, y + h - 15, w - 58, 10.6, 13.4)
    ptop = para(subtitle, x + 12, min(y + h - 49, ptop - 10), w - 24, 8.4, 11, color=ACCENT)
    para(body, x + 12, ptop - 10, w - 24, 9.3, 12)


def pieces_page():
    w, h = A4
    C.setPageSize(A4)
    heading("CUT ON THE SOLID OUTLINES",
            "The cast and what they carry",
            "Character cards stay beside the board. Small discs move on it. All information is public.",
            w, h, 23)
    cardw, cardh, gutter = (w - 84) / 2, 139, 12
    y1 = h - 276
    for i, data in enumerate(CHARACTERS):
        x = 36 + (i % 2) * (cardw + gutter)
        y = y1 - (i // 2) * (cardh + 12)
        character_card(x, y, cardw, cardh, data)

    oy, oh = 248, 126
    ow = (w - 96) / 3
    objects = [
        ("Nestan's letter", "+ VEIL FRINGE", "Start with Avtandil. Tariel receives this at the Reeds.", "letter"),
        ("Avtandil's notice", "TO PRIDON", "Start aside. Disc N tracks delivery; put this under Pridon when N arrives.", "letter"),
        ("Armor for Pridon", "THE THIRD SUIT", "Created when the chambers open. Choose one carrier; deliver it to Pridon.", "armor"),
    ]
    for i, data in enumerate(objects):
        object_card(36 + i * (ow + 12), oy, ow, oh, *data)

    txt("FOUR CHARACTER DISCS", 36, 224, 9, "BodyBold", ACCENT)
    txt("ACTION I + II  /  ROUND R  /  NOTICE N", 290, 224, 8.2, "BodyBold", ACCENT)
    for i, label in enumerate(["A", "T", "AS", "P", "I", "II", "R", "N"]):
        x = 54 + i * 68
        C.setStrokeColor(INK)
        C.setLineWidth(0.8)
        C.circle(x, 184, 20, fill=0, stroke=1)
        txt(label, x, 177, 16 if len(label) == 1 else 13.5, "BodyBold", align="center")
    para("<b>Use:</b> A, T, AS, and P are the movable pieces. Put I and II on character cards to mark "
         "who has acted this round. R marks the round. N tracks the notice's courier journey. "
         "Keep all large cards beside the board. Coins can replace small discs.",
         36, 137, w - 72, 10.2, 14)
    para("<b>Reset for another play:</b> erase the five board checkboxes, return the objects to their "
         "starting positions, and try a different armor carrier. Keep the complete cast available.",
         36, 84, w - 72, 9.5, 12.7, color=MUTED)
    footer(3, "CUTOUTS", w, h)
    C.showPage()


def scenes_page():
    w, h = A4
    C.setPageSize(A4)
    heading("READ THESE SHORT PASSAGES AT THEIR MARKED MOMENTS",
            "The chapter on the table",
            "A retelling of project chapters 52-54. The main events and ending remain fixed.", w, h, 25)
    y = h - 143
    scenes = [
        ("1  News from Gulansharo", "READ AT SETUP",
         "Nestan's reply has reached Avtandil. Her letter and a fringe from her veil will speak to "
         "Tariel across their separation. Avtandil also writes to Pridon: Nestan has been found in "
         "Kadjeti, and the brothers will come to him. Pridon's retainers carry this notice while "
         "Avtandil takes the sea route toward Tariel."),
        ("2  The letter among the reeds", "READ WHEN TARIEL RECEIVES THE LETTER",
         "Avtandil brings Tariel Nestan's words and the veil token. She remains faithful to him, "
         "but fears that he will throw his life away against the fortress. The letter restores "
         "their connection. The friends must now travel back to Asmat, who will recognize "
         "Nestan's handwriting and share their joy."),
        ("3  The unopened chambers", "READ WHEN THE CHAMBERS OPEN",
         "At Tariel's suggestion, the three open the stored treasure of the Devis. Among the riches "
         "they find three exceptional suits of armor and their weapons. Avtandil and Tariel equip "
         "themselves. The third suit is bundled as a gift for Pridon. Now the three will travel "
         "toward his kingdom."),
        ("4  The reunion", "READ WHEN ALL FINISH CONDITIONS ARE MET",
         "The companions reach Pridon's kingdom and give him his armor. Pridon provides three "
         "hundred selected horsemen and knows the way toward Kadjeti. Asmat remains in his household. "
         "The three sworn brothers depart together. The next chapter would follow their approach "
         "to the fortress."),
    ]
    for title, cue, body in scenes:
        txt(title, 36, y, 15.5, "TitleBold")
        txt(cue, 36, y - 17, 7.8, "BodyBold", ACCENT)
        y = para(body, 36, y - 29, w - 72, 10.6, 14.6) - 24
    line(36, y + 7, w - 36, y + 7)
    txt("WHAT IS FROM THE POEM; WHAT IS A GAME RULE", 36, y - 12, 9, "BodyBold", ACCENT)
    y = para(
        "<b>Story source:</b> actual stanza text in this project's chapters 52-54, especially Georgian-edition "
        "stanzas 1318-1325, 1327-1361, 1364-1374, and 1386-1392. English numbering differs. "
        "These passages are new summaries.<br/>"
        "<b>Game abstractions:</b> waypoints, two-round courier travel, individual disc movement, three "
        "preparation actions, armor-carrier choice, and round targets. In the poem the three travel "
        "together, and Asmat initially rides behind a knight. The pirate spoils, horse purchase, "
        "horse-herd prank, and hospitality are outside this small playable excerpt.<br/>"
        "<b>Prototype status:</b> a solver verifies a 10-round minimum and a 10-round solution with "
        "each possible armor carrier. Table enjoyment and the first-play target still need human playtesting.",
        36, y - 24, w - 72, 8.9, 11.9, color=MUTED,
    )
    assert y > 75, y
    txt("YOUR PLAY:  players ______   armor carrier ______   finishing round ______", 36, 57, 9.3)
    footer(4, "SCENES AND NOTES", w, h)
    C.showPage()


rules_page()
board_page()
pieces_page()
scenes_page()
C.save()
(TMP / "text-bounds.json").write_text(json.dumps(BOUNDS, indent=2))
print(PDF)
print(f"4 pages; {PDF.stat().st_size:,} bytes")
