#!/usr/bin/env python3
"""Build the print-ready 21-card Georgian A5 duplex PDF (Painted Portraits Only)."""

import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output" / "character-cards-ka-a5"
MANIFEST = json.loads((HERE / "portrait-manifest.json").read_text())
COPY = json.loads((HERE / "display-copy.ka.json").read_text())
UI = json.loads((HERE / "locale.ka.json").read_text())
FULL_BUILD = json.loads((OUT / "build-manifest.json").read_text())

PAINTED_ITEMS = [
    (idx, item["character_id"], COPY[item["character_id"]]["name"], item["asset"])
    for idx, item in enumerate(MANIFEST["portraits"])
    if item["asset"] and item["status"] != "generic_silhouette"
]
assert len(PAINTED_ITEMS) == 21, len(PAINTED_ITEMS)

OBJC_SOURCE = r"""
#import <Foundation/Foundation.h>
#import <PDFKit/PDFKit.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *cfgPath = [NSString stringWithUTF8String:argv[1]];
        NSDictionary *cfg = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:cfgPath] options:0 error:nil];

        PDFDocument *srcDuplex = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:cfg[@"src_duplex"]]];
        PDFDocument *outDuplex = [[PDFDocument alloc] init];

        for (NSDictionary *item in cfg[@"items"]) {
            int idx = [item[@"index"] intValue];
            PDFPage *front = [srcDuplex pageAtIndex:(idx * 2)];
            PDFPage *back = [srcDuplex pageAtIndex:(idx * 2 + 1)];
            if (front) [outDuplex insertPage:front atIndex:[outDuplex pageCount]];
            if (back) [outDuplex insertPage:back atIndex:[outDuplex pageCount]];
        }
        [outDuplex writeToFile:cfg[@"out_duplex"]];
    }
    return 0;
}
"""


def main():
    out_duplex = OUT / "pantersskin-character-cards-ka-a5-painted-21-a4-duplex.pdf"
    cfg = {
        "src_duplex": str(OUT / "pantersskin-character-cards-ka-a5-a4-duplex.pdf"),
        "out_duplex": str(out_duplex),
        "items": [
            {"index": idx, "id": cid, "name": name, "asset": asset}
            for idx, cid, name, asset in PAINTED_ITEMS
        ],
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg_file = tmp_path / "cfg.json"
        bin_file = tmp_path / "builder"
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
        subprocess.run(
            [
                "clang", "-x", "objective-c", "-O2",
                "-framework", "Foundation",
                "-framework", "PDFKit",
                "-", "-o", str(bin_file),
            ],
            input=OBJC_SOURCE.encode("utf-8"),
            check=True,
        )
        subprocess.run([str(bin_file), str(cfg_file)], check=True)

    sheets = [
        {"sheet": i + 1, "original_sheet": idx + 1, "character_id": cid, "name_ka": name, "front_center": cid, "back_center": cid, "portrait": asset}
        for i, (idx, cid, name, asset) in enumerate(PAINTED_ITEMS)
    ]
    manifest = {
        "date": "2026-11-08",
        "language": "ka",
        "edition": "painted_portraits_only_21",
        "card_count": 21,
        "sides": 2,
        "card_size": "A5",
        "card_size_mm": [148, 210],
        "home_printing": {
            "paper": "A4",
            "orientation": "portrait",
            "cards_per_sheet": 1,
            "total_sheets": 21,
            "total_pages": 42,
            "duplex_flip": "long_edge",
            "scale": "100% / actual size"
        },
        "pdfs": [
            {"file": str(out_duplex.relative_to(ROOT)), "pages": 42, "sheets": 21, "page_size_mm": [210, 297], "duplex_flip": "long_edge", "sheet_order": sheets}
        ],
        "layout_metrics": {cid: FULL_BUILD["layout_metrics"][cid] for _, cid, _, _ in PAINTED_ITEMS}
    }
    (OUT / "build-manifest-painted-21.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"{out_duplex.relative_to(ROOT)} ({out_duplex.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
