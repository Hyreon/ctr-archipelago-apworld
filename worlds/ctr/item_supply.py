from typing import Iterable, List, Sequence

from BaseClasses import Item, ItemClassification

import json
import pkgutil
from collections import defaultdict

from .Items import load_item_table
from .Options import (OxideGoal)
from .itemsanity import WEAPONS, ITEM_NAMES
from .custom_lettersanity import CUSTOM_LETTER_ITEM_DATA, CUSTOM_LETTERSANITY_CLASS
from .relic_tiers import RELIC_TIERS
from .tizi_helper import TIZI_HELPER_ITEM
from .turbo_grant import TURBO_GRANT_ITEM
from .custom_tracks import replacement_trophy_location, resolved_custom_tracks
from . import tizi_helper
from . import turbo_grant
from . import wumpa_family
from . import characters
from . import lettersanity
from . import progressive_capability
from . import elastic_bounds

# Comfort-only issues #14/#15 pack. It stays atomic when a reduced location
# set cannot host all five, rather than emitting a seed-dependent subset.
SURFACE_ITEM_NAMES = frozenset({
    "Ignore Grass", "Ignore Dirt", "Ignore Snow", "Ignore Water", "Ignore Ice",
})

def compute_item_pool_data(world):
    """A pure definition for the item pool. No Item object is
    constructed (world.create_item is itself a side-effecting call,
    per the caller's own instruction), no location is touched, no
    world/multiworld attribute is mutated. Every real commitment is
    returned as plain data for apply_item_pool_data to act on.

    Padding sets like the Ignore Terrain items are not part of the mandatory
    item pool. The world will attempt to create them if there's room to spare.

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
        "padding_sets": defaultdict(list),  # {group: [item_name, ...], ...}
        "dynamic_item_count": 0,    # estimated number of untracked items
        "needed_filler": 0
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

    _wumpa_counts = wumpa_family.created_item_counts(world) # the progressive starting wumpa

    pool_names = []
    for item in load_item_table():
        padding_group = None
        if _GEM_GOAL and not world.options.shuffle_gems.value and item["name"] in _GEMS:
            continue
        count = item["count"]
        if (item["name"] == "Wumpa Fruit" and
                world.options.oxide_goal.value == OxideGoal.option_101_percent and
                world.options.oxide_1_optional.value == 2):
            count = max(0, count - 1)  # existing copy locked at Oxide 1
        if world.options.itemsanity.value and item["name"] in ITEM_NAMES:
            count = 1
        if item["name"] in SURFACE_ITEM_NAMES:
            _terrain_mode = int(world.options.use_terrain_modifiers.value)
            count = 1 if _terrain_mode in (1, 2) else 0
            if _terrain_mode == 2:
                padding_group = "SURFACE_ITEM"
        if item["name"] == TIZI_HELPER_ITEM:
            count = tizi_helper.created_item_count(world)
        if item["name"] in _wumpa_counts:
            count = _wumpa_counts[item["name"]]
        if item["name"] == TURBO_GRANT_ITEM:
            count = turbo_grant.created_item_count(world)
        if int(world.options.lettersanity.value) in (2, 3) and item["name"] in lettersanity.ALL_ITEM_NAMES:
            track = item["name"].rsplit("(", 1)[1][:-1]
            letter = item["name"].split(" ", 2)[1]
            count = int(track in world.options._lettersanity_selected and
                        (int(world.options.lettersanity.value) == 3 or
                            letter in world.options._lettersanity_selected[track]))
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
            if padding_group is None:
                pool_names.extend([item["name"]] * count)
            else:
                result["padding_sets"][padding_group].extend([item["name"]] * count)

    result["precollected"] = characters.unlock_item_name(world.ctr_starting_character)
    pool_names.extend(characters.created_unlock_names(world))

    # Sparse custom letter items follow certified slot selection, not the
    # positional retail item table. Included alongside the general table's
    # lettersanity items above, before capacity/overflow checks run in
    # apply_item_pool_data.
    pool_names.extend(CUSTOM_LETTERSANITY_CLASS.created_item_names(world.options))

    # dynamic items that will be / might be generated on the fly
    result["dynamic_item_count"] += sum(progressive_capability.created_item_counts(world).values())
    result["needed_filler"] = elastic_bounds.estimated_filler_reserve(world)

    result["pool_names"] = pool_names
    result["padding_sets"] = dict(result["padding_sets"]) # flatten to dict and not defaultdict for safety

    return result
