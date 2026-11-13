# Gotcha Force Setup Guide

## Required software

* Dolphin (a recent version; 2506 or newer recommended).
* A Gotcha Force USA ISO (game id `GG4E08`).
* Archipelago 0.6.7 or newer. It already includes everything the
  client needs to talk to Dolphin (running Archipelago from source
  installs it from the world's `requirements.txt`).

## Patching your ISO (once)

You play a **patched copy** of the game. The patch adds the on-map
mission status display (the X/Y check counters and the colored
mission icons); your original ISO is never modified.

The patch is **the same for every seed**: everything seed-specific
comes from the server while you play. So there is no patch file to
download for your slot — you patch once and reuse the copy for every
multiworld:

1. In the Archipelago Launcher, click **Gotcha Force ISO Patcher**.
2. Select your clean Gotcha Force USA ISO.
3. A copy named like `Gotcha Force (USA) [AP].iso` appears next to
   it. Add that copy to Dolphin and play it from now on.

After updating the apworld, run the patcher again on your clean ISO:
the ` [AP]` copy is refreshed in place. The client tells you when the
copy you are playing has no patch or was made with an older version.

## Playing a seed

1. Generate the multiworld as usual and host it.
2. Start Dolphin and boot your patched copy (the ` [AP]` one).
3. **Use a fresh save for each seed.** Start a New Game and play the
   intro until you reach the world map. Important: the client reads
   your mission victories as checks, so connecting on an old save
   will immediately send checks for everything that save had already
   beaten — and starting a new game will eventually overwrite the
   save on your memory card, so back it up first if you care about it.
4. Open the **Gotcha Force Client** and connect with your slot name.
   On the room page, clicking your slot opens the client already
   pointed at the server; you can also open it from the Archipelago
   Launcher and type the address. Connect early (before or during the
   intro is ideal).
5. The client hooks Dolphin automatically and keeps the game in sync
   from then on: missions open up as you receive Story Keys, beating
   them sends checks, the gacha pops as checks, and received items are
   applied instantly.

## Reading the world map

The map always lists every mission you can currently play (missions
are always repeatable). With the patched copy, each mission also shows
its status at a glance:

* **Green icon** — you already beat that mission.
* **Faded gray icon** — playable, but out of logic for now (you may
  still try it).
* **X/Y counter** — checks found / total checks for that mission. It
  turns yellow when you have found them all.

## The Tracker and Inventory tabs

The client window has two tabs of its own.

The **Tracker** tab lists your playable missions
grouped by map zone, each one listed with its real in-game title
(mission titles repeat, so the number in front is the unique id) and
expandable to show its remaining checks — mission clear checks first,
then rewards, and gacha checks always last. Out-of-logic missions are
dimmed and marked. The number next to a zone or a mission counts the
checks you can get right now; a check that is still out of logic is
shown marked but not counted, and a mission whose remaining checks
are all out of logic is dimmed and marked as a whole. Achievements
that are not tied to one mission appear at the bottom, grouped by
type (Partner Style, Rival Style, Tribe Force, Ace Duel). **Go Mode**,
next to the filter buttons, tells you whether the final mission is
already within reach with what you have: **Yes** in green, **No** in
red. It updates on its own as you play.

The gacha checks of a mission are named after the borg they drop,
which gives away who you will fight there. By default the tab folds
them into a single line per mission, "Gacha: N checks left"; press
**Show gacha spoilers** to see them one by one. The mission counter
is the same either way.

The **Inventory** tab shows what you have and how much is left:
your goal mission, the checks found, Death Crystals, Story Keys, the
GF Energy Cap, the Gotcha Box and G Red, then the zones, the
commanders (with the upgrade level each one has) and the borgs in
your collection, including the fragments still to complete. A counter
turns green once it is complete. It fills as soon as you connect to
the server, even before the game is running, and each group can be
folded; the tabs remember your folds.

## Client commands

* `/checks` — list missions with remaining checks, by zone and with
  their in-game titles (`/checks all` includes out-of-logic ones).
* `/mission` — show the mission currently selected: its id and
  in-game title (useful for bug reports).
* `/dolphin` — connection status.

## Important notes

* Keep the client running while you play; it is the source of truth
  for your progression state.
* The Gotcha Box arrives with **two random borgs** picked by your
  seed (they replace the fixed starter borgs from the original game).
* Some borg items are progression: they are guaranteed to show up
  early-ish in the multiworld, so you always have something to fight
  with. Logic itself only gates missions by GF Energy.
* Save through the normal in-game flow (START on the map, then SAVE).
  Avoid mixing old emulator save states with your current card — the
  game refuses to save if they do not match.
* Story cutscenes and vanilla reward hand-outs are suppressed by
  design: everything flows through Archipelago instead.
