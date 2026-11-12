#!/usr/bin/env python3
"""Compose painted map art with precise Georgian labels, routes and fold panels.

The image is embedded unchanged. Layout overlays remain vector text and paths.
"""

import argparse
import hashlib
import json
from pathlib import Path

from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import build_map as base

rl_config.useA85 = False
HERE, ROOT = base.HERE, base.ROOT
MM, W, H = base.MM, base.W, base.H
DATA, PRODUCTION = base.DATA, base.PRODUCTION


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--art", required=True, type=Path, help="Unchanged generated manuscript-map artwork")
    p.add_argument("--layout", type=Path, default=HERE / "painted-map-layout.ka.json")
    p.add_argument("--out", type=Path, default=ROOT / "output/painted-realm-map")
    p.add_argument("--draft-no-routes", action="store_true", help="Suppress route paths and their key for art review")
    return p.parse_args()


class PaintedDrawing(base.Drawing):
    def __init__(self, c, art, layout, routes=True):
        super().__init__(c)
        self.art, self.layout = art, layout
        self.show_routes = routes and layout["routes"].get("enabled", True)
        pixels_w, pixels_h = art.getSize()
        scale = min(W / pixels_w, H / pixels_h)
        self.art_box = [(W - pixels_w * scale) / 2, (H - pixels_h * scale) / 2,
                        pixels_w * scale, pixels_h * scale]

    def wash(self, cx, y, w, h, alpha=.88):
        """A quiet translucent parchment wash, without diagram cards or borders."""
        self.c.saveState()
        self.c.setFillAlpha(alpha)
        self.ellipse(cx - w / 2, y, w, h, self.layout.get("paper_color", base.IVORY))
        self.c.restoreState()

    def halo_text(self, s, x, y, size=11, font="Geo", ink=base.INK,
                  align="left", primary=False, halo=None):
        """Outline the glyphs lightly, leaving the surrounding painting visible."""
        if halo and halo.get("width_pt", 1.2) > 0 and halo.get("alpha", .85) > 0:
            text_width = base.width(s, size, font)
            start = x - text_width / 2 if align == "center" else \
                    x - text_width if align == "right" else x
            self.c.saveState()
            self.c.setStrokeColor(base.color(halo.get("color", "#F4E3BD")))
            self.c.setStrokeAlpha(halo.get("alpha", .85))
            self.c.setLineWidth(halo.get("width_pt", 1.2))
            self.c.setLineJoin(1)
            t = self.c.beginText(start * MM, y * MM)
            t.setTextRenderMode(1)  # Stroke only, beneath the normal filled glyphs.
            t.setCharSpace(0)
            for family, text in base.runs(s, font):
                t.setFont(family, size)
                t.textOut(text)
            self.c.drawText(t)
            self.c.restoreState()
        # Only this normal pass registers the label's bounds.
        return self.text(s, x, y, size, font, ink, align, primary)

    def route_path(self, path, kind):
        """Use the same softly integrated route treatment on the map and key."""
        spec = self.layout["routes"]
        style = spec.get("styles", {}).get(kind, {})
        default = base.ROUTE_STYLES[kind]
        ink = style.get("stroke_color", spec.get(kind + "_color", default["color"]))
        dash = style.get("dash_mm", {"land": None, "sea": [2.8, 1.9],
                                     "mixed": [4.3, 1.5, .6, 1.5],
                                     "narrative": [.55, 1.55]}[kind])
        halo_width = style.get("halo_mm", spec["halo_mm"])
        if halo_width > 0 and style.get("halo_alpha", 1) > 0:
            self.c.saveState()
            self.c.setStrokeAlpha(style.get("halo_alpha", 1))
            self.shape(path, stroke=style.get("halo_color", base.IVORY), weight=halo_width)
            self.c.restoreState()
        self.c.saveState()
        self.c.setStrokeAlpha(style.get("stroke_alpha", 1))
        self.shape(path, stroke=ink, weight=style.get("stroke_mm", spec["stroke_mm"]), dash=dash)
        self.c.restoreState()

    def painted_routes(self):
        spec = self.layout["routes"]
        for route in DATA["routes"]:
            if not route["rendered"]:
                continue
            path = spec["paths"][route["id"]]
            self.route_path(path, route["kind"])
        self.route_labels()

    def route_labels(self):
        """Optional labels identify plot-specific links without creating map nodes."""
        active_ids = {route["id"] for route in DATA["routes"] if route["rendered"]}
        for route_id, entries in self.layout["routes"].get("labels", {}).items():
            if route_id not in active_ids:
                continue
            entries = entries if isinstance(entries, list) else [entries]
            for label in entries:
                text, x, y = label["text"], label["x"], label["y"]
                size = label.get("size_pt", 10.5)
                font = label.get("font", "Geo")
                align = label.get("align", "center")
                if label.get("paper_backing", False):
                    text_width = base.width(text, size, font)
                    cx = x + text_width / 2 if align == "left" else \
                         x - text_width / 2 if align == "right" else x
                    self.wash(cx, y - 1.8, text_width + label.get("paper_padding_mm", 6),
                              size / MM + 3.2, label.get("paper_alpha", .45))
                self.text(text, x, y, size, font,
                          label.get("ink", self.layout["caption_ink"]), align, True)

    def painted_legend(self):
        spec = self.layout["legend"]
        if not spec.get("enabled", True):
            return
        x = spec["x"]
        self.text(DATA["legend"]["heading"].upper(), x, spec["heading_y"], 15,
                  "GeoBold", self.layout["label_ink"], primary=True)
        active_kinds = {route["kind"] for route in DATA["routes"] if route["rendered"]}
        kinds = [kind for kind in spec.get("kinds", ["land", "sea", "mixed", "narrative"])
                 if kind in active_kinds]
        for i, kind in enumerate(kinds):
            y = spec["first_row_y"] - i * spec["row_step_mm"]
            self.route_path([("M", [x, y]), ("L", [x + spec["line_width_mm"], y])], kind)
            self.text(DATA["legend"][kind], x + spec["text_offset_mm"], y - 1.5,
                      spec.get("text_size_pt", 11), ink=self.layout["caption_ink"], primary=True)
        self.para(DATA["legend"]["note"], x, spec["note_top_y"],
                  spec["note_width_mm"], size=9.8, leading=13, ink=self.layout["caption_ink"])

    def map(self):
        self.rect(0, 0, W, H, self.layout.get("paper_color", base.IVORY))
        x, y, w, h = self.art_box
        self.c.drawImage(self.art, x * MM, y * MM, width=w * MM, height=h * MM,
                         preserveAspectRatio=True, mask="auto")
        if self.show_routes:
            self.painted_routes()
        for realm in DATA["realms"]:
            spec = self.layout["realms"][realm["id"]]
            x, y = spec["x"], spec["label_y"]
            size, caption_size = spec["name_size_pt"], spec["caption_size_pt"]
            label = realm["name_ka"].upper()
            if spec.get("paper_backing", True):
                self.wash(x, y - 3.2, base.width(label, size, "GeoDisplay") + 13, 12.3, .9)
                cap_w = base.width(realm["caption_ka"], caption_size, "Geo")
                self.wash(x, y - spec["caption_offset_mm"] - 2.1, cap_w + 10, 7.4, .84)
            name_halo = spec.get("name_text_halo", spec.get("text_halo"))
            inherited_caption_halo = dict(name_halo) if name_halo else None
            if inherited_caption_halo:
                inherited_caption_halo["width_pt"] = spec.get("caption_halo_width_pt", .7)
            caption_halo = spec.get("caption_text_halo", inherited_caption_halo)
            self.halo_text(label, x, y, size, "GeoDisplay",
                           spec.get("name_ink", self.layout["label_ink"]), "center", True, name_halo)
            self.line(x - 17, y - 5, x + 17, y - 5, base.GOLD, .24)
            self.halo_text(realm["caption_ka"], x, y - spec["caption_offset_mm"], caption_size,
                           "Geo", spec.get("caption_ink", self.layout["caption_ink"]),
                           "center", True, caption_halo)
        title = self.layout["title"]
        x, y = title["x"], title["y"]
        label = DATA["title"].upper()
        title_w = base.width(label, title["size_pt"], "GeoDisplay")
        align = title.get("align", "left")
        if title.get("paper_backing", True):
            self.wash(x + title_w / 2, y - 3, title_w + 14, 15, .9)
        self.text(label, x, y, title["size_pt"], "GeoDisplay", self.layout["label_ink"], align, True)
        self.text(DATA["subtitle"], x, title["subtitle_y"], title["subtitle_size_pt"],
                  ink=title.get("caption_ink", self.layout["caption_ink"]), align=align, primary=True)
        if self.show_routes:
            self.painted_legend()
        if self.layout.get("fold_ticks", True):
            for fx in DATA["folds"]["vertical_mm"]:
                self.line(fx, 2, fx, 5, base.GOLD, .28)
                self.line(fx, H - 2, fx, H - 5, base.GOLD, .28)
            self.line(2, 210, 5, 210, base.GOLD, .28)
            self.line(W - 2, 210, W - 5, 210, base.GOLD, .28)


