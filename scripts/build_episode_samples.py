#!/usr/bin/env python3
"""Build Georgian episode 1-2 manga card samples from data/episode_data.json."""

import argparse
import hashlib
import io
import json
import re
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

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check-layout", action="store_true")
ARGS = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/episode_data.json"
SOURCE_BYTES = SOURCE.read_bytes()
DATA = json.loads(SOURCE_BYTES)
EPISODES = sorted(DATA["episodes"], key=lambda e: e["episode_number"])[:2]
assert [e["episode_number"] for e in EPISODES] == [1, 2]
assert all(1 <= len(e["scene_descriptions"]) <= 4 for e in EPISODES)
ASSETS = ROOT / "assets/episodes/episode-data-sample-v1"
OUT = ROOT / "output/pdf/episode-data-sample-v1"
MM = 72 / 25.4
W, H = 148 * MM, 210 * MM
M = 9 * MM
PAPER = colors.HexColor("#F8F5EC")
INK = colors.HexColor("#303B34")
GREEN = colors.HexColor("#203D37")
GOLD = colors.HexColor("#A58958")
MUTED = colors.HexColor("#647168")
rl_config.useA85 = False

FONT_DIR = ROOT / "tmp/georgian-deck/fonts"
if not all((FONT_DIR / f"Georgian-{style}.ttf").exists() for style in ["Regular", "Bold", "Display"]):
    from fontTools.ttLib import TTFont as FontToolsFont
    from fontTools.varLib.instancer import instantiateVariableFont
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for style, weight, optical in [("Regular", 400, 17), ("Bold", 650, 17), ("Display", 700, 28)]:
        font = instantiateVariableFont(FontToolsFont("/System/Library/Fonts/SFGeorgian.ttf"),
                                       {"wght": weight, "opsz": optical}, inplace=True)
        font["name"].setName("EpisodeGeorgian-" + style, 6, 3, 1, 0x409)
        font.save(FONT_DIR / f"Georgian-{style}.ttf")
