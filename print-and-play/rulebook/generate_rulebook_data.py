#!/usr/bin/env python3
"""Generate canonical rulebook data (print-and-play/rulebook/rulebook-data.ka.json and data/rulebook.ka.json).

This compiles the complete Georgian rulebook dataset from authoritative sources:
- print-and-play/episode-deck/episode-cards.ka.json
- print-and-play/rulebook/rulebook-copy.ka.json
- print-and-play/character-deck/display-copy.ka.json
- print-and-play/foldable-realm-map/map-data.ka.json
"""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EPISODES_PATH = ROOT / "print-and-play/episode-deck/episode-cards.ka.json"
COPY_PATH = ROOT / "print-and-play/rulebook/rulebook-copy.ka.json"
DISPLAY_COPY_PATH = ROOT / "print-and-play/character-deck/display-copy.ka.json"
CHARACTER_CARDS_PATH = ROOT / "data/character-cards.json"
MAP_DATA_PATH = ROOT / "print-and-play/foldable-realm-map/map-data.ka.json"

OUT_PNP = ROOT / "print-and-play/rulebook/rulebook-data.ka.json"
OUT_DATA = ROOT / "data/rulebook.ka.json"


def assert_no_latin_in_georgian(text, field_name=""):
    """Ensure no unintended Latin letters appear in Georgian copy."""
    clean_text = unicodedata.normalize("NFC", str(text))
    latin_chars = sorted({c for c in clean_text if "LATIN" in unicodedata.name(c, "")})
    if latin_chars:
        raise ValueError(f"Found Latin characters {latin_chars} in {field_name}: '{text}'")