def new_pdf(path, page_size, art, layout, routes=True):
    c = canvas.Canvas(str(path), pagesize=page_size, pageCompression=1)
    c.setTitle("სამეფოთა რუკა / მოხატული გამოცემა")
    c.setAuthor("ვეფხისტყაოსნის პროექტი")
    c.setSubject("შვიდი სივრცე / დასაკეცი რუკა / ქართული წარწერები")
    return c, PaintedDrawing(c, art, layout, routes)


def main():
    args = parse_args()
    art_path = args.art.resolve()
    if not art_path.is_file() or not art_path.stat().st_size:
        raise FileNotFoundError(art_path)
    args.out.mkdir(parents=True, exist_ok=True)
    layout = json.loads(args.layout.read_text())
    assert set(layout["realms"]) == {r["id"] for r in DATA["realms"]}
    active_routes = [route for route in DATA["routes"] if route["rendered"]]
    active_ids = [route["id"] for route in active_routes]
    assert len(active_ids) == len(set(active_ids)), "Duplicate rendered route IDs"
    if not args.draft_no_routes and layout["routes"].get("enabled", True):
        assert set(active_ids) <= set(layout["routes"]["paths"]), \
            "Every rendered route needs an explicit painted-map path"
        for route in active_routes:
            assert route["kind"] in base.ROUTE_STYLES, (route["id"], "unsupported route kind")
            assert route["kind"] in DATA["legend"], (route["id"], "missing Georgian legend text")
            path = layout["routes"]["paths"][route["id"]]
            assert path and path[0][0] == "M", (route["id"], "path must start with M")
            for command, values in path:
                assert command in ("M", "L", "C"), (route["id"], command)
                assert len(values) == (6 if command == "C" else 2), (route["id"], values)
                assert all(isinstance(n, (int, float)) for n in values), (route["id"], values)
            for x, y in (path[0][1][-2:], path[-1][1][-2:]):
                assert 0 <= x <= W and 0 <= y <= H, (route["id"], "endpoint outside map")
    art = ImageReader(str(art_path))
    routes = not args.draft_no_routes
    native = args.out / "painted-realm-map-ka-592x420.pdf"
    c, d = new_pdf(native, (W * MM, H * MM), art, layout, routes)
    d.map()
    boxes, art_box = d.label_boxes, d.art_box
    c.save()
    for label in boxes:
        x0, y0, x1, y1 = label["bbox_mm"]
        assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H, label
        for fx in DATA["folds"]["vertical_mm"]:
            assert x1 <= fx - 4 or x0 >= fx + 4, (label["text"], "vertical fold", fx)
        for fy in DATA["folds"]["horizontal_mm"]:
            assert y1 <= fy - 4 or y0 >= fy + 4, (label["text"], "horizontal fold", fy)

    tiled = args.out / "painted-realm-map-ka-a4-print.pdf"
    c, d = new_pdf(tiled, A4, art, layout, routes)
    panels = []
    for index, panel in enumerate(PRODUCTION["home_print"]["panels"], 1):
        x0, y0, x1, y1 = panel["core_world_bbox_mm"]
        c.bookmarkPage(f"panel-{index}")
        c.addOutlineEntry(f"პანელი {index}", f"panel-{index}", 0)
        d.rect(23, 35.5, 164, 226, base.IVORY)
        c.saveState()
        clip = c.beginPath()
        clip.rect(23 * MM, 35.5 * MM, 164 * MM, 226 * MM)
        c.clipPath(clip, stroke=0)
        c.translate((31 - x0) * MM, (43.5 - y0) * MM)
        d.map()
        c.restoreState()
        base.cropmarks(d, 31, 43.5, 148, 210)
        d.text(f"სამეფოთა რუკა / პანელი {index} / 8", 16, 278, 14, "GeoBold", base.GREEN)
        row = "ზედა რიგი" if index <= 4 else "ქვედა რიგი"
        d.text(f"{row} / სვეტი {(index - 1) % 4 + 1}", 16, 268, 10.5, ink=base.MUTED)
        base.panel_diagram(d, 163, 265, 29, index)
        d.text("ჭრის ზომა: 148 × 210 მმ", 105, 26, 10, ink=base.MUTED, align="center")
        d.text("A4 / ბეჭდვა 100%-ზე / ერთ მხარეს", 105, 17, 9, ink=base.MUTED, align="center")
        c.showPage()
        panels.append({"page": index, "world_bbox_mm": [x0, y0, x1, y1],
                       "a4_core_bbox_mm": [31, 43.5, 179, 253.5]})
    c.bookmarkPage("assembly")
    c.addOutlineEntry("აწყობა და დაკეცვა", "assembly", 0)
    base.assembly(d)
    c.showPage()
    c.save()
    guide = args.out / "painted-realm-map-ka-folding-guide.pdf"
    c, d = new_pdf(guide, A4, art, layout, routes)
    base.assembly(d)
    c.save()
    pixels_w, pixels_h = art.getSize()
    manifest = {
        "date": "2026-11-09", "language": "ka", "edition": "painted manuscript map",
        "board_size_mm": [W, H], "folded_size_mm": [148, 210], "realm_count": 7,
        "art_source": str(art_path), "art_sha256": hashlib.sha256(art_path.read_bytes()).hexdigest(),
        "art_pixels": [pixels_w, pixels_h], "art_placement_mm": art_box,
        "art_effective_dpi": [round(pixels_w / (art_box[2] / 25.4), 2),
                              round(pixels_h / (art_box[3] / 25.4), 2)],
        "art_processing": "Original generated asset embedded unchanged; aspect ratio preserved, no retouching or upscaling.",
        "labels_and_routes": "Vector Georgian labels and optional route overlays controlled by the painted-map layout.",
        "routes_visible": bool(d.show_routes),
        "legend_visible": bool(d.show_routes and layout["legend"].get("enabled", True)),
        "route_count": len(active_routes) if d.show_routes else 0,
        "rendered_routes": [{"id": route["id"], "from": route["from"], "to": route["to"],
                             "kind": route["kind"],
                             "path_start_mm": layout["routes"]["paths"][route["id"]][0][1][-2:],
                             "path_end_mm": layout["routes"]["paths"][route["id"]][-1][1][-2:]}
                            for route in active_routes] if d.show_routes else [],
        "layout_source": str(args.layout.resolve()), "important_label_boxes": boxes,
        "print_panels": panels, "a4_print_pages": 9,
        "files": [{"path": str(path.resolve()), "bytes": path.stat().st_size,
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in (native, tiled, guide)],
    }
    (args.out / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for path in (native, tiled, guide):
        print(path.resolve())


if __name__ == "__main__":
    main()