for name, filename in [("Body", "Georgian-Regular.ttf"), ("Bold", "Georgian-Bold.ttf"),
                       ("Display", "Georgian-Display.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
for name, filename in [("Latin", "Arial.ttf"), ("LatinBold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(Path("/System/Library/Fonts/Supplemental") / filename)))


def plain(text):
    return str(text).replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")


def runs(text, font):
    cmap = pdfmetrics.getFont(font).face.charToGlyph
    fallback = "Latin" if font == "Body" else "LatinBold"
    result = []
    for ch in plain(text):
        family = font if ord(ch) in cmap else fallback
        assert ord(ch) in pdfmetrics.getFont(family).face.charToGlyph, (font, ch)
        if result and result[-1][0] == family:
            result[-1] = (family, result[-1][1] + ch)
        else:
            result.append((family, ch))
    return result


def width(text, font, size):
    return sum(pdfmetrics.stringWidth(t, f, size) for f, t in runs(text, font))


def para(text, available, size=10.6, leading=14.8, font="Body", color=INK, center=False):
    markup = "<br/>".join("".join(f'<font name="{f}">{escape(t)}</font>'
                                    for f, t in runs(line, font))
                             for line in plain(text).split("\n"))
    p = Paragraph(markup, ParagraphStyle("episode", fontName=font, fontSize=size,
                  leading=leading, textColor=color, alignment=1 if center else 0))
    _, height = p.wrap(available, 3000)
    return p, height


def latest_portrait(cid):
    candidates = []
    for p in (ROOT / "assets/characters/manga-color").glob(f"{cid}-v*.png"):
        match = re.fullmatch(re.escape(cid) + r"-v(\d+)\.png", p.name)
        if match:
            candidates.append((int(match[1]), p))
    assert candidates, (cid, "missing manga character reference")
    return max(candidates)[1]


def scene_path(ep, scene):
    return ASSETS / f"episode-{ep['episode_number']:02}-scene-{scene['scene_order']:02}.png"


class Renderer:
    def __init__(self, c, page_size=(W, H)):
        self.c = c
        self.page_size = page_size
        self.blocks = []
        self.context = None
        self.images = {}

    def record(self, kind, x, y, w, h, text=None, size=None):
        pw, ph = self.page_size
        assert x >= 13 and x + w <= pw - 13, (self.context, kind, "horizontal", x, w)
        assert y >= 14 and y + h <= ph - 14, (self.context, kind, "vertical", y, h)
        self.blocks.append({"episode": self.context[0], "side": self.context[1], "kind": kind,
                            "rect": [round(n, 2) for n in [x, y, w, h]],
                            "text": text, "font_size": size})

    def text(self, s, x, y, size=10, font="Body", color=INK, align="left", kind="text"):
        s = plain(s)
        measured = width(s, font, size)
        if align == "center":
            x -= measured / 2
        elif align == "right":
            x -= measured
        self.record(kind, x, y - 2, measured, size + 4, s, size)
        self.c.setFillColor(color)
        for family, run in runs(s, font):
            self.c.setFont(family, size)
            self.c.drawString(x, y, run)
            x += pdfmetrics.stringWidth(run, family, size)

    def paragraph(self, text, x, top, available, kind="paragraph", **kwargs):
        p, height = para(text, available, **kwargs)
        self.record(kind, x, top - height, available, height, text, kwargs.get("size", 10.6))
        p.drawOn(self.c, x, top - height)
        return top - height

    def line(self, y, left=M, right=None):
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(.6)
        self.c.line(left, y, W - M if right is None else right, y)

    def image(self, path, x, top, box_width, box_height, kind="scene_image"):
        if ARGS.check_layout and not path.exists():
            iw, ih = 3, 2
        else:
            with Image.open(path) as im:
                iw, ih = im.size
                if path not in self.images:
                    self.images[path] = ImageReader(im.copy())
        scale = min(box_width / iw, box_height / ih)
        dw, dh = iw * scale, ih * scale
        dx, dy = x + (box_width - dw) / 2, top - box_height + (box_height - dh) / 2
        self.record(kind, dx, dy, dw, dh, str(path.relative_to(ROOT)))
        if not ARGS.check_layout:
            self.c.saveState()
            if kind == "character_portrait":
                clip = self.c.beginPath()
                clip.circle(dx + dw / 2, dy + dh / 2, min(dw, dh) / 2)
                self.c.clipPath(clip, stroke=0)
            self.c.drawImage(self.images[path], dx, dy, width=dw, height=dh, mask="auto")
            self.c.restoreState()

    def header(self, ep, side):
        self.context = (ep["episode_number"], side)
        self.c.setFillColor(PAPER)
        self.c.rect(0, 0, W, H, fill=1, stroke=0)
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(.65)
        self.c.roundRect(5 * MM, 5 * MM, W - 10 * MM, H - 10 * MM,
                         4 * MM, fill=0, stroke=1)
        self.text(f"ეპიზოდი {ep['episode_number']:02}", M, H - 29, 9.5, "Bold", GREEN, kind="episode_number")
        act = ep["act_title"]["ka"].split("—", 1)[0].strip()
        self.text(act, W - M, H - 29, 9.5, color=MUTED, align="right", kind="act")
        bottom = self.paragraph(ep["title"]["ka"], M, H - 46, W - 2 * M, "title",
                                size=18, leading=23, font="Display", color=GREEN)
        assert bottom >= H - 94, (ep["episode_number"], "title height")
        chapters = str(ep["chapters"][0]) if len(ep["chapters"]) == 1 else f"{ep['chapters'][0]}-{ep['chapters'][-1]}"
        chapter_label = "თავი" if len(ep["chapters"]) == 1 else "თავები"
        self.text(f"{chapter_label} {chapters}   •   სტროფები {ep['stanza_range']}",
                  M, H - 108, 9, color=MUTED, kind="source_range")
        self.line(H - 117)

    def footer(self):
        self.text(DATA["work"]["title_ka"], W / 2, 23, 7.8, color=MUTED, align="center", kind="deck_title")

    def caption(self, ep, scene, x, top, available, size=9.1):
        return self.paragraph(f"{scene['scene_order']}. {scene['title']['ka']}", x, top,
                               available, "scene_title", size=size, leading=size + 3,
                               font="Bold", color=GREEN)

    def front(self, ep):
        self.header(ep, "front")
        scenes = sorted(ep["scene_descriptions"], key=lambda s: s["scene_order"])
        top, available = H - 130, W - 2 * M
        if len(scenes) == 1:
            scene = scenes[0]
            self.image(scene_path(ep, scene), M, top, available, 244)
            cap_bottom = self.caption(ep, scene, M, top - 253, available)
            end = self.paragraph(scene["moment_summary"]["ka"], M, cap_bottom - 11,
                                 available, "scene_summary", size=10.2, leading=14.1)
            assert end >= 108, (ep["episode_number"], "scene summary height", end)
            self.text("მთავარი პერსონაჟი".upper(), M, 94, 8.7, "Bold", GREEN, kind="cast_label")
            actor = next(c for c in ep["characters"] if c["role_type"] == "primary")
            self.image(latest_portrait(actor["character_id"]), M, 81, 38, 38, "character_portrait")
            self.text(actor["name"]["ka"], M + 50, 64, 11, "Bold", GREEN, kind="character_name")
            mentioned = [c["name"]["ka"] for c in ep["characters"] if c["role_type"] == "mentioned"]
            if mentioned:
                self.text("მოხსენიებული: " + ", ".join(mentioned), M + 50, 46, 9, color=MUTED, kind="mentioned_cast")
        elif len(scenes) == 3:
            self.image(scene_path(ep, scenes[0]), M, top, available, 229)
            cap_bottom = self.caption(ep, scenes[0], M, top - 238, available)
            lower_top = min(cap_bottom - 11, 205)
            gutter, cell = 10, (available - 10) / 2
            for i, scene in enumerate(scenes[1:]):
                x = M + i * (cell + gutter)
                self.image(scene_path(ep, scene), x, lower_top, cell, 120)
                bottom = self.caption(ep, scene, x, lower_top - 128, cell, size=8.5)
                assert bottom >= 39, (ep["episode_number"], scene["scene_order"], "caption", bottom)
        else:
            # Two scenes stack; four scenes form a two-by-two manga grid.
            columns = 1 if len(scenes) == 2 else 2
            cell = (available - (columns - 1) * 10) / columns
            panel_height = 157 if columns == 1 else 140
            for i, scene in enumerate(scenes):
                row, col = divmod(i, columns)
                panel_top = top - row * (panel_height + 55)
                x = M + col * (cell + 10)
                self.image(scene_path(ep, scene), x, panel_top, cell, panel_height)
                end = self.caption(ep, scene, x, panel_top - panel_height - 9, cell, size=8.6)
                assert end >= 39
        self.footer()

    def back(self, ep):
        self.header(ep, "back")
        available = W - 2 * M
        verse = ep["less_popular_stanza"]
        story = ep["executive_summary"]["ka"]
        prompt = ep["player_scene_input"]["general_prompt"]["ka"]
        for body, leading in [(10.7, 15), (10.3, 14.4), (10, 14)]:
            total = sum(para(t, available, size=s, leading=l)[1] for t, s, l in
                        [(story, body, leading), (verse["verse_ka"], 10.1, 14.2), (prompt, body, leading)])
            if H - 136 - total - 87 >= 78:
                break
        y = H - 137
        self.text("შინაარსი".upper(), M, y, 9, "Bold", GREEN, kind="summary_label")
        y = self.paragraph(story, M, y - 14, available, "executive_summary",
                            size=body, leading=leading) - 16
        self.text(f"სტროფი {verse['stanza_number']}   •   თავი {verse['chapter_number']}",
                  M, y, 9, "Bold", GREEN, kind="verse_label")
        y = self.paragraph(verse["verse_ka"], M, y - 14, available, "selected_stanza",
                            size=10.1, leading=14.2) - 16
        self.text("გაითამაშეთ".upper(), M, y, 9, "Bold", GREEN, kind="roleplay_label")
        y = self.paragraph(prompt, M, y - 14, available, "roleplay_prompt",
                            size=body, leading=leading)
        assert y >= 78, (ep["episode_number"], "back content too long", y)
        self.line(66)
        active = [c["name"]["ka"] for c in ep["characters"] if c["role_type"] != "mentioned"]
        end = self.paragraph("მონაწილეები: " + " • ".join(active), M, 55, available,
                             "active_cast", size=8.6, leading=11.7, color=MUTED)
        assert end >= 31
        self.footer()


def make_canvas(path, size, title):
    c = canvas.Canvas(io.BytesIO() if ARGS.check_layout else str(path), pagesize=size, pageCompression=1)
    c.setTitle(title)
    c.setAuthor(DATA["work"]["title_en"])
    return c


def quiz_pdf(path):
    pw, ph = A4
    c = make_canvas(path, A4, "Episodes 1-2 - Georgian quiz reference")
    r = Renderer(c, A4)
    letters = ["ა", "ბ", "გ", "დ"]
    for ep in EPISODES:
        r.context = (ep["episode_number"], "quiz")
        c.setFillColor(PAPER)
        c.rect(0, 0, pw, ph, fill=1, stroke=0)
        r.text(f"ეპიზოდი {ep['episode_number']:02} / კითხვები", 34, ph - 35, 10, "Bold", GREEN, kind="quiz_header")
        title_bottom = r.paragraph(ep["title"]["ka"], 34, ph - 51, pw - 68, "quiz_title",
                                   size=19, leading=25, font="Display", color=GREEN)
        col_width, gutter = (pw - 68 - 24) / 2, 24
        top = min(title_bottom - 24, ph - 108)
        for col in range(2):
            x, y = 34 + col * (col_width + gutter), top
            for q in ep["questions"][col * 3:col * 3 + 3]:
                y = r.paragraph(f"{q['question_number']}. {q['question']['ka']}", x, y,
                                  col_width, "quiz_question", size=10.4, leading=14.3, font="Bold", color=GREEN) - 7
                for i, option in enumerate(q["options"]):
                    y = r.paragraph(f"{letters[i]}) {option['ka']}", x + 4, y, col_width - 4,
                                      "quiz_option", size=10, leading=13.6) - 3
                y -= 17
            assert y >= 92, (ep["episode_number"], col, "quiz overflow", y)
        c.setStrokeColor(GOLD)
        c.setLineWidth(.6)
        c.line(34, 69, pw - 34, 69)
        answers = "   •   ".join(f"{q['question_number']} - {letters[q['correct_option_index']]}" for q in ep["questions"])
        r.text("პასუხები: " + answers, 34, 48, 9, color=MUTED, kind="answer_key")
        r.text(DATA["work"]["title_ka"], pw - 34, 27, 8, color=MUTED, align="right", kind="deck_title")
        c.showPage()
    c.save()
    return r.blocks


if not ARGS.check_layout:
    OUT.mkdir(parents=True, exist_ok=True)
    for ep in EPISODES:
        for scene in ep["scene_descriptions"]:
            assert scene_path(ep, scene).is_file(), scene_path(ep, scene)

native = OUT / "episode-cards-01-02-a5.pdf"
c = make_canvas(native, (W, H), "Episodes 1-2 - Georgian manga A5 cards")
r = Renderer(c)
for ep in EPISODES:
    for side in ["front", "back"]:
        getattr(r, side)(ep)
        c.showPage()
c.save()

review = OUT / "episode-cards-01-02-review.pdf"
rw, rh = landscape(A3)
c = make_canvas(review, (rw, rh), "Episodes 1-2 - manga card front and back review")
rr = Renderer(c)
review_labels = Renderer(c, (rw, rh))
gutter = 12 * MM
start_x, start_y = (rw - 2 * W - gutter) / 2, (rh - H) / 2 - 5 * MM
for ep in EPISODES:
    review_labels.context = (ep["episode_number"], "review")
    review_labels.text(f"{ep['episode_number']:02} / " + ep["title"]["ka"],
                       start_x, rh - 45, 13, "Bold", GREEN)
    for i, side in enumerate(["front", "back"]):
        x = start_x + i * (W + gutter)
        c.setFillColor(MUTED)
        c.setFont("Body", 10)
        c.drawString(x, start_y + H + 13, "წინა მხარე" if side == "front" else "უკანა მხარე")
        c.saveState()
        c.translate(x, start_y)
        getattr(rr, side)(ep)
        c.restoreState()
    c.showPage()
c.save()

quiz = OUT / "episode-quiz-01-02-reference.pdf"
quiz_blocks = quiz_pdf(quiz)

if not ARGS.check_layout:
    scene_records = []
    for ep in EPISODES:
        for scene in ep["scene_descriptions"]:
            p = scene_path(ep, scene)
            with Image.open(p) as im:
                dimensions = list(im.size)
            receipt = p.with_suffix(".json")
            scene_records.append({"episode": ep["episode_number"], "scene_order": scene["scene_order"],
                "title_ka": scene["title"]["ka"], "asset": str(p.relative_to(ROOT)),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "dimensions": dimensions,
                "characters_present": scene["characters_present"],
                "reference_portraits": {cid: str(latest_portrait(cid).relative_to(ROOT)) for cid in scene["characters_present"]},
                "generation_receipt": str(receipt.relative_to(ROOT)),
                "generation": json.loads(receipt.read_text()) if receipt.exists() else None})
    manifest = {"date": "2026-11-14", "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE_BYTES).hexdigest(), "language": "ka", "card_size_mm": [148, 210],
        "scene_counts": {str(ep["episode_number"]): len(ep["scene_descriptions"]) for ep in EPISODES},
        "image_fit": "Original scene images shown in full, with no cropping or stretching.",
        "outputs": [str(p.relative_to(ROOT)) for p in [native, review, quiz]],
        "scenes": scene_records, "text_blocks": r.blocks, "quiz_blocks": quiz_blocks}
    (OUT / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (ASSETS / "generation-manifest.json").write_text(json.dumps({"tool": "built-in image_gen", "source": manifest["source"], "scenes": scene_records}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"layout_check": ARGS.check_layout, "checked_blocks": len(r.blocks) + len(quiz_blocks),
                  "outputs": [str(p.relative_to(ROOT)) for p in [native, review, quiz]]}, indent=2))
