#!/usr/bin/env python3
"""Independent source, content, physical-size and duplex episode-deck audit.

This validator deliberately imports no builder modules. PDF text is grouped by
physical card slot, so swapped-back checks test the actual exported pages.
"""

import argparse
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from pypdf._page import PageObject
from pypdf.generic import ContentStream, NameObject


ROOT = Path(__file__).resolve().parents[2]
MM = 72 / 25.4
FILES = {
    "a5_single": ("pantersskin-episode-cards-ka-a5-single.pdf", 48, (148, 210)),
    "a5_duplex": ("pantersskin-episode-cards-ka-a5-a4-duplex.pdf", 24, (297, 210)),
    "a6_duplex": ("pantersskin-episode-cards-ka-a6-a4-duplex.pdf", 12, (210, 297)),
}
SLOTS = {
    "a5_duplex": [(0, 0, 148, 210), (149, 0, 297, 210)],
    "a6_duplex": [(0, 149, 105, 297), (105, 149, 210, 297),
                  (0, 0, 105, 148), (105, 0, 210, 148)],
}
ILLUSTRATIONS = ROOT / "output/episode-illustrations/illustration-manifest.json"


def norm(text):
    text = unicodedata.normalize("NFC", text).casefold()
    text = re.sub(r"[\u2010-\u2014]", "-", text)
    for i in range(20):
        text = text.replace(chr(0x2460 + i), str(i + 1))
    return "".join(text.split())


def expected_action(text):
    """Independently reviewed route-ID localization; all other copy is exact."""
    localizations = {
        "გზით india_khataeti": "„ტარიელის ლაშქრობის გზით“",
        "გზით india_mulgazanzar": "ზღვითა და ხმელეთით მულღაზანზარისკენ",
        "გზით cave_mulgazanzar / india_cave „გაჭრა და ხეტიალი“": "გზით „გაჭრა და ხეტიალი“",
        "გზით arabia_cave": "„ავთანდილის ძიების გზით“",
        "გზით mulgazanzar_gulansharo": "სანაპირო და საზღვაო გზით",
        ", gulansharo_cave": "",
    }
    for original, replacement in localizations.items():
        text = text.replace(original, replacement)
    return re.sub(r"\s*\([a-z][a-z0-9_]*(?:\s*[,/→]\s*[a-z][a-z0-9_]*)*\)", "", text)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_source(source):
    episodes = source["episodes"]
    require(len(episodes) == 24, "Expected 24 source episodes")
    require([e["episode_number"] for e in episodes] == list(range(1, 25)),
            "Episode numbers are not exactly 1..24 in order")
    chapters = [n for e in episodes for n in e["chapters"]]
    require(chapters == list(range(1, 66)), "Chapters are not exactly 1..65 in strict sequence")
    cursor = 1
    for episode in episodes:
        require(episode["stanza_start"] == cursor,
                f"Stanza gap/overlap before episode {episode['episode_number']}")
        require(episode["stanza_end"] >= episode["stanza_start"], "Inverted stanza range")
        cursor = episode["stanza_end"] + 1
        require(len(episode["quote"]["full_stanza_ka"].splitlines()) == 4,
                f"Episode {episode['episode_number']} quatrain is not four source lines")
    require(cursor == 1670, "Stanza coverage does not end at 1669")
    return episodes


def multiply(local, parent):
    a, b, c, d, e, f = local
    A, B, C, D, E, F = parent
    return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F]


def form_instances(page):
    """Read actual page Do placements, rather than trusting manifest coordinates."""
    stack, current, instances = [], [1, 0, 0, 1, 0, 0], []
    objects = page["/Resources"].get("/XObject", {})
    for args, op in ContentStream(page.get_contents(), page.pdf).operations:
        if op == b"q":
            stack.append(current[:])
        elif op == b"Q":
            current = stack.pop()
        elif op == b"cm":
            current = multiply([float(v) for v in args], current)
        elif op == b"Do":
            obj = objects[args[0]].get_object()
            if obj.get("/Subtype") == "/Form":
                transform = multiply([float(v) for v in obj.get("/Matrix", [1, 0, 0, 1, 0, 0])], current)
                instances.append({"name": str(args[0]), "form": obj, "transform": transform})
    return instances


