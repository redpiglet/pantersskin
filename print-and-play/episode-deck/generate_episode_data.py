#!/usr/bin/env python3
"""Generate and validate the Episode Deck data files (JSON + CSV) for Vepkhistkaosani.

Links the 65-chapter poem corpus (`data/chapters/chapter-*.json`),
the 65-chapter character-presence bar on the A5 Character Cards
(`data/character-chapter-presence.json` & `print-and-play/character-deck/display-copy.ka.json`),
the 30 mm Character Portrait Tokens (`print-and-play/character-tokens/`),
and the 7-Realm Foldable Map (`print-and-play/foldable-realm-map/map-data.ka.json`).
"""

import csv
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from episode_data_enrichments import EPISODE_ENRICHMENTS

CHAPTERS_INDEX = json.loads((ROOT / "data/chapters-index.json").read_text())["chapters_index"]
PRESENCE_DATA = json.loads((ROOT / "data/character-chapter-presence.json").read_text())["chapters"]
DISPLAY_COPY = json.loads((ROOT / "print-and-play/character-deck/display-copy.ka.json").read_text())
PORTRAIT_MANIFEST = json.loads((ROOT / "print-and-play/character-deck/portrait-manifest.json").read_text())
MAP_DATA = json.loads((ROOT / "print-and-play/foldable-realm-map/map-data.ka.json").read_text())

CHAPTER_BY_NUM = {c["chapter_number"]: c for c in CHAPTERS_INDEX}
PRESENCE_BY_CH = {c["chapter"]: c["characters"] for c in PRESENCE_DATA}
PAINTED_IDS = {
    p["character_id"]
    for p in PORTRAIT_MANIFEST["portraits"]
    if p["status"] == "latest_existing_portrait"
}
REALM_BY_ID = {r["id"]: r for r in MAP_DATA["realms"]}
ROUTE_BY_ID = {r["id"]: r for r in MAP_DATA["routes"] if r["rendered"]}

# Load all stanzas by (chapter_number, stanza_number)
STANZA_BY_LOC = {}
CHAPTER_STANZA_BOUNDS = {}
for path in sorted(glob.glob(str(ROOT / "data/chapters/chapter-*.json"))):
    ch_doc = json.load(open(path))
    ch_num = ch_doc["chapter_number"]
    st_nums = [s["stanza_number"] for s in ch_doc["stanzas"]]
    CHAPTER_STANZA_BOUNDS[ch_num] = (min(st_nums), max(st_nums))
    for s in ch_doc["stanzas"]:
        STANZA_BY_LOC[(ch_num, s["stanza_number"])] = s

ACTS = {
    1: {
        "act_number": 1,
        "title_ka": "კარი I — არაბეთი და უცხო მოყმის ძიება",
        "title_en": "Act I — Arabia & the Quest for the Stranger Knight",
    },
    2: {
        "act_number": 2,
        "title_ka": "კარი II — ტარიელის თავგადასავალი: ინდოეთი, ხატაეთი და დაკარგვა",
        "title_en": "Act II — Tariel's Chronicle: India, Khataeti & Loss",
    },
    3: {
        "act_number": 3,
        "title_ka": "კარი III — ავთანდილის ანდერძი, ლომ-ვეფხვი და გზა ფრიდონისკენ",
        "title_en": "Act III — Avtandil's Testament, Lion-Panther & Road to Pridon",
    },
    4: {
        "act_number": 4,
        "title_ka": "კარი IV — გულანშარო, ფატმანი და ცნობა ქაჯეთიდან",
        "title_en": "Act IV — Gulansharo, Fatman & Tidings from Kadjeti",
    },
    5: {
        "act_number": 5,
        "title_ka": "კარი V — ქაჯეთის აღება, ნესტანის ხსნა და დაბრუნება",
        "title_en": "Act V — Storming of Kadjeti, Liberation & Homecoming",
    },
}

