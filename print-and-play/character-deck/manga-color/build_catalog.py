#!/usr/bin/env python3
"""Package and structurally verify the21 coloured manga portrait variants.

Original portraits and the14 silhouette placeholders are read-only. The newest
{character_id}-vN.png is selected; --allow-partial produces progress proofs.
"""
import argparse
import copy
import hashlib
import html
import json
import math
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE.parent/"portrait-manifest.json"
COPY=HERE.parent/"display-copy.ka.json"
ASSETS=ROOT/"assets/characters/manga-color"
OUT=ROOT/"output/character-portraits-manga-color"
IVORY="#F6F1E4"
GREEN="#203D37"
GOLD="#A58958"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).relative_to(ROOT))


def info(path):
    path=Path(path)
    return {"file":relative(path),"bytes":path.stat().st_size,"sha256":sha(path)}


def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")


def newest(cid):
    candidates=[]
    pattern=re.compile(re.escape(cid)+r"-v(\d+)\.png$")
    for path in ASSETS.glob(cid+"-v*.png"):
        match=pattern.fullmatch(path.name)
        if match:candidates.append((int(match[1]),path))
    return max(candidates,key=lambda p:p[0]) if candidates else (None,None)


def inspect_png(path):
    with Image.open(path) as image:image.verify()
    with Image.open(path) as image:
        size=list(image.size);mode=image.mode
        has_alpha="A" in image.getbands() or "transparency" in image.info
        rgba=image.convert("RGBA");alpha=rgba.getchannel("A")
        width,height=size
        cx,cy=(width-1)/2,(height-1)/2
        radius=.43*min(size)
        mask=Image.new("L",tuple(size),0)
        ImageDraw.Draw(mask).ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=255)
        low=alpha.point(lambda a:255 if a<250 else 0)
        holes=ImageChops.multiply(mask,low).histogram()[255]
        zero_alpha=alpha.histogram()[0]
    errors=[]
    if size[0]!=size[1]:errors.append("portrait canvas is not square")
    if min(size)<768:errors.append("portrait resolution below768px")
    if holes:errors.append(f"{holes} pixels with alpha<250 inside radius0.43")
    return {"pixel_dimensions":size,"pixel_mode":mode,"has_alpha_channel":has_alpha,
            "transparent_pixels":zero_alpha,"inner_circle_radius_fraction":.43,
            "inner_circle_alpha_below_250":holes,"inner_circle_opaque":holes==0,
            "opaque_outer_corners_permitted":True,"errors":errors}


def find_receipt(cid,revision):
    for path in (HERE/"receipts"/f"{cid}-v{revision}.json",HERE/"receipts"/f"{cid}.json"):
        if path.is_file():return path
    return None


def load_font(size,bold=False):
    sys.path.insert(0,str(HERE.parent))
    from prepare_georgian_fonts import prepare
    folder=prepare(ROOT)
    return ImageFont.truetype(str(folder/f'Georgian-{"Bold" if bold else "Regular"}.ttf'),size)


def fit_font(draw,text,max_width,size=23):
    while size>15:
        font=load_font(size,True)
        if draw.textbbox((0,0),text,font=font)[2]<=max_width:return font
        size-=1
    return load_font(size,True)