def build_rulebook_data():
    ep_data = json.loads(EPISODES_PATH.read_text(encoding="utf-8"))
    copy_data = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    disp_data = json.loads(DISPLAY_COPY_PATH.read_text(encoding="utf-8"))
    char_cards_by_id = {
        c["id"]: c for c in json.loads(CHARACTER_CARDS_PATH.read_text(encoding="utf-8"))["characters"]
    }
    map_data = json.loads(MAP_DATA_PATH.read_text(encoding="utf-8"))

    # 1. Meta & Header Information
    meta = {
        "title_ka": copy_data["title_ka"],
        "subtitle_ka": copy_data["subtitle_ka"],
        "tagline_ka": "სამაგიდო თამაში 24 ეპიზოდად — შოთა რუსთაველის პოემის მიხედვით",
        "edition_name_ka": "პერსონაჟთა 21 ნიშნის გამოცემა",
        "version": "1.0.0",
        "language": "ka",
        "token_mode": "character_tokens_only_21",
        "poem_basis_ka": copy_data["edition_ka"],
        "art_basis_ka": copy_data["art_ka"],
        "total_episodes": 24,
        "total_chapters": 65,
        "total_stanzas": 1669,
        "total_acts": 5,
        "total_realms": 7,
        "total_character_tokens": 21,
        "total_character_cards": 21,
    }

    # 2. Overview & Cooperative Concept
    overview = {
        "summary_ka": copy_data["overview_ka"],
        "detailed_ka": (
            "„ვეფხისტყაოსანი“ არის კოოპერაციული სიუჟეტური სამაგიდო თამაში, რომელიც მოთამაშეებს საშუალებას "
            "აძლევს, 24 თანმიმდევრულ ეპიზოდში გააცოცხლონ ქართული ეპოსის უკვდავი თავგადასავალი. "
            "თამაში იწყება შოთა რუსთაველის პროლოგითა და არაბეთის სამეფო კარის ამბით, გრძელდება ტარიელის "
            "ტრაგიკული მოგონებებით, ავთანდილის ერთგული ძიებით, ძმადნაფიცთა შეყრითა და ქაჯეთის ციხის "
            "შტურმით, და გვირგვინდება სამივე სამეფოს დიდი ზეიმითა და მშვიდობით. "
            "მოთამაშეები ერთად კითხულობენ ეპიზოდებს, გადაადგილებენ 21 მოხატულ ნიშანს 7 სამეფოს რუკაზე, "
            "აკვირდებიან პერსონაჟთა მონაწილეობას 24-ეპიზოდიან სკალაზე და ასრულებენ თითოეული სვლის სიუჟეტურ მიზანს."
        ),
        "game_nature_ka": (
            "თამაშში არ არის კამათელი, ქულები ან დაპირისპირება მოთამაშეებს შორის. "
            "გამარჯვება საერთოა და მიიღწევა 24-ე ეპიზოდის ბოლოს, როდესაც ყველა გმირი თავის საბოლოო "
            "მშვიდობიან სამყოფელს დაუბრუნდება."
        ),
    }

    # 3. Physical Components Manifest
    components = [
        {
            "id": "realm_map",
            "name_ka": "სამეფოთა მოხატული რუკა",
            "quantity": 1,
            "dimensions": "592 × 420 მმ",
            "description_ka": (
                "რუკაზე გამოსახულია პოემის 7 სამეფო (არაბეთი, უდაბნო და ქვაბი, ინდოეთი, ხატაეთი, "
                "მულღაზანზარი, გულანშარო, ქაჯეთი), ზღვა და რუკის სათაური. რუკა თავისუფალია მარშრუტების "
                "ხაზებისგან, რაც ნიშნების თავისუფალ გადაადგილებას უზრუნველყოფს."
            ),
            "file_path": "output/painted-realm-map-clean/painted-realm-map-ka-592x420.pdf",
        },
        {
            "id": "character_tokens",
            "name_ka": "მოხატული პერსონაჟების ნიშნები",
            "quantity": 21,
            "dimensions": "30 მმ დიამეტრი, ორმხრივი",
            "description_ka": (
                "ხის ან მუყაოს 21 მრგვალი ნიშანი პერსონაჟთა ფერადი მინიატურული პორტრეტებითა და "
                "ქართული სახელებით. გამოიყენება მხოლოდ პერსონაჟთა ნიშნები (თამაშში არ არის ნივთების, "
                "კავშირების ან მთვლელების დამატებითი ნიშნები)."
            ),
            "file_path": "output/character-tokens/pantersskin-character-tokens-ka-painted-21-30mm-a4.pdf",
        },
        {
            "id": "character_cards",
            "name_ka": "პერსონაჟთა მოხატული ბარათები",
            "quantity": 21,
            "dimensions": "148 × 210 მმ (ორმხრივი)",
            "description_ka": (
                "21 მოხატული პერსონაჟის ბარათი. წინა მხარე: მინიატურული პორტრეტი, როლი, სამეფო და "
                "მოკლე დახასიათება. უკანა მხარე: სრული ბიოგრაფია, ეპითეტები, ურთიერთკავშირები და "
                "24-წრიანი სკალა „ეპიზოდებში (1-24)“."
            ),
            "file_path": "output/character-cards-ka-a5/pantersskin-character-cards-ka-a5-painted-21-a4-duplex.pdf",
        },
        {
            "id": "episode_cards",
            "name_ka": "ეპიზოდების დასტა",
            "quantity": 24,
            "dimensions": "148 × 210 მმ (ორმხრივი)",
            "description_ka": (
                "24 ეპიზოდის ბარათი, დაყოფილი 5 კარად. წინა მხარე: ხელნაწერი მინიატურა, კარი, თავები, "
                "სამეფოები, თხრობის რეჟიმი და ნიშნების გადაადგილების ინსტრუქცია. უკანა მხარე: "
                "ეპიზოდის შინაარსი, სვლის მიზანი, საკვანძო სტროფი/აფორიზმი და სკალა „ეპიზოდებში (1-24)“."
            ),
            "file_path": "output/episode-deck/pantersskin-episode-cards-ka-a5-a4-duplex.pdf",
        },
        {
            "id": "rulebook_sheet",
            "name_ka": "თამაშის წესები და მომზადების ფურცელი",
            "quantity": 1,
            "dimensions": "210 × 297 მმ ან 148 × 210 მმ (ორმხრივი)",
            "description_ka": (
                "ორმხრივი საცნობარო ფურცელი. გვერდი 1: თამაშის წესები, სვლის ციკლი, ნიშნების მოძრაობის "
                "მექანიკა, მოგონების ჩარჩო და სკალის განმარტება. გვერდი 2: მომზადების ნაბიჯები, 7 სამეფოს "
                "სქემა და 24 ეპიზოდის სრული საცნობარო ცხრილი."
            ),
            "file_path": "output/rulebook/pantersskin-rulebook-ka-a4.pdf",
        },
    ]

    # 4. Step-by-Step Board Setup
    setup_steps = [
        {
            "step_number": 1,
            "title_ka": "რუკის გაშლა",
            "instruction_ka": "გაშალეთ სამეფოთა მოხატული რუკა მაგიდის ცენტრში ისე, რომ 7-ვე სამეფო ყველა მოთამაშისთვის კარგად ჩანდეს.",
        },
        {
            "step_number": 2,
            "title_ka": "ნიშნების დახარისხება",
            "instruction_ka": "დაახარისხეთ 21 მოხატული ნიშანი პერსონაჟების მიხედვით. გამოყავით არაბეთის სამეფო კარი და რუსთაველის ნიშანი.",
        },
        {
            "step_number": 3,
            "title_ka": "პერსონაჟთა ბარათების განლაგება",
            "instruction_ka": "21 პერსონაჟის ბარათი დააწყვეთ რუკის გვერდით, წინა მხარით ზემოთ. მოთამაშეებს ნებისმიერ დროს შეუძლიათ მათი დათვალიერება.",
        },
        {
            "step_number": 4,
            "title_ka": "ეპიზოდების დასტის მომზადება",
            "instruction_ka": "24 ეპიზოდის ბარათი დაალაგეთ ნუმერაციის მიხედვით (1-დან 24-მდე), ისე რომ პირველი ეპიზოდი („პროლოგი“) იდოს დასტის თავზე.",
        },
        {
            "step_number": 5,
            "title_ka": "საწყისი განლაგება რუკაზე",
            "instruction_ka": "შოთა რუსთაველის ნიშანი დადეთ რუკის სათაურთან (ზედა მარცხენა კუთხეში) ან მის პერსონაჟის ბარათზე. არაბეთში (სამეფო 1) განათავსეთ არაბეთის სამეფო კარის 5 პერსონაჟი: როსტევანი, თინათინი, ავთანდილი, სოგრატი და შერმადინი.",
        },
        {
            "step_number": 6,
            "title_ka": "რეზერვის მომზადება",
            "instruction_ka": "დანარჩენი 15 პერსონაჟის ნიშანი დაალაგეთ რუკის გვერდით რეზერვში. ისინი რუკაზე ეტაპობრივად შემოვლენ ეპიზოდების ბარათების მითითებით.",
        },
    ]

    # 5. Gameplay Loop (Episode Turn Sequence)
    gameplay_loop = [
        {
            "phase_number": 1,
            "phase_name_ka": "ეპიზოდის გახსნა",
            "instruction_ka": "აიღეთ და გახსენით მომდევნო ეპიზოდის ბარათი (1-დან 24-მდე თანმიმდევრობით).",
        },
        {
            "phase_number": 2,
            "phase_name_ka": "წინა მხარის წაკითხვა",
            "instruction_ka": "წაიკითხეთ კარი, თავებისა და სტროფების დიაპაზონი, მოქმედი სამეფოები და თხრობის რეჟიმი (აწმყო, მოგონება/ჩარჩო ან დასასრული).",
        },
        {
            "phase_number": 3,
            "phase_name_ka": "ნიშნების გადაადგილება",
            "instruction_ka": "შეასრულეთ ბარათზე მითითებული ინსტრუქცია „ნიშნების გადაადგილება რუკაზე“ — გადაიყვანეთ პერსონაჟები სამეფოებს შორის, დააჯგუფეთ ისინი ან მოხსენით რუკიდან.",
        },
        {
            "phase_number": 4,
            "phase_name_ka": "შინაარსი და სტროფი",
            "instruction_ka": "გადააბრუნეთ ბარათი და წაიკითხეთ ეპიზოდის შინაარსი, სვლის მიზანი, სრული სტროფი/აფორიზმი და მოქმედი გმირები.",
        },
        {
            "phase_number": 5,
            "phase_name_ka": "სკალის შედარება",
            "instruction_ka": "შეადარეთ ეპიზოდის ნომერი (1-24) პერსონაჟთა ბარათებზე არსებულ სკალას „ეპიზოდებში (1-24)“.",
        },
        {
            "phase_number": 6,
            "phase_name_ka": "მიზნის შესრულება",
            "instruction_ka": "შეასრულეთ ეპიზოდის მიზანი (კითხვა, აფორიზმის ამოცნობა ან სიუჟეტური მოქმედება) და გადადით მომდევნო ეპიზოდზე.",
        },
    ]

    # 6. Token Movement & Mechanics
    token_actions = [
        {
            "kind": "move",
            "title_ka": "გადაადგილება",
            "instruction_ka": "გადაიყვანეთ ნიშანი სამეფოებს შორის (1-7), ეპიზოდის ბარათის მითითებით. რუკაზე ხაზოვანი გზები არ გზღუდავთ — გადაადგილება ხდება პირდაპირ დანიშნულების სამეფოში.",
            "rule_note_ka": "არაბეთიდან ქვაბში, ქვაბიდან ინდოეთში თუ გულანშაროდან ქაჯეთში გადასვლა სრულდება ბარათის მითითებისთანავე.",
        },
        {
            "kind": "group",
            "title_ka": "დაჯგუფება და კავშირი",
            "instruction_ka": "გვერდიგვერდ ან შეხებული ნიშნები აღნიშნავს ფიცს, სიყვარულს, ძმადნაფიცობას, ერთობლივ ლაშქრობას ან პოლიტიკურ კავშირს.",
            "rule_note_ka": "მაგალითად: ავთანდილისა და ტარიელის დაძმობილება ქვაბში (ეპ. 5), სამი მოყმის შეყრა (ეპ. 20) ან ქორწილები (ეპ. 22-24).",
        },
        {
            "kind": "face",
            "title_ka": "პირისპირ დაპირისპირება",
            "instruction_ka": "ნიშნების ერთმანეთის პირისპირ დგომა აღნიშნავს დაპირისპირებას, მტრობას ან უშუალო ბრძოლას.",
            "rule_note_ka": "მაგალითად: ტარიელი და ხვარაზმშას ძე (ეპ. 10), ან სამი მოყმე ქაჯეთის მცველების პირისპირ (ეპ. 21).",
        },
        {
            "kind": "remove",
            "title_ka": "რუკიდან მოხსნა",
            "instruction_ka": "დამარცხების, დაღუპვის ან ამბიდან სამუდამოდ გასვლისას ნიშანი იხსნება რუკიდან. თამაშის განმავლობაში იხსნება ზუსტად 5 პერსონაჟი:",
            "rule_note_ka": "1. ხვარაზმშას ძე (ეპ. 10); 2. დავარი (ეპ. 11); 3. ჭაშნაგირი (ეპ. 17); 4. დულარდუხტი (ეპ. 21); 5. როსანი (ეპ. 21).",
        },
        {
            "kind": "temporary",
            "title_ka": "დროებითი შემოსვლა და გასვლა",
            "instruction_ka": "ნიშანი ხანმოკლედ შედის სამეფოში და შემდეგ ტოვებს მას ბარათის მითითებით.",
            "rule_note_ka": "მაგალითად: მე-3 ეპიზოდში ტარიელი მცირე ხნით ჩნდება არაბეთში და შემდეგ ქვაბში გადადის. ეს ნიშნავს სამეფოს დატოვებას და არა რუკიდან მოხსნას.",
        },
    ]

    # 7. Flashback & Recollection Mechanics
    flashback_rules = {
        "title_ka": "მოგონება და თხრობის ჩარჩო",
        "description_ka": copy_data["flashback_ka"],
        "modes": [
            {
                "mode": "present",
                "label_ka": "აწმყო მოქმედება",
                "color_role": "green",
                "description_ka": "ამბავი რეალურ დროში ვითარდება; ნიშნები მოქმედებენ იმ სამეფოში, სადაც ფიზიკურად იმყოფებიან.",
            },
            {
                "mode": "recollection",
                "label_ka": "მოგონება / ჩარჩო",
                "color_role": "gold",
                "description_ka": "გმირი იხსენებს წარსულს. მსმენელი რჩება ჩარჩოს სამეფოში, ხოლო მთხრობელი და მოგონების გმირები მოქმედებას წარსულის სამეფოებში გაითამაშებენ.",
            },
            {
                "mode": "conclusion",
                "label_ka": "დასასრული / ეპილოგი",
                "color_role": "green",
                "description_ka": "პოემის დასკვნითი ეპიზოდი; გმირების საბოლოო დამკვიდრება მშვიდობიან სამეფოებში.",
            },
        ],
        "recollection_anchors_ka": (
            "1. ტარიელის თავგადასავალი (ეპ. 6-12): თხრობის ჩარჩოა ქვაბი (სამეფო 2). ავთანდილი რჩება ქვაბში მსმენელად. "
            "ტარიელი და ასმათი მოგონებას გაითამაშებენ ინდოეთში (3), ხატაეთსა (4) და მულღაზანზარში (5). მე-12 ეპიზოდში ორივე ქვაბში ბრუნდება.\n"
            "2. ფატმანის მონათხრობი (ეპ. 18): თხრობის ჩარჩოა გულანშარო (სამეფო 6). ავთანდილი ისმენს ფატმანისგან ნესტანის გადარჩენისა და ქაჯეთში წაყვანის ამბავს."
        ),
    }

    # 8. Scale 1–24 Integration Rules
    scale_rules = {
        "title_ka": "სკალა „ეპიზოდებში“ (1-24)",
        "explanation_ka": copy_data["scale_ka"],
        "detailed_rules_ka": [
            "თამაშის 24-ვე ეპიზოდი წარმოდგენილია 24 თანმიმდევრული წრით (დაყოფილი 5 კარად) როგორც ეპიზოდების, ისე პერსონაჟთა ბარათებზე.",
            "ეპიზოდის ბარათზე შევსებული წრე მიუთითებს თავად ამ ეპიზოდის ადგილს მთელ 24-სვლიან მოგზაურობაში (მაგ. მე-6 ეპიზოდში შევსებულია მე-6 წრე).",
            "პერსონაჟის ბარათზე შევსებული წრეები აღნიშნავს ყველა იმ ეპიზოდს, რომელშიც ეს პერსონაჟი მონაწილეობს ან რუკაზე ნიშნით მოქმედებს (გადაადგილდება, ჯგუფდება ან იხსნება).",
            "თუ პერსონაჟის ბარათზე მიმდინარე ეპიზოდის ნომერი შევსებულია, ეს პერსონაჟი მოცემული ეპიზოდის აქტიური მონაწილეა.",
            "ცარიელი წრე არ ნიშნავს ნიშნის რუკიდან მოხსნას. ნიშანი რჩება თავის სამეფოში, სანამ ეპიზოდის ბარათი პირდაპირ არ უბრძანებს გადაადგილებას ან მოხსნას.",
        ],
    }

    # 9. Victory Condition & End-game State
    victory = {
        "title_ka": "თამაშის დასრულება და გამარჯვება",
        "condition_ka": copy_data["win_ka"],
        "final_positions_ka": [
            {
                "realm_number": 3,
                "realm_name_ka": "ინდოეთი",
                "characters_ka": ["ტარიელი", "ნესტან-დარეჯანი", "ასმათი"],
                "status_ka": "ტარიელისა და ნესტანის ქორწილი, შვიდივე სამეფოს გაერთიანება და ასმათისთვის ქვეყნის მეშვიდედის ბოძება.",
            },
            {
                "realm_number": 1,
                "realm_name_ka": "არაბეთი",
                "characters_ka": ["ავთანდილი", "თინათინი", "როსტევანი", "შერმადინი", "სოგრატი"],
                "status_ka": "ავთანდილისა და თინათინის ქორწილი, მეფობა არაბეთში და უხვი წყალობა.",
            },
            {
                "realm_number": 5,
                "realm_name_ka": "მულღაზანზარი",
                "characters_ka": ["ნურადინ-ფრიდონი"],
                "status_ka": "ფრიდონის გამარჯვებული დაბრუნება თავის სამეფოში და ძმადნაფიცთა ურყევი კავშირი.",
            },
            {
                "realm_number": 6,
                "realm_name_ka": "გულანშარო",
                "characters_ka": ["უსენი", "ფატმანი"],
                "status_ka": "ვაჭართა ქალაქის მშვიდობა და ფატმანის მადლიერება გმირებისადმი.",
            },
        ],
    }

    # 10. The 7 Realms Reference
    realms = [
        {
            "number": 1,
            "id": "arabia",
            "name_ka": "არაბეთი",
            "caption_ka": "როსტევანისა და თინათინის სამეფო კარი",
            "color": "#9B684B",
            "core_characters_ka": ["როსტევანი", "თინათინი", "ავთანდილი", "შერმადინი", "სოგრატი"],
        },
        {
            "number": 2,
            "id": "cave",
            "name_ka": "უდაბნო და ქვაბი",
            "caption_ka": "დევითა გამოქვაბული და ტარიელის თავშესაფარი",
            "color": "#6D7A68",
            "core_characters_ka": ["ტარიელი", "ასმათი", "ავთანდილი"],
        },
        {
            "number": 3,
            "id": "india",
            "name_ka": "ინდოეთი",
            "caption_ka": "ფარსადანისა და ნესტან-დარეჯანის სამეფო",
            "color": "#A05A32",
            "core_characters_ka": ["ფარსადანი", "სარიდანი", "ტარიელი", "ნესტან-დარეჯანი", "დავარი", "ხვარაზმშას ძე"],
        },
        {
            "number": 4,
            "id": "khataeti",
            "name_ka": "ხატაეთი",
            "caption_ka": "რამაზ მეფის ურჩი მხარე",
            "color": "#8C6A5A",
            "core_characters_ka": ["რამაზი", "ტარიელი"],
        },
        {
            "number": 5,
            "id": "mulghazanzar",
            "name_ka": "მულღაზანზარი",
            "caption_ka": "ნურადინ-ფრიდონის ზღვისპირა სამფლობელო",
            "color": "#4A6E78",
            "core_characters_ka": ["ნურადინ-ფრიდონი", "ტარიელი", "ავთანდილი"],
        },
        {
            "number": 6,
            "id": "gulansharo",
            "name_ka": "გულანშარო",
            "caption_ka": "ზღვისპირა სავაჭრო ქალაქი",
            "color": "#B8860B",
            "core_characters_ka": ["უსენი", "ფატმანი", "ჭაშნაგირი", "სურხავი", "ავთანდილი"],
        },
        {
            "number": 7,
            "id": "kadjeti",
            "name_ka": "ქაჯეთი",
            "caption_ka": "მიუდგომელი კლდოვანი ციხესიმაგრე",
            "color": "#6B4C70",
            "core_characters_ka": ["დულარდუხტი", "როსანი", "ნესტან-დარეჯანი"],
        },
    ]

    # 11. Complete 24 Episodes Reference
    episodes_manifest = []
    short_titles = copy_data["episode_short_titles"]
    roman_to_num = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}

    for ep in ep_data["episodes"]:
        num = ep["episode_number"]
        short_title = short_titles.get(str(num), ep["title_ka"])
        focal_chars_ka = [c["name_ka"] for c in ep.get("focal_characters", [])]
        chapters = ep["chapters"]
        ch_span = str(chapters[0]) if len(chapters) == 1 else f"{chapters[0]}-{chapters[-1]}"

        act_title_ka = ep["act_title_ka"]
        for r, n in roman_to_num.items():
            act_title_ka = re.sub(rf"\b{r}\b", n, act_title_ka)

        ep_entry = {
            "episode_number": num,
            "act_number": ep["act_number"],
            "act_title_ka": act_title_ka,
            "title_ka": ep["title_ka"],
            "short_title_ka": short_title,
            "chapters": chapters,
            "chapter_range_label_ka": ep["chapter_range_label_ka"],
            "chapter_span_ka": ch_span,
            "stanza_range": ep["stanza_range"],
            "stanza_start": ep["stanza_start"],
            "stanza_end": ep["stanza_end"],
            "mode": ep["mode"],
            "mode_label_ka": ep["mode_label_ka"],
            "primary_realm": {
                "number": ep["primary_realm"]["number"],
                "name_ka": ep["primary_realm"]["name_ka"],
                "caption_ka": ep["primary_realm"].get("caption_ka", ""),
            },
            "focal_characters_ka": focal_chars_ka,
            "token_action_ka": ep.get("token_action_ka", ""),
            "objective_ka": ep.get("objective_ka", ""),
            "summary_ka": ep.get("summary_ka", ""),
            "quote": {
                "chapter": ep["quote"]["chapter"],
                "stanza_number": ep["quote"]["stanza_number"],
                "line_ka": ep["quote"]["line_ka"],
                "locator_label_ka": ep["quote"]["locator_label_ka"],
            },
        }
        episodes_manifest.append(ep_entry)

    # 12. Characters Manifest (The 21 Tokens)
    # Mapping initial placement and roles
    character_specs = [
        {"id": "rustaveli", "name_ka": "შოთა რუსთაველი", "role_ka": "პოეტი და მთხრობელი", "initial_realm_ka": "რუკის სათაური / ბარათი", "first_ep": 1, "removal_ep": None, "final_realm_ka": "რუკის სათაური / ბარათი"},
        {"id": "rostevan", "name_ka": "როსტევანი", "role_ka": "არაბეთის მეფე", "initial_realm_ka": "არაბეთი (სამეფო 1)", "first_ep": 1, "removal_ep": None, "final_realm_ka": "არაბეთი (სამეფო 1)"},
        {"id": "tinatin", "name_ka": "თინათინი", "role_ka": "არაბეთის მბრძანებელი", "initial_realm_ka": "არაბეთი (სამეფო 1)", "first_ep": 1, "removal_ep": None, "final_realm_ka": "არაბეთი (სამეფო 1)"},
        {"id": "avtandil", "name_ka": "ავთანდილი", "role_ka": "არაბეთის სპასპეტი", "initial_realm_ka": "არაბეთი (სამეფო 1)", "first_ep": 1, "removal_ep": None, "final_realm_ka": "არაბეთი (სამეფო 1)"},
        {"id": "sograt", "name_ka": "სოგრატი", "role_ka": "არაბეთის ვაზირი", "initial_realm_ka": "არაბეთი (სამეფო 1)", "first_ep": 1, "removal_ep": None, "final_realm_ka": "არაბეთი (სამეფო 1)"},
        {"id": "shermadin", "name_ka": "შერმადინი", "role_ka": "ავთანდილის ერთგული მსახური", "initial_realm_ka": "არაბეთი (სამეფო 1)", "first_ep": 1, "removal_ep": None, "final_realm_ka": "არაბეთი (სამეფო 1)"},
        {"id": "tariel", "name_ka": "ტარიელი", "role_ka": "ინდოეთის ამირბარი, ვეფხისტყაოსანი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 3-ში)", "first_ep": 3, "removal_ep": None, "final_realm_ka": "ინდოეთი (სამეფო 3)"},
        {"id": "asmat", "name_ka": "ასმათი", "role_ka": "ნესტანის მესაიდუმლე, ტარიელის თანამგზავრი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 5-ში)", "first_ep": 5, "removal_ep": None, "final_realm_ka": "ინდოეთი (სამეფო 3)"},
        {"id": "nestan", "name_ka": "ნესტან-დარეჯანი", "role_ka": "ინდოეთის მემკვიდრე", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 6-ში)", "first_ep": 6, "removal_ep": None, "final_realm_ka": "ინდოეთი (სამეფო 3)"},
        {"id": "parsadan", "name_ka": "ფარსადანი", "role_ka": "ინდოეთის მეფე", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 6-ში)", "first_ep": 6, "removal_ep": None, "final_realm_ka": "ინდოეთი (სამეფო 3)"},
        {"id": "saridan", "name_ka": "სარიდანი", "role_ka": "ტარიელის მამა, ინდოეთის მეშვიდე მეფე", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 6-ში)", "first_ep": 6, "removal_ep": None, "final_realm_ka": "ინდოეთი (სამეფო 3)"},
        {"id": "davari", "name_ka": "დავარი", "role_ka": "ფარსადანის და, ნესტანის აღმზრდელი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 6-ში)", "first_ep": 6, "removal_ep": 11, "final_realm_ka": "მოხსნილია რუკიდან (ეპ. 11)"},
        {"id": "ramaz", "name_ka": "რამაზი", "role_ka": "ხატაეთის მეფე", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 7-ში)", "first_ep": 7, "removal_ep": None, "final_realm_ka": "ხატაეთი (სამეფო 4)"},
        {"id": "khvarazmsha", "name_ka": "ხვარაზმშას ძე", "role_ka": "ნესტანის სასიძო", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 10-ში)", "first_ep": 10, "removal_ep": 10, "final_realm_ka": "მოხსნილია რუკიდან (ეპ. 10)"},
        {"id": "pridon", "name_ka": "ნურადინ-ფრიდონი", "role_ka": "მულღაზანზარის მმართველი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 12-ში)", "first_ep": 12, "removal_ep": None, "final_realm_ka": "მულღაზანზარი (სამეფო 5)"},
        {"id": "usen", "name_ka": "უსენი", "role_ka": "გულანშაროს ქარავანთუხუცესი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 18-ში)", "first_ep": 18, "removal_ep": None, "final_realm_ka": "გულანშარო (სამეფო 6)"},
        {"id": "fatman", "name_ka": "ფატმან ხათუნი", "role_ka": "უსენის მეუღლე, ნესტანის მხსნელი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 17-ში)", "first_ep": 17, "removal_ep": None, "final_realm_ka": "გულანშარო (სამეფო 6)"},
        {"id": "chashnagiri", "name_ka": "ჭაშნაგირი", "role_ka": "გულანშაროს მეფის მსახური", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 17-ში)", "first_ep": 17, "removal_ep": 17, "final_realm_ka": "მოხსნილია რუკიდან (ეპ. 17)"},
        {"id": "surkhavi", "name_ka": "სურხავი", "role_ka": "გულანშაროს ქალაქის მცველი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 18-ში)", "first_ep": 18, "removal_ep": None, "final_realm_ka": "გულანშარო (სამეფო 6)"},
        {"id": "dulardukht", "name_ka": "დულარდუხტი", "role_ka": "ქაჯეთის დედოფალი", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 18-ში)", "first_ep": 18, "removal_ep": 21, "final_realm_ka": "მოხსნილია რუკიდან (ეპ. 21)"},
        {"id": "rosan", "name_ka": "როსანი", "role_ka": "ქაჯეთის მემკვიდრე", "initial_realm_ka": "რეზერვი (შემოდის ეპ. 18-ში)", "first_ep": 18, "removal_ep": 21, "final_realm_ka": "მოხსნილია რუკიდან (ეპ. 21)"},
    ]

    characters_manifest = []
    for spec in character_specs:
        cid = spec["id"]
        disp = disp_data.get(cid, {})
        ep_pres = char_cards_by_id[cid]["episode_presence"]
        characters_manifest.append({
            "id": cid,
            "name_ka": spec["name_ka"],
            "short_name_ka": disp.get("short_name", spec["name_ka"]),
            "role_ka": spec["role_ka"],
            "initial_placement_ka": spec["initial_realm_ka"],
            "first_active_episode": spec["first_ep"],
            "removal_episode": spec["removal_ep"],
            "final_realm_ka": spec["final_realm_ka"],
            "included_episodes": ep_pres["included_episodes"],
            "token_action_only_episodes": ep_pres["token_action_only_episodes"],
            "short_description_ka": disp.get("short_description", ""),
        })

    # 13. Print & Production Specifications
    print_production = {
        "formats": {
            "A4": {
                "name_ka": "დიდი ფორმატი (210 × 297 მმ)",
                "width_mm": 210,
                "height_mm": 297,
                "pages": 2,
                "margins_mm": 9.0,
                "safe_margin_mm": 8.0,
                "min_font_pt": 9.0,
                "body_font_pt": 10.4,
                "recommended_paper": "200-250 გრ/მ² მქრქალი ან აბრეშუმისებრი მუყაო",
                "duplex_rule_ka": "ორმხრივი ბეჭდვა გრძელ კიდეზე გადაბრუნებით",
                "file_path": "output/rulebook/pantersskin-rulebook-ka-a4.pdf",
            },
            "A5": {
                "name_ka": "კომპაქტური ფორმატი (148 × 210 მმ)",
                "width_mm": 148,
                "height_mm": 210,
                "pages": 2,
                "margins_mm": 9.0,
                "safe_margin_mm": 8.0,
                "min_font_pt": 8.0,
                "body_font_pt": 8.2,
                "recommended_paper": "200-250 გრ/მ² მქრქალი მუყაო",
                "duplex_rule_ka": "ორმხრივი ბეჭდვა გრძელ კიდეზე გადაბრუნებით",
                "file_path": "output/rulebook/pantersskin-rulebook-ka-a5.pdf",
            },
        },
        "general_instructions_ka": [
            copy_data["print_ka"],
            "დაბეჭდეთ რეალური ზომით (100% მასშტაბი). გამორთეთ გვერდზე მორგების (fit to page) პარამეტრი.",
            "ფურცელს დაჭრა არ სჭირდება — განლაგება ზუსტად ერგება სტანდარტულ დიდ ან კომპაქტურ ფურცელს.",
            "გვერდი 1 შეიცავს წესებსა და მექანიკებს; გვერდი 2 შეიცავს მომზადებასა და 24 ეპიზოდის სწრაფ ცნობარს.",
        ],
    }

    # 14. Full Root Object Assembly
    rulebook_data = {
        "$schema": "./rulebook-data.schema.json",
        "schema_version": "1.0.0",
        "meta": meta,
        "overview": overview,
        "components": components,
        "setup_steps": setup_steps,
        "gameplay_loop": gameplay_loop,
        "token_actions": token_actions,
        "flashback_rules": flashback_rules,
        "scale_rules": scale_rules,
        "victory": victory,
        "realms": realms,
        "characters_manifest": characters_manifest,
        "episodes": episodes_manifest,
        "print_production": print_production,
        "source_interpretations": copy_data.get("source_interpretations", []),
    }

    # Validate no Latin letters in Georgian texts
    def deep_check(obj, path=""):
        if isinstance(obj, str):
            if path.endswith("_ka") or "instruction_ka" in path or "overview" in path:
                # Don't check schema url or IDs
                if not obj.startswith("http") and not obj.startswith("output/") and not obj.startswith("assets/"):
                    assert_no_latin_in_georgian(obj, path)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                deep_check(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                deep_check(v, f"{path}[{i}]")

    deep_check(rulebook_data)

    # Save to both target locations
    OUT_PNP.parent.mkdir(parents=True, exist_ok=True)
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)

    json_text = json.dumps(rulebook_data, ensure_ascii=False, indent=2)
    OUT_PNP.write_text(json_text, encoding="utf-8")
    OUT_DATA.write_text(json_text, encoding="utf-8")

    print(f"Successfully generated rulebook data:")
    print(f"  - {OUT_PNP} ({len(json_text)} bytes, {len(rulebook_data['episodes'])} episodes, {len(rulebook_data['characters_manifest'])} characters)")
    print(f"  - {OUT_DATA} ({len(json_text)} bytes)")


if __name__ == "__main__":
    build_rulebook_data()
