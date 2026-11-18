# Tzeentch Scenario Editor

**Tzeentch Scenario Editor** and its logo were made with AI (claude.ai)

Designed for *Medieval II: Total War - Beginning of The End Times* (BOTET mod), coded in Python

---

## -INFORMATION-

* The editor will never add or modify any of the mod files
* `"_internal"` folder contains the editor's resources, do not delete it
* `"m2tw_scenario_editor_config.json"` stores the editor's saved preferences (colors/paths...), you can delete it anytime

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

> * Map folders need to be placed in: `Medieval II - Total War\mods\BOTETv3\data\world\maps\battle`
> * `battle_descriptions.txt` goes in: `Medieval II - Total War\mods\BOTETv3\data\text` (you can replace the original file)
> * `battle_descriptions.txt` is not required for a scenario to work but all players must have the same scenario folder

---

## -NOTES-

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
