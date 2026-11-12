# Character deck

The current edition contains 35 Georgian character cards, 148 × 210 mm (A5). Each front has a portrait, name, role and introduction; each back has a compact story, interpretation, relationship portraits and a 65-chapter scale.

The 21 painted portraits use the latest selected versions. The remaining 14 characters have generated generic silhouette PNGs on their own fronts, with the portrait-pending label retained. These silhouettes indicate roles without asserting a finished individual likeness. The relationships section shows only characters with selected painted portraits; generic silhouettes never appear as contact thumbnails. Full interaction lists remain in the source JSON. The same selected painted portrait is used on its own card and in every displayed relationship.

The chapter heading is **„თავებში“**. The **„ჩანს / არ ჩანს“** legend is omitted. The filled and outlined circles, chapter numbers, major ticks every ten chapters, minor ticks every five and endpoint markers remain.

## Current A5 Georgian outputs

- `../../output/character-cards-ka-a5/pantersskin-character-cards-ka-a5.pdf`: 70 native A5 pages, front then back for each character.
- `../../output/character-cards-ka-a5/pantersskin-character-cards-ka-a5-a4-duplex.pdf`: 70 A4 portrait pages, one centered A5 card per sheet, alternating front and matching back. 35 sheets.
- `../../output/character-cards-ka-a5/pantersskin-character-cards-ka-a5-review.pdf`: 35 A3 landscape pages showing both sides together at actual size.
- `../../output/character-cards-ka-a5/build-manifest.json`: output inventory, card dimensions, print placement, portrait counts and layout measurements.

## A5 home printing

Use the current **A4 duplex PDF**. Select **A4, portrait, actual size / 100%, double-sided, flip on long edge**. Each A5 card is centered on its sheet; its back uses the same centered position. The file includes crop marks and requires no multiple-pages-per-sheet or booklet setting.

Print pages 1–2 first to check alignment and orientation. The front and reverse should have the same character name. Cut along the card boundaries using the crop marks. Rounded corners are optional.

Two exact A5 cards fit A4 landscape mathematically, but leave no top or bottom margin for ordinary printers or crop marks. The one-card-per-sheet file preserves the full A5 dimensions with comfortable printing margins.

## Data and production

- Main content: `../../data/character-cards.json`. Full overviews, original insights, actions, relationships and source notes are retained there.
- Georgian printed text: `display-copy.ka.json`. This contains names, avatar names, realms, roles, front descriptions, plot summaries and interpretations for all 35 cards.
- English printed text: `display-copy.json`.
- Georgian labels and print captions: `locale.ka.json`.
- Current size and display rules: `deck-settings.json`. A5 is the default; contacts without portraits are filtered only when rendering.
- Selected images and hashes: `portrait-manifest.json`.
- Interaction evidence: `../../data/character-interactions.json`. The canonical lists are unchanged by display filtering.
- Chapter appearances: `../../data/character-chapter-presence.json`, with scene-based notes for all 65 chapters. Circles show appearances, not citation counts.

The Sea King's son has no depicted encounter or scene appearance: his proposed marriage is arranged while he is absent. Rustaveli's card marks the explicit author frame in chapters 1 and 65; narration does not create fictional encounters.

The Georgian translation was produced in three batches and checked by a separate editorial pass against the source content and Georgian poem names. Compact summaries preserve readable text. Full source commentary remains in the main JSON.

Generate the current Georgian edition with Python 3, ReportLab and Pillow:

```sh
python3 print-and-play/character-deck/build_deck.py --language ka
```

`deck-settings.json` selects A5 by default. It can also be requested explicitly:

```sh
python3 print-and-play/character-deck/build_deck.py --language ka --card-size A5
```

For a quick layout check without generating PDFs:

```sh
python3 print-and-play/character-deck/build_deck.py --language ka --check-layout
```

Add `--overviews` to generate optional complete-cast overview PDFs. The renderer checks image hashes, canonical reciprocal interaction IDs, chapter masks and text bounds. Displayed relationship lists can be asymmetric because a character with a generic silhouette front may display another character's painted portrait while being omitted from that character's gallery. Artwork status, not merely the existence of an image file, determines contact-thumbnail eligibility.

## Fonts and image resolution

`prepare_georgian_fonts.py` creates regular, semibold and display instances of the installed macOS SF Georgian font in the temporary build cache. It requires FontTools. Arial supplies numerals and punctuation absent from that font; Georgian letters and Mtavruli titles are embedded. Georgian compound names wrap at their hyphens.

A5 PDFs embed portraits at up to **1200 pixels**, providing about **314 dpi** at the large medallion's printed size. A6 uses up to **900 pixels**, about **332 dpi**. Original full-resolution PNGs and installed font files remain unchanged. English rendering uses Arial and Georgia from macOS's Supplemental fonts directory.

## Previous A6 editions

The previously generated A6 files remain available separately. Their earlier layouts may include the relationships and chapter legend used at that stage.

### Georgian A6

- `../../output/character-cards-ka/pantersskin-character-cards-ka-a6.pdf`: 70 native A6 pages.
- `../../output/character-cards-ka/pantersskin-character-cards-ka-a4-duplex.pdf`: 36 A4 landscape pages, two A6 cards per sheet; print at 100%, duplex, flip on short edge.
- `../../output/character-cards-ka/pantersskin-character-cards-ka-review.pdf`: 35 A4 landscape review pages.
- `../../output/character-cards-ka/build-manifest.json`: earlier Georgian build details.

### English A6

- `../../output/character-cards/pantersskin-character-cards-a6.pdf`: 70 native A6 pages.
- `../../output/character-cards/pantersskin-character-cards-a4-duplex.pdf`: 36 A4 landscape pages, two A6 cards per sheet; print at 100%, duplex, flip on short edge.
- `../../output/character-cards/pantersskin-character-cards-review.pdf`: 35 A4 landscape review pages.
- `../../output/character-cards/pantersskin-character-cards-fronts-overview.pdf` and `../../output/character-cards/pantersskin-character-cards-backs-overview.pdf`: previous complete-cast visual overviews.
- `../../output/character-cards/build-manifest.json`: earlier English build details.

To regenerate A6 at 105 × 148 mm using the **current** portrait-only relationships and simplified chapter heading:

```sh
python3 print-and-play/character-deck/build_deck.py --language ka --card-size A6
```

This selects the A6 output directory and A4 landscape two-up printing format; it applies the current display rules rather than recreating the historical legend and silhouette galleries. Use `--language en --card-size A6` for English.
