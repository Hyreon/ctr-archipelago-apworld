"""Overflow shedding: what a seed gives up when it has more items than places.

Archipelago requires a seed to end with exactly as many items as unfilled
locations. CTR normally reaches that by TOP-UP: build the items the seed must
have, then mint `Wumpa Fruit` for every location left over (42 of them on a
default seed). That direction is easy and lives in `create_items`.

This module owns the other direction, which is rare and was wrong until
2026-08-18: what to give up when the pool comes out BIGGER than the supply.

AFTER THE ITEM BOX PADDING CHANGES provided by Hyreon (2026-09-12),
only filler items are removed. This overrules Stef (2026-08-18),
who decided that when all the filler has been removed, the comfort pack
should be cut out entirely if it would make room. However, since the comfort
pack is now toggleable like the Turbo Grant or Tizi Helper, and there is an
overabundance of checks from item boxes, a new ruling is needed. The comfort
pack is no longer quietly disabled when the user has it on, and can now be
disabled by the user when they want to avoid it in their seed.

THE ORDER IS RULED (Hyreon, 2026-09-12), not a preference:

  1. FILLER, because that is what filler is for. A comfort item is never
     dropped while a SHEDDABLE filler item is still in the pool.

     Not all filler is sheddable. Archipelago fills `EXCLUDED` locations from
     the filler pool ALONE (`Fill.py`: excluded locations are filled from
     `filleritempool`, and `usefulitempool` only joins for ordinary locations
     afterwards), so a seed must keep at least one filler item per excluded
     location or fill dies with "Not enough filler items for excluded
     locations". CTR always has at least one: `_install_goal` marks the goal
     location EXCLUDED (#27) so that no world's progression can land on it, and
     a player's own `exclude_locations` adds more.

     This was found the hard way on 2026-08-18: a first cut of this module shed
     filler without a floor, passed its own 2000-seed item/location arm, and
     then failed the matrix's default arm on two seeds out of five thousand
     with exactly that FillError. Shedding the last filler in favour of keeping
     comfort items is the one way to satisfy the item/location count and still
     make the seed unfillable.
  2. Nothing else. A seed still over after both is genuinely unsatisfiable and
     `create_items` refuses it with an OptionError naming the shortfall.

WHAT IS NEVER SHED. Progression, because dropping it can make a seed
unwinnable. And the option-created single items (`Tizi Helper`, `Turbo Grant`):
those are toggles the player switched on, so a seed that cannot fit them is
refused rather than silently ignoring the option. Neither is filler-classified,
so both fall out of tier 1 for free; this module never needs to name them.

TIER 1 KEYS ON CLASSIFICATION, NOT ON A NAME. `Wumpa Fruit` is the only filler
the static table creates today, but `Small Wumpa Bundle` and `Big Wumpa Bundle`
are filler too and currently sit frozen-but-inert at count 0. They join tier 1
automatically on the day an option creates them, with no change here.

WHY THIS EXISTS AS A FUNCTION. The behaviour it replaced was four lines inline
in `create_items` and could only be tested by generating a seed whose option
combination happened to land on the exact overflow under test. That is how the
all-or-nothing bug survived: it needed a seed six over, which is roughly one in
five hundred. Here every tier is reachable with a synthetic pool.
"""
from typing import Iterable, List, Sequence

from BaseClasses import Item, ItemClassification


def shed_overflow(pool: Sequence[Item], unfilled: int,
                  surface_item_names: Iterable[str],
                  filler_floor: int = 0) -> List[Item]:
    """Return the pool reduced toward `unfilled`, in the ruled order.

    `filler_floor` is how many filler items this seed must KEEP for its
    `EXCLUDED` locations, which only filler can fill. Callers pass
    `elastic_bounds.estimated_filler_reserve`, which is the estimate rather than
    the exact count on purpose: AP core applies a player's `exclude_locations`
    as location progress state AFTER every world's `create_items`, so the exact
    number is not knowable here.

    Returns the pool unchanged when it already fits. May return a pool that is
    still too big (tier 3 is the caller's refusal) or, after tier 2, one that is
    now SMALLER than `unfilled`; the caller's filler top-up closes that gap.
    """
    if len(pool) <= unfilled:
        return list(pool)

    surface_names = frozenset(surface_item_names)

    # Tier 1: filler, exactly as much as the overflow needs and no more, and
    # never below the floor the excluded locations require.
    overflow = len(pool) - unfilled
    total_filler = sum(1 for item in pool
                       if item.classification == ItemClassification.filler)
    sheddable = max(0, total_filler - max(0, filler_floor))
    to_shed = min(overflow, sheddable)

    shed = 0
    kept: List[Item] = []
    for item in pool:
        if shed < to_shed and item.classification == ItemClassification.filler:
            shed += 1
            continue
        kept.append(item)
    pool = kept

    if len(pool) <= unfilled:
        return pool

    return pool

import json
import pkgutil

from .Items import load_item_table
from .itemsanity import WEAPONS, ITEM_NAMES
from .relic_tiers import RELIC_TIERS
from .tizi_helper import TIZI_HELPER_ITEM
from .turbo_grant import TURBO_GRANT_ITEM
from . import tizi_helper
from . import turbo_grant
from . import wumpa_family
from . import characters
from . import lettersanity
from . import progressive_capability

