# Hyreon's Fork of CTR Archipelago

This fork improves the design of the randomizer, and provides more customization options. The main repository is focusing on improving raw capabilities like custom levels, which is the more important task, but I want to make sure the experience is consistently good.

In progress changes to the randomizer include but are not limited to:
- Trim down the # of boxes when there's filler in the multi-world ([box-tighten](https://github.com/Hyreon/ctr-archipelago-apworld/tree/box-tighten))
- Forbid duplicate racers on the racer pad locks ([racer-lock-dedupe](https://github.com/Hyreon/ctr-archipelago-apworld/tree/racer-lock-dedupe))

Planned changes to the randomizer include but are not limited to:
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

## box-tighten
- When the amount of locations exceeds the number of mandatory items, boxes are now randomly removed from the seed.
- This is not the default behavior. You can enable it by setting `use_all_boxes` to `false`.

This has a number of knock-on effects on other parts of the code, so the scope was expanded to include the following improvements:
- Rather than hand-rolling a copy of the logic for item generation to predict how many there will be, `create_items` now begins by calling a pure function to decide what items to create. That pure function can be used elsewhere to decide how many locations to use. 
- Rung-sizer has been rewritten:
  - Now uses the new pure function
  - Now uses language in sync with the current state of the project
  - No longer fails when podium is off but items are on, with plenty of item slots; now it only fails when both the podiums and the item boxes are unable to cover required items
- You can now configure the amount of expected filler, allowing a precise amount of Wumpa Fruit or traps to be added to the multiworld. This can also be used to fine-tune in the event that a seed would fail to generate, due to an off-by-one error.
- You can now toggle "comfort items" (the terrain modifiers, like "Ignore Grass" and "Ignore Water") in the config. Setting `use_terrain_modifiers` to `'on'` enables them. They are `padding` by default, meaning they will only be added when there is room to spare - they are preferred to traps and wumpa fruit, but no room will be made for them.
- This toggle is designed to generalize to other items, like Tizi Helper and Turbo Grant. Actually implementing these was deemed out of scope.

DISCLAIMERS:
- Some tests are broken. I'm going to need help with them.
 - Setting `use_all_boxes` to default to true causes tests to break, since it expects specific item boxes. Rather than manually editing each test, I decided to make this default to `false`, even though it is a worse user experience to add so many filler items. Reverting that is beyond my current ability.
 - 24 tests are failing because of the opinionated changes I've made to some core functions.
- Some documentation contained in the create_items function was lost when transferring it to a pure function. If it is essential context, I can dig it back up.

Once these test cases are fixed, a pull request will be created.

```
FAILED worlds/ctr/test/test_character_phase.py::TestAllUnlockedMode::test_the_error_names_both_concrete_fixes - AssertionError: 'character_unlocks' not found in "CTR: the current mandatory item pool exceeds the current available location pool. Reduce the amount of items or increase the amount of locations. Need 14 more locations for 97 unass...
FAILED worlds/ctr/test/test_item_supply.py::TestTierOneFillerFirst::test_it_sheds_only_as_much_filler_as_the_overflow_needs - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestTierOneFillerFirst::test_one_over_sheds_one_filler_and_keeps_the_comfort_pack - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestTierOneFillerFirst::test_progression_is_never_shed - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestTierTwoComfortPack::test_filler_goes_before_the_pack_even_when_both_are_needed - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestTierTwoComfortPack::test_the_pack_goes_whole_and_may_undershoot - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestTierTwoComfortPack::test_the_pack_is_kept_when_dropping_it_would_not_be_enough - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestBundlesJoinTierOneByClassification::test_any_filler_classified_item_is_shed_regardless_of_name - TypeError: '>' not supported between instances of 'frozenset' and 'int'
FAILED worlds/ctr/test/test_item_supply.py::TestFillerFloorForExcludedLocations::test_filler_at_the_floor_is_not_shed - TypeError: shed_overflow() got multiple values for argument 'filler_floor'
FAILED worlds/ctr/test/test_item_supply.py::TestFillerFloorForExcludedLocations::test_only_filler_above_the_floor_is_shed - TypeError: shed_overflow() got multiple values for argument 'filler_floor'
FAILED worlds/ctr/test/test_item_supply.py::TestFillerFloorForExcludedLocations::test_the_floor_pushes_the_overflow_down_to_the_comfort_pack - TypeError: shed_overflow() got multiple values for argument 'filler_floor'
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_disabled_goal_at_rung_ceiling_not_rejected_by_reserve_overestimate - TypeError: required_categories() missing 1 required positional argument: 'remaining_locations_needed'
SUBFAILED(capability='progressive_boost') worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_held_opt_out_fails_instead_of_silently_expanding - AssertionError: OptionError not raised
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_held_opt_out_fails_instead_of_silently_expanding - AttributeError: '_AssertRaisesContext' object has no attribute 'exception'
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_host_veto_raises_instead_of_mutating - AttributeError: module 'worlds.ctr.location_sizer' has no attribute 'apply_rung_sizing'
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_legacy_host_opt_in_cannot_override_yaml - AttributeError: module 'worlds.ctr.location_sizer' has no attribute 'apply_rung_sizing'
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_master_toggle_is_never_enabled - AssertionError: 'never enables that master toggle' not found in "CTR: the current mandatory item pool exceeds the current available location pool. Reduce the amount of items or increase the amount of locations. Need 16 more locatio...
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_sufficient_default_layout_is_a_noop - AttributeError: module 'worlds.ctr.location_sizer' has no attribute 'apply_rung_sizing'
FAILED worlds/ctr/test/test_location_sizer.py::TestRungSizingGeneration::test_supply_poor_per_character_gets_numeric_capability_error - AssertionError: 'would add 192 item(s)' not found in "CTR: the current mandatory item pool exceeds the current available location pool. Reduce the amount of items or increase the amount of locations. Need 142 more locations for 289...
FAILED worlds/ctr/test/test_oxide_1_optional.py::TestOxide1Optional::test_filler_tight_pool_reserves_excluded_reward_with_capabilities - AssertionError: 0 not greater than or equal to 1
FAILED worlds/ctr/test/test_progressive_capability.py::TestCapabilityPoolOverflowRaises::test_setup_raises_option_error - AssertionError: 'Progressive Boost' not found in "CTR: the current mandatory item pool exceeds the current available location pool. Reduce the amount of items or increase the amount of locations. Need 29 more locations for 112 unas...
FAILED worlds/ctr/test/test_progressive_capability.py::TestStatsPerCharacterSupplyPoor::test_raises_option_error - AssertionError: 'would add 192 item(s)' not found in "CTR: the current mandatory item pool exceeds the current available location pool. Reduce the amount of items or increase the amount of locations. Need 142 more locations for 289...
SUBFAILED(mode='locations_and_items') worlds/ctr/test/test_trial_lettersanity_admission.py::TestTrialLettersanityAdmission::test_sizer_counts_custom_demand_before_regions_without_rng - AssertionError: 0 != 2
SUBFAILED(mode='items_only') worlds/ctr/test/test_trial_lettersanity_admission.py::TestTrialLettersanityAdmission::test_sizer_counts_custom_demand_before_regions_without_rng - AssertionError: 0 != 3
```

## racer-lock-dedupe
- Can now configure race pads to avoid (or even to prefer) duplicates, as an absolute rule or as a bias
- Handles just fine even when pads > racers
- Waiting for a sync with box-tighten, upstream changes, and ensuring that tests pass before a pull request is ready.


> [!NOTE]
> **This is the Crash Team Racing (CTR) Archipelago fork.** The CTR world lives at [`worlds/ctr/`](worlds/ctr/). See the [CTR world README](worlds/ctr/README.md) for the project introduction, player links, credits and AI usage disclosure. The companion game client is [`dowlle/ctr-native-ap`](https://github.com/dowlle/ctr-native-ap), a native CTR PC build that connects to Archipelago in-process with no emulator or ROM patching.
>
> **Status:** supported player releases are published as matched client and `ctr.apworld` pairs on the [client release page](https://github.com/dowlle/ctr-native-ap/releases). Development branches in this fork may be ahead of the latest player release. Everything below this note is the upstream Archipelago README.
