# Hyreon's Fork of CTR Archipelago

This fork improves the design of the randomizer, and provides more customization options. The main repository is focusing on improving raw capabilities like custom levels, which is the more important task, but I want to make sure the experience is consistently good.

Planned changes to the randomizer include but are not limited to:
- Trim down the # of boxes when there's filler in the multi-world (box-tighten)
- Forbid duplicate racers on the racer pad locks (racer-lock-dedupe)
- Forbid distributing character upgrades until the character is potentially available (progressive-stats-lockgic)
- Forbid distributing CTR letters until the track is potentially available (lettersanity-lockgic)
- Plando support for racer pad locks, so that you can assign a racer to a track (racer-lock-plando)
- Configuration to disable duplicate tracks inside a single cup (cup-track-dedupe)
- Configuration to set starting and target stats for progressive stats distribution (progressive-stats-config)

Planned changes to the game include but are not limited to:
- When lettersanity is enabled, the unlocked letters are shown near the pad. The icon is different when a course has letters to touch but can't be complete (lettersanity-progress-counter)
- Turn on/off USF lock; if off, USF is always available from corresponding USF pads (usf-availability)
- An alternative logic for boosts; if enabled, you unlock mini-turbos 1, 2, and 3 rather than miniturbos 1-3 + boost pads + items, and then a USF cheat, and then a blue fire cheat (turbo-alternative-logic)
- Location checks for entering a level, so that we can unlock new items (or traps) upon entering a level (location-enter-track)
- Make cheats like ignore grass, blue fire, tizi helper configurable as character-unique (cheats-character-unique)
- Add team pad locks beside racer pad locks, so that a level could be locked behind say any one of the four racers Crash, Coco, Polar and Pura (racer-lock-team-based)
- An option to turn character lives into items, rather than single unlockables. Character lives are lost when you win, lose or exit a track. If you have 0 lives, you get 1 life for each unlocked character and trigger a deathlink (character-lives)
- Item config: you can turn on/off items that you've picked up, with a limited number of item locks available (item-inventory-screen)

Much like the original project, this uses AI-assisted development.

