# Painted manuscript map

The painted edition replaces the first map's geometric scenery with a detailed painting, generated using the built-in OpenAI ImageGen tool. Tariel v13 and Nestan v3 supplied the tempera/gouache, mineral-color and antique-gold style references. The earlier map supplied only a spatial composition reference. The painting has no generated lettering: Georgian names and captions are typeset separately.

## Current clean edition

The current map has **no route lines, journey annotations or legend**, as requested. Route display and legend display are disabled in `painted-map-layout.ka.json`; the checked journey records remain in the source JSON.

The selected painting is `assets/maps/painted-realms-v5.png`. Its main-heading area and the clearing beneath Gulansharo were refined with the built-in image tool to match the other painted parchment fields. The main title is centered in open space below the foliage. Gulansharo's name and caption use larger, dark-green lettering positioned fully within its new clearing. All seven realms remain, including inland Kadjeti. There are no added label boxes or text outlines.

## Revised geography edition

The geography and underlying journey data incorporate the primary-source review in [critique-audit.json](critique-audit.json). The previous routed proof visualized these journeys; the current clean edition retains the data but hides the overlays:

- **Gulansharo → Cave** combines sea and inland travel and bypasses Mulghazanzar.
- **Arabia → India** is the overland homecoming. The local source starts in chapter 61 and continues through 62–63; Pridon also accompanies the party.
- **India → Cave** is a narrative summary rather than a direct physical road: Tariel's backstory includes a year's sea search, a visit to Pridon, and further wandering. The JSON records `direct_road: false`, `movement_route: false`, and those intermediate events.
- **Kadjeti** is repainted in dry mountainous hinterland with a winding land approach. The sea crossing followed by land travel on Mulghazanzar → Kadjeti is retained. Coastlines and distances are interpretive; the poem gives no exact modern coordinates.

All ten sourced journeys and the exile summary remain in the source data. Earlier JSON versions are retained in `revisions/before-geography-corrections/`; the preceding routed layout is retained in `revisions/before-clean-labels/`.

## Review and folding proofs

- [Clean painted map PDF](../../output/painted-realm-map-clean/painted-realm-map-ka-592x420.pdf), 592 × 420 mm.
- [Clean A4 folding proof](../../output/painted-realm-map-clean/painted-realm-map-ka-a4-print.pdf): eight A4 map panels followed by the assembly guide.
- [Clean composite preview](../../output/painted-realm-map-clean/painted-map-preview.png).
- [Selected painting](../../assets/maps/painted-realms-v5.png). Earlier paintings v1–v4 and source revisions are preserved; the superseded generated routed proof has been removed.

The same four-column/two-row geometry folds to 148 × 210 mm (A5). Print panels at 100%, single-sided; the ninth page explains trimming, joining and folding. Geographic placement remains a narrative interpretation. Sourced routes and their classifications remain in `route-audit.json`.

## Resolution

The current built-in generations returned **1492 × 1054 pixels**, including the earlier request for a native 3360 × 2384 export. At the full 592 mm map width, the painting is approximately **64 dpi**. These files are **design and folding proofs**, not a high-resolution commercial print master. The Georgian type remains vector-sharp. Pixel editing was performed through the built-in image tool; the selected final PNG is embedded without further retouching or artificial upscaling. A higher-resolution artwork export is needed for sharp large-format production.

## Exact prompts and provenance

- [Initial generation request](painted-generation-request.json): complete prompt and three reference-image paths.
- [Resolution refinement request](painted-high-resolution-request.json): complete second prompt, preserving the painting's composition.
- [Initial inland correction](painted-geography-correction-request.json) and [stronger hinterland correction](painted-geography-correction-request-v2.json): complete built-in ImageGen edit prompts. The first repaint still read as coastal, so the second moved the lower coastline west and made the entire lower-right panel dry country.
- [Label readability refinement](painted-label-readability-request.json): exact two-area edit prompt, reference image and selected output. The artwork was edited through the built-in image tool; all lettering remains separately typeset.
- `../../output/painted-realm-map-clean/build-manifest.json`: selected artwork hash, native pixels, actual placement/DPI, text bounds, tile geometry, route/legend visibility and PDF hashes.
- `painted-map-layout.ka.json`: editable label positions and disabled route/legend display settings. It adds no primitive landscape, diagram nodes, label pills or legend box to the painting.

## Rebuild

```sh
python3 print-and-play/foldable-realm-map/build_painted_map.py --art assets/maps/painted-realms-v5.png --out output/painted-realm-map-clean
```

Earlier character cards, native portrait PNGs, the first map and the separate realm-map/token package are preserved.
