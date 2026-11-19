# Tzeentch Scenario Editor

**Tzeentch Scenario Editor** and its logo were made with AI (claude.ai)

Designed for *Medieval II: Total War - Beginning of The End Times* (BOTET mod), coded in Python

---

## -INFORMATION-

* The editor will never add or modify any of the mod files
* `"_internal"` folder contains the editor's resources, do not delete it
* `"Config.json"` stores the editor's saved preferences (colors/paths...), you can delete it anytime

---

## -HOW TO USE-

1. Open Tzeentch Scenario Editor
2. You can choose between English and French
3. Select the location of your `Data` folder that is inside your BOTET mod
4. The editor will load units, weather and map coordinates
5. You can now create a lot of different scenarios and even generate one randomly
6. You don't need to fill in Custom Maps/Snapshot/Loading Screen: scenarios are generated with world map coordinates
7. Custom map is only if you want to copy an existing `map.wfc`
8. Click `"Random scenario..."` (top left) to set random parameters
9. Click `">GENERATE SCENARIO"` (top right) to create your scenario
10. If you want to make your scenario for Solo, tick the option in the top right corner

### When you click `">GENERATE SCENARIO"`:
* It will create a folder next to the editor, containing your scenario (`descr_battle.txt`) and its thumbnail (`snapshot_battle.tga`)
* It will also create, and update, a `battle_descriptions.txt` file next to the editor: it serves to display details of maps in the game menu
* The editor will automatically add your scenario's summary to the `battle_descriptions.txt` (the one in the editor folder): read the tooltips in the editor for more information

* **Map folders** need to be placed in: `Medieval II - Total War\mods\BOTETv3\data\world\maps\battle`
* **`battle_descriptions.txt`** goes in: `Medieval II - Total War\mods\BOTETv3\data\text` (you can replace the original file)
* **`battle_descriptions.txt` is not required** for a scenario to work, **but all players must have the same scenario folder**

---

## -RULES & MECHANICS-

*(Medieval II Total War 1.52 + BOTET v3 - rules derived from in-game testing and current editor behavior: v2.1)*

### 1. ARMIES AND UNITS
* **Maximum armies:** 8 armies max; a faction can only appear once (duplicates are forbidden).
* **Maximum units:** 20 units max per army.
* **Faction restrictions:** Units from another faction cannot be added to an army (blocked manually; flagged on import). Auxiliary units of a faction are only available if the scenario's **"Auxiliary"** option is enabled.
* **Unit copies & extra cost:** Beyond a unit's max copy limit, each additional copy costs the unit's price (with upgrades) `+ (rank - max) x extra_cost`. This extra cost is the 8th `stat_cost` value: equal to the base cost for most units (max 4: 5th = x2, 6th = x3...), and `65535` for generals and a few unique units.
  * *Measured in-game:* Stormvermin Bg (Skaven general) level 9, armour 1, weapon 2: `6090` / `71625` / `137160` / `202695` / `268230`; without upgrades: `840` / `66375` / `131910`... Placing multiple copies of the same general is still possible (at a very high cost).
