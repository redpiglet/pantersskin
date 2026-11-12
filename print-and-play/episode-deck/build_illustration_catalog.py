#!/usr/bin/env python3
"""Package the 24 selected native episode paintings and create review materials."""

import hashlib
import html
import io
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import build_episode_deck as typography

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "output/episode-illustrations"
MM = 72 / 25.4
SOURCE_PATH = HERE / "episode-cards.ka.json"
SOURCE = json.loads(SOURCE_PATH.read_text())
BRIEF_DATA = json.loads((HERE / "scene-briefs.json").read_text())
BRIEFS = {e["episode_number"]: e for e in BRIEF_DATA["episodes"]}
STYLE = json.loads((HERE / "illustration-style.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_reference(path):
    p = Path(path)
    return str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p)


def collect():
    entries, prompts = [], []
    for e in SOURCE["episodes"]:
        n = e["episode_number"]
        receipt_path = HERE / f"illustration-receipts/episode-{n:02d}.json"
        receipt = json.loads(receipt_path.read_text())
        asset = receipt.get("selected_asset") or receipt.get("asset") or receipt["asset_path"]
        path = ROOT / asset
        qa = receipt.get("visual_qa", receipt.get("qa", {}))
        passed = qa.get("passed") or qa.get("status") == "passed" or all(
            qa.get(k) for k in ("visually_reviewed", "text_free", "no_banners_or_scrolls", "single_scene"))
        assert passed, (n, "Artwork has not passed visual review")
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            pixels = list(image.size)
        ratio = pixels[0] / pixels[1]
        assert abs(ratio / 1.6 - 1) < .01, (n, pixels)
        chars = receipt.get("character_ids") or receipt.get("scene_character_ids") or BRIEFS[n]["character_ids"]
        generated_pixels = receipt.get("native_generated_pixels", pixels)
        entry = {"episode_number": n, "id": e["id"], "title_ka": e["title_ka"],
                 "title_en": e["title_en"], "chapters": e["chapters"],
                 "chapter_range_label_ka": e["chapter_range_label_ka"], "stanza_range": e["stanza_range"],
                 "asset": asset, "native_pixels": generated_pixels, "pixel_dimensions": pixels,
                 "export_pixels": pixels, "actual_aspect_ratio": ratio,
                 "export_processing": receipt.get("export_processing", "Generated PNG copied unchanged"),
                 "requested_aspect_ratio": "16:10", "sha256": sha(path), "bytes": path.stat().st_size,
                 "scene_character_ids": chars,
                 "shared_prop_ids": BRIEFS[n].get("shared_prop_ids", []),
                 "selected_scene": receipt.get("actual_scene") or qa.get("scene") or BRIEFS[n]["scene_description_en"],
                 "generation_receipt": str(receipt_path.relative_to(ROOT)),
                 "visual_review_passed": True, "visual_review": qa,
                 "native_dpi_at_130mm_width": round(generated_pixels[0] / (130 / 25.4), 1),
                 "export_dpi_at_130mm_width": round(pixels[0] / (130 / 25.4), 1)}
        entries.append(entry)
        refs = receipt.get("references", receipt.get("referenced_image_paths", receipt.get("reference_assets", [])))
        prompts.append({"episode_number": n, "id": e["id"], "selected_asset": asset,
                        "tool": "built-in image_gen.imagegen", "prompt": receipt["prompt"],
                        "references": [relative_reference(p) for p in refs],
                        "attempts": receipt.get("attempts", []),
                        "correction": receipt.get("edit_prompt") or receipt.get("correction"),
                        "generation_receipt": str(receipt_path.relative_to(ROOT))})
    assert [e["episode_number"] for e in entries] == list(range(1, 25))
    assert len({e["sha256"] for e in entries}) == 24, "Every episode must have its own painting"
    return entries, prompts


def para(c, text, x, top, w, size, bold=False, ink="#203D37"):
    p, h = typography.paragraph(text, w, size, size * 1.2, "GeoBold" if bold else "Geo", ink)
    p.drawOn(c, x * MM, (top - h) * MM)
    return top - h


def review_pdf(entries):
    path = OUT / "pantersskin-episode-illustrations-ka-review.pdf"
    c = canvas.Canvas(str(path), pagesize=(297 * MM, 210 * MM), pageCompression=1)
    c.setTitle("ეპიზოდების ილუსტრაციები / 24 სცენა")
    c.setAuthor("ვეფხისტყაოსნის პროექტი")
    for start in range(0, 24, 4):
        c.setFillColor(colors.HexColor("#F6F1E4"))
        c.rect(0, 0, 297 * MM, 210 * MM, fill=1, stroke=0)
        para(c, "ეპიზოდების ილუსტრაციები / 24 სცენა", 11.5, 206, 240, 12, True)
        para(c, f"{start // 4 + 1} / 6", 272, 205, 16, 9)
        for index, entry in enumerate(entries[start:start + 4]):
            row, col = divmod(index, 2)
            x, top, w, h = 11.5 + col * 144, 194 - row * 95, 130, 81.25
            # Review-only JPEG payload; selected native PNG artwork stays untouched.
            with Image.open(ROOT / entry["asset"]) as source:
                preview = source.convert("RGB")
                preview.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
                data = io.BytesIO()
                preview.save(data, format="JPEG", quality=92, subsampling=0)
                data.seek(0)
            c.drawImage(ImageReader(data), x * MM, (top - h) * MM, w * MM, h * MM,
                        preserveAspectRatio=True, anchor="c")
            y = para(c, f"{entry['episode_number']:02d}. {entry['title_ka']}",
                     x, top - h - 1.2, w, 8.5, True)
            y = para(c, f"{entry['chapter_range_label_ka']} / სტრ. {entry['stanza_range']}",
                     x, y - .6, w, 6.8, ink="#647168")
            assert y >= 5, (entry["episode_number"], "Review caption crosses page edge", y)
        c.showPage()
    c.save()
    return path


def gallery(entries, portable=False):
    figures = []
    for entry in entries:
        src = ("images/" + Path(entry["asset"]).name) if portable else ("../../" + entry["asset"])
        title = html.escape(f"{entry['episode_number']:02d}. {entry['title_ka']}")
        subtitle = html.escape(f"{entry['chapter_range_label_ka']} / სტრ. {entry['stanza_range']}")
        figures.append(f'<figure><a href="{src}" target="_blank"><img src="{src}" loading="lazy" alt="{title}"></a><figcaption><strong>{title}</strong><span>{subtitle}</span></figcaption></figure>')
    return '''<!doctype html><html lang="ka"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ეპიზოდების ილუსტრაციები</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f6f1e4;color:#203d37;font-family:Arial,sans-serif}header,main{max-width:1440px;margin:auto;padding:24px}header{padding-bottom:0}h1{font-size:28px;margin:0 0 10px}p{line-height:1.6;color:#647168}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}figure{margin:0;background:#fffaf0;border:1px solid #c5b38c;border-radius:8px;overflow:hidden}img{display:block;width:100%;aspect-ratio:16/10;object-fit:contain}figcaption{padding:14px 18px;line-height:1.5}figcaption span{display:block;font-size:13px;color:#647168;margin-top:6px}a{color:inherit}@media(max-width:760px){main{grid-template-columns:1fr;padding:16px}header{padding:20px 16px}h1{font-size:23px}}</style>
<header><h1>ეპიზოდების ილუსტრაციები</h1><p>24 დამოუკიდებელი, უწარწერო სცენა. სურათზე დაჭერით გაიხსნება თავდაპირველი ფაილი. სათაურები მოთავსებულია მხოლოდ გალერეაში, ნახატების გარეთ.</p></header><main>''' + "\n".join(figures) + "</main></html>\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries, prompts = collect()
    prompt_set = {"date": "2026-11-10", "tool": "built-in image_gen.imagegen", "style": STYLE,
                  "shared_visual_props": BRIEF_DATA.get("shared_visual_props", {}),
                  "count": 24, "episodes": prompts}
    prompt_path = HERE / "illustration-prompts.json"
    prompt_path.write_text(json.dumps(prompt_set, ensure_ascii=False, indent=2) + "\n")
    pdf = review_pdf(entries)
    (OUT / "gallery.html").write_text(gallery(entries))
    manifest = {"date": "2026-11-10", "tool": "built-in image_gen.imagegen", "count": 24,
                "source": str(SOURCE_PATH.relative_to(ROOT)), "source_sha256": sha(SOURCE_PATH),
                "source_preserved": True, "selected_paintings": entries,
                "scene_briefs": "print-and-play/episode-deck/scene-briefs.json",
                "shared_visual_props": BRIEF_DATA.get("shared_visual_props", {}),
                "art_processing": "All painted content corrections made with built-in image generation. Corrected files use a one-pixel horizontal export-size normalization where required to deliver1586x992; unchanged native generated copies are preserved separately. Review PDF uses smaller JPEG preview payloads only.",
                "aspect_ratio_note": "Horizontal16:10 composition. Exact selected export dimensions and native generated dimensions are recorded separately for every file.",
                "review_pdf": str(pdf.relative_to(ROOT)), "review_pdf_pages": 6,
                "review_pdf_sha256": sha(pdf), "prompt_set": str(prompt_path.relative_to(ROOT)),
                "selected_revision_note": "Selected versions are listed per episode. Earlier versions remain outside the final archive. Episodes06,08,09,10,11,12,19,20 carry the requested scene corrections; episode23 retains its previously approvedv2."}
    manifest_path = OUT / "illustration-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    qa_dir = OUT / "quality-reviews"
    qa_dir.mkdir(exist_ok=True)
    # Prior reports describe earlier image hashes and must not certify new edits.
    history = qa_dir / "history"
    for prior in qa_dir.glob("review-?.json"):
        history.mkdir(exist_ok=True)
        target = history / prior.name
        if not target.exists():
            shutil.copyfile(prior, target)
        prior.unlink()
    current_review = {"status": "selected_receipt_visual_qa_passed", "count": 24,
                      "method": "Current selected-revision visual checks from each generation receipt; exact selected hashes below.",
                      "assets": [{"episode_number": e["episode_number"], "asset": e["asset"],
                                  "sha256": e["sha256"], "pixel_dimensions": e["pixel_dimensions"],
                                  "visual_review": e["visual_review"]} for e in entries]}
    (qa_dir / "selected-artwork-review.json").write_text(json.dumps(current_review, ensure_ascii=False, indent=2) + "\n")
    revisions = ", ".join(f"{e['episode_number']:02d}: {Path(e['asset']).name}" for e in entries)
    readme = """# ეპიზოდების ილუსტრაციები

24 შერჩეული სცენა „ვეფხისტყაოსნის“ ეპიზოდებისთვის. ყველა სურათი დამოუკიდებელი PNG ფაილია და ნახატის შიგნით არ შეიცავს ტექსტს, ასოებს, ნომრებს, წარწერიან ლენტებს ან გრაგნილებს.

გახსენით gallery.html ეპიზოდების მიხედვით დასათვალიერებლად. სურათზე დაჭერით იხსნება თავდაპირველი ფაილი. გალერეის სათაურები ნახატების გარეთაა.

images საქაღალდეში ზუსტად 24 შერჩეული PNG არის. ფაილის პირველი ნომერი ეპიზოდის ნომერია. კონკრეტული შერჩეული ვერსია მითითებულია ქვემოთ და ანგარიშში.

რვა შესწორებული ეპიზოდის (06,08,09,10,11,12,19,20) საბოლოო ფაილები ზუსტად 1586 × 992 პიქსელია. გამოსახულების გენერატორის ერთპიქსელიანი განსხვავება გასწორდა მხოლოდ ჰორიზონტალური საექსპორტო ზომის ნორმალიზაციით; დაუმუშავებელი გენერირებული ასლები პროექტშიც შენარჩუნებულია. სხვა დამტკიცებული სურათები უცვლელია, მათ შორის 23-ე ეპიზოდი 1585 × 992 პიქსელზე. ფორმატი დაახლოებით16:10-ია; 130 მმ სიგანეზე დეტალიზაცია დაახლოებით310 წერტილია დუიმზე. დახატული შინაარსი მხოლოდ ჩაშენებული გამოსახულების ინსტრუმენტით შეიცვალა; არ მოჭრილა კადრი და არ შესრულებულა ხელით გადახატვა.

ნახატები შეიქმნა ჩაშენებული გამოსახულების გენერატორით. illustration-prompts.json ინახავს ყველა მოთხოვნასა და გამოყენებული პერსონაჟების/სტილის საცნობარო ფაილების სიას; illustration-manifest.json - ეპიზოდების შესაბამისობას, შერჩეულ ვერსიებს, ზომებსა და საკონტროლო ჯამებს. quality-reviews საქაღალდეშია დამოუკიდებელი ვიზუალური შემოწმებები. სცენები ამოწმებს პერსონაჟების თანადასწრებასა და სამოსის ქრონოლოგიას; ერთი ეპიზოდის სხვადასხვა დროსა და სივრცეში მომხდარი მოვლენები ერთ კადრში არ არის შერეული.
"""
    readme += "\nშერჩეული ფაილები:\n" + revisions + "\n"
    (OUT / "README.md").write_text(readme)
    archive = OUT / "pantersskin-episode-illustrations-24.zip"
    portable_manifest = json.loads(json.dumps(manifest))
    for entry in portable_manifest["selected_paintings"]:
        entry["project_asset"] = entry["asset"]
        entry["asset"] = "images/" + Path(entry["asset"]).name
    for prop in portable_manifest.get("shared_visual_props", {}).values():
        if prop.get("canonical_fabric_image"):
            prop["canonical_fabric_image"] = "images/" + Path(prop["canonical_fabric_image"]).name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for entry in entries:
            z.write(ROOT / entry["asset"], "images/" + Path(entry["asset"]).name)
        z.writestr("gallery.html", gallery(entries, portable=True))
        z.writestr("illustration-manifest.json", json.dumps(portable_manifest, ensure_ascii=False, indent=2) + "\n")
        z.writestr("illustration-prompts.json", json.dumps(prompt_set, ensure_ascii=False, indent=2) + "\n")
        z.writestr("README.md", readme)
        for review in sorted(qa_dir.glob("*.json")):
            z.write(review, "quality-reviews/" + review.name)
    with zipfile.ZipFile(archive) as z:
        assert len([n for n in z.namelist() if n.startswith("images/") and n.endswith(".png")]) == 24
        assert z.testzip() is None
        for entry in entries:
            assert hashlib.sha256(z.read("images/" + Path(entry["asset"]).name)).hexdigest() == entry["sha256"]
    print(pdf.resolve())
    print(archive.resolve())
    print((OUT / "gallery.html").resolve())


if __name__ == "__main__":
    main()
