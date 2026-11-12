"""Copy an unchanged built-in generated PNG and record its prompt and provenance."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('character_id')
    parser.add_argument('generated_png', type=Path)
    parser.add_argument('--revision', type=int, default=1)
    parser.add_argument('--override-entry', type=Path)
    args = parser.parse_args()
    plan_path = Path(__file__).with_name('prompts.json')
    plan = json.loads(plan_path.read_text())
    entry = next(e for e in plan['entries'] if e['id'] == args.character_id)
    if args.override_entry:
        entry = json.loads(args.override_entry.read_text())
        plan_path = args.override_entry.resolve()
    if args.revision != 1:
        entry = dict(entry, asset=f'assets/characters/manga-color/{args.character_id}-v{args.revision}.png')
    destination = ROOT / entry['asset']
    source = args.generated_png.resolve()
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise SystemExit(f'Refusing to overwrite a different image: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.resolve() != source:
        shutil.copyfile(source, destination)
    with Image.open(destination) as im:
        im.verify()
    with Image.open(destination) as im:
        pixels = list(im.size)
        mode = im.mode
        alpha = im.getchannel('A').getextrema() if 'A' in im.getbands() else None
    receipt = {
        'character_id': args.character_id,
        'date': datetime.now(timezone.utc).isoformat(),
        'tool': 'built-in image_gen.imagegen',
        'mode': 'built-in',
        'asset': entry['asset'],
        'source_generated_png': str(source),
        'references': entry['references'],
        'prompt': entry['prompt'],
        'prompt_set': str(plan_path.relative_to(ROOT)),
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'bytes': destination.stat().st_size,
        'native_pixels': pixels,
        'image_mode': mode,
        'alpha_extrema': alpha,
        'processing': 'Copied unchanged; native pixels and alpha preserved',
        'visual_review': 'pending'
    }
    receipt_path = Path(__file__).with_name('receipts') / f'{args.character_id}-v{args.revision}.json'
    receipt_path.parent.mkdir(exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k:receipt[k] for k in ['character_id','asset','native_pixels','image_mode','alpha_extrema']}))

if __name__ == '__main__':
    main()
