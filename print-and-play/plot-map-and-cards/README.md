# Panther's Skin: plot map and character cards

This revision is an explanatory tabletop map of the whole plot, with character reference cards. The map shows the poem's telling order; it also labels the earlier stories told by Tariel and Fatman. The character cards link people and relationships to numbered places on that map.

## The printed set

- **Two A4 map panels:** read stops 1-5 on the left, then 6-10 on the right. Place them side by side.
- **Two A4 card sheets:** twelve character cards, six per sheet. Cut only the cards.
- A separate **one-page A3 map** is available for a larger printer or on-screen overview.

Print single-sided at actual size. All four packet sheets are A4 portrait. Names, numbers, and dashed outlines carry the meaning in black and white too.

## Use it together

Choose a few character cards and place them beside the map. Follow their numbered plot connections, set their cards near the relevant scenes, and compare where their paths meet. Keep all twelve cards available as references. Selection changes the focus of the retelling; all characters remain in the story.

The board presents the plot openly. Each card explains the person's role, contribution to the plot, key relationships, and corresponding map stops. No one needs to answer questions, spend resources, or meet a turn target.

The first cards cover Avtandil, Tariel, Nestan, Tinatin, Asmat, Pridon, and Fatman. Supporting cards cover Rostevan, Shermadin, Parsadan, Davar, and Usen.

## How the map explains time

The numbered arrows follow the order in which the poem tells the story. Two dashed boxes show earlier events retold later:

1. **Stop 3:** Tariel's account of his life in India, his love for Nestan, their separation, and the beginning of his search.
2. **Stop 6:** Fatman's account of what happened to Nestan before Avtandil reached Gulansharo.

These are not extra journeys undertaken by Avtandil in the present. Place labels identify narrative settings rather than exact geography.

## Sources and scope

The source is the existing project corpus, especially `data/chapters/chapter-02.json` through `chapter-64.json`. Each map stop and character card carries chapter references. The ten map stops compress the plot; the prologue, epilogue, several secondary encounters, and detailed commentary are outside this overview. The portraits are embedded unchanged from `assets/characters`.

The earlier letter-and-reunion game prototype is preserved separately. This set replaces its travel-and-timing focus with a plot overview and explanatory character cards.

## Edit and rebuild

- `map.json`: map titles, narration, places, cast, and chapter references.
- `cards.json`: character content and numbered map appearances.
- `build_set.py`: printable layout and PDF generation.

The builder requires ReportLab and Pillow. It writes the A4 packet and A3 map under `output/pdf`.
