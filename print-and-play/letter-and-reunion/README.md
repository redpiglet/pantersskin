# Panther's Skin: The Letter and the Reunion

A small cooperative print-and-play prototype for 2–4 players who already know the poem. Allow about 15–20 minutes for a first play. This is one chapter, not a complete game of the whole poem.

The group makes the familiar events unfold: Avtandil sends news ahead, brings Nestan's letter to Tariel, reunites the company at the cave, and carries the third suit of armor to Pridon.

## Print and prepare

Print `output/pdf/panthers-skin-letter-and-reunion.pdf` on four single-sided A4 sheets at actual size. Page 2 is landscape; use automatic orientation. Cut the pieces on page 3. Keep the character cards beside the board; move the small character discs on the board. Coins or handwritten counters can replace the discs.

You need four character discs, four character cards, three object cards, two action markers, one round marker, one notice disc (N), and a pencil. Keep all large cards beside the board; only small discs move on it. All information is public. The portraits are reused from this project's character artwork.

## Choose characters

Each player chooses a character to voice: Avtandil, Tariel, Asmat, or Pridon. Read that character's scene passages when they occur. Unchosen characters are shared. **All four characters are available to the group, and any player may activate any character.** Choosing a favorite never removes somebody from the poem or leaves a player waiting for an offstage role.

Rotate the lead player each round. The lead proposes the first action; decide the second together. Different players can carry out the two actions.

## Setup

- Put Avtandil in Gulansharo, Tariel in the Reeds, Asmat in the Cave, and Pridon in Mulghazanzar.
- Put **Nestan's letter + veil fringe** under Avtandil's character card.
- Put **Avtandil's notice**, **Armor for Pridon**, and notice disc **N** aside, not under a character.
- Leave the two story checkboxes and Pridon's three preparation boxes empty.
- Put the round marker on 1. Keep both action markers available.
- Read scene 1 on page 4.

## Each round

Perform **up to two actions**, one after the other. Each action activates one character. A character may act **only once in the round**. Put an action marker on that character's card. The first action can unlock the second action immediately.

At round end, **if N has been dispatched and is still in transit**, move it one step along its dashed courier route: **Gulansharo → At sea → Pridon**. This is automatic and uses no action. The first step happens at the end of the round in which the notice was sent. At arrival, put the notice card under Pridon's character card and set N aside. The large card remains aside until that delivery.

Retrieve the action markers and advance the round marker. You may end a round early; unused actions are lost.

## Available actions

| Actor | Action | Conditions and result |
|---|---|---|
| Avtandil | Send notice | Once, at Gulansharo, before departure. Put notice disc **N** in Gulansharo; leave the large notice card aside until delivery. |
| Avtandil, Tariel, or Asmat | Travel | Move that one disc one solid arrow forward. Observe the story gates below. |
| Tariel | Receive Nestan's letter | At the Reeds, with Avtandil present. Move the letter + fringe card from Avtandil to Tariel. Mark **Letter received** and read scene 2. |
| Tariel | Open the chambers | At the Cave, with Avtandil and Asmat present, after receiving the letter. Mark **Chambers opened**. The two knights equip themselves. Choose Avtandil, Tariel, or Asmat to carry the bundled third suit; put **Armor for Pridon** under that character's card. Read scene 3. |
| Pridon | Read the notice | Only after his notice reaches him. Mark the first preparation box. |
| Pridon | Gather 300 horsemen | Only after reading the notice. Mark the second preparation box. |
| Pridon | Ready the crossing | Only after gathering the horsemen. Mark the third preparation box. |
| Armor carrier | Give Pridon his armor | At Mulghazanzar. Move the bundle to Pridon's character card. This is one action by the carrier; Pridon need not spend an action. |

The armor carrier is chosen when the chambers open and stays the carrier until delivery. There are no other object transfers in this prototype. Pridon stays at Mulghazanzar throughout this chapter. Preparation actions can happen while the travelers are on the road.

Each named action except **Travel** can happen only once. Presence at a meeting does not activate a character: only the actor named in the table uses an action.

## Story gates

The board's arrows describe one-way progress through this chapter.