def contact_sheet(records,path):
    cols=5;tw=260;th=306;gap=15;top=72
    rows=math.ceil(len(records)/cols)
    sheet=Image.new("RGB",(cols*tw+(cols+1)*gap,top+rows*th+(rows+1)*gap),IVORY)
    draw=ImageDraw.Draw(sheet)
    draw.text((gap,17),"პერსონაჟები: ფერადი მანგა",font=load_font(31,True),fill=GREEN)
    for index,record in enumerate(records):
        x=gap+(index%cols)*(tw+gap);y=top+gap+(index//cols)*(th+gap)
        asset=record.get("asset")
        if asset:
            with Image.open(ROOT/asset) as image:
                image=image.convert("RGBA")
                image.thumbnail((tw,tw),Image.Resampling.LANCZOS)
                sheet.paste(image,(x+(tw-image.width)//2,y+(tw-image.height)//2),image)
        else:
            draw.ellipse((x+18,y+18,x+tw-18,y+tw-18),outline=GOLD,width=2)
            label="მზადდება"
            font=load_font(22)
            box=draw.textbbox((0,0),label,font=font)
            draw.text((x+(tw-box[2])/2,y+tw/2-12),label,font=font,fill=GREEN)
        # SFGeorgian has no Latin punctuation fallback in Pillow.
        name=re.sub(r"[-‐‑‒–—]", " ", record["short_name_ka"])
        font=fit_font(draw,name,tw-6)
        box=draw.textbbox((0,0),name,font=font)
        draw.text((x+(tw-box[2])/2,y+tw+10),name,font=font,fill=GREEN)
        if record.get("inner_circle_alpha_below_250",0):
            label="ალფა გადასამოწმებელია"
            font=load_font(15)
            box=draw.textbbox((0,0),label,font=font)
            draw.text((x+(tw-box[2])/2,y+tw+40),label,font=font,fill="#874B40")
    sheet.save(path)


def gallery(records,placeholders,path):
    def url(asset):return html.escape(os.path.relpath(ROOT/asset,path.parent),quote=True)
    items=[]
    for record in records:
        name=html.escape(record["short_name_ka"])
        picture=(f'<a href="{url(record["asset"])}"><img src="{url(record["asset"])}" alt="{name}" loading="lazy"></a>'
                 if record.get("asset") else '<div class="pending">მზადდება</div>')
        note='<small class="issue">ალფა გადასამოწმებელია</small>' if record.get("inner_circle_alpha_below_250",0) else ''
        items.append(f'<figure>{picture}<figcaption>{name}{note}</figcaption></figure>')
    silhouettes=''.join(f'<figure><img src="{url(p["asset"])}" alt="{html.escape(p["name_ka"])}" loading="lazy"><figcaption>{html.escape(p["name_ka"])}</figcaption></figure>' for p in placeholders)
    ready=sum(bool(r.get("asset")) for r in records)
    markup='''<!doctype html><html lang="ka"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>პერსონაჟები • ფერადი მანგა</title><style>
    *{box-sizing:border-box}body{margin:0;padding:24px;background:#F6F1E4;color:#203D37;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans Georgian",sans-serif}main{max-width:1500px;margin:auto}h1{font-size:26px}p{line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:20px}figure{margin:0;text-align:center}figure img{width:100%;height:auto;aspect-ratio:1;object-fit:contain}figcaption{padding:9px 0;font-size:17px}.pending{aspect-ratio:1;display:grid;place-items:center;border:1px solid #A58958;border-radius:50%;color:#647168}.issue{display:block;color:#874B40;font-size:13px}details{margin-top:34px}summary{padding:12px 0;cursor:pointer}.small{grid-template-columns:repeat(auto-fit,minmax(130px,1fr))}a{color:inherit}</style><main>
    <h1>პერსონაჟები • ფერადი მანგა</h1>'''
    markup+=f'<p>მზადაა {ready} / 21 პორტრეტი. სურათზე დაჭერით იხსნება სრული ზომის ფაილი.</p><div class="grid">'+''.join(items)+'</div>'
    markup+='<details><summary>14 სილუეტი — შენარჩუნებული ფაილები</summary><div class="grid small">'+silhouettes+'</div></details></main></html>'
    path.write_text(markup)


def selected_prompts(records,stamp):
    """Keep final-version receipts authoritative over the initial prompt plan."""
    entries=[]
    for record in records:
        if not record.get("asset"):continue
        receipt_path=record.get("generation_receipt")
        receipt=json.loads((ROOT/receipt_path).read_text()) if receipt_path else {}
        entries.append({
            "character_id":record["character_id"],"name_ka":record["name_ka"],
            "asset":record["asset"],"revision":record["revision"],
            "sha256":record.get("sha256"),"generation_receipt":receipt_path,
            "prompt":receipt.get("prompt"),"references":receipt.get("references",[]),
            "tool":receipt.get("tool"),"mode":receipt.get("mode"),
            "visual_review":receipt.get("visual_review","pending"),
            "processing":receipt.get("processing"),
        })
    return {"date":stamp,"selection_rule":"Prompts and references are copied from the generation receipt for the selected highest-version PNG; rejected versions are excluded.",
            "portrait_count":len(entries),"entries":entries}


def package(records,prompts_path,readme_path,zip_path):
    # ZIP_STORED preserves each PNG's exact native bytes; no image processing.
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_STORED) as archive:
        for record in records:
            if record.get("asset"):
                archive.write(ROOT/record["asset"],f'{record["character_id"]}.png')
        archive.write(prompts_path,prompts_path.name)
        archive.write(readme_path,readme_path.name)


def build(allow_partial=False):
    OUT.mkdir(parents=True,exist_ok=True)
    source_hash=sha(SOURCE);source=json.loads(SOURCE.read_text());names=json.loads(COPY.read_text())
    originals=source["portraits"]
    painted=[p for p in originals if p["status"]!="generic_silhouette"]
    placeholders=[p for p in originals if p["status"]=="generic_silhouette"]
    if len(painted)!=21 or len(placeholders)!=14:raise ValueError("Expected21painted+14silhouette source profiles")
    expected_ids={p["character_id"] for p in painted}
    original_checks=[];failures=[];warnings=[];records=[];entries=[]
    for original in originals:
        path=ROOT/original["asset"]
        actual=sha(path) if path.is_file() else None
        okay=actual==original["sha256"]
        original_checks.append({"character_id":original["character_id"],"asset":original["asset"],"expected_sha256":original["sha256"],"actual_sha256":actual,"unchanged":okay})
        if not okay:failures.append(f'Original asset changed or missing:{original["asset"]}')
        if original["status"]=="generic_silhouette":
            entries.append(copy.deepcopy(original));continue
        cid=original["character_id"];revision,path=newest(cid)
        record={"character_id":cid,"name_ka":names[cid]["name"],"short_name_ka":names[cid].get("short_name",names[cid]["name"]),"original_asset":original["asset"],"asset":relative(path) if path else None,"revision":revision,"errors":[]}
        if path:
            try:record.update(inspect_png(path));record.update(bytes=path.stat().st_size,sha256=sha(path))
            except Exception as error:record["errors"].append(str(error))
            receipt=find_receipt(cid,revision)
            record["generation_receipt"]=relative(receipt) if receipt else None
            if receipt:
                try:
                    receipt_data=json.loads(receipt.read_text())
                    if receipt_data.get("sha256") and receipt_data["sha256"]!=record.get("sha256"):
                        record["errors"].append("generation receipt SHA mismatch")
                except Exception as error:record["errors"].append(f"receipt:{error}")
            else:warnings.append(f"No selected-version generation receipt yet:{cid}-v{revision}")
        else:record["errors"].append("missing generated manga portrait")
        failures.extend(f'{cid}:{error}' for error in record["errors"])
        records.append(record)
        entries.append({**copy.deepcopy(original),"asset":record["asset"],"revision":revision,
            "sha256":record.get("sha256"),"status":"manga_color_portrait" if record["asset"] else "missing_manga_asset",
            "original_asset":original["asset"],"original_revision":original["revision"],
            "name_ka":record["name_ka"],"short_name_ka":record["short_name_ka"],
            "pixel_dimensions":record.get("pixel_dimensions"),"generation_receipt":record.get("generation_receipt")})
    ready_ids={r["character_id"] for r in records if r["asset"]}
    missing=sorted(expected_ids-ready_ids)
    assert len(entries)==35 and len(records)==21
    assert [e for e in entries if e["status"]=="generic_silhouette"]==placeholders
    assert sha(SOURCE)==source_hash,"Original portrait manifest changed during catalog build"
    status="passed" if not failures else ("partial" if allow_partial else "failed")
    stamp=datetime.now(ZoneInfo("Asia/Tbilisi")).isoformat()
    prompts_path=OUT/"selected-prompts.json"
    write_json(prompts_path,selected_prompts(records,stamp))
    manifest={"date":stamp,"style":"manga-color","selection_rule":"Highest numbered {id}-vN.png in assets/characters/manga-color; 14 original silhouettes retained without changes.","original_manifest":relative(SOURCE),"original_manifest_sha256":source_hash,"portraits":entries,"artwork_counts":{"painted_portraits":21,"available_manga_portraits":len(ready_ids),"generic_silhouettes":14,"front_assets":35},"complete":not missing,"validation_status":status,"prompt_set":relative(prompts_path)}
    manifest_path=OUT/"portrait-manifest.json";write_json(manifest_path,manifest)
    alternate_path=HERE.parent/"portrait-manifest.manga-color.json"
    alternate_path.write_bytes(manifest_path.read_bytes())
    gallery_path=OUT/"gallery.html"
    display_placeholders=[{**p,"name_ka":names[p["character_id"]]["name"]} for p in placeholders]
    gallery(records,display_placeholders,gallery_path)
    sheet_path=OUT/"contact-sheet.png";contact_sheet(records,sheet_path)
    readme_path=OUT/"README.md"
    original_count=sum(p["unchanged"] for p in original_checks)
    readme_path.write_text(f'''# ფერადი მანგის პორტრეტები

მზადაა {len(ready_ids)} პორტრეტი 21-დან. გალერეა: `gallery.html`; ერთიანი ხედი: `contact-sheet.png`.

არჩეულია თითოეული პერსონაჟის უდიდესი ვერსიის ნომრის მქონე ფაილი. საწყისი 35 ფაილის საკონტროლო ჯამი გადამოწმებულია: უცვლელია {original_count} / 35. 14 სილუეტის ჩანაწერი და ფაილის მისამართი ზუსტად შენარჩუნებულია.

`portrait-manifest.json` შეიცავს 35 ჩანაწერს. `selected-prompts.json` შეიცავს მხოლოდ არჩეული ვერსიების ინსტრუქციებს, წყაროებსა და შემოწმების სტატუსს.

`manga-color-portraits-21.zip` შეიცავს {len(ready_ids)} არჩეულ სურათს, ორიგინალი ხარისხით და პიქსელების შეუცვლელად; არქივში ფაილის სახელი პერსონაჟის იდენტიფიკატორია. ინსტრუქციები და ეს ფაილიც თან ერთვის.

გამჭვირვალე გარე კუთხეები აუცილებელი არ არის. გამოყენებისას პორტრეტი წრიულად მოიჭრას. შიდა წრე გაუმჭვირვალე უნდა იყოს. ავტომატური შემოწმების შედეგებია `validation.json`-ში, ფაილების ზომები და საკონტროლო ჯამები კი `build-manifest.json`-ში.
''')
    zip_path=OUT/"manga-color-portraits-21.zip"
    package(records,prompts_path,readme_path,zip_path)
    artifacts=(manifest_path,alternate_path,gallery_path,sheet_path,prompts_path,readme_path,zip_path)
    validation={"date":stamp,"status":status,"allow_partial":allow_partial,"expected_painted_ids":sorted(expected_ids),"selected_painted_ids":sorted(ready_ids),"missing_painted_ids":missing,"portrait_checks":records,"original_asset_checks":original_checks,"originals_verified_count":original_count,"silhouette_count":14,"silhouette_entries_exactly_preserved":True,"alpha_policy":"Opaque RGB or RGBA outer corners allowed; all alpha-bearing new portraits must have 0 pixels below 250 within radius 0.43*min(size). Original portraits and silhouettes excluded from new alpha QA.","visual_review_note":"Structural checks do not replace inspection of style, identity and artwork lettering.","failures":failures,"warnings":warnings,"outputs":[info(p) for p in artifacts]}
    validation_path=OUT/"validation.json";write_json(validation_path,validation)
    inputs=[SOURCE,COPY,Path(__file__)]+([HERE/"prompts.json"] if (HERE/"prompts.json").is_file() else [])
    inputs+=[ROOT/r["generation_receipt"] for r in records if r.get("generation_receipt")]
    build_manifest={"date":stamp,"status":status,"source_inputs":[info(p) for p in inputs],"outputs":[info(p) for p in (*artifacts,validation_path)],"portrait_count":21,"available_portrait_count":len(ready_ids),"preserved_silhouette_count":14,"all35_original_assets_unchanged":all(p["unchanged"] for p in original_checks),"selected_assets":[{k:r[k] for k in ("character_id","asset","revision","sha256","bytes") if k in r} for r in records]}
    write_json(OUT/"build-manifest.json",build_manifest)
    print(json.dumps({"status":status,"available":len(ready_ids),"valid":sum(not r["errors"] for r in records),"missing":missing,"alpha_holes":{r["character_id"]:r.get("inner_circle_alpha_below_250") for r in records if r.get("inner_circle_alpha_below_250")},"gallery":relative(gallery_path),"contact_sheet":relative(sheet_path)},ensure_ascii=False))
    if failures and not allow_partial:raise SystemExit("Catalog validation failed; seeoutput/character-portraits-manga-color/validation.json")
    return validation


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-partial",action="store_true",help="Produce progress proofs while portraits or fixes are still being generated")
    build(parser.parse_args().allow_partial)
