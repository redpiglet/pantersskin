# 7-Realm Map Board & Character / Item Tokens (Georgian Edition)

This package provides the tabletop board game components that pair with the **21-card Georgian A5 Character Deck**:

1. **7-Realm Map Board (`pantersskin-realm-map-ka-a3.pdf` & `pantersskin-realm-map-ka-a4-split.pdf`)**
   - Depicts all **7 Realms** of *The Knight in the Panther's Skin* (`1. არაბეთი`, `2. უდაბნო და დევთა ქვაბი`, `3. ინდოეთი`, `4. ხატაეთი`, `5. მულღაზანზარი`, `6. გულანშარო`, `7. ქაჯეთის ციხე`).
   - Each realm contains **circular 28 mm token slots** (`ფიშკა 1..6`) with starting setup hints for home characters and open slots for visiting travelers and carried items.
   - Connects realms via **Land Routes (სახმელეთო გზა)** and **Sea Routes (საზღვაო გზა)**.
   - Includes a bottom **10-Stage & 65-Chapter Progression Track (`თავები 1–65`)** that directly matches the 65-chapter presence bar (`თავებში`) on the back of every A5 character card.

2. **Character, Item, Bond & Tracker Tokens (`pantersskin-tokens-and-guide-ka-a4.pdf`)**
   - **Page 1:** All **21 Painted Character Medallion Tokens** (`Ø 28 mm`) with realm-colored outer rings, antique-gold inner rims, and Georgian name ribbons, plus 3 progression markers (`თავის მაჩვენებელი`, `ეტაპის მაჩვენებელი`, `მოქმედება I`).
   - **Page 2:**
     - **8 Key Item & Epistle Tokens (`Ø 28 mm`):** `ნესტანის წერილი + რიდის კალთა`, `ავთანდილის ანდერძი`, `ცნობა ფრიდონთან`, `ფატმანის წერილი`, `ვეფხის ტყავი`, `დევთა სამი აბჯარი`, `თინათინის ნიშანი`, `ქაჯეთის 3 კარიბჭე`.
     - **8 Relationship / Bond Tokens (`Ø 28 mm`):** `მიჯნურობა`, `დაძმობილება`, `მეფობა / ყმობა`, `ერთგულება`, `ეპისტოლე`, `ბრძოლა`, `დახსნა`, `თანაგრძნობა`.
     - **4 Additional Action & Courier Markers:** `მოქმედება I`, `მოქმედება II`, `მოქმედება III`, `ხომალდი / მაცნე`.
   - **Page 3:** Complete Georgian tabletop rules and setup guide.

3. **All-in-One A4 Print Packet (`pantersskin-board-game-complete-ka-a4.pdf`)**
   - Combines the **2× A4 Split Map Panels** (Pages 1–2), **2× A4 Token Cutout Sheets** (Pages 3–4), and **1× A4 Rules Sheet** (Page 5) into a single 5-page single-sided A4 document.

## Rebuild

```sh
python3 print-and-play/character-deck/build_painted_21.py
python3 print-and-play/realm-map-and-tokens/build_realm_board.py
```