1. Avtandil sends his notice before leaving Gulansharo.
2. Avtandil and Tariel remain at the Reeds until Tariel receives Nestan's letter.
3. Everyone at the Cave stays there until the chambers are opened.

After opening the chambers, move the three traveling discs separately along the Riding Road to Mulghazanzar. Each move advances one disc. This models the party's progress; the poem describes the three traveling together, with Asmat initially riding behind one of the knights.

## Finish

Finish immediately and record the **current round** when:

- Avtandil, Tariel, and Asmat are all at Mulghazanzar with Pridon;
- Pridon's three preparation boxes are marked;
- the armor bundle has been delivered to Pridon.

Read scene 4. The three sworn brothers leave for Kadjeti; Asmat stays in Pridon's household. That departure is the ending, not an extra action.

For your first play, try to finish within **12 rounds**. A **10-round** reunion is the tighter puzzle benchmark. If you exceed the target, keep playing and record your finishing round. The poem's outcome remains the same. Continue counting on paper beyond round 12 if needed.

The timing and 10-round lower bound have been checked with a state-space solver. Human enjoyment, play time, and the first-play target have not yet been tested at a table.

## The four scene passages

### 1. News from Gulansharo

Nestan's reply has reached Avtandil. Her letter and a fringe from her veil will speak to Tariel across their separation. Avtandil also writes to Pridon: Nestan has been found in Kadjeti, and the brothers will come to him. Pridon's retainers carry this notice while Avtandil takes the sea route toward Tariel.

### 2. The letter among the reeds

Avtandil finds Tariel near the cave and brings him Nestan's words and the veil token. She remains faithful to him, but fears that he will throw his life away against the fortress. The letter restores their connection. The friends must now travel back to Asmat, who will recognize Nestan's handwriting and share their joy.

### 3. The unopened chambers

At Tariel's suggestion, the three open the stored treasure of the Devis. Among the riches they find three exceptional suits of armor and their weapons. Avtandil and Tariel equip themselves. The third suit is bundled as a gift for Pridon. Now the three will travel toward his kingdom.

### 4. The reunion

The companions reach Pridon's kingdom and give him his armor. Their plans become a common undertaking: Pridon provides three hundred selected horsemen and knows the way toward Kadjeti. Asmat remains in his household. The three sworn brothers depart together; the next chapter would follow their approach to the fortress.

## Source and adaptation notes

The story follows the actual stanza text in the project's `data/chapters/chapter-52.json`, `chapter-53.json`, and `chapter-54.json`, especially Georgian-edition stanzas 1318–1325, 1327–1361, 1364–1374, and 1386–1392. The English translation uses different stanza numbering. The passages above are new summaries, not quotations from the poem.

We checked the stanza text because some generated summaries in the project conflict with it. Nestan's message warns Tariel against dying in an assault; it is not an invitation to rush the fortress. The text finds the armor in the Devis' treasury; this prototype does not call it Kadji-forged.

Waypoints, the courier's two round-ends, separate traveler movements, three preparation actions, freedom to choose an armor carrier, and round benchmarks are **gameplay abstractions**. The poem does not supply these distances, durations, or an armor carrier. Preparing a crossing before the reunion represents Pridon's readiness; the detailed planning is compressed here. The horse-herd prank, hospitality, pirate spoils, and buying Asmat a horse are omitted from the playable tasks.

The four characters are selected for this excerpt. Nestan, Tinatin, and others would have active chapters in a fuller game; their absence here is not a rule for the entire design.

## Check or rebuild

Run `check_schedules.py` with Python 3 to examine legal schedules. Run `build_packet.py` with a Python environment containing ReportLab and Pillow to rebuild the PDF. The builder writes only under `output/pdf` and `tmp/pdfs`.

## A playtest record

- Players / date:
- Armor carrier:
- Finishing round:
- A decision that required discussion:
- An action or rule that was unclear:
- Did moving the pieces help you experience the scene?
- Which character needed a more interesting part?

The next design decision should follow an actual playthrough of this small chapter. This prototype has one fixed plot and a modest scheduling puzzle; it does not yet establish enough variety for a complete game.