* **Unit cost formula:** `base cost + armour x armour cost + weapon x weapon cost`; the experience multiplier only applies to multiples of 25 of the cost (`580 -> 575 x multiplier + 5`).
* **Experience & Armour:** Experience up to 3 in multiplayer, up to 9 only with **"Solo scenario"**. Armour up to the unit's maximum.
* **Unit sizes:** Displayed soldier counts correspond to the **"Large Unit Scale"** setting (the mod's standard scale).
* **Gold & Soldier limits:** Gold: minimum `80` (cheapest unit), maximum `1,000,000`. Max soldiers: minimum `7`, maximum `100,000`.
* **Performance warning:** Beyond 4 teams or 4,000 soldiers, the game displays a performance warning; the editor highlights this in red without blocking it.

### 2. GENERAL *(In-game rule, measured across ~50 test armies)*
An army's general is determined in the following order:
1. The unit with the `general` attribute (**"True General"**, marked with a star), regardless of its position in the list;
2. Otherwise, the **FIRST cavalry unit** in the list, provided it is **not a mercenary** *(if the first cavalry unit is a mercenary, all cavalry units are ignored, even non-mercenary cavalry placed further down)*;
3. Otherwise, the **first siege unit** in the list (mercenary or not);
4. Otherwise, the **1st unit** in the list.

* Cost and soldier count have no effect. List order matters: use the **Move Up / Move Down** buttons.
* The general's row is highlighted in the list (**blue** = male general, **pink** = female general).
* *Verified in-game:* Mercenary siege before or after non-mercenary siege (whichever comes first in the list wins), 100% mercenary armies.
* *Unverified:* Multiple different "True Generals" in the same army (two copies of the same general are possible in the editor, but it is the same unit; two distinct generals do not exist within a single faction). Tests G2/G3 (two generals from other factions) picked the first one in the list.

### 3. SIEGES
* A siege pits two teams against each other: one attacks, the other defends (switching one team's role reverses the other's).
* Only attacking armies can carry siege engines. Available engine types depend on the settlement; **Fortress** and **Citadel** require at least one ram.
* **Carriers:** A unit can carry only one engine. Eligible carriers: **infantry with 10 soldiers or more**.
  * *Never eligible:* Cavalry, siege units, and units tested as ineligible in-game (mages, shamans, wizards, trolls, chaos spawn, minotaurs, banshees, yhetees, torpedoes, etc. — internal list of 38 units). The general can carry an engine if their unit is eligible.
* **Limits per attacking army:** 9 engines of each type, 20 in total.
* **Spacing:** Armies carrying engines get wider line spacing (prevents unit overlap).
* **Siege distance:** Min/max range depends on the settlement; the attacker is placed at the farthest distance by default. Spawns always stay inside the map boundaries.
* **Fort & Motte and Bailey:** Fort adds a single `"fort owner X creator Y"` line after `"weather"` (rams only). Motte and Bailey: defence level 1, rams only, Humans / Elves / Savages cultures.
* **Abandoned engines:** Can only be destroyed by a human teammate; an AI ally can pick them up (standard game behavior).

### 4. RANDOM GENERATION *(Scenarios and Armies)*
* Each army targets the requested gold without exceeding it; max gap of `300` gold below target; max gap of `100` gold between two teams.
* If the faction has a **"True General"** and the budget allows it, it is picked first (no error message if the budget is too low) and is never replaced during value adjustments.
* Other units are picked randomly (infantry, ranged, cavalry, siege with weights), within allowed copy limits; at most 2 siege units per army; auxiliary units only if the option is enabled.
* **Post-pick adjustments:** Units are added, replaced, or upgraded until the army falls within the gold tolerance, followed by saturation (the army cannot afford to buy or upgrade any unit with the remaining gold). With **"Upgrades"** enabled: experience `<= 3`, armour `<= 2`, weapon `<= 1`.
* The general (following the rule in Section 2) is moved to the top of the list at the end of generation.
* **Random siege:** Each attacking army receives one engine per eligible unit (up to 20 max), distributed at a `1 ram / 2 towers / 3 ladders` ratio (within settlement limits), with carriers picked at random, including the general. At least one engine per attacking army; Fortress / Citadel always get a ram. If an army cannot carry any engine, generation retries; if it fails: `"Attacking army ... has no siege engine"`.
* **Impossible values** *(huge gold, tiny soldier limits...)*: The editor places no units or gives up after ~9 seconds without freezing.
* **Options:** Loyal alliances (teams follow allowed alliances), chaotic climates (any season / weather), free map, same spawn, etc.

### 5. IMPORT / EXPORT
* **"Import a scenario"** reads a `descr_battle.txt` file (standard battle or siege: settlement, culture, defence level, fort, engines, roles, same spawn). Positions are recalculated automatically.
* Files are written with `CRLF` line endings; `battle_descriptions.txt` is encoded in `UTF-16 (LE, BOM)` and written in English.
* The settings file is named `Config.json` (located next to the executable).

### 6. UNSUPPORTED / IMPOSSIBLE FEATURES
* Two armies of the same faction; multiple attacking teams in a siege *(failed in-game tests, dropped)*; units from another faction.
* Siege engines on cavalry, siege units, or ineligible units; engines on a non-sieging army; more than 9 engines of one type or 20 in total.
* Picking the general by any means other than list order / unit attributes: the game decides *(see Section 2)*.

---

## -ADDITIONAL NOTES-

* Editor always displays v9.9.9 : Real version number will be on discord and github
* This editor was created to make multiplayer scenarios with AI bots
* There are still maps that can crash the game at the start, picking a fixed location lowers the risk
* Some maps are not fit for siege battles, a warning should tell you. Still, you may try as some will work
* You can create maps with more than 4 teams, up to 8, but the last factions may be off-screen in the menu
* Randomly generated scenarios have been tested a lot, they should almost all work
* Improvements could always be made (perfect settlement coordinates, adding script options...)
* This mod is license-free: you can modify it as you want

---

*-Abyss*
