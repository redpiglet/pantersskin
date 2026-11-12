# Character portrait discs

Circular **30 mm** Georgian character tokens for moving across the painted realm map. They reuse the exact selected portrait medallions from the A5 character cards, including their painted gold borders. Georgian short names sit inside each circular cut line; full names appear below the discs as a cutting-sheet reference.

## Printable files

- [Complete set, 35 discs on two A4 pages](../../output/character-tokens/pantersskin-character-tokens-ka-30mm-a4.pdf): page 1 has the 21 painted portraits; page 2 has the 14 existing silhouette placeholders.
- [Painted portraits only, 21 discs on one A4 page](../../output/character-tokens/pantersskin-character-tokens-ka-painted-21-30mm-a4.pdf).
- [Painted sheet preview](../../output/character-tokens/preview-1.png) and [supplemental silhouette preview](../../output/character-tokens/preview-2.png).

Print **A4, actual size / 100%, single-sided**. Disable fit-to-page scaling. Measure the 30 mm control bar before cutting. Mount the print on thin card and cut on the fine outer circular outlines. The names stay on the discs after cutting; no ribbon or tab extends beyond their round shape. The files contain fronts only and require no reverse-side alignment.

The complete set matches all 35 profiles. Silhouettes are existing placeholders, not new individual portraits. The painted **ხვარაზმშას ძე** is the prince; the silhouette **ხვარაზმშა** is his father. They remain separate characters. The tokens identify characters without assigning them a fixed home realm or adding game rules.

## Sources and reproduction

- Selected artwork and hashes: `../character-deck/portrait-manifest.json`.
- Georgian names: `../character-deck/display-copy.ka.json` (`short_name` on the disc; `name` below it).
- Dimensions and palette: `production-spec.json`.
- Export inventory and exact token positions: `../../output/character-tokens/build-manifest.json`.

All original PNG artwork remains unchanged. The PDF embeds 600 px versions of the same centered, complete medallions at a printed portrait diameter of 29 mm, approximately 526 dpi. The fine outer cutting contour is exactly 30 mm in diameter. Type and cut lines remain vector artwork.

Rebuild with the project's Python runtime and ReportLab/Pillow:

```sh
python3 print-and-play/character-tokens/build_tokens.py
```

The separate older `realm-map-and-tokens` package is preserved.
