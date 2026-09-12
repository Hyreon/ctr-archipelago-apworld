"""Adaptive podium-rung sizing (issue #71).

Podium's four sub-toggles are a parent/child ladder, not a scalar.  This
module computes the smallest layout that would give the generated pool a spare
location.  It never changes a player-selected subcategory: if the configured
layout is too small, generation raises with the required category count.  This
supersedes the earlier host-gated upward expansion because existing host files
carried its old default-on value and could not distinguish that inherited value
from informed consent to override a YAML.  It also never enables the master
``podium_placement_checks`` toggle.

The nine effective layouts are listed in ``RUNG_LADDER``.  When a YAML enables
a child while its parent is off, candidate selection expands the current raw
toggle state instead of normalising it, so sizing never turns a player-enabled
toggle off.  Ties prefer the layout that creates the fewest new names and then
held-position rungs over finish rungs, as ruled on 2026-08-10.
"""
from dataclasses import dataclass
from itertools import product
import logging
from typing import Iterable, Optional, Tuple

from Options import OptionError

from .Items import load_item_table
from .Locations import CTR_LOCATION_CLASSES, _LOCATION_DATA
from .elastic_bounds import predicted_goal_excluded_reserve
from .itemsanity import ITEMSANITY_CLASS, ITEM_NAMES as ITEMSANITY_ITEM_NAMES
from .lettersanity import LETTERSANITY_CLASS, ITEM_NAMES as LETTERSANITY_ITEM_NAMES
from .podium import PODIUM_CLASS, TROPHY_TRACKS, created_rung_keys
from .item_boxes import ITEM_BOX_CLASS
from .relic_tiers import RELIC_TIERS
from .tizi_helper import TIZI_HELPER_ITEM
from . import tizi_helper
from . import turbo_grant
from . import wumpa_family
from . import characters
from . import progressive_capability
from . import item_supply

logger = logging.getLogger(__name__)


_TOGGLE_NAMES = (
    "podium_finish_rungs",
    "podium_any_position_rung",
    "podium_held_rungs",
    "podium_held_fifth_rung",
)
_GEM_NAMES = frozenset({"Red Gem", "Green Gem", "Blue Gem", "Yellow Gem", "Purple Gem"})
_SURFACE_ITEM_NAMES = frozenset({
    "Ignore Grass", "Ignore Dirt", "Ignore Snow", "Ignore Water", "Ignore Ice",
})


@dataclass(frozen=True)
class RungLayout:
    """One canonical effective layout, in finish/any/held/fifth order."""

    finish: bool
    any_position: bool
    held: bool
    held_fifth: bool

    @property
    def categories(self) -> int:
        return len(self.keys)

    @property
    def keys(self) -> Tuple[str, ...]:
        return tuple(created_rung_keys(
            self.finish, self.any_position, self.held, self.held_fifth))


# Nine reachable category shapes once each child is collapsed against its
# parent. Their order is only documentation; selection has explicit sort keys.
RUNG_LADDER: Tuple[RungLayout, ...] = (
    RungLayout(False, False, False, False),
    RungLayout(True, False, False, False),
    RungLayout(True, True, False, False),
    RungLayout(False, False, True, False),
    RungLayout(False, False, True, True),
    RungLayout(True, False, True, False),
    RungLayout(True, True, True, False),
    RungLayout(True, False, True, True),
    RungLayout(True, True, True, True),
)
assert tuple(sorted({row.categories for row in RUNG_LADDER})) == (0, 1, 2, 3, 4, 5)


def _raw_values(options) -> Tuple[bool, bool, bool, bool]:
    return tuple(bool(getattr(options, name).value) for name in _TOGGLE_NAMES)


def _layout_from_values(values: Tuple[bool, bool, bool, bool]) -> RungLayout:
    return RungLayout(*values)


def category_count(options) -> int:
    """Number of active rung categories for these resolved options."""
    if not bool(options.podium_placement_checks.value):
        return 0
    return _layout_from_values(_raw_values(options)).categories


def rows_reachable_from(options) -> Tuple[RungLayout, ...]:
    """Every raw-toggle superset of the player's selection.

    The effective ladder has nine rows, but preserving an inert child toggle
    requires considering its raw value while selecting a row.  This produces
    at most sixteen candidates and returns each effective layout once.
    """
    current = _raw_values(options)
    rows = {
        _layout_from_values(values)
        for values in product((False, True), repeat=4)
        if all(not old or new for old, new in zip(current, values))
    }
    return tuple(sorted(rows, key=lambda row: (
        row.categories, row.held is False, row.finish is False,
        row.any_position is False, row.held_fifth is False)))


def _base_location_supply(world) -> int:
    """Live non-podium location count before adding rung categories.

    Static Time Trial slots are represented by ``_ctr_relic_created`` rather
    than their frozen full table. Any optional class that becomes live before
    #71's next touch contributes automatically through the #176 registry.
    """
    static_without_trials = sum(
        1 for loc in _LOCATION_DATA if not loc["name"].endswith(" Time Trial"))
    relics = sum(world._ctr_relic_created.values())
    other_classes = sum(
        len(location_class.created_locations(world.options))
        for location_class in CTR_LOCATION_CLASSES
        if location_class is not PODIUM_CLASS
        and location_class is not ITEM_BOX_CLASS)
    return static_without_trials + relics + other_classes


