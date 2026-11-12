"""Create local static instances of macOS's Georgian font for PDF embedding."""

import sys
from pathlib import Path


def prepare(root):
    cache = root / "tmp/georgian-deck/fonts"
    cache.mkdir(parents=True, exist_ok=True)
    marker = cache / "static-fonts-v2.complete"
    if marker.is_file() and all((cache / f"Georgian-{s}.ttf").is_file()
                                for s in ("Regular", "Bold", "Display")):
        return cache
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        # The local macOS Python installation already supplies this pure-Python library.
        candidates = list((Path.home() / "Library/Python").glob("*/lib/python/site-packages/fontTools"))
        if not candidates:
            raise RuntimeError("Georgian PDF fonts require fonttools; install it for your Python environment.")
        sys.path.append(str(candidates[-1].parent))
        from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    for style, weight, optical in [("Regular", 400, 17), ("Bold", 650, 17), ("Display", 700, 28)]:
        font = TTFont("/System/Library/Fonts/SFGeorgian.ttf")
        font = instantiateVariableFont(font, {"wght": weight, "opsz": optical}, inplace=True)
        # Unique PostScript names prevent ReportLab collapsing the three weights.
        for name_id, value in [(1, "Pantersskin Georgian"), (2, style),
                               (4, "Pantersskin Georgian " + style),
                               (6, "PantersskinGeorgian-" + style),
                               (16, "Pantersskin Georgian"), (17, style)]:
            font["name"].setName(value, name_id, 3, 1, 0x409)
            font["name"].setName(value, name_id, 1, 0, 0)
        font.save(cache / f"Georgian-{style}.ttf")
    marker.write_text("Static Georgian font instances; originals remain unchanged.\n")
    return cache
