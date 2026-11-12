#!/usr/bin/env python3
"""Independently verify the exported Georgian two-sided rulebook.

No builder code is imported. Physical sizes, glyph positions, font sizes,
language and table contents are read from the PDFs themselves. The layout
report identifies the table's semantic row/column regions; the text found in
those regions is compared with data/rulebook.ka.json, not with builder copy.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pdfplumber
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
MM = 72 / 25.4
EDITIONS = {
    "A4": ("pantersskin-rulebook-ka-a4.pdf", (210, 297), 9),
    "A5": ("pantersskin-rulebook-ka-a5.pdf", (148, 210), 8),
}
SOURCE_PATH = ROOT / "data/rulebook.ka.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def normalized(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    return "".join(text.split())


def contains_latin(text):
    return sorted({c for c in text if "LATIN" in unicodedata.name(c, "")})


def source_check(source):
    meta = source["meta"]
    require(meta["token_mode"] == "character_tokens_only_21", "Unexpected source token mode")
    require(meta["language"] == "ka", "Unexpected rulebook language")
    require(meta["total_episodes"] == 24 and meta["total_chapters"] == 65
            and meta["total_stanzas"] == 1669, "Unexpected source poem coverage")
    require(meta["total_character_tokens"] == meta["total_character_cards"] == 21,
            "Expected21 painted character tokens and cards")
    require(len(source["characters_manifest"]) == 21, "Expected21 character manifest entries")
    require([r["number"] for r in source["realms"]] == list(range(1, 8)), "Expected realms1..7")
    require([s["step_number"] for s in source["setup_steps"]] == list(range(1, 7)),
            "Expected six sequential source setup steps")
    require([s["phase_number"] for s in source["gameplay_loop"]] == list(range(1, 7)),
            "Expected six sequential source turn phases")
    require([a["kind"] for a in source["token_actions"]] == ["move", "group", "face", "remove", "temporary"],
            "Expected five source token actions")
    episodes = source["episodes"]
    require([e["episode_number"] for e in episodes] == list(range(1, 25)), "Source episodes must be 1..24")
    require([c for e in episodes for c in e["chapters"]] == list(range(1, 66)), "Source chapters must be 1..65 without gaps")
    cursor = 1
    for e in episodes:
        require(e["stanza_start"] == cursor, f"Stanza discontinuity at episode {e['episode_number']}")
        cursor = e["stanza_end"] + 1
    require(cursor == 1670, "Source stanza coverage must end at 1669")
    return episodes


def bbox_mm(obj):
    """pdfplumber y0/y1 use the required PDF bottom-left coordinate system."""
    return [float(obj[k]) / MM for k in ("x0", "y0", "x1", "y1")]


def inside(box, width, height, margin=8, tolerance=.03):
    return (box[0] >= margin - tolerance and box[1] >= margin - tolerance
            and box[2] <= width - margin + tolerance
            and box[3] <= height - margin + tolerance)


def text_in_box(page, box):
    """Select actual glyph centers to avoid adjacent-row extraction bleed."""
    x0, y0, x1, y1 = [float(v) * MM for v in box]
    selected = []
    for ch in page.chars:
        x = (ch["x0"] + ch["x1"]) / 2
        y = (ch["y0"] + ch["y1"]) / 2
        if x0 - .04 <= x <= x1 + .04 and y0 - .04 <= y <= y1 + .04:
            selected.append(ch)
    # PDF insertion order preserves Georgian grapheme and wrapped-line order.
    return "".join(ch["text"] for ch in selected)


def source_range(episode):
    chapters = episode["chapters"]
    return str(chapters[0]) if len(chapters) == 1 else f"{chapters[0]}-{chapters[-1]}"


def circle_check(page, edition, page_number, example_chapters):
    """Inspect actual cubic circle paths, including drawn circled numerals."""
    circles = []
    for shape in page.curves:
        operations = [part[0] for part in shape.get("path", [])]
        if operations not in (["m", "c", "c", "c", "c"], ["m", "c", "c", "c", "c", "h"]):
            continue
        box = bbox_mm(shape)
        if abs((box[2] - box[0]) - (box[3] - box[1])) > .015:
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        radius = (box[2] - box[0]) / 2
        circles.append({"x": cx, "y": cy, "radius": radius, "filled": bool(shape.get("fill"))})
        for ch in page.chars:
            if not ch["text"].isdecimal():
                continue
            gx = (ch["x0"] + ch["x1"]) / (2 * MM)
            gy = (ch["y0"] + ch["y1"]) / (2 * MM)
            require((gx - cx)**2 + (gy - cy)**2 >= radius**2,
                    f"{edition} page {page_number}: numeric glyph {ch['text']} inside a drawn circle")
    result = {"drawn_circled_numerals": [], "actual_circle_count": len(circles)}
    if page_number == 1:
        groups = {}
        for circle in circles:
            groups.setdefault(round(circle["y"], 2), []).append(circle)
        timeline = [group for group in groups.values() if len(group) == 65]
        require(len(timeline) == 1, f"{edition}: expected exactly one actual 65-circle timeline")
        timeline = sorted(timeline[0], key=lambda circle: circle["x"])
        filled = [i + 1 for i, circle in enumerate(timeline) if circle["filled"]]
        require(filled == example_chapters,
                f"{edition}: example timeline must fill source episode06 chapters {example_chapters}")
        result["timeline"] = {"circle_count": 65, "filled_chapters": filled}
    return result


def table_check(page, table, episodes, edition):
    require(len(table["rows"]) == 24, f"{edition}: table layout must have 24 rows")
    columns = table["columns_mm"]
    require(len(columns) == 5 and all(a < b for a, b in zip(columns, columns[1:])),
            f"{edition}: expected five increasing boundaries for four columns")
    actual_numbers, rows = [], []
    for index, (row, episode) in enumerate(zip(table["rows"], episodes), 1):
        require(row["episode_number"] == index, f"{edition}: table metadata row order")
        box = row["bbox_mm"]
        cells = [text_in_box(page, [columns[n], box[1], columns[n + 1], box[3]])
                 for n in range(4)]
        number_tokens = re.findall(r"\d+", cells[0])
        require(len(number_tokens) == 1 and int(number_tokens[0]) == index,
                f"{edition}: actual table row {index} episode number: {cells[0]!r}")
        actual_numbers.append(int(number_tokens[0]))
        require(cells[1].strip() and not contains_latin(cells[1]),
                f"{edition}: actual row {index} missing Georgian short title")
        realm = episode["primary_realm"]
        expected_realm = f"{realm['number']} {realm['name_ka']}"
        require(normalized(cells[2]) == normalized(expected_realm),
                f"{edition}: actual row {index} realm {cells[2]!r}, expected {expected_realm!r}")
        require(normalized(cells[3]) == source_range(episode),
                f"{edition}: actual row {index} chapters {cells[3]!r}, expected {source_range(episode)!r}")
        require(normalized(cells[1]) == normalized(episode["short_title_ka"]),
                f"{edition}: row {index} title differs from rulebook source or is clipped")
        rows.append({"episode_number": index, "actual_cells": cells,
                     "realm_number": realm["number"], "chapters": episode["chapters"]})
    require(actual_numbers == list(range(1, 25)), f"{edition}: episode column must contain exactly 1..24")
    require(len(set(actual_numbers)) == 24, f"{edition}: duplicated episode table numbers")
    return {"status": "passed", "actual_episode_numbers": actual_numbers, "rows": rows}


def font_check(reader, used_fontnames):
    fonts = {}
    def inspect(resources):
        resources = resources.get_object()
        for name, ref in resources.get("/Font", {}).items():
            font = ref.get_object()
            base_name = str(font.get("/BaseFont", name)).lstrip("/")
            if base_name not in used_fontnames:
                continue
            children = font.get("/DescendantFonts", [font])
            for child in children:
                child = child.get_object()
                descriptor = child.get("/FontDescriptor")
                require(descriptor is not None, f"Unembedded or undescribed PDF font {name}")
                descriptor = descriptor.get_object()
                require(any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3")),
                        f"PDF font {name} has no embedded font program")
            fonts[base_name] = "embedded"
        for ref in resources.get("/XObject", {}).values():
            obj = ref.get_object()
            require(obj.get("/Subtype") != "/Image", "Rulebook diagrams must be vector artwork")
            if obj.get("/Resources"):
                inspect(obj["/Resources"])
    for page in reader.pages:
        inspect(page["/Resources"])
    require(fonts, "No embedded fonts found")
    return fonts


def layout_edition(report, edition):
    editions = report.get("editions", report)
    require(edition in editions, f"Missing {edition} layout report")
    return editions[edition]


def printed_source_fields(source):
    """Core two-page content, as distinct from optional long-form references.

    The source also supplies extended overview, biographies, complete episode
    records, and detailed examples. Those are not duplicated on the compact
    sheet. The selected core instructions must appear in full, not be rewritten
    or silently replaced with the previous local editorial-copy JSON.
    """
    fields = [("meta.title_ka", source["meta"]["title_ka"]),
              ("meta.subtitle_ka", source["meta"]["subtitle_ka"]),
              ("overview.summary_ka", source["overview"]["summary_ka"])]
    for collection in ("setup_steps", "gameplay_loop", "token_actions"):
        for index, item in enumerate(source[collection]):
            fields.append((f"{collection}[{index}].instruction_ka", item["instruction_ka"]))
    removal = next(a for a in source["token_actions"] if a["kind"] == "remove")
    fields += [("token_actions[remove].rule_note_ka", removal["rule_note_ka"]),
               ("flashback_rules.description_ka", source["flashback_rules"]["description_ka"]),
               ("scale_rules.explanation_ka", source["scale_rules"]["explanation_ka"]),
               ("victory.condition_ka", source["victory"]["condition_ka"]),
               ("meta.poem_basis_ka", source["meta"]["poem_basis_ka"]),
               ("meta.art_basis_ka", source["meta"]["art_basis_ka"]),
               ("print_production.general_instructions_ka[0]",
                source["print_production"]["general_instructions_ka"][0])]
    fields += [(f"flashback_rules.modes[{index}].label_ka", mode["label_ka"])
               for index, mode in enumerate(source["flashback_rules"]["modes"])]
    return fields


def source_content_check(pages, source, edition):
    actual = normalized("\n".join(page.extract_text() or "" for page in pages))
    checked = []
    for field, expected in printed_source_fields(source):
        require(normalized(expected) in actual,
                f"{edition}: source content missing or rewritten: {field}: {expected!r}")
        checked.append({"source_field": field, "status": "exact_text_present"})
    return {"status": "passed", "source_fields_checked": checked,
            "setup_steps_checked": 6, "turn_phases_checked": 6, "token_actions_checked": 5}


def validate_pdf(path, edition, dimensions, minimum, layout, source, episodes):
    reader = PdfReader(path)
    require(len(reader.pages) == 2, f"{edition}: expected exactly two pages")
    result = {"file": path.name, "bytes": path.stat().st_size, "sha256": digest(path), "pages": []}
    with pdfplumber.open(path) as pdf:
        used_fontnames = {ch["fontname"] for page in pdf.pages for ch in page.chars if ch["text"].strip()}
        result["fonts"] = font_check(reader, used_fontnames)
        result["source_content"] = source_content_check(reader.pages, source, edition)
        for index, (pypage, page) in enumerate(zip(reader.pages, pdf.pages)):
            page_no = index + 1
            size = (float(pypage.mediabox.width) / MM, float(pypage.mediabox.height) / MM)
            require(all(abs(a - b) < .015 for a, b in zip(size, dimensions)),
                    f"{edition} page {page_no}: wrong physical dimensions {size}")
            require(list(pypage.cropbox) == list(pypage.mediabox),
                    f"{edition} page {page_no}: crop box hides content")
            extracted = pypage.extract_text() or ""
            require(len(extracted) > 200, f"{edition} page {page_no}: insufficient extractable text")
            latin = contains_latin(extracted)
            require(not latin, f"{edition} page {page_no}: printed Latin characters {latin}")
            circled = [c for c in extracted if "CIRCLED" in unicodedata.name(c, "")
                       and unicodedata.category(c).startswith("N")]
            require(not circled, f"{edition} page {page_no}: circled numerals {circled}")
            require(not re.search(r"[a-z]+_[a-z_]+", extracted, re.I),
                    f"{edition} page {page_no}: printed internal code")
            chars = [c for c in page.chars if c["text"].strip()]
            require(chars, f"{edition} page {page_no}: no actual glyphs")
            low = [c for c in chars if float(c["size"]) < minimum - .02]
            require(not low, f"{edition} page {page_no}: text below {minimum}pt: {low[:3]}")
            outside = [{"text": c["text"], "bbox_mm": bbox_mm(c)} for c in chars
                       if not inside(bbox_mm(c), *dimensions)]
            require(not outside, f"{edition} page {page_no}: glyphs outside 8mm safe margin: {outside[:3]}")
            vector_count, paper_count = 0, 0
            for obj in page.lines + page.rects + page.curves:
                box = bbox_mm(obj)
                # A solid ivory paper background may occupy the whole media.
                full_paper = (all(abs(a - b) < .02 for a, b in zip(box, [0, 0, *dimensions]))
                              and bool(obj.get("fill")) and not obj.get("stroke"))
                if full_paper:
                    paper_count += 1
                    continue
                radius = float(obj.get("linewidth") or 0) / MM / 2 if obj.get("stroke", True) else 0
                ink_box = [box[0] - radius, box[1] - radius, box[2] + radius, box[3] + radius]
                require(inside(ink_box, *dimensions),
                        f"{edition} page {page_no}: vector ink outside safe margin: {ink_box}")
                vector_count += 1
            page_layout = layout["pages"][index]
            for box in page_layout.get("text_boxes", []):
                require(inside(box["bbox_mm"], *dimensions),
                        f"{edition} page {page_no}: declared text bounds outside safe margin")
                # PDF glyph text must appear in the full-size planned text region.
                if box.get("text"):
                    found = text_in_box(page, box["bbox_mm"])
                    require(normalized(found) == normalized(box["text"]),
                            f"{edition} page {page_no}: clipped/overlapping planned text: {box['text']!r} vs {found!r}")
            page_result = {
                "page": page_no, "size_mm": list(size), "text_characters": len(extracted),
                "actual_glyph_count": len(chars), "minimum_actual_font_pt": min(float(c["size"]) for c in chars),
                "required_minimum_font_pt": minimum,
                "minimum_actual_glyph_margin_mm": min(min(bbox_mm(c)[0], bbox_mm(c)[1],
                    dimensions[0] - bbox_mm(c)[2], dimensions[1] - bbox_mm(c)[3]) for c in chars),
                "safe_margin_mm": 8, "vector_objects_checked": vector_count,
                "full_page_paper_backgrounds": paper_count, "latin_characters": [], "circled_numerals": [],
                "planned_text_regions_checked": len(page_layout.get("text_boxes", [])),
            }
            page_result["circle_diagrams"] = circle_check(page, edition, page_no, episodes[5]["chapters"])
            if page_no == 2:
                require("table" in page_layout, f"{edition}: no page 2 table region")
                page_result["episode_table"] = table_check(page, page_layout["table"], episodes, edition)
            result["pages"].append(page_result)
    return result


def verify(output_dir=None):
    out = Path(output_dir or ROOT / "output/rulebook")
    report = {"status": "failed", "verification_method": "independent PDF glyph, vector, font and table inspection; no builder import",
              "source": str(SOURCE_PATH.relative_to(ROOT)), "source_sha256": digest(SOURCE_PATH),
              "editions": {}}
    try:
        source = json.loads(SOURCE_PATH.read_text())
        episodes = source_check(source)
        layout_path = out / "layout-report.json"
        layout = json.loads(layout_path.read_text())
        report["layout_report_sha256"] = digest(layout_path)
        for edition, (filename, dimensions, minimum) in EDITIONS.items():
            report["editions"][edition] = validate_pdf(out / filename, edition, dimensions, minimum,
                                                       layout_edition(layout, edition), source, episodes)
        previews = []
        for path in sorted(out.glob("*.png")):
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                previews.append({"file": path.name, "pixel_dimensions": list(im.size),
                                 "mode": im.mode, "bytes": path.stat().st_size, "sha256": digest(path)})
        require(len(previews) >= 4, "Expected rendered PNG previews for all four pages")
        report["previews"] = previews
        report["source_coverage"] = {"episode_numbers": list(range(1, 25)), "chapters": [1, 65], "stanzas": [1, 1669],
                                     "token_mode": source["meta"]["token_mode"]}
        report["status"] = "independent_source_content_and_pdf_geometry_passed"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        raise
    (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/rulebook")
    args = parser.parse_args()
    result = verify(args.out)
    print(json.dumps({"status": result["status"], "editions": list(result["editions"]),
                      "report": str(args.out / "validation.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