def fragments(page):
    result = []
    instances = form_instances(page)
    sources = []
    if instances:
        for instance in instances:
            fake = PageObject(page.pdf)
            fake[NameObject("/Contents")] = instance["form"]
            fake[NameObject("/Resources")] = instance["form"]["/Resources"]
            sources.append((fake, instance["transform"]))
    else:
        sources.append((page, [1, 0, 0, 1, 0, 0]))
    for source, external in sources:
        def visit(text, cm, tm, font, size):
            if not text.strip():
                return
            combined = multiply(multiply(tm, cm), external)
            result.append({"text": text, "x": combined[4] / MM, "y": combined[5] / MM,
                           "upright": combined[0] > 0 and combined[3] > 0})
        source.extract_text(visitor_text=visit)
    return result


def page_size(page):
    return (float(page.mediabox.width) / MM, float(page.mediabox.height) / MM)


def expected_numbers(key, sheet_index, back):
    per_sheet = 2 if key == "a5_duplex" else 4
    numbers = list(range(sheet_index * per_sheet + 1, (sheet_index + 1) * per_sheet + 1))
    return ([numbers[1], numbers[0]] if per_sheet == 2 else
            [numbers[1], numbers[0], numbers[3], numbers[2]]) if back else numbers


def check_native(reader, episodes):
    checks = []
    ascii_hits = []
    for index, page in enumerate(reader.pages):
        episode = episodes[index // 2]
        side = "front" if index % 2 == 0 else "back"
        text = page.extract_text()
        normalized = norm(text)
        require(norm(episode["title_ka"]) in normalized,
                f"Native page {index + 1}: expected episode {episode['episode_number']} title")
        # The page's own unique title identifies its episode on both sides.
        found = [e["episode_number"] for e in episodes if norm(e["title_ka"]) in normalized]
        require(found == [episode["episode_number"]],
                f"Native page {index + 1}: title belongs to episode(s) {found}")
        require(norm(episode["quote"]["locator_label_ka"]) in normalized,
                f"Native page {index + 1}: missing exact quote locator")
        if side == "front":
            require(norm(expected_action(episode["token_action_ka"])) in normalized,
                    f"Native page {index + 1}: missing token action")
            require(norm(episode["quote"]["line_ka"]) in normalized,
                    f"Native page {index + 1}: missing quote line")
        else:
            for field in ("summary_ka", "objective_ka"):
                require(norm(expected_action(episode[field])) in normalized,
                        f"Native page {index + 1}: missing {field}")
            for line in episode["quote"]["full_stanza_ka"].splitlines():
                require(norm(line) in normalized, f"Native page {index + 1}: missing quatrain line")
            for chapter in episode["chapter_titles_ka"]:
                require(norm(chapter["title_ka"]) in normalized,
                        f"Native page {index + 1}: missing chapter {chapter['chapter']} title")
            for character in episode["all_chapter_characters"]:
                require(norm(character["short_name_ka"]) in normalized or
                        norm(character["name_ka"]) in normalized,
                        f"Native page {index + 1}: missing roster character {character['id']}")
        latin = re.findall(r"[A-Za-z]+", text)
        if latin:
            ascii_hits.append({"page": index + 1, "tokens": latin})
        for fragment in fragments(page):
            if re.search(r"[\u10A0-\u10FF\u1C90-\u1CBF]", fragment["text"]):
                require(fragment["upright"], f"Native page {index + 1}: mirrored/inverted Georgian text")
        checks.append({"page": index + 1, "episode": episode["episode_number"], "side": side})
    require(not ascii_hits, f"ASCII Latin letters found on native cards: {ascii_hits}")
    return checks


def check_imposed(key, reader, episodes):
    checks = []
    for index, page in enumerate(reader.pages):
        back = index % 2 == 1
        expected = expected_numbers(key, index // 2, back)
        instances = form_instances(page)
        require(len(instances) == len(expected), f"{key} page {index + 1}: wrong actual Form count")
        for slot_index, (instance, rect, number) in enumerate(zip(instances, SLOTS[key], expected)):
            x0, y0, x1, y1 = rect
            actual = instance["transform"]
            wanted = [1, 0, 0, 1, x0 * MM, y0 * MM]
            require(all(abs(a - b) < .01 for a, b in zip(actual, wanted)),
                    f"{key} page {index + 1} slot {slot_index}: wrong actual placement/mirror/rotation {actual}")
            bounds = [float(v) / MM for v in instance["form"]["/BBox"]]
            require(all(abs(a - b) < .01 for a, b in zip(bounds, [0, 0, x1 - x0, y1 - y0])),
                    f"{key} page {index + 1} slot {slot_index}: wrong actual card frame bounds {bounds}")
            require(instance["name"].endswith(episodes[number - 1]["id"] + ("_back" if back else "_front")),
                    f"{key} page {index + 1} slot {slot_index}: wrong actual named Form")
        groups = [[] for _ in SLOTS[key]]
        for fragment in fragments(page):
            for slot_index, (x0, y0, x1, y1) in enumerate(SLOTS[key]):
                if x0 - .1 <= fragment["x"] < x1 + .1 and y0 - .1 <= fragment["y"] < y1 + .1:
                    groups[slot_index].append(fragment)
                    break
        for slot_index, (number, group) in enumerate(zip(expected, groups)):
            text = norm("".join(fragment["text"] for fragment in group))
            wanted = norm(episodes[number - 1]["title_ka"])
            require(wanted in text,
                    f"{key} page {index + 1} slot {slot_index}: episode {number} title not found")
            found = [e["episode_number"] for e in episodes if norm(e["title_ka"]) in text]
            require(found == [number],
                    f"{key} page {index + 1} slot {slot_index}: unexpected title(s) {found}")
            for fragment in group:
                if re.search(r"[\u10A0-\u10FF\u1C90-\u1CBF]", fragment["text"]):
                    require(fragment["upright"],
                            f"{key} page {index + 1} slot {slot_index}: glyphs mirrored/inverted")
        checks.append({"page": index + 1, "side": "back" if back else "front",
                       "episode_slots": expected, "actual_form_frames_and_placements_checked": True,
                       "actual_30mm_calibration_bar": check_calibration(page, key)})
    return checks


def check_calibration(page, key):
    paths, path = [], []
    for args, op in ContentStream(page.get_contents(), page.pdf).operations:
        if op == b"n":
            path = []
        elif op in (b"m", b"l"):
            path.append(([float(v) / MM for v in args], op))
        elif op == b"S":
            if [op for _, op in path] == [b"m", b"l"]:
                paths.append([xy for xy, _ in path])
            path = []
    expected = [[148.5, 90], [148.5, 120]] if key == "a5_duplex" else [[90, 148.5], [120, 148.5]]
    require(any(all(abs(a - b) < .002 for point, wanted in zip(path, expected)
                    for a, b in zip(point, wanted)) for path in paths), f"{key}: missing actual30mm control bar")
    return True


def check_timeline_forms(reader, episodes, size):
    """Count actual PDF circle paths and their actual fill colours, per back."""
    forms = {}
    for page in reader.pages:
        for instance in form_instances(page):
            if instance["name"].endswith("_back"):
                forms[instance["name"]] = instance["form"]
    require(len(forms) == 24, f"{size}: expected24 unique back Forms")
    scale = 148 / 105 if size == "A5" else 1
    wanted_radius, wanted_y = 1.6 * scale, 21.5 * scale
    green = [0x20 / 255, 0x3D / 255, 0x37 / 255]
    ivory = [0xF6 / 255, 0xF1 / 255, 0xE4 / 255]
    checks = []
    for episode in episodes:
        matches = [(name, form) for name, form in forms.items() if name.endswith(episode["id"] + "_back")]
        require(len(matches) == 1, f"{size}: missing unique back Form for{episode['id']}")
        name, form = matches[0]
        state, stack, path, circles = {"fill": [0, 0, 0]}, [], [], []
        for args, op in ContentStream(form, reader).operations:
            if op == b"q":
                stack.append({"fill": state["fill"][:]})
            elif op == b"Q":
                state = stack.pop()
            elif op == b"rg":
                state["fill"] = [float(v) for v in args]
            elif op == b"g":
                state["fill"] = [float(args[0])] * 3
            elif op == b"n":
                path = []
            elif op in (b"m", b"c", b"l", b"h"):
                path.append(([float(v) for v in args], op))
            elif op in (b"B", b"B*", b"f", b"f*"):
                if [kind for _, kind in path] == [b"m", b"c", b"c", b"c", b"c"]:
                    coordinates = [v for values, _ in path for v in values]
                    xs, ys = coordinates[::2], coordinates[1::2]
                    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                    rx, ry = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
                    if abs(cy - wanted_y) < .02 and abs(rx - wanted_radius) < .02 and abs(ry - wanted_radius) < .02:
                        fill = state["fill"]
                        active = max(abs(a - b) for a, b in zip(fill, green)) < .00001
                        inactive = max(abs(a - b) for a, b in zip(fill, ivory)) < .00001
                        require(active or inactive, f"{size} ep{episode['episode_number']}: wrong timeline fill{fill}")
                        circles.append((cx, active))
                path = []
            elif op in (b"S", b"s", b"b", b"b*"):
                path = []
        require(len(circles) == 65, f"{size} ep{episode['episode_number']}: expected65 circlepaths, got{len(circles)}")
        circles.sort()
        actual = [index + 1 for index, (_, active) in enumerate(circles) if active]
        require(actual == episode["chapters"], f"{size} ep{episode['episode_number']}: actualfill mask{actual} != source{episode['chapters']}")
        checks.append({"episode": episode["episode_number"], "actual_circle_paths": 65,
                       "actual_filled_chapters": actual})
    return checks


def compact_reader(reader, episodes):
    forms = {}
    for page in reader.pages:
        for instance in form_instances(page):
            forms[instance["name"]] = instance["form"]
    pages = []
    for episode in episodes:
        for side in ("front", "back"):
            form = next(form for name, form in forms.items() if name.endswith(episode["id"] + "_" + side))
            page = PageObject(reader)
            page[NameObject("/Contents")] = form
            page[NameObject("/Resources")] = form["/Resources"]
            pages.append(page)
    return type("IndependentCompactFormReader", (), {"pages": pages})()


def check_actual_frames(reader, size):
    forms = {}
    for page in reader.pages:
        for instance in form_instances(page):
            forms[instance["name"]] = instance["form"]
    require(len(forms) == 48, f"{size}: expected48 unique card Forms")
    w, h = (148, 210) if size == "A5" else (105, 148)
    for name, form in forms.items():
        boxes, path = [], []
        for args, op in ContentStream(form, reader).operations:
            if op == b"n":
                path = []
            elif op in (b"m", b"l", b"c"):
                path.extend(float(v) / MM for v in args)
            elif op == b"re":
                x, y, ww, hh = [float(v) / MM for v in args]
                path += [x, y, x + ww, y + hh]
            elif op in (b"S", b"s"):
                if path:
                    xs, ys = path[::2], path[1::2]
                    boxes.append([min(xs), min(ys), max(xs), max(ys)])
                path = []
            elif op in (b"f", b"f*", b"B", b"B*", b"b", b"b*"):
                path = []
        for wanted in ([1, 1, w - 1, h - 1], [2.5, 2.5, w - 2.5, h - 2.5]):
            require(any(max(abs(a - b) for a, b in zip(box, wanted)) < .01 for box in boxes),
                    f"{size} {name}: actual inner/outer frame path not at expected margin {wanted}")
    return {"unique_card_forms": 48, "actual_green_frame_inset_mm": 1,
            "actual_gold_frame_inset_mm": 2.5}


def load_selected_scenes(path, episodes):
    """Load the independent artwork selection, verifying file and decoded pixels."""
    source = json.loads(path.read_text())
    selected = source["selected_paintings"]
    require(len(selected) == 24, "Illustration manifest must select24 paintings")
    scenes = {}
    for episode in episodes:
        matches = [entry for entry in selected if entry["id"] == episode["id"]]
        require(len(matches) == 1, f"Expected one selected scene for{episode['id']}")
        entry = matches[0]
        require(entry["episode_number"] == episode["episode_number"], "Illustration episode number mismatch")
        asset = Path(entry["asset"])
        asset = asset if asset.is_absolute() else ROOT / asset
        require(asset.is_file(), f"Selected illustration missing:{asset}")
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        require(digest == entry["sha256"], f"Selected illustration file hash mismatch:{asset}")
        with Image.open(asset) as image:
            rgb = image.convert("RGB")
            dimensions = list(rgb.size)
            decoded_digest = hashlib.sha256(rgb.tobytes()).hexdigest()
        expected_dimensions = entry.get("pixel_dimensions", entry.get("export_pixels", entry.get("native_pixels")))
        require(dimensions == expected_dimensions, f"Illustration dimensions mismatch:{asset}")
        require(abs((dimensions[0] / dimensions[1]) / 1.6 - 1) < .01,
                f"Selected illustration is not a horizontal16:10 scene:{asset}")
        scenes[episode["id"]] = {"episode_number": episode["episode_number"], "id": episode["id"],
                                  "asset": str(asset.relative_to(ROOT)) if asset.is_relative_to(ROOT) else str(asset),
                                  "sha256": digest, "pixel_dimensions": dimensions,
                                  "decoded_rgb_sha256": decoded_digest}
    require(len(scenes) == 24, "Selected scene IDs must be unique")
    return scenes


def front_image_instances(form, reader):
    """Read actual image drawing transforms inside one card Form."""
    stack, current, instances = [], [1, 0, 0, 1, 0, 0], []
    objects = form["/Resources"].get("/XObject", {})
    for args, op in ContentStream(form, reader).operations:
        if op == b"q":
            stack.append(current[:])
        elif op == b"Q":
            current = stack.pop()
        elif op == b"cm":
            current = multiply([float(value) for value in args], current)
        elif op == b"Do":
            obj = objects[args[0]].get_object()
            require(obj.get("/Subtype") == "/Image", "A front must draw the scene directly, without nested image/portrait Forms")
            instances.append({"name": str(args[0]), "image": obj, "transform": current[:]})
    return instances


def check_front_graphics(form, reader, episode_number, size):
    """Forbid old route dashes and portrait-size circle/clip graphics."""
    path, portrait_circles = [], 0
    for args, op in ContentStream(form, reader).operations:
        if op == b"d":
            require(len(args[0]) == 0,
                    f"{size} episode{episode_number}: obsolete dashed route graphics remain")
        if op in (b"W", b"W*"):
            raise AssertionError(f"{size} episode{episode_number}: front contains a clipping path; artwork must be uncropped")
        if op == b"n":
            path = []
        elif op in (b"m", b"c", b"l", b"h", b"re"):
            path.append(([float(value) / MM for value in args], op))
        elif op in (b"S", b"s", b"B", b"B*", b"f", b"f*", b"b", b"b*"):
            shape = [kind for _, kind in path]
            if shape in ([b"m", b"c", b"c", b"c", b"c"],
                         [b"m", b"c", b"c", b"c", b"c", b"h"]):
                values = [value for coords, _ in path for value in coords]
                xs, ys = values[::2], values[1::2]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if min(w, h) >= 6 and abs(w - h) < .05:
                    portrait_circles += 1
            path = []
    require(portrait_circles == 0,
            f"{size} episode{episode_number}: obsolete circular portrait graphics remain")
    return {"nonempty_dash_patterns": 0, "portrait_sized_circle_paths": 0, "clipping_paths": 0}


def check_scene_images(reader, episodes, size, scenes):
    """Verify the actual native, selected painting embedded on every card front."""
    forms = {}
    for page in reader.pages:
        for instance in form_instances(page):
            if instance["name"].endswith("_front"):
                forms[instance["name"]] = instance["form"]
    require(len(forms) == 24, f"{size}: expected24 unique scene-front Forms")
    checks = []
    for episode in episodes:
        matches = [(name, form) for name, form in forms.items()
                   if name.endswith(episode["id"] + "_front")]
        require(len(matches) == 1, f"{size}: missing unique front Form for{episode['id']}")
        _, form = matches[0]
        selected = scenes[episode["id"]]
        drawings = front_image_instances(form, reader)
        require(len(drawings) == 1,
                f"{size} episode{episode['episode_number']}: expected one scene image, got{len(drawings)}")
        image_resources = [obj.get_object() for obj in form["/Resources"].get("/XObject", {}).values()
                           if obj.get_object().get("/Subtype") == "/Image"]
        require(len(image_resources) == 1,
                f"{size} episode{episode['episode_number']}: front retains extra portrait image resources")
        drawing = drawings[0]
        image = drawing["image"]
        dimensions = [int(image["/Width"]), int(image["/Height"])]
        require(dimensions == selected["pixel_dimensions"],
                f"{size} episode{episode['episode_number']}: embedded scene is resampled or wrong image")
        require(image.get("/ColorSpace") == "/DeviceRGB" and int(image.get("/BitsPerComponent", 0)) == 8,
                f"{size} episode{episode['episode_number']}: expected native8-bit RGB scene")
        require(hashlib.sha256(image.get_data()).hexdigest() == selected["decoded_rgb_sha256"],
                f"{size} episode{episode['episode_number']}: embedded painting pixels differ from selected asset")
        a, b, c, d, x, y = drawing["transform"]
        require(a > 0 and d > 0 and abs(b) < .001 and abs(c) < .001,
                f"{size} episode{episode['episode_number']}: scene is mirrored or rotated")
        require(abs((a / d) / (dimensions[0] / dimensions[1]) - 1) < .0001,
                f"{size} episode{episode['episode_number']}: scene aspect ratio is stretched")
        bounds = [float(value) for value in form["/BBox"]]
        require(x >= bounds[0] + 2.5 * MM - .01 and y >= bounds[1] + 2.5 * MM - .01
                and x + a <= bounds[2] - 2.5 * MM + .01 and y + d <= bounds[3] - 2.5 * MM + .01,
                f"{size} episode{episode['episode_number']}: scene crosses the safe card frame")
        require(a >= (bounds[2] - bounds[0]) * .5,
                f"{size} episode{episode['episode_number']}: painting is too small to be the front vignette")
        graphics = check_front_graphics(form, reader, episode["episode_number"], size)
        checks.append({"episode": episode["episode_number"], "selected_asset": selected["asset"],
                       "selected_asset_sha256": selected["sha256"], "image_drawings": 1,
                       "embedded_pixel_dimensions": dimensions, "native_rgb_pixels_match_selected": True,
                       "actual_image_bbox_mm": [round(value / MM, 4) for value in (x, y, x + a, y + d)],
                       "aspect_ratio_preserved": True, "uncropped": True, **graphics})
    return checks


def check_scene_manifest(manifest, scenes, illustration_path):
    path = Path(manifest["illustration_source"])
    path = path if path.is_absolute() else ROOT / path
    require(path.resolve() == illustration_path.resolve(), "Build manifest uses an unexpected illustration manifest")
    require(manifest["illustration_manifest_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest(),
            "Build manifest illustration-manifest hash mismatch")
    records = manifest["scene_assets"]
    require(len(records) == 24 and len({record["id"] for record in records}) == 24,
            "Build manifest must expose24 distinct selected episode scenes")
    for record in records:
        expected = scenes.get(record["id"])
        require(expected is not None, f"Unknown build-manifest scene ID:{record['id']}")
        for key in ("episode_number", "asset", "sha256", "pixel_dimensions"):
            require(record[key] == expected[key], f"Build manifest scene{record['id']} differs from selected illustration:{key}")
    return {"illustration_manifest_hash_checked": True, "selected_scene_records_checked": 24,
            "selected_asset_file_hashes_checked": True}


def check_manifest(manifest, checks, hashes, a5_single_only=False):
    """Check reported slot maps against source order and actualPDF results."""
    require(isinstance(manifest, dict), "Manifest is not an object")
    inventory = manifest.get("pdfs", manifest.get("files", []))
    checked_maps = []
    found_files = set()
    expected_files = {"a5_single"} if a5_single_only else set(FILES)
    if isinstance(inventory, list):
        for record in inventory:
            name = str(record.get("file", record.get("path", "")))
            for key, (filename, pages, dimensions) in FILES.items():
                if key not in expected_files:
                    continue
                if name.endswith(filename):
                    found_files.add(key)
                    require(record.get("sha256") == hashes[filename], f"Manifest PDF hash mismatch: {filename}")
                    if "pages" in record:
                        require(record["pages"] == pages, f"Manifest page count wrong: {filename}")
                    if "page_size_mm" in record:
                        require(all(abs(a - b) < .01 for a, b in zip(record["page_size_mm"], dimensions)),
                                f"Manifest dimensions wrong: {filename}")
                    if key == "a5_single":
                        order = record["page_order"]
                        require(len(order) == 48, "Manifest nativepage map length")
                        for index, entry in enumerate(order):
                            require(entry["page"] == index + 1 and entry["episode_number"] == index // 2 + 1
                                    and entry["side"] == ("front" if index % 2 == 0 else "back"),
                                    "Manifest nativepage map differs from actual/sourceorder")
                    else:
                        sheet_order = record["sheet_order"]
                        require(len(sheet_order) == pages // 2, f"Manifest {key}: wrongsheetcount")
                        require(record["duplex_flip"] == ("short_edge" if key == "a5_duplex" else "long_edge"),
                                f"Manifest {key}: wrong duplex edge")
                        for sheet_index, sheet in enumerate(sheet_order):
                            require(sheet["sheet"] == sheet_index + 1, "Manifest sheetnumbers")
                            for side_index, page in enumerate(sheet["pages"]):
                                side = "front" if side_index == 0 else "back"
                                expected = expected_numbers(key, sheet_index, side == "back")
                                require(page["page"] == sheet_index * 2 + side_index + 1 and page["side"] == side,
                                        f"Manifest {key} sheet{sheet_index + 1}: wrongpage/side")
                                require([s["episode_number"] for s in page["slots"]] == expected,
                                        f"Manifest {key} sheet{sheet_index + 1} {side}: wrongepisodes")
                                for index, slot in enumerate(page["slots"]):
                                    require(slot["slot"] == index and slot["rotation_degrees"] == 0,
                                            f"Manifest {key}: slot index/rotation")
                                    require(slot["origin_mm"] == list(SLOTS[key][index][:2]),
                                            f"Manifest {key}: slotoverride {slot['origin_mm']}")
                            checked_maps.append({"edition": key, "sheet": sheet_index + 1})
    require(found_files == expected_files, "Manifest inventory does not match the requested editions")
    require(len(checked_maps) == (0 if a5_single_only else 18), "Manifest has the wrong number of imposed sheet maps")
    return {"inventory_checked": True, "pdf_hashes_checked": True, "slot_maps_checked": checked_maps,
            "slot_schema_needs_mapping": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/episode-deck")
    parser.add_argument("--source", type=Path, default=ROOT / "print-and-play/episode-deck/episode-cards.ka.json")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--a5-single-only", action="store_true", help="Verify only the native A5 front/back edition")
    parser.add_argument("--illustrations", type=Path, default=ILLUSTRATIONS,
                        help="Selected episode-illustration manifest")
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    episodes = check_source(source)
    scenes = load_selected_scenes(args.illustrations, episodes)
    readers, hashes = {}, {}
    for key, (filename, count, dimensions) in FILES.items():
        if args.a5_single_only and key != "a5_single":
            continue
        path = args.output_dir / filename
        require(path.is_file(), f"Missing export: {path}")
        hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        reader = PdfReader(path)
        require(len(reader.pages) == count, f"{filename}: expected {count} pages, got {len(reader.pages)}")
        for index, page in enumerate(reader.pages, 1):
            actual = page_size(page)
            require(all(abs(a - b) < .01 for a, b in zip(actual, dimensions)),
                    f"{filename} page {index}: dimensions {actual}, expected {dimensions}")
        readers[key] = reader
    checks = {"a5_single": check_native(readers["a5_single"], episodes)}
    for key in (() if args.a5_single_only else ("a5_duplex", "a6_duplex")):
        checks[key] = check_imposed(key, readers[key], episodes)
    compact_checks = [] if args.a5_single_only else check_native(compact_reader(readers["a6_duplex"], episodes), episodes)
    manifest = json.loads((args.output_dir / "build-manifest.json").read_text())
    report = {"status": "independent_source_content_and_pdf_geometry_passed",
              "scope": "a5_single_only" if args.a5_single_only else "all_editions",
              "source_episodes": 24, "source_chapters": "1..65", "source_stanzas": "1..1669",
              "native_ascii_latin_letters": 0, "pdf_checks": checks,
              "compact_full_copy_checks": compact_checks,
              "actual_timeline_fill_checks": {
                  "A5": check_timeline_forms(readers["a5_single"], episodes, "A5")},
              "actual_drawn_frame_checks": {
                  "A5": check_actual_frames(readers["a5_single"], "A5")},
              "actual_scene_image_checks": {
                  "A5_single": check_scene_images(readers["a5_single"], episodes, "A5", scenes)},
              "pdf_sha256": hashes,
              "manifest_checks": check_manifest(manifest, checks, hashes, args.a5_single_only),
              "scene_manifest_checks": check_scene_manifest(manifest, scenes, args.illustrations),
              "physical_print_test": False}
    if not args.a5_single_only:
        report["actual_timeline_fill_checks"]["A6"] = check_timeline_forms(readers["a6_duplex"], episodes, "A6")
        report["actual_drawn_frame_checks"]["A6"] = check_actual_frames(readers["a6_duplex"], "A6")
        report["actual_scene_image_checks"]["A5_duplex"] = check_scene_images(readers["a5_duplex"], episodes, "A5", scenes)
        report["actual_scene_image_checks"]["A6_duplex"] = check_scene_images(readers["a6_duplex"], episodes, "A6", scenes)
    require(all(hashlib.sha256((args.output_dir / filename).read_bytes()).hexdigest() == digest
                for filename, digest in hashes.items()), "A PDF changed during the independent audit")
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload)
    print(payload)


if __name__ == "__main__":
    main()