EPISODE_SPECS = [
    {
        "episode_number": 1,
        "id": "ep_01_prologue",
        "act": 1,
        "chapters": [1],
        "mode": "framing",
        "mode_label_ka": "პროლოგი / ჩარჩო",
        "title_ka": "დასაწყისი — შოთა რუსთაველის პროლოგი",
        "title_en": "Prologue — Invocation, Poetics & Theory of Love",
        "primary_realm": "arabia",
        "secondary_realms": [],
        "frame_realm": None,
        "routes_used": [],
        "focal_characters": ["rustaveli"],
        "summary_ka": "პოეტი შესთხოვს შემოქმედს, აქებს თამარ მეფეს და აყალიბებს შაირობისა და მიჯნურობის თეორიას, სანამ არაბეთის ამბავს დაიწყებს.",
        "token_action_ka": "დადეთ შოთა რუსთაველის ნიშანი რუკის სათაურთან (ზედა მარცხენა კუთხეში) ან მის პერსონაჟის ბარათზე და მოამზადეთ არაბეთის სამეფო კარის პერსონაჟთა ნიშნები.",
        "objective_ka": "გახსენით თამაში: წაიკითხეთ პროლოგის აფორიზმი და დაასახელეთ სამი ძმადნაფიცი გმირი, რომელთაც პოეტი იხსენიებს.",
        "quote_chapter": 1,
        "quote_stanza": 12,
        "quote_line_ka": "გრძელი სიტყვა მოკლედ ითქმის, შაირია ამად კარგი.",
        "character_inputs_ka": [
            {
                "character_id": "rustaveli",
                "name_ka": "შოთა რუსთაველი",
                "role_ka": "მთხრობელი და პოეტი",
                "action_ka": "დადეთ შოთა რუსთაველის ნიშანი რუკის სათაურთან (ზედა მარცხენა კუთხეში) ან მის პერსონაჟის ბარათზე. წაიკითხეთ პროლოგის აფორიზმი და მოამზადეთ არაბეთის სამეფო კარის ნიშნები ამბის დასაწყებად.",
                "dialogue_ka": "„გრძელი სიტყვა მოკლედ ითქმის, შაირია ამად კარგი.“",
                "cue_ka": "შეავედრეთ შემოქმედს დაწყებული ამბავი და გააცანით მოთამაშეებს პოემის სამი გმირი."
            }
        ],
    },
    {
        "episode_number": 2,
        "id": "ep_02_tinatin_coronation",
        "act": 1,
        "chapters": [2, 3],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "თინათინის გამეფება და სამეფო ნადირობა",
        "title_en": "Coronation of Tinatin & the Royal Hunt",
        "primary_realm": "arabia",
        "secondary_realms": [],
        "frame_realm": None,
        "routes_used": [],
        "focal_characters": ["rostevan", "tinatin", "avtandil", "sograt"],
        "summary_ka": "ხანდაზმული როსტევან მეფე ვეზირ სოგრატის რჩევით ტახტზე სვამს თავის ასულს, თინათინს. ნადიმი სრულდება როსტევანისა და სპასპეტ ავთანდილის სანადირო შეჯიბრით.",
        "token_action_ka": "განათავსეთ როსტევანის, თინათინის, ავთანდილისა და სოგრატის ნიშნები არაბეთში (სამეფო 1); თინათინისა და ავთანდილის ნიშნები დადეთ გვერდიგვერდ.",
        "objective_ka": "დააწყვეთ არაბეთის სამეფო კარი რუკაზე და შეამოწმეთ ამ ოთხი პერსონაჟის ბარათების „ეპიზოდებში“ სკალაზე მე-2 ეპიზოდი.",
        "quote_chapter": 2,
        "quote_stanza": 39,
        "quote_line_ka": "ლეკვი ლომისა სწორია, ძუ იყოს, თუნდა ხვადია.",
        "character_inputs_ka": [
            {
                "character_id": "rostevan",
                "name_ka": "როსტევანი",
                "role_ka": "არაბეთის მეფე",
                "action_ka": "განათავსეთ როსტევანის ნიშანი არაბეთში (სამეფო 1). გამოაცხადეთ თქვენი ასულის, თინათინის გამეფება და ტახტის გადაცემა; ნადიმზე კი სანადირო შეჯიბრში გამოიწვიეთ სპასპეტი ავთანდილი.",
                "dialogue_ka": "„თუცა ქალია, ხელმწიფედ მართ ღმრთისა დანაბადია; არ გათნევთ, იცის მეფობა, უთქვენოდ გვითქვამს კვლა დია!“",
                "cue_ka": "დალოცეთ ახალი ხელმწიფე და გაამხნევეთ შეკრებილი სამეფო კარი."
            },
            {
                "character_id": "sograt",
                "name_ka": "სოგრატი",
                "role_ka": "არაბეთის უხუცესი ვეზირი",
                "action_ka": "განათავსეთ სოგრატის ნიშანი არაბეთში (სამეფო 1). დაუჭირეთ მხარი როსტევან მეფეს ასულის გამეფებაში; სანადირო ასპარეზობისას კი დანიშნეთ მსაჯულები ნანადირევის დასათვლელად.",
                "dialogue_ka": "„რა ვარდმან მისი ყვავილი გაახმოს, დაამჭნაროსა, / მისგან სხვა დაებადების, რათგან ცა ესრეთ ჰმაროსა...“",
                "cue_ka": "შეახსენეთ მეფეს, რომ ასული მზესავით გაანათებს არაბეთს."
            },
            {
                "character_id": "tinatin",
                "name_ka": "თინათინი",
                "role_ka": "არაბეთის ახალი ხელმწიფე",
                "action_ka": "განათავსეთ თინათინის ნიშანი არაბეთში (სამეფო 1) და მიუახლოვეთ ავთანდილის ნიშანს. მიიღეთ მამისგან გვირგვინი, გახსენით სამეფო სალარო და უხვად დაასაჩუქრეთ დიდებულები, ლაშქარი და გლახაკები.",
                "dialogue_ka": "„დღეს მეფემან ჩემმან მისსა ხელმწიფობასა დამადგა, / ესე საუნჯე ჩემია, რაცა შიგან ძეს, რაცა დგა!“",
                "cue_ka": "გამოიჩინეთ მეფური გულუხვობა, რათა „გაიცეს, რაცა ებოძოს“."
            },
            {
                "character_id": "avtandil",
                "name_ka": "ავთანდილი",
                "role_ka": "არაბეთის სპასპეტი",
                "action_ka": "განათავსეთ ავთანდილის ნიშანი არაბეთში (სამეფო 1) თინათინის გვერდით (დაჯგუფება). მიაგეთ თაყვანი ახალ ხელმწიფეს, მიიღეთ როსტევან მეფის სანადირო გამოწვევა და მოამზადეთ მშვილდ-ისარი.",
                "dialogue_ka": "„ლეკვი ლომისა სწორია, ძუ იყოს, თუნდა ხვადია!“",
                "cue_ka": "დაუდასტურეთ ერთგულება თინათინს და გაეჯიბრეთ როსტევანს ოსტატობაში."
            }
        ],
    },
    {
        "episode_number": 3,
        "id": "ep_03_stranger_at_stream",
        "act": 1,
        "chapters": [4],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "უცხო მოყმის ნახვა წყაროსთან",
        "title_en": "The Weeping Knight in the Panther's Skin",
        "primary_realm": "arabia",
        "secondary_realms": ["wilderness"],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["tariel", "rostevan", "avtandil", "tinatin"],
        "summary_ka": "ნადირობის შემდეგ როსტევანი და ავთანდილი წყაროსთან ხედავენ მტირალ ვეფხისტყაოსან მოყმეს (ტარიელს), რომელიც მონებს იგერიებს და უკვალოდ ქრება. თინათინი დაღონებულ მამას ანუგეშებს.",
        "token_action_ka": "დროებით შემოიყვანეთ ტარიელის ნიშანი არაბეთის (სამეფო 1) საზღვართან როსტევანისა და ავთანდილის პირისპირ, შემდეგ კი გადაადგილეთ უდაბნოსა და ქვაბში (სამეფო 2).",
        "objective_ka": "გახსენით კავშირი არაბეთსა და ქვაბს შორის: ტარიელის ნიშანი იკავებს ქვაბს (სამეფო 2).",
        "quote_chapter": 4,
        "quote_stanza": 107,
        "quote_line_ka": "კაცმან საქმე მოიგვაროს, ვეჭვ, ჭმუნვასა ესე სჯობდეს.",
    },
    {
        "episode_number": 4,
        "id": "ep_04_tinatin_commission",
        "act": 1,
        "chapters": [5, 6],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "თინათინის ბრძანება და შერმადინის დატოვება",
        "title_en": "Tinatin's Commission & Avtandil's Charter to Shermadin",
        "primary_realm": "arabia",
        "secondary_realms": [],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["tinatin", "avtandil", "shermadin", "rostevan"],
        "summary_ka": "თინათინი ავთანდილს სიყვარულის ფიცით სამი წლით გზავნის უცხო მოყმის საძებრად. ავთანდილი სამფლობელოს ერთგულ შერმადინს აბარებს და მარტო მიემგზავრება.",
        "token_action_ka": "არაბეთში (სამეფო 1) შეახეთ თინათინისა და ავთანდილის ნიშნები ფიცის ნიშნად, დადეთ იქ შერმადინის ნიშანი მცველად, ხოლო ავთანდილის ნიშანი მოამზადეთ ქვაბისკენ (სამეფო 2) გასამგზავრებლად.",
        "objective_ka": "დაადასტურეთ ფიცი თინათინსა და ავთანდილს შორის და მოამზადეთ ავთანდილი სამწლიანი ძიებისთვის.",
        "quote_chapter": 5,
        "quote_stanza": 162,
        "quote_line_ka": "მარგალიტი არვის მიჰხვდეს უსასყიდლოდ, უვაჭრელად.",
    },
    {
        "episode_number": 5,
        "id": "ep_05_cave_brotherhood",
        "act": 1,
        "chapters": [7, 8, 9],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "ქვაბში მისვლა, ასმათთან საუბარი და დაძმობილება",
        "title_en": "Finding the Cave, Asmat's Trust & Sworn Brotherhood",
        "primary_realm": "wilderness",
        "secondary_realms": ["arabia"],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["avtandil", "tariel", "asmat"],
        "summary_ka": "სამი ხატაელი მონადირე ძმის ნაამბობით ავთანდილი მიაკვლევს დევთა ქვაბს, მიჯნურობის სახელით მოიპოვებს ასმათის ნდობას და ტარიელთან მარადიულ ძმობას შეფიცავს.",
        "token_action_ka": "გადაადგილეთ ავთანდილის ნიშანი არაბეთიდან (სამეფო 1) უდაბნოსა და ქვაბში (სამეფო 2) და დადეთ გვერდიგვერდ ტარიელისა და ასმათის ნიშნებთან ძმადნაფიცობის ნიშნად.",
        "objective_ka": "შეკრიბეთ ტარიელი, ავთანდილი და ასმათი ქვაბში (სამეფო 2) — აქედან იწყება ტარიელის თავგადასავლის თხრობა.",
        "quote_chapter": 9,
        "quote_stanza": 302,
        "quote_line_ka": "არს უკეთესი, რაცაღა სწადს განგებასა ზენასა.",
    },
    {
        "episode_number": 6,
        "id": "ep_06_india_youth_love",
        "act": 2,
        "chapters": [10, 11],
        "mode": "recollection",
        "mode_label_ka": "მოგონება (თხრობა ქვაბში)",
        "title_ka": "ტარიელის აღზრდა ინდოეთში და ნესტანის ხილვა",
        "title_en": "Tariel's Upbringing in India & First Sight of Nestan",
        "primary_realm": "india",
        "secondary_realms": ["wilderness"],
        "frame_realm": "wilderness",
        "routes_used": [],
        "focal_characters": ["tariel", "nestan", "asmat", "parsadan", "saridan", "davari", "avtandil"],
        "summary_ka": "ქვაბში მჯდომი ტარიელი ავთანდილს უყვება, როგორ შეუერთა მამამისმა სარიდანმა თავისი სამეფო ფარსადანს, როგორ აღზარდა დავარმა ნესტან-დარეჯანი და როგორ დაბნედდა ტარიელი ნესტანის პირველი დანახვისას.",
        "token_action_ka": "ავთანდილის ნიშანი დატოვეთ ქვაბში (სამეფო 2) მსმენელად; განათავსეთ ფარსადანის, სარიდანის, ნესტან-დარეჯანისა და დავარის ნიშნები ინდოეთში (სამეფო 3) და დროებით გადაიყვანეთ იქ ტარიელისა და ასმათის ნიშნები მოგონების გასათამაშებლად.",
        "objective_ka": "გახსენით ინდოეთის სამეფო კარი (სამეფო 3) რუკაზე და გააცოცხლეთ ტარიელის მოგონების პირველი ეპიზოდი.",
        "quote_chapter": 10,
        "quote_stanza": 319,
        "quote_line_ka": "მოვიწიფე, დავემსგავსე მზესა თვალად, ლომსა ნაკვთად.",
    },
    {
        "episode_number": 7,
        "id": "ep_07_first_letters_oath",
        "act": 2,
        "chapters": [12, 13, 14, 15, 16, 17],
        "mode": "recollection",
        "mode_label_ka": "მოგონება (თხრობა ქვაბში)",
        "title_ka": "პირველი წერილები და ფიცი ნესტანის კარავში",
        "title_en": "First Love Letters, Summons to Khataeti & Mutual Oath",
        "primary_realm": "india",
        "secondary_realms": ["khataveti"],
        "frame_realm": "wilderness",
        "routes_used": ["india_khataeti"],
        "focal_characters": ["tariel", "nestan", "asmat", "ramaz"],
        "summary_ka": "ასმათს მოაქვს ნესტანის პირველი წერილი, რომელიც ტარიელს ხატაელთა დამორჩილებას ავალებს. რამაზ მეფის უარის შემდეგ ნესტანი და ტარიელი კარავში პირისპირ ხვდებიან და ერთგულების ფიცს დებენ.",
        "token_action_ka": "დადეთ რამაზ მეფის ნიშანი ხატაეთში (სამეფო 4), ხოლო ინდოეთში (სამეფო 3) გვერდიგვერდ განალაგეთ ტარიელის, ნესტან-დარეჯანისა და ასმათის ნიშნები კარავში დადებული ფიცის ნიშნად.",
        "objective_ka": "გახსენით ხატაეთი (სამეფო 4) რუკაზე და მოამზადეთ ტარიელის ნიშანი ხატაეთში სალაშქროდ.",
        "quote_chapter": 12,
        "quote_stanza": 378,
        "quote_line_ka": "შენგან ჩემისა ქმრობისა წინასაც ვიყავ მდომია.",
    },
    {
        "episode_number": 8,
        "id": "ep_08_khataeti_campaign",
        "act": 2,
        "chapters": [18, 19],
        "mode": "recollection",
        "mode_label_ka": "მოგონება (თხრობა ქვაბში)",
        "title_ka": "ლაშქრობა ხატაეთში და გამარჯვებით დაბრუნება",
        "title_en": "Expedition to Khataeti, Defeat of Ramaz & Victory Banquet",
        "primary_realm": "khataveti",
        "secondary_realms": ["india"],
        "frame_realm": "wilderness",
        "routes_used": ["india_khataeti"],
        "focal_characters": ["tariel", "ramaz", "parsadan", "nestan"],
        "summary_ka": "ხატაელი მაცნის გაფრთხილებით ტარიელი ამარცხებს რამაზ მეფის ჩასაფრებულ ლაშქარს, იპყრობს რამაზს და გამარჯვებით ბრუნდება ინდოეთში, სადაც ფარსადანი რამაზს ხარკის პირობით შეიწყალებს.",
        "token_action_ka": "გადაადგილეთ ტარიელის ნიშანი ინდოეთიდან (სამეფო 3) ხატაეთში (სამეფო 4) რამაზ მეფის პირისპირ, შემდეგ კი გამარჯვების ნიშნად დააბრუნეთ ინდოეთში (სამეფო 3) ფარსადანთან და ნესტან-დარეჯანთან.",
        "objective_ka": "შეასრულეთ ხატაეთის ლაშქრობა რუკაზე და დააბრუნეთ ტარიელის ნიშანი ინდოეთის სამეფო ნადიმზე.",
        "quote_chapter": 18,
        "quote_stanza": 444,
        "quote_line_ka": "შექმნეს რაზმი მრავალკეცი, თუცა, ღმერთო, ვერა მავნეს.",
    },
    {
        "episode_number": 9,
        "id": "ep_09_armlet_and_veil",
        "act": 2,
        "chapters": [20, 21, 22],
        "mode": "recollection",
        "mode_label_ka": "მოგონება და ქვაბის ჩარჩო",
        "title_ka": "სამკლავურისა და ხატაური რიდის გაცვლა",
        "title_en": "Exchange of the Armlet & Khatavian Veil; Fainting in the Cave",
        "primary_realm": "india",
        "secondary_realms": ["wilderness"],
        "frame_realm": "wilderness",
        "routes_used": [],
        "focal_characters": ["tariel", "nestan", "asmat", "avtandil"],
        "summary_ka": "ნესტანი ტარიელს უგზავნის სამკლავურს და სთხოვს ხატაურ რიდეს. ამ სახსოვრის გახსენებაზე ტარიელი ქვაბში გონებას კარგავს, ხოლო ავთანდილი და ასმათი მას მოაბრუნებენ.",
        "token_action_ka": "ინდოეთში (სამეფო 3) მიუახლოვეთ ერთმანეთს ტარიელისა და ნესტან-დარეჯანის ნიშნები სამკლავურისა და ხატაური რიდის გაცვლის ნიშნად, ხოლო ასმათის ნიშანი დადეთ მათ შორის შუამავლად.",
        "objective_ka": "დააკავშირეთ ინდოეთის მოგონება და ქვაბის აწმყო: შეამოწმეთ ტარიელის, ნესტანის, ასმათისა და ავთანდილის ბარათების „ეპიზოდებში“ სკალაზე მე-9 ეპიზოდი.",
        "quote_chapter": 20,
        "quote_stanza": 493,
        "quote_line_ka": "ვნახე სიტურფე წყალ-ჯავარისა შენისა.",
    },
    {
        "episode_number": 10,
        "id": "ep_10_khwarazmsha_slaying",
        "act": 2,
        "chapters": [23, 24, 25],
        "mode": "recollection",
        "mode_label_ka": "მოგონება (თხრობა ქვაბში)",
        "title_ka": "საქორწინო თათბირი და ხვარაზმშას ძის მოკვლა",
        "title_en": "Marriage Counsel in India & Slaying of the Khwarazmian Prince",
        "primary_realm": "india",
        "secondary_realms": [],
        "frame_realm": "wilderness",
        "routes_used": [],
        "focal_characters": ["tariel", "nestan", "parsadan", "khvarazmsha", "asmat"],
        "summary_ka": "ფარსადანი ნესტანის საქმროდ იწვევს ხვარაზმშას ძეს. ნესტანთან თათბირის შემდეგ ტარიელი ღამით კარავში კლავს სასიძოს და თავის ქალაქში მაგრდება.",
        "token_action_ka": "შემოიყვანეთ ხვარაზმშას ძის ნიშანი ინდოეთში (სამეფო 3) ტარიელის პირისპირ, ხოლო ეპიზოდის დასრულებისას მოხსენით ხვარაზმშას ძის ნიშანი რუკიდან.",
        "objective_ka": "გაითამაშეთ ინდოეთის კარის კრიზისი: ხვარაზმშას ძის მოკვლით იწყება ნესტან-დარეჯანის დაკარგვა.",
        "quote_chapter": 24,
        "quote_stanza": 531,
        "quote_line_ka": "მან მიბრძანა: “რაცა იცი, თქვიო”, თავი დამიქნია.",
    },
    {
        "episode_number": 11,
        "id": "ep_11_nestan_abduction",
        "act": 2,
        "chapters": [26],
        "mode": "recollection",
        "mode_label_ka": "მოგონება (თხრობა ქვაბში)",
        "title_ka": "დავარის რისხვა და ნესტანის ზღვაში გადაკარგვა",
        "title_en": "Davar's Wrath & the Casting of Nestan Out to Sea",
        "primary_realm": "india",
        "secondary_realms": ["gulansharo", "mulgazanzar"],
        "frame_realm": "wilderness",
        "routes_used": ["india_gulansharo", "india_mulgazanzar"],
        "focal_characters": ["tariel", "nestan", "asmat", "parsadan", "davari"],
        "summary_ka": "ფარსადანი სასიკვდილოდ ემუქრება თავის დას, დავარს. დავარი სცემს ნესტანს, ორ მონას კიდობნით ზღვაში გაატანს და თავს იკლავს. ასმათისგან ამბის გამგონე ტარიელი სატრფოს საძებრად გადის.",
        "token_action_ka": "მოხსენით დავარის ნიშანი ინდოეთიდან (სამეფო 3); გადაადგილეთ ნესტან-დარეჯანის ნიშანი ინდოეთიდან საზღვაო მიმართულებით გულანშაროსკენ (სამეფო 6), ხოლო ტარიელისა და ასმათის ნიშნები — მულღაზანზარისკენ (სამეფო 5).",
        "objective_ka": "დაიწყეთ დიდი ძიება ზღვასა და ხმელეთზე: ნესტან-დარეჯანისა და ტარიელის ნიშნები ინდოეთს ტოვებენ.",
        "quote_chapter": 26,
        "quote_stanza": 581,
        "quote_line_ka": "წადით, დაკარგეთ მუნ, სადა ზღვისა ჭიპია.",
    },
    {
        "episode_number": 12,
        "id": "ep_12_pridon_and_exile",
        "act": 2,
        "chapters": [27, 28, 29],
        "mode": "recollection",
        "mode_label_ka": "მოგონების დასასრული → ქვაბი",
        "title_ka": "ფრიდონთან დაძმობილება და ქვაბში დამკვიდრება",
        "title_en": "Brotherhood with Pridon in Mulghazanzar & Retreat to the Cave",
        "primary_realm": "mulgazanzar",
        "secondary_realms": ["wilderness", "india"],
        "frame_realm": "wilderness",
        "routes_used": ["india_mulgazanzar", "cave_mulgazanzar", "india_cave"],
        "focal_characters": ["tariel", "pridon", "asmat", "nestan", "avtandil"],
        "summary_ka": "ერთწლიანი ძიების შემდეგ ტარიელი ზღვის პირას ხვდება დაჭრილ ნურადინ-ფრიდონს, ეხმარება ბიძაშვილების ძლევაში და მისგან იგებს ნესტანის ნავით გატაცების ამბავს, რის შემდეგაც ასმათთან ერთად დევთა ქვაბში სახლდება.",
        "token_action_ka": "განათავსეთ ნურადინ-ფრიდონის ნიშანი მულღაზანზარში (სამეფო 5); შეახვედრეთ მას ტარიელის ნიშანი, შემდეგ კი ტარიელისა და ასმათის ნიშნები დააბრუნეთ უდაბნოსა და ქვაბში (სამეფო 2) ავთანდილთან.",
        "objective_ka": "დაასრულეთ ტარიელის მონათხრობი: ტარიელი, ავთანდილი და ასმათი კვლავ ერთად არიან ქვაბში (სამეფო 2).",
        "quote_chapter": 27,
        "quote_stanza": 603,
        "quote_line_ka": "ნავითა გავე, ზღვისაგან შტო რამე გამოვიდოდა.",
    },
    {
        "episode_number": 13,
        "id": "ep_13_return_to_arabia",
        "act": 3,
        "chapters": [30, 31],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "ავთანდილის დაბრუნება არაბეთს და ვეზირის შუამდგომლობა",
        "title_en": "Avtandil's Return to Arabia & Sograt's Petition to Rostevan",
        "primary_realm": "arabia",
        "secondary_realms": ["wilderness"],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["avtandil", "tinatin", "rostevan", "shermadin", "sograt"],
        "summary_ka": "ავთანდილი ბრუნდება არაბეთში, თინათინს უყვება ტარიელის ამბავს და სოგრატ ვეზირის პირით სთხოვს როსტევანს გაშვებას, თუმცა მეფე განრისხდება და უარს ამბობს.",
        "token_action_ka": "გადაადგილეთ ავთანდილის ნიშანი ქვაბიდან (სამეფო 2) უკან არაბეთში (სამეფო 1) თინათინის, როსტევანის, შერმადინისა და სოგრატის ნიშნებთან.",
        "objective_ka": "შეკრიბეთ არაბეთის ხუთივე პერსონაჟის ნიშანი არაბეთში (სამეფო 1).",
        "quote_chapter": 30,
        "quote_stanza": 703,
        "quote_line_ka": "ხამს მოყვარე მოყვრისათვის თავი ჭირსა არ დამრიდად.",
    },
    {
        "episode_number": 14,
        "id": "ep_14_avtandil_testament",
        "act": 3,
        "chapters": [32, 33, 34, 35],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "ავთანდილის ანდერძი, ლოცვა და ფარული გაპარვა",
        "title_en": "Avtandil's Testament, Prayer & Secret Flight from Arabia",
        "primary_realm": "arabia",
        "secondary_realms": [],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["avtandil", "shermadin", "rostevan", "sograt"],
        "summary_ka": "ფიცის ერთგული ავთანდილი წერს ბრძნულ ანდერძს როსტევან მეფის წინაშე, ქონებას გლახაკებს ურიგებს, სახლს შერმადინს აბარებს და ფარულად მიდის ტარიელის საშველად.",
        "token_action_ka": "შერმადინის, როსტევანის, თინათინისა და სოგრატის ნიშნები რჩებიან არაბეთში (სამეფო 1); გადაადგილეთ ავთანდილის ნიშანი არაბეთიდან ქვაბისკენ (სამეფო 2).",
        "objective_ka": "წაიკითხეთ ავთანდილის ანდერძის სტროფი და გააცილეთ ავთანდილის ნიშანი მეორე ძიებაში.",
        "quote_chapter": 33,
        "quote_stanza": 789,
        "quote_line_ka": "სიცრუე და ორპირობა ავნებს ხორცსა, მერმე სულსა.",
    },
    {
        "episode_number": 15,
        "id": "ep_15_lion_and_panther",
        "act": 3,
        "chapters": [36, 37, 38, 39],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "დაბნედილი ტარიელის პოვნა და ლომ-ვეფხვის დახოცა",
        "title_en": "Finding Unconscious Tariel, the Slain Lion & Panther, and Return to the Cave",
        "primary_realm": "wilderness",
        "secondary_realms": ["arabia"],
        "frame_realm": None,
        "routes_used": ["arabia_cave"],
        "focal_characters": ["avtandil", "tariel", "asmat"],
        "summary_ka": "ქვაბში მისულ ავთანდილს ასმათი აუწყებს ტარიელის გადაკარგვას. ავთანდილი შამბნარში პოულობს ლომ-ვეფხვის მკვლელ, სიკვდილის პირას მისულ ტარიელს, ბრძნული სიტყვით მოაბრუნებს და ქვაბში ასმათთან მიჰყავს.",
        "token_action_ka": "მიიყვანეთ ავთანდილის ნიშანი უდაბნოსა და ქვაბში (სამეფო 2) და დადეთ გვერდიგვერდ ტარიელისა და ასმათის ნიშნებთან.",
        "objective_ka": "დააბრუნეთ ტარიელი ქვაბში: ტარიელისა და ასმათის ნიშნები რჩებიან ქვაბში (სამეფო 2), ხოლო ავთანდილი მულღაზანზარისკენ მიემართება.",
        "quote_chapter": 36,
        "quote_stanza": 854,
        "quote_line_ka": "ვინ მოყვარესა არ ეძებს, იგი თავისა მტერია.",
    },
    {
        "episode_number": 16,
        "id": "ep_16_hymn_and_pridon",
        "act": 3,
        "chapters": [40, 41],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "მნათობთა სიმღერა და სტუმრობა ფრიდონთან",
        "title_en": "Hymn to the Planets & Avtandil's Arrival at Pridon's",
        "primary_realm": "mulgazanzar",
        "secondary_realms": ["wilderness"],
        "frame_realm": None,
        "routes_used": ["cave_mulgazanzar"],
        "focal_characters": ["avtandil", "pridon"],
        "summary_ka": "მარტო მიმავალი ავთანდილი შვიდ მნათობს უმღერის, ჩადის მულღაზანზარში ნურადინ-ფრიდონთან, ნახულობს ნესტანის გატაცების კონცხს და ზღვათა სამეფოსკენ მიემართება.",
        "token_action_ka": "გადაადგილეთ ავთანდილის ნიშანი ქვაბიდან (სამეფო 2) მულღაზანზარში (სამეფო 5) და დადეთ ნურადინ-ფრიდონის ნიშანთან ერთად.",
        "objective_ka": "შეახვედრეთ ავთანდილისა და ფრიდონის ნიშნები მულღაზანზარში (სამეფო 5) და დაადგინეთ საზღვაო ძიების მიმართულება.",
        "quote_chapter": 40,
        "quote_stanza": 959,
        "quote_line_ka": "ჰე მუშთარო, გეაჯები შენ, მართალსა ბრჭესა, ღმრთულსა.",
    },
    {
        "episode_number": 17,
        "id": "ep_17_gulansharo_chashnagir",
        "act": 4,
        "chapters": [42, 43, 44, 45, 46],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "მეკობრეთა ძლევა, გულანშაროში ჩასვლა და ჭაშნაგირის მოკვლა",
        "title_en": "Defeat of the Pirates, Arrival in Gulansharo & Slaying of the Chashnagir",
        "primary_realm": "gulansharo",
        "secondary_realms": ["mulgazanzar"],
        "frame_realm": None,
        "routes_used": ["mulgazanzar_gulansharo"],
        "focal_characters": ["avtandil", "fatman", "chashnagiri"],
        "summary_ka": "ავთანდილი მეკობრეებისგან იხსნის უსამის ქარავანს, ვაჭრის სამოსით შედის გულანშაროში, ეწვევა ფატმან ხათუნს და ფარულად კლავს მოღალატე ჭაშნაგირს, რომელიც ფატმანს ნესტანის გამხელით ემუქრებოდა.",
        "token_action_ka": "გადაადგილეთ ავთანდილის ნიშანი მულღაზანზარიდან (სამეფო 5) გულანშაროში (სამეფო 6); დადეთ იქ ფატმან ხათუნისა და ჭაშნაგირის ნიშნები, ხოლო ეპიზოდის ბოლოს მოხსენით ჭაშნაგირის ნიშანი რუკიდან.",
        "objective_ka": "გახსენით გულანშარო (სამეფო 6), მოაშორეთ მოღალატე ჭაშნაგირის ნიშანი და მოიპოვეთ ფატმან ხათუნის ნდობა.",
        "quote_chapter": 42,
        "quote_stanza": 1046,
        "quote_line_ka": "დიდთა ხეთა მოერევის, მცირე დასწვავს ნაბერწკალი.",
    },
    {
        "episode_number": 18,
        "id": "ep_18_fatman_story_kadjeti",
        "act": 4,
        "chapters": [47, 48],
        "mode": "recollection",
        "mode_label_ka": "ფატმანის მონათხრობი გულანშაროში",
        "title_ka": "ფატმანის მონათხრობი: ნესტანის შეფარება და ქაჯეთში დატყვევება",
        "title_en": "Fatman's Tale: Nestan's Shelter in Gulansharo & Capture into Kadjeti",
        "primary_realm": "gulansharo",
        "secondary_realms": ["kajeti"],
        "frame_realm": "gulansharo",
        "routes_used": ["india_gulansharo", "gulansharo_kajeti"],
        "focal_characters": ["avtandil", "fatman", "nestan", "usen", "surkhavi", "dulardukht", "rosan"],
        "summary_ka": "ფატმანი უყვება ავთანდილს, როგორ იხსნა ზღვით მოყვანილი ნესტანი, როგორ გასცა მთვრალმა უსენმა საიდუმლო მელიქ-სურხავ მეფესთან და როგორ ჩაუვარდა გაქცეული ნესტანი ქაჯთა მეთაურ როშაქს, რომელმაც იგი ქაჯეთში დულარდუხტსა და როსანს მიჰგვარა.",
        "token_action_ka": "განათავსეთ უსენისა და მელიქ-სურხავის ნიშნები გულანშაროში (სამეფო 6); გადაადგილეთ ნესტან-დარეჯანის ნიშანი გულანშაროდან ქაჯეთში (სამეფო 7) და დადეთ იქ დულარდუხტისა და როსანის ნიშნების გარემოცვაში.",
        "objective_ka": "გახსენით მეშვიდე სამეფო — ქაჯეთი (სამეფო 7): ნესტან-დარეჯანის ადგილსამყოფელი ნაპოვნია!",
        "quote_chapter": 47,
        "quote_stanza": 1130,
        "quote_line_ka": "მე იდუმალ ვიხედვიდი, სულ-ღებული ვიყავ შინა.",
    },
    {
        "episode_number": 19,
        "id": "ep_19_letters_from_kadjeti",
        "act": 4,
        "chapters": [49, 50, 51, 52],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "მიმოწერა ქაჯეთთან, ნესტანის წერილი და უწყება ფრიდონთან",
        "title_en": "Letters Between Gulansharo & Kadjeti; Nestan's Letter to Tariel",
        "primary_realm": "kajeti",
        "secondary_realms": ["gulansharo"],
        "frame_realm": None,
        "routes_used": ["gulansharo_kajeti", "gulansharo_cave"],
        "focal_characters": ["nestan", "fatman", "avtandil", "usen"],
        "summary_ka": "ფატმანის გრძნეული მოციქული ქაჯეთში ნესტანს წერილს მიუტანს. ნესტანი უგზავნის წერილსა და ხატაური რიდის ნაკვეთს ტარიელს, ხოლო ავთანდილი წერილს უგზავნის ფრიდონს და გულანშაროს ტოვებს.",
        "token_action_ka": "გულანშაროში (სამეფო 6) შეახეთ ფატმან ხათუნისა და ავთანდილის ნიშნები ქაჯეთიდან (სამეფო 7) ნესტან-დარეჯანის წერილის მიღების ნიშნად და მოამზადეთ ავთანდილის ნიშანი პირდაპირ ქვაბში (სამეფო 2) დასაბრუნებლად.",
        "objective_ka": "დააკავშირეთ ქაჯეთში მყოფი ნესტან-დარეჯანი გულანშაროში მყოფ ფატმანთან და ავთანდილთან — სასიხარულო ცნობა ტარიელთან მიდის.",
        "quote_chapter": 51,
        "quote_stanza": 1304,
        "quote_line_ka": "მომცნეს ფრთენი და აღვფრინდე, მივჰხვდე მას ჩემსა ნდომასა.",
    },
    {
        "episode_number": 20,
        "id": "ep_20_reunion_and_march",
        "act": 5,
        "chapters": [53, 54],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "შეყრა ქვაბში, დევთა საჭურველი და ლაშქრობა ქაჯეთისკენ",
        "title_en": "Reunion at the Cave, Devis' Armor & March via Mulghazanzar to Kadjeti",
        "primary_realm": "wilderness",
        "secondary_realms": ["mulgazanzar", "kajeti"],
        "frame_realm": None,
        "routes_used": ["gulansharo_cave", "cave_mulgazanzar", "mulgazanzar_kajeti"],
        "focal_characters": ["avtandil", "tariel", "asmat", "pridon", "nestan"],
        "summary_ka": "ავთანდილი ფრიდონის გვერდის ავლით ჩადის ქვაბში და ტარიელს ნესტანის წერილსა და რიდის ნაკვეთს გადასცემს. გმირები ხსნიან დევთა საჭურვლის საგანძურს, ასმათთან ერთად მიდიან მულღაზანზარში და ფრიდონის სამასი მხედრით ზღვითა და ხმელეთით ქაჯეთს მიადგებიან.",
        "token_action_ka": "1) გადაადგილეთ ავთანდილის ნიშანი გულანშაროდან (სამეფო 6) პირდაპირ ქვაბში (სამეფო 2); 2) გადაიყვანეთ ტარიელის, ავთანდილისა და ასმათის ნიშნები მულღაზანზარში (სამეფო 5); 3) დატოვეთ ასმათის ნიშანი მულღაზანზარში, ხოლო ტარიელის, ავთანდილისა და ფრიდონის ნიშნები მიიყვანეთ ქაჯეთთან (სამეფო 7).",
        "objective_ka": "შეკრიბეთ სამივე ძმადნაფიცის (ტარიელის, ავთანდილის, ფრიდონის) ნიშნები ქაჯეთის ციხესთან (სამეფო 7).",
        "quote_chapter": 53,
        "quote_stanza": 1361,
        "quote_line_ka": "ბოროტსა სძლია კეთილმან, — არსება მისი გრძელია!",
    },
    {
        "episode_number": 21,
        "id": "ep_21_storming_of_kadjeti",
        "act": 5,
        "chapters": [55, 56, 57],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "სამი გმირის თათბირი, ქაჯეთის აღება და ნესტანის ხსნა",
        "title_en": "The Three Counsels, Storming of Kadjeti & Liberation of Nestan",
        "primary_realm": "kajeti",
        "secondary_realms": [],
        "frame_realm": None,
        "routes_used": ["mulgazanzar_kajeti"],
        "focal_characters": ["tariel", "avtandil", "pridon", "nestan"],
        "summary_ka": "ქაჯეთის წინ ფრიდონი, ავთანდილი და ტარიელი სამ გეგმას განიხილავენ. ტარიელის რჩევით სამას მხედარს სამად ყოფენ, განთიადზე სამივე კარს ერთდროულად შეუტევენ, ციხეს იღებენ და ნესტან-დარეჯანს ათავისუფლებენ.",
        "token_action_ka": "ქაჯეთში (სამეფო 7) მოხსენით რუკიდან დულარდუხტისა და როსანის ნიშნები, ხოლო ტარიელის, ავთანდილისა და ფრიდონის ნიშნები დადეთ ნესტან-დარეჯანის ნიშანთან ერთად.",
        "objective_ka": "გაათავისუფლეთ ნესტან-დარეჯანი ქაჯეთის ციხიდან და გააერთიანეთ ოთხივე გმირის ნიშანი ქაჯეთში (სამეფო 7)!",
        "quote_chapter": 57,
        "quote_stanza": 1416,
        "quote_line_ka": "სამგნითვე კართა შესჯარნეს, ჭირნი არ ნახეს კაფისა.",
    },
    {
        "episode_number": 22,
        "id": "ep_22_sea_king_and_mulgazanzar_wedding",
        "act": 5,
        "chapters": [58, 59],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "სტუმრობა ზღვათა მეფესთან და ქორწილი მულღაზანზარში",
        "title_en": "Reception by Melik-Surkhav, Gift to Fatman & Wedding in Mulghazanzar",
        "primary_realm": "mulgazanzar",
        "secondary_realms": ["gulansharo", "kajeti"],
        "frame_realm": None,
        "routes_used": ["gulansharo_kajeti", "mulgazanzar_gulansharo"],
        "focal_characters": ["tariel", "nestan", "avtandil", "pridon", "asmat", "fatman", "surkhavi"],
        "summary_ka": "გამარჯვებულ გმირებს მელიქ-სურხავი და ფატმანი ეგებებიან; ტარიელი ფატმანს ქაჯეთის ციხესა და საგანძურს უბოძებს. შემდეგ გმირები მულღაზანზარში ჩადიან, სადაც ასმათი ნესტანს ეხვევა და ფრიდონი რვადღიან ქორწილს მართავს.",
        "token_action_ka": "გადაადგილეთ ტარიელის, ნესტან-დარეჯანის, ავთანდილისა და ფრიდონის ნიშნები ქაჯეთიდან (სამეფო 7) გულანშაროს (სამეფო 6, ფატმანთან და მელიქ-სურხავთან) გავლით მულღაზანზარში (სამეფო 5) ასმათის ნიშანთან.",
        "objective_ka": "აღნიშნეთ ტარიელისა და ნესტან-დარეჯანის პირველი ქორწილი მულღაზანზარში (სამეფო 5) ფრიდონთან და ასმათთან ერთად.",
        "quote_chapter": 59,
        "quote_stanza": 1472,
        "quote_line_ka": "თუ შენ შენს ცოლსა არ შეგრთავ, მე ჩემსა არ ვექმარები.",
    },
    {
        "episode_number": 23,
        "id": "ep_23_arabia_reunion_and_wedding",
        "act": 5,
        "chapters": [60, 61],
        "mode": "present",
        "mode_label_ka": "აწმყო მოქმედება",
        "title_ka": "არაბეთში დაბრუნება და ავთანდილისა და თინათინის ქორწილი",
        "title_en": "Return via the Cave to Arabia & Wedding of Avtandil and Tinatin",
        "primary_realm": "arabia",
        "secondary_realms": ["wilderness", "mulgazanzar"],
        "frame_realm": None,
        "routes_used": ["cave_mulgazanzar", "arabia_cave"],
        "focal_characters": ["avtandil", "tinatin", "tariel", "nestan", "pridon", "rostevan", "asmat"],
        "summary_ka": "სამი ძმადნაფიცი, ნესტანი და ასმათი ქვაბზე გავლით ჩადიან არაბეთში. ტარიელის შუამდგომლობით როსტევანი პატიობს ავთანდილს და იმართება ავთანდილისა და თინათინის დიდებული ქორწილი.",
        "token_action_ka": "გადაადგილეთ ტარიელის, ნესტან-დარეჯანის, ავთანდილის, ფრიდონისა და ასმათის ნიშნები მულღაზანზარიდან (სამეფო 5) ქვაბის (სამეფო 2) გავლით არაბეთში (სამეფო 1) როსტევანისა და თინათინის ნიშნებთან.",
        "objective_ka": "შეკრიბეთ მთავარი გმირების ნიშნები არაბეთში (სამეფო 1) და აღნიშნეთ ავთანდილისა და თინათინის გამეფება-ქორწინება.",
        "quote_chapter": 61,
        "quote_stanza": 1553,
        "quote_line_ka": "სამ დღე იყო ინდოთ მეფე ავთანდილის ვით მაყარი.",
    },
    {
        "episode_number": 24,
        "id": "ep_24_india_coronation_epilogue",
        "act": 5,
        "chapters": [62, 63, 64, 65],
        "mode": "present",
        "mode_label_ka": "დასკვნა და ეპილოგი",
        "title_ka": "ინდოეთში დაბრუნება, ტარიელისა და ნესტანის გამეფება და დასასრული",
        "title_en": "Return to India, Coronation of Tariel & Nestan, and Epilogue",
        "primary_realm": "india",
        "secondary_realms": ["arabia", "khataveti", "mulgazanzar"],
        "frame_realm": None,
        "routes_used": ["arabia_india", "india_khataeti"],
        "focal_characters": ["tariel", "nestan", "avtandil", "pridon", "asmat", "tinatin", "ramaz", "rustaveli"],
        "summary_ka": "ფარსადანის სიკვდილის ცნობის შემდეგ გმირები არაბეთიდან ინდოეთში ბრუნდებიან, კვლავ იმორჩილებენ და იწყალებენ რამაზ მეფეს. ტარიელი და ნესტანი ინდოეთის ტახტზე სხდებიან, ასმათს სამეფოს მეშვიდედს უბოძებენ, ძმადნაფიცები თავიანთ სამეფოებს უბრუნდებიან და რუსთაველი პოემას ასრულებს.",
        "token_action_ka": "გადაადგილეთ ტარიელის, ნესტან-დარეჯანის, ავთანდილის, ფრიდონისა და ასმათის ნიშნები არაბეთიდან (სამეფო 1) ინდოეთში (სამეფო 3); ბოლოს დააბრუნეთ ავთანდილის ნიშანი არაბეთში (სამეფო 1) თინათინთან, ხოლო ფრიდონის ნიშანი — მულღაზანზარში (სამეფო 5).",
        "objective_ka": "დაასრულეთ თამაში: ტარიელი, ნესტან-დარეჯანი და ასმათი ინდოეთში (სამეფო 3) არიან, ავთანდილი და თინათინი — არაბეთში (სამეფო 1), ფრიდონი — მულღაზანზარში (სამეფო 5)!",
        "quote_chapter": 65,
        "quote_stanza": 1665,
        "quote_line_ka": "გასრულდა მათი ამბავი ვითა სიზმარი ღამისა.",
    },
]