def predicted_mandatory_pool(world) -> int:
    data = item_supply.compute_item_pool_data(world)
    mandatory = sum(
        1 for name in data["pool_names"]
        if name != "Wumpa Fruit" and name not in item_supply.SURFACE_ITEM_NAMES
    )
    mandatory += sum(progressive_capability.created_item_counts(world).values())
    return mandatory


def _capability_packs_active(world) -> bool:
    # Deliberately NOT extended to the character unlocks (#54/#209). Those 15
    # items are always-on demand and are already counted in
    # predicted_mandatory_pool, so `minimum` covers them exactly. The extra
    # working margin and the floor of three exist for the capability packs
    # specifically; widening them to "always" would silently raise every
    # default seed to three rung categories, which is a behaviour change this
    # feature has no reason to make.
    return bool(world.options.progressive_boost.value or world.options.progressive_stats.value)


def needed_locations(world):
    # The amount of locations that need to be provided.
    # If this number is negative, the mandatory locations already
    # provide more than what the game needs.
    demand = predicted_mandatory_pool(world)
    demand += predicted_goal_excluded_reserve(world.options)
    demand += world.options.expected_filler
    base = _base_location_supply(world)
    base -= len(world.options.exclude_locations.value)
    return demand - base

def _locations_with_categories(categories):
    return len(TROPHY_TRACKS) * categories

def required_boxes(world, flex_locations = 0) -> Optional[int]:
    demand = needed_locations(world) + flex_locations
    available_boxes = len(ITEM_BOX_CLASS.created_locations(world.options))
    if world.options.use_all_boxes:
        return available_boxes
    print("Demand / Available Boxes:", demand, available_boxes)
    return max(0, min(demand, available_boxes))

def required_categories(world, flex_locations = 0) -> Optional[int]:
    """Smallest rung-category count that accounts for all needed items.

    ``None`` means the full five-category ladder cannot satisfy the current
    live registry and item pool.

    flex_locations allows consideration for locations already ruled part of the game.
    """
    demand = needed_locations(world) - flex_locations
    print("Needed / Claimed / Demand:", needed_locations(world), flex_locations, demand)
    minimum = next((categories for categories in range(6)
                    if demand <= _locations_with_categories(categories)), None)
    if minimum is None:
        return None

    return minimum


def _new_name_count(current: RungLayout, candidate: RungLayout) -> int:
    return len(set(candidate.keys) - set(current.keys)) * len(TROPHY_TRACKS)


def _held_category_count(layout: RungLayout) -> int:
    return (2 if layout.held else 0) + (1 if layout.held and layout.held_fifth else 0)


def _select_layout(options, target: int) -> Optional[RungLayout]:
    current = _layout_from_values(_raw_values(options))
    candidates = [row for row in rows_reachable_from(options)
                  if row.categories >= target]
    if not candidates:
        return None
    return min(candidates, key=lambda row: (
        row.categories,
        _new_name_count(current, row),
        -_held_category_count(row),
    ))

def apply_rung_sizing(world, flex_locations = 0) -> Optional[str]:
    """Apply the ruled upward-only sizing policy, or raise clearly.

    This runs in ``generate_early`` before regions consume the podium toggles.
    A sufficient player layout is untouched and takes no random draw.
    """
    target = required_categories(world, flex_locations = flex_locations)
    current = category_count(world.options)
    if target is None:
        capability_added = sum(
            progressive_capability.created_item_counts(world).values())
        if capability_added:
            total_demand = predicted_mandatory_pool(world)
            total_demand += predicted_goal_excluded_reserve(world.options)
            total_demand += len(world.options.exclude_locations.value)
            maximum_supply = _base_location_supply(world) + len(TROPHY_TRACKS) * 5
            progressive_capability.raise_if_capability_items_exceed_location_supply(
                world, available_supply=max(
                    0, maximum_supply - (total_demand - capability_added)))
        raise OptionError(
            "CTR: the current mandatory item pool exceeds the full five-category "
            "Podium Rung ladder. Disable an item-pool option or add a live "
            "location class; the rung sizer cannot create more than 80 locations.")
    if current >= target:
        return _locations_with_categories(target)
    if not bool(world.options.podium_placement_checks.value):
        raise OptionError(
            "CTR: this seed needs more Podium Rung capacity, but Podium Placement "
            "Checks is off. The adaptive sizer never enables that master toggle; "
            "turn it on, or reduce the enabled item-pool options -- the usual "
            "candidates are Character Unlocks (15 items, set 'character_unlocks' "
            "to false for all-unlocked mode), Progressive Stats (12) and "
            "Progressive Boost (2-3). All three add pool items without adding "
            "any locations of their own.")
    raise OptionError(
        f"CTR: this seed needs at least {target} Podium Rung categories, but "
        f"the YAML selects {current}. CTR will not turn disabled rung options "
        "back on. Enable more podium rung subcategories, enable another "
        "location family such as Item Box Locations, or reduce item-pool "
        "options such as Progressive Boost or Progressive Stats.")
