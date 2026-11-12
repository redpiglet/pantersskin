# Foldable realm map

A Georgian print-and-play map of the seven requested settings: Arabia, Wilderness/Cave, India, Khataeti, Mulghazanzar, Gulansharo and Kadjeti. Its ivory, dark green and antique-gold treatment follows the character cards. It is a map component, with no added rules, questions, resources or scoring tracks.

The **current painted edition, clearer labels and geography corrections** are documented in [PAINTED-MAP.md](PAINTED-MAP.md). The current map hides all route lines, journey annotations and the legend. The files listed immediately below are the earlier schematic proof, preserved for comparison.

## Files

- [Full-size vector map](../../output/foldable-realm-map/samqaro-realm-map-ka-592x420.pdf): one page, **592 × 420 mm**.
- [A4 print pack](../../output/foldable-realm-map/samqaro-realm-map-ka-a4-print.pdf): pages **1–8 are map panels**; page **9 is the assembly/folding guide**.
- [Separate folding guide](../../output/foldable-realm-map/samqaro-realm-map-ka-folding-guide.pdf).
- [Map preview](../../output/foldable-realm-map/realm-map-preview.png).

The map is 2 mm narrower than ISO A2 so four equal columns fold to exactly **148 × 210 mm (A5)**, matching the character-card format. A print shop can place it at 100% on A2 with 1 mm horizontal margins.

## Home printing and folding

Print the first eight pages of the A4 pack **single-sided, A4 portrait, at 100% / actual size**. The 148 × 210 mm panel cores sit inside safe page margins, with 8 mm of duplicate artwork around each core for alignment and trimming. Cut at the corner crop marks and discard that surrounding duplicate artwork.

Arrange panels 1–4 across the top and 5–8 across the bottom. Match the artwork and join the panel edges on the reverse with thin, flexible tape. Fold the bottom row behind the top, then accordion-fold the resulting long strip into four panels. No center slit is required. The separate guide shows the panel order and Georgian instructions.

The master has small fold ticks at its edges. Realm names, captions and key labels are at least 4 mm away from the fold lines; there are no long construction lines through the finished map.

## Story and geography

This is an illustrated narrative map: coastlines, terrain, placement and distances are schematic. The earlier schematic PDF shows eight connections. The current source retains all ten sourced journeys plus a distinct narrative summary of Tariel's long journey from India to the caves. The previous routed painted proof displays them; the current clean painted edition hides all routes and the legend. The data does not assert shared borders or exact sailing lanes.

`route-audit.json` records the checked primary Georgian source spans. In particular, the journey from Mulghazanzar to Kadjeti includes a sea crossing (chapter 54, project stanza 1390). Nestan's sea route passes the Mulghazanzar coast as a witnessed waypoint. The earlier schematic draft omitted two secondary journeys; both are retained in the current source data and the previous routed proof. The journey data summarizes travel rather than reproducing every travelling episode chronologically.

`critique-audit.json` records the later primary-source review. The source restores Gulansharo–cave and Arabia–India and adds the explicitly non-road India–cave summary. The painting places Kadjeti in dry mountainous hinterland. No sourced route in the current data is disabled; the separate painted layout switches off their visual display.

The earlier `realm-map-and-tokens` package is preserved separately. This map does not reuse its unverified chapter ranges or land-only classification of the Kadjeti expedition.

## Rebuild

```sh
python3 print-and-play/foldable-realm-map/build_map.py
```

Requires ReportLab and the existing Georgian font-preparation helper from the character-deck package. All board art, labels, lines and landmarks are vector elements; there are no external image dependencies. `map-data.ka.json` holds the map content; `production-spec.json` holds print/fold geometry. The build manifest records labels, panel bounds and file hashes.