# Comfort-only issues #14/#15 pack. It stays atomic when a reduced location
# set cannot host all five, rather than emitting a seed-dependent subset.
SURFACE_ITEM_NAMES = frozenset({
    "Ignore Grass", "Ignore Dirt", "Ignore Snow", "Ignore Water", "Ignore Ice",
})

def compute_item_pool_data(world):
    """Pure. No Item object is constructed (world.create_item is
    itself a side-effecting call, per the caller's own instruction), no
    location is touched, no world/multiworld attribute is mutated. Every
    real commitment is returned as plain data for apply_item_pool_data to
    act on.

    This does not serve as a guarantee of what the actual item pool will
    look like. Random values and custom constraints may change what
    the seed actually uses.
    """
    _vmap = json.loads(
        pkgutil.get_data(__package__, "data/vanilla_mapping.json").decode("utf-8")
    )["ShuffleOptions"]
    _GEMS = {"Red Gem", "Green Gem", "Blue Gem", "Yellow Gem", "Purple Gem"}

    result = {
        "relic_progression_map": world._relic_progression_map(),
        "early_items": {},          # {item_name: count}
        "locked_placements": {},    # {location_name: item_name}
        "pool_names": [],           # [item_name, ...] -- general pool, NAMES only
        "precollected": None,       # item_name for starting character
        "dynamic_item_count": 0
    }

    # Vanilla-fill lever 2: seat the 4 hub-backbone Keys early.
    if (world.options.warppad_unlock_requirements.value == 0
            and world.options.shuffle_keys.value):
        result["early_items"]["Key"] = 4

    # Relic-tier exact-count removal.
    _relic_locked = {
        _relic_item: 18 - world._ctr_relic_created.get(_relic_item, 18)
        for _tier_label, _relic_item, _opt_name in RELIC_TIERS
    }

    _GEM_GOAL = world.options.gems_required_goal.value > 0
    _gems_locked, _keys_locked, _arena_locked, _cups_locked = {}, {}, {}, {}

    if not world.options.shuffle_gems.value and not _GEM_GOAL:
        for _loc_name, _gem_name in _vmap["Gems"].items():
            _loc_name = replacement_trophy_location(resolved_custom_tracks(world), _loc_name)
            result["locked_placements"][_loc_name] = _gem_name
            _gems_locked[_gem_name] = _gems_locked.get(_gem_name, 0) + 1

    if not world.options.shuffle_keys.value:
        for _loc_name, _key_name in _vmap["Boss Keys"].items():
            result["locked_placements"][_loc_name] = _key_name
            _keys_locked[_key_name] = _keys_locked.get(_key_name, 0) + 1

    if not world.options.include_battle_arenas.value:
        for _loc_name, _token_name in _vmap["Bonus Round Tokens"].items():
            result["locked_placements"][_loc_name] = _token_name
            _arena_locked[_token_name] = _arena_locked.get(_token_name, 0) + 1

    if (not world.options.include_gem_cups.value
            and world.options.shuffle_gems.value and not _GEM_GOAL):
        for _loc_name, _gem_name in _vmap["Gems"].items():
            _loc_name = replacement_trophy_location(resolved_custom_tracks(world), _loc_name)
            result["locked_placements"][_loc_name] = _gem_name
            _cups_locked[_gem_name] = _cups_locked.get(_gem_name, 0) + 1

    _wumpa_counts = wumpa_family.created_item_counts(world)

    pool_names = []
    for item in load_item_table():
        if _GEM_GOAL and not world.options.shuffle_gems.value and item["name"] in _GEMS:
            continue
        count = item["count"]
        if world.options.itemsanity.value and item["name"] in ITEM_NAMES:
            count = 1
        if item["name"] in SURFACE_ITEM_NAMES:
            count = 1 if world.options.use_terrain_modifiers else 0
        if item["name"] == TIZI_HELPER_ITEM:
            count = tizi_helper.created_item_count(world)
        if item["name"] in _wumpa_counts:
            count = _wumpa_counts[item["name"]]
        if item["name"] == TURBO_GRANT_ITEM:
            count = turbo_grant.created_item_count(world)
        if int(world.options.lettersanity.value) in (2, 3) and item["name"] in lettersanity.ITEM_NAMES:
            track = item["name"].rsplit("(", 1)[1][:-1]
            letter = item["name"].split(" ", 2)[1]
            count = int(int(world.options.lettersanity.value) == 3
                        or letter in world.options._lettersanity_selected[track])
        if item["name"] in _relic_locked:
            count = max(0, count - _relic_locked[item["name"]])
        if item["name"] in _gems_locked:
            count = max(0, count - _gems_locked[item["name"]])
        if item["name"] in _keys_locked:
            count = max(0, count - _keys_locked[item["name"]])
        if item["name"] in _arena_locked:
            count = max(0, count - _arena_locked[item["name"]])
        if item["name"] in _cups_locked:
            count = max(0, count - _cups_locked[item["name"]])
        if count > 0:
            pool_names.extend([item["name"]] * count)

    result["precollected"] = characters.unlock_item_name(world.ctr_starting_character)
    pool_names.extend(characters.created_unlock_names(world))

    result["dynamic_item_count"] = sum(progressive_capability.created_item_counts(world).values())

    result["pool_names"] = pool_names

    return result
