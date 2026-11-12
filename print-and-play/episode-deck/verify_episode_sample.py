#!/usr/bin/env python3
"""Independently audit selected A5 episode cards against the current JSON.

No builder modules are imported. Source text, actual PDF glyphs, native image
pixels, form placement and the new24-episode scale are inspected independently.
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
from pypdf.generic import ContentStream

from verify_episode_deck import (MM, check_front_graphics, check_source,
    expected_action, form_instances, fragments, front_image_instances, norm,
    page_size, require)

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"print-and-play/episode-deck/episode-cards.ka.json"
ILLUSTRATIONS=ROOT/"output/episode-illustrations/illustration-manifest.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_filename(numbers):
    return "pantersskin-episode-cards-ka-a5-episodes-"+"-".join(f"{n:02d}" for n in numbers)+".pdf"


def inside(box,w=148,h=210,margin=2.6):
    return box[0]>=margin-.03 and box[1]>=margin-.03 and box[2]<=w-margin+.03 and box[3]<=h-margin+.03


def glyph_box(char):
    return [float(char[k])/MM for k in ("x0","y0","x1","y1")]


def in_region(page,box):
    x0,y0,x1,y1=[float(n)*MM for n in box]
    chars=[ch for ch in page.chars if x0-.04<=(ch["x0"]+ch["x1"])/2<=x1+.04
           and y0-.04<=(ch["y0"]+ch["y1"])/2<=y1+.04]
    return "".join(ch["text"] for ch in chars)


def all_fonts_embedded(reader):
    found={}
    def visit(resources):
        resources=resources.get_object()
        for key,ref in resources.get("/Font",{}).items():
            f=ref.get_object()
            # The unused default Helvetica resource is not printed.
            if str(f.get("/BaseFont"))=="/Helvetica":
                continue
            for child in f.get("/DescendantFonts",[f]):
                child=child.get_object();descriptor=child.get("/FontDescriptor")
                require(descriptor is not None,f"Missing embedded font descriptor: {key}")
                descriptor=descriptor.get_object()
                require(any(k in descriptor for k in ("/FontFile","/FontFile2","/FontFile3")),
                        f"Unembedded font: {key}")
            found[str(f.get("/BaseFont",key))]="embedded"
        for ref in resources.get("/XObject",{}).values():
            obj=ref.get_object()
            if obj.get("/Resources"):visit(obj["/Resources"])
    for page in reader.pages:visit(page["/Resources"])
    require(found,"No embedded fonts found")
    return found


def illustration_manifest_path(path=None):
    path=Path(path or ILLUSTRATIONS)
    return (path if path.is_absolute() else ROOT/path).resolve()


def selected_scene(episode,illustration_path=None):
    manifest=json.loads(illustration_manifest_path(illustration_path).read_text())
    candidates=[a for a in manifest["selected_paintings"] if a["id"]==episode["id"]]
    require(len(candidates)==1,f"Expected one selected illustration for {episode['id']}")
    item=candidates[0];path=ROOT/item["asset"]
    require(item["episode_number"]==episode["episode_number"],"Wrong illustration episode")
    require(sha(path)==item["sha256"],f"Selected image SHA mismatch: {path}")
    with Image.open(path) as image:
        rgb=image.convert("RGB")
        dimensions=list(rgb.size);decoded=hashlib.sha256(rgb.tobytes()).hexdigest()
    return {"asset":item["asset"],"sha256":item["sha256"],"dimensions":dimensions,"decoded_rgb_sha256":decoded}


def scene_check(form,reader,episode,illustration_path=None):
    chosen=selected_scene(episode,illustration_path)
    instances=front_image_instances(form,reader)
    require(len(instances)==1,f"Episode {episode['episode_number']}: expected exactly one painted scene")
    item=instances[0];image=item["image"]
    dims=[int(image["/Width"]),int(image["/Height"])]
    require(dims==chosen["dimensions"],"Scene image was resampled or changed")
    require(image.get("/ColorSpace")=="/DeviceRGB" and int(image.get("/BitsPerComponent",0))==8,
            "Expected native8-bit RGB selected painting")
    require(hashlib.sha256(image.get_data()).hexdigest()==chosen["decoded_rgb_sha256"],
            "Embedded scene pixels differ from the selected artwork")
    a,b,c,d,x,y=item["transform"]
    require(a>0 and d>0 and abs(b)<.001 and abs(c)<.001,"Painting is mirrored or rotated")
    require(abs((a/d)/(dims[0]/dims[1])-1)<.0001,"Painting is stretched")
    box=[x/MM,y/MM,(x+a)/MM,(y+d)/MM]
    require(inside(box),"Scene crosses safe card bounds")
    native_fit=min(130/dims[0],81.25/dims[1])
    expected_w,expected_h=dims[0]*native_fit,dims[1]*native_fit
    require(abs(a/MM-expected_w)<.01 and abs(d/MM-expected_h)<.01,
            "Painting does not preserve the native-image fit within the approved130×81.25mm frame")
    graphics=check_front_graphics(form,reader,episode["episode_number"],"A5 selected")
    return {"selected_asset":chosen["asset"],"selected_asset_sha256":chosen["sha256"],
            "image_drawings":1,"native_rgb_pixels_match_selected":True,
            "pixel_dimensions":dims,"actual_image_bbox_mm":box,**graphics}


def episode_scale(form,reader,episode):
    palette=json.loads((ROOT/"print-and-play/episode-deck/production-spec.json").read_text())["palette"]
    rgb=lambda s:[int(s[i:i+2],16)/255 for i in (1,3,5)]
    green,ivory=rgb(palette["green"]),rgb(palette["ivory"])
    stack=[];fill=[0,0,0];path=[];circles=[]
    for args,op in ContentStream(form,reader).operations:
        if op==b"q":stack.append(fill[:])
        elif op==b"Q":fill=stack.pop()
        elif op==b"rg":fill=[float(n) for n in args]
        elif op==b"g":fill=[float(args[0])]*3
        elif op==b"n":path=[]
        elif op in (b"m",b"c",b"l",b"h",b"re"):path.append(([float(n) for n in args],op))
        elif op in (b"B",b"B*",b"f",b"f*",b"S",b"s",b"b",b"b*"):
            kinds=[kind for _,kind in path]
            if kinds in ([b"m",b"c",b"c",b"c",b"c"],[b"m",b"c",b"c",b"c",b"c",b"h"]):
                values=[v for coords,_ in path for v in coords]
                xs,ys=values[::2],values[1::2]
                rx,ry=(max(xs)-min(xs))/2,(max(ys)-min(ys))/2
                if abs(rx-ry)<.02 and rx>1:
                    require(op in (b"B",b"B*",b"f",b"f*"),"Episode scale circle has no explicit fill")
                    active=max(abs(a-b) for a,b in zip(fill,green))<.00002
                    inactive=max(abs(a-b) for a,b in zip(fill,ivory))<.00002
                    require(active or inactive,"Wrong episode scale circle colour")
                    circles.append({"x":(min(xs)+max(xs))/2,"y":(min(ys)+max(ys))/2,"active":active})
            path=[]
    rows={}
    for circle in circles:rows.setdefault(round(circle["y"],2),[]).append(circle)
    timelines=[row for row in rows.values() if len(row)==24]
    require(len(timelines)==1,f"Episode {episode['episode_number']}: expected one row of24 actual scale circles")
    require(len(circles)==24,f"Episode {episode['episode_number']}: found extra circular scale marks")
    timeline=sorted(timelines[0],key=lambda p:p["x"])
    mask=[i+1 for i,circle in enumerate(timeline) if circle["active"]]
    require(mask==[episode["episode_number"]],f"Episode scale mask is {mask}; expected the episode's own number")
    return {"actual_circle_paths":24,"actual_filled_episodes":mask,"actual_row_y_mm":timeline[0]["y"]/MM}


def exact_field(normalized,text,location):
    require(norm(expected_action(text)) in normalized,f"Missing or altered exact source field: {location}")


def verify(output_dir,episode_numbers=None,illustration_path=None):
    output_dir=Path(output_dir).resolve()
    numbers=list(episode_numbers or [1,2])
    illustration_path=illustration_manifest_path(illustration_path)
    report={"status":"failed","scope":"selected_a5_episodes","episode_numbers":numbers,
            "source_json":str(SOURCE.relative_to(ROOT)),"source_sha256":sha(SOURCE),
            "illustration_source":str(illustration_path.relative_to(ROOT)) if illustration_path.is_relative_to(ROOT) else str(illustration_path),
            "verification_method":"independent source text, PDF glyph/form/image/path inspection; no builder import"}
    try:
        require(illustration_path.is_file(),f"Missing selected illustration manifest: {illustration_path}")
        report["illustration_manifest_sha256"]=sha(illustration_path)
        source=json.loads(SOURCE.read_text())
        all_episodes=check_source(source)
        require(numbers==sorted(set(numbers)) and all(1<=n<=24 for n in numbers),"Selected episodes must be unique ordered1..24")
        episodes=[all_episodes[n-1] for n in numbers]
        require("ეპიზოდებში" in " ".join(source["gameplay_loop_ka"]),"Source does not specify the new episode scale")
        path=output_dir/selected_filename(numbers)
        require(path.is_file(),f"Missing selected export: {path}")
        reader=PdfReader(path);require(len(reader.pages)==2*len(episodes),"Wrong selected page count")
        manifest_path=output_dir/"build-manifest.json"
        manifest=json.loads(manifest_path.read_text())
        require(illustration_manifest_path(manifest["illustration_source"])==illustration_path,
                "Build manifest uses a different illustration selection")
        require(manifest["illustration_manifest_sha256"]==report["illustration_manifest_sha256"],
                "Build manifest illustration selection SHA mismatch")
        layouts=manifest["layout_metrics"]["A5"]
        report["fonts"]=all_fonts_embedded(reader)
        checks=[]
        with pdfplumber.open(path) as pdf:
            for index,(page,parsed) in enumerate(zip(reader.pages,pdf.pages)):
                episode=episodes[index//2];side="front" if index%2==0 else "back"
                dimensions=page_size(page)
                require(all(abs(a-b)<.015 for a,b in zip(dimensions,(148,210))),f"Page {index+1}: wrong A5 size")
                require(list(page.cropbox)==list(page.mediabox),"Crop box hides card content")
                instances=form_instances(page)
                require(len(instances)==1,"Each selected page must contain exactly one card Form")
                instance=instances[0]
                require(instance["name"].endswith(episode["id"]+"_"+side),"Wrong actual front/back episode Form")
                require(all(abs(a-b)<.001 for a,b in zip(instance["transform"],[1,0,0,1,0,0])),"Card is shifted, rotated or mirrored")
                bounds=[float(n)/MM for n in instance["form"]["/BBox"]]
                require(all(abs(a-b)<.01 for a,b in zip(bounds,[0,0,148,210])),"Card Form bounding box clips content")
                text=page.extract_text() or "";normalized=norm(text)
                latin=sorted({c for c in text if "LATIN" in unicodedata.name(c,"")})
                require(not latin,f"Page {index+1}: printed Latin letters {latin}")
                require(not any("CIRCLED" in unicodedata.name(c,"") and c.isnumeric() for c in text),"Printed circled numerals")
                exact_field(normalized,episode["title_ka"],"title_ka")
                exact_field(normalized,episode["mode_label_ka"],"mode_label_ka")
                fields=[]
                if side=="front":
                    for key in ("token_action_ka",):exact_field(normalized,episode[key],key);fields.append(key)
                    # A selected line can end before the full quatrain's closing
                    # quotation mark (episode02). The complete four source lines
                    # below remain an exact, punctuation-preserving check.
                    unquote=lambda s:re.sub(r'[„“”«»"]',"",s)
                    require(norm(unquote(episode["quote"]["line_ka"])) in norm(unquote(text)),
                            "Missing selected verse line within the full stanza")
                    exact_field(normalized,episode["quote"]["locator_label_ka"],"quote.locator_label_ka")
                    for line in episode["quote"]["full_stanza_ka"].splitlines():exact_field(normalized,line,"full stanza line")
                    fields.append("quote.full_stanza_ka")
                    exact_field(normalized,episode["chapter_range_label_ka"],"chapter_range_label_ka")
                    exact_field(normalized,episode["stanza_range"],"stanza_range")
                else:
                    for key in ("summary_ka","objective_ka"):exact_field(normalized,episode[key],key);fields.append(key)
                    for chapter in episode["chapter_titles_ka"]:exact_field(normalized,chapter["title_ka"],"chapter title")
                    for person in episode["all_chapter_characters"]:
                        require(norm(person["name_ka"]) in normalized or norm(person["short_name_ka"]) in normalized,"Missing participant")
                    for person in episode.get("character_inputs_ka",[]):
                        for key in ("name_ka","role_ka","action_ka","dialogue_ka","cue_ka"):
                            label=f"character_inputs_ka.{person['character_id']}.{key}"
                            exact_field(normalized,person[key],label);fields.append(label)
                    require(norm("ეპიზოდებში 1-24") in normalized,"Missing updated24-episode scale heading")
                    require(norm("თავებში 1-65") not in normalized,"Obsolete65-chapter scale remains")
                for fragment in fragments(page):
                    if re.search(r"[\u10A0-\u10FF\u1C90-\u1CBF]",fragment["text"]):require(fragment["upright"],"Mirrored or inverted Georgian text")
                chars=[ch for ch in parsed.chars if ch["text"].strip()]
                require(chars,"No actual printed glyphs")
                outside=[{"text":ch["text"],"box":glyph_box(ch)} for ch in chars if not inside(glyph_box(ch))]
                require(not outside,f"Page {index+1}: text outside safe card area: {outside[:3]}")
                boxes=layouts[episode["id"]][side]["text_boxes"]
                for box in boxes:
                    require(inside(box["bbox_mm"]),"Declared text region outside safe area")
                    found=in_region(parsed,box["bbox_mm"])
                    require(norm(found)==norm(box["text"]),f"Page {index+1}: text region clipped or overlapped: {box['text']!r} versus {found!r}")
                result={"page":index+1,"episode":episode["episode_number"],"side":side,"size_mm":list(dimensions),
                        "source_fields_verified":fields,"text_regions_verified":len(boxes),"printed_latin_letters":0,
                        "minimum_actual_font_pt":min(float(ch["size"]) for ch in chars),"actual_glyph_bounds_checked":len(chars)}
                if side=="front":result["painting"]=scene_check(instance["form"],reader,episode,illustration_path)
                else:result["timeline"]=episode_scale(instance["form"],reader,episode)
                checks.append(result)
        report["pages"]=checks;report["pdf"]={"file":str(path.relative_to(ROOT)),"pages":len(reader.pages),"bytes":path.stat().st_size,"sha256":sha(path)}
        # Validate any matching output record without assuming a particular
        # builder inventory key beyond its established pdfs list.
        inventory=manifest.get("pdfs",[])
        matching=[item for item in inventory if Path(item["file"]).name==path.name]
        require(len(matching)==1,"Selected PDF missing from build manifest")
        require(matching[0]["sha256"]==sha(path),"Selected PDF manifest SHA mismatch")
        require(matching[0]["pages"]==len(reader.pages),"Selected PDF manifest page count mismatch")
        report["manifest_sha256"]=sha(manifest_path)
        report["source_copy_unchanged"]=sha(SOURCE)==report["source_sha256"]
        report["status"]="independent_selected_episode_verification_passed"
    except Exception as error:
        report["error"]=f"{type(error).__name__}: {error}"
        output_dir.mkdir(parents=True,exist_ok=True)
        (output_dir/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        raise
    (output_dir/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes",type=int,nargs="+",default=[1,2])
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--illustrations",type=Path,default=ILLUSTRATIONS,
                        help="Selected illustration manifest; supports alternate artwork editions")
    args=parser.parse_args()
    out=args.output_dir or ROOT/"output/episode-deck"/("episodes-"+"-".join(f"{n:02d}" for n in args.episodes))
    report=verify(out,args.episodes,illustration_path=args.illustrations)
    print(json.dumps({"status":report["status"],"report":str(out/"validation.json")},ensure_ascii=False))


if __name__=="__main__":main()