def build():
    HERE.mkdir(parents=True, exist_ok=True)

    # 1. Verify chapter coverage 1..65 with no gaps or overlaps
    covered = []
    for spec in EPISODE_SPECS:
        covered.extend(spec["chapters"])
    assert covered == list(range(1, 66)), f"Expected 1..65 sequential, got {covered}"

    episodes_out = []
    for spec in EPISODE_SPECS:
        chs = spec["chapters"]
        ch_start, ch_end = chs[0], chs[-1]
        st_start = CHAPTER_STANZA_BOUNDS[ch_start][0]
        st_end = CHAPTER_STANZA_BOUNDS[ch_end][1]
        ch_label = f"თავი {ch_start}" if ch_start == ch_end else f"თავები {ch_start}–{ch_end}"
        st_range_str = f"{st_start}–{st_end}"

        # Validate realms
        assert spec["primary_realm"] in REALM_BY_ID, spec["primary_realm"]
        for r in spec["secondary_realms"]:
            assert r in REALM_BY_ID, r
        if spec["frame_realm"] is not None:
            assert spec["frame_realm"] in REALM_BY_ID, spec["frame_realm"]

        # Validate routes
        for route_id in spec["routes_used"]:
            assert route_id in ROUTE_BY_ID, f"Unknown route_id: {route_id}"

        # Compute exact union of characters from data/character-chapter-presence.json
        all_chars = []
        for ch in chs:
            for cid in PRESENCE_BY_CH[ch]:
                if cid not in all_chars:
                    all_chars.append(cid)

        painted_chars = [cid for cid in all_chars if cid in PAINTED_IDS]
        silhouette_chars = [cid for cid in all_chars if cid not in PAINTED_IDS]

        # Ensure focal_characters are valid and in all_chars
        for cid in spec["focal_characters"]:
            assert cid in DISPLAY_COPY, f"Unknown focal character {cid}"
            assert cid in all_chars, f"Focal character {cid} not in presence for chapters {chs}: {all_chars}"

        # Validate quote stanza
        q_ch, q_st = spec["quote_chapter"], spec["quote_stanza"]
        assert q_ch in chs, f"Quote chapter {q_ch} not in episode chapters {chs}"
        assert (q_ch, q_st) in STANZA_BY_LOC, f"Stanza {(q_ch, q_st)} not found"
        stanza_obj = STANZA_BY_LOC[(q_ch, q_st)]
        core_quote = spec["quote_line_ka"].rstrip('.!?"”»').replace("„", "“")
        normalized_stanza = stanza_obj["georgian_raw_text"].replace("«", "“").replace("»", "”")
        assert core_quote in normalized_stanza, (
            f"Quote line not found in Ch {q_ch} St {q_st}:\n"
            f"Expected: {spec['quote_line_ka']}\n"
            f"Actual:\n{stanza_obj['georgian_raw_text']}"
        )

        enrich = EPISODE_ENRICHMENTS.get(spec["episode_number"], {})
        char_inputs = enrich.get("character_inputs_ka") or spec.get("character_inputs_ka", [])
        aphorisms = enrich.get("aphorisms_ka") or spec.get("aphorisms_ka", [])

        primary_realm_obj = REALM_BY_ID[spec["primary_realm"]]
        act_obj = ACTS[spec["act"]]

        episode_record = {
            "episode_number": spec["episode_number"],
            "id": spec["id"],
            "act_number": spec["act"],
            "act_title_ka": act_obj["title_ka"],
            "act_title_en": act_obj["title_en"],
            "chapters": chs,
            "chapter_range_label_ka": (
                f"თავი {ch_start}" if ch_start == ch_end else f"თავები {ch_start}–{ch_end}"
            ),
            "stanza_range": f"{st_start}–{st_end}",
            "stanza_start": st_start,
            "stanza_end": st_end,
            "mode": spec["mode"],
            "mode_label_ka": spec["mode_label_ka"],
            "title_ka": spec["title_ka"],
            "title_en": spec["title_en"],
            "primary_realm": {
                "id": primary_realm_obj["id"],
                "number": primary_realm_obj["number"],
                "name_ka": primary_realm_obj["name_ka"],
                "caption_ka": primary_realm_obj["caption_ka"],
                "color": primary_realm_obj["color"],
            },
            "secondary_realms": [
                {
                    "id": r_id,
                    "number": REALM_BY_ID[r_id]["number"],
                    "name_ka": REALM_BY_ID[r_id]["name_ka"],
                }
                for r_id in spec["secondary_realms"]
            ],
            "frame_realm": (
                {
                    "id": spec["frame_realm"],
                    "number": REALM_BY_ID[spec["frame_realm"]]["number"],
                    "name_ka": REALM_BY_ID[spec["frame_realm"]]["name_ka"],
                }
                if spec["frame_realm"]
                else None
            ),
            "routes_used": [
                {
                    "id": rt_id,
                    "from": ROUTE_BY_ID[rt_id]["from"],
                    "to": ROUTE_BY_ID[rt_id]["to"],
                    "kind": ROUTE_BY_ID[rt_id]["kind"],
                    "label_ka": ROUTE_BY_ID[rt_id]["label_ka"],
                }
                for rt_id in spec["routes_used"]
            ],
            "focal_characters": [
                {
                    "id": cid,
                    "name_ka": DISPLAY_COPY[cid]["name"],
                    "short_name_ka": DISPLAY_COPY[cid]["short_name"],
                    "has_painted_portrait": cid in PAINTED_IDS,
                }
                for cid in spec["focal_characters"]
            ],
            "painted_characters": [
                {
                    "id": cid,
                    "name_ka": DISPLAY_COPY[cid]["name"],
                    "short_name_ka": DISPLAY_COPY[cid]["short_name"],
                }
                for cid in painted_chars
            ],
            "all_chapter_characters": [
                {
                    "id": cid,
                    "name_ka": DISPLAY_COPY[cid]["name"],
                    "short_name_ka": DISPLAY_COPY[cid]["short_name"],
                    "has_painted_portrait": cid in PAINTED_IDS,
                }
                for cid in all_chars
            ],
            "silhouette_characters": [
                {
                    "id": cid,
                    "name_ka": DISPLAY_COPY[cid]["name"],
                    "short_name_ka": DISPLAY_COPY[cid]["short_name"],
                }
                for cid in silhouette_chars
            ],
            "chapter_titles_ka": [
                {
                    "chapter": ch,
                    "title_ka": CHAPTER_BY_NUM[ch]["chapter_title_ka"],
                    "stanza_range": CHAPTER_BY_NUM[ch]["stanza_range"],
                }
                for ch in chs
            ],
            "summary_ka": spec["summary_ka"],
            "token_action_ka": spec["token_action_ka"],
            "character_inputs_ka": char_inputs,
            "aphorisms_ka": aphorisms,
            "objective_ka": spec["objective_ka"],
            "reader_url": f"https://nikusha37.github.io/pantersskin/reader.html?ep={spec['episode_number']:02d}",
            "qr_asset_svg": f"assets/qr/episode-{spec['episode_number']:02d}-qr.svg",
            "qr_label_ka": f"დაასკანერეთ სრული ტექსტის წასაკითხად ({ch_label}, სტრ. {st_range_str})",
            "quote": {
                "chapter": q_ch,
                "stanza_number": q_st,
                "wardrop_stanza_number": stanza_obj["wardrop_stanza_number"],
                "line_ka": spec["quote_line_ka"],
                "full_stanza_ka": stanza_obj["georgian_raw_text"],
                "english_translation": stanza_obj["english_translation"],
                "locator_label_ka": f"თავი {q_ch}, სტრ. {q_st}",
            },
        }
        episodes_out.append(episode_record)

    deck_doc = {
        "status": "verified_against_primary_chapters_and_realm_map",
        "language": "ka",
        "deck_title_ka": "ეპიზოდების დასტა — ვეფხისტყაოსნის 24 სიუჟეტური სვლა",
        "deck_subtitle_ka": "სამაგიდო თამაშის სვლების მართვა: თავები 1–65, 7 სამეფო და პერსონაჟთა ნიშნების გადაადგილება",
        "total_episodes": len(episodes_out),
        "total_chapters_covered": 65,
        "total_stanzas_covered": 1669,
        "linked_components": {
            "character_cards_a5": "output/character-cards-ka-a5/pantersskin-character-cards-ka-a5-painted-21-a4-duplex.pdf",
            "character_tokens_30mm": "output/character-tokens/pantersskin-character-tokens-ka-painted-21-30mm-a4.pdf",
            "painted_realm_map_clean": "output/painted-realm-map-clean/painted-realm-map-ka-592x420.pdf",
            "painted_realm_map": "output/painted-realm-map/painted-realm-map-ka-592x420.pdf",
            "vector_realm_map": "output/foldable-realm-map/samqaro-realm-map-ka-592x420.pdf",
            "episode_illustrations": "output/episode-illustrations/illustration-manifest.json",
            "character_presence_source": "data/character-chapter-presence.json",
            "realm_map_source": "print-and-play/foldable-realm-map/map-data.ka.json",
        },
        "token_mode": "character_tokens_only_21",
        "gameplay_loop_ka": [
            "1. ყოველი სვლის დასაწყისში გახსენით მომდევნო ეპიზოდის ბარათი (1-დან 24-მდე თანმიმდევრობით).",
            "2. შეამოწმეთ ბარათზე მითითებული ეპიზოდის ნომერი (1–24) და მოძებნეთ იგივე ნომერი A5 პერსონაჟთა ბარათების უკანა მხარეს არსებულ სკალაზე „ეპიზოდებში“ (1–24).",
            "3. შეასრულეთ პუნქტი „ნიშნების გადაადგილება რუკაზე“ მხოლოდ 21 მოხატული 30 მმ პერსონაჟის ნიშნით: გადაადგილეთ ისინი სამეფოებს შორის (1–7), დადეთ გვერდიგვერდ კავშირის/ფიცის ნიშნად, ან მოხსენით დამარცხებული პერსონაჟის ნიშანი რუკიდან.",
            "4. წაიკითხეთ ეპიზოდის შინაარსი, აფორიზმი/სტროფი და შეასრულეთ სვლის მიზანი.",
        ],
        "acts": list(ACTS.values()),
        "episodes": episodes_out,
    }

    json_path = HERE / "episode-cards.ka.json"
    data_json_path = ROOT / "data/episode-cards.json"
    csv_path = HERE / "episode-cards.ka.csv"

    json_text = json.dumps(deck_doc, ensure_ascii=False, indent=2) + "\n"
    json_path.write_text(json_text, encoding="utf-8")
    data_json_path.write_text(json_text, encoding="utf-8")

    # Also write flat CSV for spreadsheet review/editing
    csv_fields = [
        "episode_number",
        "id",
        "act_number",
        "act_title_ka",
        "chapter_range_label_ka",
        "chapters_list",
        "stanza_range",
        "mode",
        "mode_label_ka",
        "title_ka",
        "title_en",
        "primary_realm_id",
        "primary_realm_number",
        "primary_realm_ka",
        "secondary_realms_ka",
        "frame_realm_ka",
        "routes_used_ids",
        "routes_used_ka",
        "focal_characters_ids",
        "focal_characters_ka",
        "painted_characters_ka",
        "all_chapter_characters_ka",
        "summary_ka",
        "token_action_ka",
        "objective_ka",
        "quote_locator_ka",
        "quote_line_ka",
        "quote_full_stanza_ka",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for ep in episodes_out:
            writer.writerow({
                "episode_number": ep["episode_number"],
                "id": ep["id"],
                "act_number": ep["act_number"],
                "act_title_ka": ep["act_title_ka"],
                "chapter_range_label_ka": ep["chapter_range_label_ka"],
                "chapters_list": ",".join(str(c) for c in ep["chapters"]),
                "stanza_range": ep["stanza_range"],
                "mode": ep["mode"],
                "mode_label_ka": ep["mode_label_ka"],
                "title_ka": ep["title_ka"],
                "title_en": ep["title_en"],
                "primary_realm_id": ep["primary_realm"]["id"],
                "primary_realm_number": ep["primary_realm"]["number"],
                "primary_realm_ka": ep["primary_realm"]["name_ka"],
                "secondary_realms_ka": ", ".join(r["name_ka"] for r in ep["secondary_realms"]),
                "frame_realm_ka": ep["frame_realm"]["name_ka"] if ep["frame_realm"] else "",
                "routes_used_ids": ", ".join(r["id"] for r in ep["routes_used"]),
                "routes_used_ka": " | ".join(r["label_ka"] for r in ep["routes_used"]),
                "focal_characters_ids": ", ".join(c["id"] for c in ep["focal_characters"]),
                "focal_characters_ka": ", ".join(c["short_name_ka"] for c in ep["focal_characters"]),
                "painted_characters_ka": ", ".join(c["short_name_ka"] for c in ep["painted_characters"]),
                "all_chapter_characters_ka": ", ".join(c["short_name_ka"] for c in ep["all_chapter_characters"]),
                "summary_ka": ep["summary_ka"],
                "token_action_ka": ep["token_action_ka"],
                "objective_ka": ep["objective_ka"],
                "quote_locator_ka": ep["quote"]["locator_label_ka"],
                "quote_line_ka": ep["quote"]["line_ka"],
                "quote_full_stanza_ka": ep["quote"]["full_stanza_ka"].replace("\n", " / "),
            })

    print(f"Generated {len(episodes_out)} episodes:")
    print(f"  JSON: {json_path}")
    print(f"  JSON: {data_json_path}")
    print(f"  CSV:  {csv_path}")


if __name__ == "__main__":
    build()