- For the original repository, see [here](https://github.com/dowlle/ctr-archipelago-apworld).
- To see my other work, including my Steam game Little Blue, visit [my personal website](https://hyreon.top).

> [!NOTE]
> **This is the Crash Team Racing (CTR) Archipelago fork.** The CTR world lives at [`worlds/ctr/`](worlds/ctr/). See the [CTR world README](worlds/ctr/README.md) for the project introduction, player links, credits and AI usage disclosure. The companion game client is [`dowlle/ctr-native-ap`](https://github.com/dowlle/ctr-native-ap), a native CTR PC build that connects to Archipelago in-process with no emulator or ROM patching.
>
> **Status:** supported player releases are published as matched client and `ctr.apworld` pairs on the [client release page](https://github.com/dowlle/ctr-native-ap/releases). Development branches in this fork may be ahead of the latest player release. Everything below this note is the upstream Archipelago README.

---

# [Archipelago](https://archipelago.gg) ![Discord Shield](https://discordapp.com/api/guilds/731205301247803413/widget.png?style=shield) | [Install](https://github.com/ArchipelagoMW/Archipelago/releases)

Archipelago provides a generic framework for developing multiworld capability for game randomizers. In all cases,
presently, Archipelago is also the randomizer itself.

Currently, the following games are supported:

* The Legend of Zelda: A Link to the Past
* Factorio
* Subnautica
* Risk of Rain 2
* The Legend of Zelda: Ocarina of Time
* Timespinner
* Super Metroid
* Secret of Evermore
* Final Fantasy
* VVVVVV
* Raft
* Super Mario 64
* Meritous
* Super Metroid/Link to the Past combo randomizer (SMZ3)
* ChecksFinder
* Hollow Knight
* The Witness
* Sonic Adventure 2: Battle
* Starcraft 2
* Donkey Kong Country 3
* Dark Souls 3
* Super Mario World
* Pokémon Red and Blue
* Hylics 2
* Overcooked! 2
* Zillion
* Lufia II Ancient Cave
* Blasphemous
* Wargroove
* Stardew Valley
* The Legend of Zelda
* The Messenger
* Kingdom Hearts 2
* The Legend of Zelda: Link's Awakening DX
* Adventure
* DLC Quest
* Noita
* Undertale
* Bumper Stickers
* Mega Man Battle Network 3: Blue Version
* Muse Dash
* DOOM 1993
* Terraria
* Lingo
* Pokémon Emerald
* DOOM II
* Shivers
* Heretic
* Landstalker: The Treasures of King Nole
* Final Fantasy Mystic Quest
* TUNIC
* Kirby's Dream Land 3
* Celeste 64
* Castlevania 64
* A Short Hike
* Yoshi's Island
* Mario & Luigi: Superstar Saga
* Bomb Rush Cyberfunk
* Aquaria
* Yu-Gi-Oh! Ultimate Masters: World Championship Tournament 2006
* A Hat in Time
* Old School Runescape
* Kingdom Hearts 1
* Mega Man 2
* Yacht Dice
* Faxanadu
* Saving Princess
* Castlevania: Circle of the Moon
* Inscryption
* Civilization VI
* The Legend of Zelda: The Wind Waker
* Jak and Daxter: The Precursor Legacy
* Super Mario Land 2: 6 Golden Coins
* shapez
* Paint
* Celeste (Open World)
* Choo-Choo Charles
* APQuest
* Satisfactory
* EarthBound
* Mega Man 3

For setup and instructions check out our [tutorials page](https://archipelago.gg/tutorial/).
Downloads can be found at [Releases](https://github.com/ArchipelagoMW/Archipelago/releases), including compiled
windows binaries.

## History

Archipelago is built upon a strong legacy of brilliant hobbyists. We want to honor that legacy by showing it here.
The repositories which Archipelago is built upon, inspired by, or otherwise owes its gratitude to are:

* [bonta0's MultiWorld](https://github.com/Bonta0/ALttPEntranceRandomizer/tree/multiworld_31)
* [AmazingAmpharos' Entrance Randomizer](https://github.com/AmazingAmpharos/ALttPEntranceRandomizer)
* [VT Web Randomizer](https://github.com/sporchia/alttp_vt_randomizer)
* [Dessyreqt's alttprandomizer](https://github.com/Dessyreqt/alttprandomizer)
* [Zarby89's](https://github.com/Ijwu/Enemizer/commits?author=Zarby89)
  and [sosuke3's](https://github.com/Ijwu/Enemizer/commits?author=sosuke3) contributions to Enemizer, which make up the
  vast majority of Enemizer contributions.

We recognize that there is a strong community of incredibly smart people that have come before us and helped pave the
path. Just because one person's name may be in a repository title does not mean that only one person made that project
happen. We can't hope to perfectly cover every single contribution that lead up to Archipelago, but we hope to honor
them fairly.

### Path to the Archipelago

Archipelago was directly forked from bonta0's `multiworld_31` branch of ALttPEntranceRandomizer (this project has a
long legacy of its own, please check it out linked above) on January 12, 2020. The repository was then named to
_MultiWorld-Utilities_ to better encompass its intended function. As Archipelago matured, then known as
"Berserker's MultiWorld" by some, we found it necessary to transform our repository into a root level repository
(as opposed to a 'forked repo') and change the name (which came later) to better reflect our project.

## Running Archipelago

For most people, all you need to do is head over to
the [releases page](https://github.com/ArchipelagoMW/Archipelago/releases), then download and run the appropriate
installer, or AppImage for Linux-based systems.

If you are a developer or are running on a platform with no compiled releases available, please see our doc on
[running Archipelago from source](docs/running%20from%20source.md).

## Related Repositories

This project makes use of multiple other projects. We wouldn't be here without these other repositories and the
contributions of their developers, past and present.

* [z3randomizer](https://github.com/ArchipelagoMW/z3randomizer)
* [Enemizer](https://github.com/Ijwu/Enemizer)
* [Ocarina of Time Randomizer](https://github.com/TestRunnerSRL/OoT-Randomizer)

## Contributing

To contribute to Archipelago, including the WebHost, core program, or by adding a new game, see our
[Contributing guidelines](/docs/contributing.md).

## FAQ

For Frequently asked questions, please see the website's [FAQ Page](https://archipelago.gg/faq/en/).

## Code of Conduct

Please refer to our [code of conduct](/docs/code_of_conduct.md).
