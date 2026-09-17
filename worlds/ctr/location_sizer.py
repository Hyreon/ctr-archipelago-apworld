"""Adaptive podium-rung sizing (issue #71) and item-box sizing (Hyreon),
merged into one descriptively named file.

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

from .podium import PODIUM_CLASS, enabled_trophy_tracks, created_rung_keys
from . import item_supply
from .elastic_bounds import predicted_goal_excluded_reserve
from .Locations import CTR_LOCATION_CLASSES, _LOCATION_DATA
from .item_boxes import ITEM_BOX_CLASS
from . import lettersanity


def _custom_ctr_slots(world):
    from .custom_tracks import resolve_custom_tracks
    return tuple(entry["slot"] for entry in resolve_custom_tracks(world).values()
                 if entry.get("modes", {}).get("ctr_challenge", False))

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
    # Sparse custom classes are populated in create_regions, after sizing.
    # Predict their admitted checks without drawing a selection or mutating RNG.
    if not hasattr(world.options, "_custom_ctr_admitted_slots"):
        slots = len(_custom_ctr_slots(world))
        other_classes += slots
        if int(world.options.lettersanity.value) in (1, 2):
            other_classes += slots * int(world.options.letters_per_track.value)
    # True-filler first Oxide consumes one real slot with its locked reward.
    locked_first = int(world.options.oxide_goal.value == 2 and
                       world.options.oxide_1_optional.value == 2)
    return static_without_trials + relics + other_classes - locked_first


def predicted_mandatory_pool(world) -> int:
    data = item_supply.compute_item_pool_data(world)
    mandatory = sum(
        1 for name in data["pool_names"]
        if name != "Wumpa Fruit"
    ) + data["dynamic_item_count"]
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

def _locations_given_rungs(world, categories):
    return len(enabled_trophy_tracks(world.options)) * categories

def required_boxes(world, remaining_locations_needed) -> Optional[int]:
    available_boxes = len(ITEM_BOX_CLASS.created_locations(world.options))

    if world.options.use_all_boxes:
        return available_boxes

    return max(0, min(remaining_locations_needed, available_boxes))

def required_categories(world, remaining_locations_needed = None) -> Optional[int]:
    """Smallest rung-category count that accounts for all needed items.

    ``None`` means the full five-category ladder cannot satisfy the current
    live registry and item pool.

    flex_locations allows consideration for locations already ruled part of the game.
    """

    if remaining_locations_needed is None:
        remaining_locations_needed = needed_locations(world)

    minimum = next((categories for categories in range(6)
                    if remaining_locations_needed <= _locations_given_rungs(world, categories)), None)

    desired_rungs = category_count(world.options)

    if minimum is None:
        return desired_rungs

    return min(minimum, category_count(world.options))


def flex_locations(world) -> Optional[str]:
    total_locations_needed = needed_locations(world)
    remaining_locations_needed = total_locations_needed

    world.podium_rungs = required_categories(world, remaining_locations_needed)
    podium_locations = _locations_given_rungs(world, world.podium_rungs)
    remaining_locations_needed -= podium_locations

    world.box_count = required_boxes(world, remaining_locations_needed)
    remaining_locations_needed -= world.box_count


    if remaining_locations_needed > 0:  # could not assign all locations
        item_data = item_supply.compute_item_pool_data(world)
        item_names = item_data["pool_names"]
        dynamic_items = item_data["dynamic_item_count"]

        raise OptionError(
            "CTR: the current mandatory item pool exceeds the current available "
            "location pool. Reduce the amount of items or increase the amount of locations. "
            f"Need {remaining_locations_needed} more locations for "
            f"{len(item_names) + dynamic_items} unassigned items: {item_names} "
            f"(+{dynamic_items} dynamic items)")
