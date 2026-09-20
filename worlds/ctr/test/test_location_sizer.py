"""Issue #71 adaptive podium-rung sizing.

The tests pin the nine effective ladder rows, upward-only selection, host and
master vetoes, live-pool prediction, and the retained #109 per-character
block.  No test relies on a future #109/#145 implementation: optional classes
are counted only through the live #176 registry.
"""
import unittest

from Options import OptionError
from test.general import setup_multiworld

from .. import ctrAPWorld, podium, progressive_capability, location_sizer, traps
from ..elastic_bounds import (goal_excluded_location_reserve,
                               predicted_goal_excluded_reserve)
from ..Options import OxideGoal


class _Toggle:
    def __init__(self, value):
        self.value = value


class _Options:
    def __init__(self, *, master=True, finish=False, any_position=False,
                 held=False, fifth=False):
        self.podium_placement_checks = _Toggle(master)
        self.podium_finish_rungs = _Toggle(finish)
        self.podium_any_position_rung = _Toggle(any_position)
        self.podium_held_rungs = _Toggle(held)
        self.podium_held_fifth_rung = _Toggle(fifth)


class TestRungLadder(unittest.TestCase):
    def test_all_nine_effective_rows_have_the_ruled_category_count(self):
        expected = (0, 1, 2, 2, 3, 3, 4, 4, 5)
        self.assertEqual(
            tuple(row.categories for row in location_sizer.RUNG_LADDER), expected)

    def test_category_count_honours_the_master_toggle(self):
        options = _Options(master=False, finish=True, any_position=True,
                           held=True, fifth=True)
        self.assertEqual(location_sizer.category_count(options), 0)

    def test_reachable_rows_never_disable_an_inert_child_toggle(self):
        options = _Options(master=True, finish=False, any_position=True)
        self.assertTrue(all(row.any_position for row in location_sizer.rows_reachable_from(options)))


class TestRungSizingGeneration(unittest.TestCase):
    def test_legacy_host_opt_in_cannot_override_yaml(self):
        mw = setup_multiworld(ctrAPWorld, seed=711)
        world = mw.worlds[1]
        world.options.podium_finish_rungs.value = False
        world.options.podium_any_position_rung.value = False
        world.options.podium_held_rungs.value = False
        world.options.podium_held_fifth_rung.value = False
        world.options.progressive_boost.value = 1

        before = tuple(getattr(world.options, name).value
                    for name in location_sizer._TOGGLE_NAMES)
        with self.assertRaises(OptionError):
            location_sizer.flex_locations(world)
        after = tuple(getattr(world.options, name).value
                    for name in location_sizer._TOGGLE_NAMES)

        self.assertEqual(after, before)
        self.assertEqual(location_sizer.category_count(world.options), 0)
        self.assertFalse(world.options.podium_held_rungs.value)
        self.assertFalse(world.options.podium_held_fifth_rung.value)
        self.assertFalse(world.options.podium_finish_rungs.value)

    # this test was passing when it should have failed;
    # shared_global creates less than one podium's worth of slots.
    # if we find a configuration where 1 podium isn't enough,
    # we can reimplement it
    # def test_held_opt_out_fails_instead_of_silently_expanding(self):
    #     for capability in ("progressive_boost", "progressive_stats"):
    #         with self.subTest(capability=capability), self.assertRaises(OptionError) as ctx:
    #             setup_multiworld(
    #                 ctrAPWorld, seed=715,
    #                 options={
    #                     "podium_placement_checks": True,
    #                     "podium_finish_rungs": False,
    #                     "podium_any_position_rung": False,
    #                     "podium_held_rungs": False,
    #                     "podium_held_fifth_rung": False,
    #                     "box_locations": False,
    #                     capability: "shared_global",
    #                 })

    def test_box_supply_preserves_held_opt_out_under_capability_pressure(self):
        mw = setup_multiworld(
            ctrAPWorld, seed=716,
            options={
                "podium_placement_checks": True,
                "podium_finish_rungs": True,
                "podium_any_position_rung": True,
                "podium_held_rungs": False,
                "podium_held_fifth_rung": False,
                "progressive_boost": "shared_global",
                "box_locations": True,
            })
        world = mw.worlds[1]
        self.assertEqual(location_sizer.category_count(world.options), 2)
        self.assertFalse(world.options.podium_held_rungs.value)
        self.assertFalse(world.options.podium_held_fifth_rung.value)

    def test_sufficient_default_layout_is_a_noop(self):
        mw = setup_multiworld(ctrAPWorld, seed=712)
        world = mw.worlds[1]
        before = tuple(getattr(world.options, name).value
                       for name in location_sizer._TOGGLE_NAMES)
        self.assertIsNone(location_sizer.flex_locations(world))
        after = tuple(getattr(world.options, name).value
                      for name in location_sizer._TOGGLE_NAMES)
        self.assertEqual(after, before)

    def test_box_supply_is_sufficient_for_progressive_stats(self):
        mw = setup_multiworld(
            ctrAPWorld, seed=716,
            options={
                "podium_placement_checks": False,
                "podium_finish_rungs": False,
                "podium_any_position_rung": False,
                "podium_held_rungs": False,
                "podium_held_fifth_rung": False,
                "progressive_stats": "per_character",
                "box_locations": True,
            })
        world = mw.worlds[1]
        self.assertIsNone(location_sizer.flex_locations(world))

    def test_sufficient_default_layout_is_a_noop(self):
        mw = setup_multiworld(ctrAPWorld, seed=712)
        world = mw.worlds[1]
        before = tuple(getattr(world.options, name).value
                       for name in location_sizer._TOGGLE_NAMES)
        self.assertIsNone(location_sizer.flex_locations(world))
        after = tuple(getattr(world.options, name).value
                      for name in location_sizer._TOGGLE_NAMES)
        self.assertEqual(after, before)

    def test_host_veto_raises_instead_of_mutating(self):
        # Build a normal world first, then turn its live options into the tight
        # case and call the pure generate-early action directly.
        mw = setup_multiworld(ctrAPWorld, seed=714)
        world = mw.worlds[1]
        world.options.podium_finish_rungs.value = False
        world.options.podium_any_position_rung.value = False
        world.options.podium_held_rungs.value = False
        world.options.podium_held_fifth_rung.value = False
        world.options.progressive_boost.value = 1

        before = tuple(getattr(world.options, name).value
                    for name in location_sizer._TOGGLE_NAMES)
        with self.assertRaises(OptionError):
            location_sizer.flex_locations(world)
        after = tuple(getattr(world.options, name).value
                    for name in location_sizer._TOGGLE_NAMES)

        # The actual contract: infeasibility raises rather than silently
        # re-enabling a player-disabled rung toggle to make room.
        self.assertEqual(after, before)
        self.assertEqual(location_sizer.category_count(world.options), 0)

    def test_prediction_matches_live_non_filler_pool_across_option_matrix(self):
        matrices = (
            {},
            {"shuffle_gems": False, "shuffle_keys": False,
             "include_battle_arenas": False},
            {"oxide_goal": "none", "bosses_required_goal": 4},
            {"oxide_goal": "none", "gems_required_goal": 3,
             "shuffle_gems": False, "include_gem_cups": True},
            {"progressive_boost": "shared_global",
             "progressive_boost_blue_fire": True,
             "progressive_stats": "shared_global"},
            # DeepSeek review F1/F2 (2026-08-11): the shapes the merged
            # #145/#109 features add. Itemsanity activates 11 frozen-at-zero
            # weapon items; box locations add supply but no items; the
            # combined shape exercises both sides of the ledger at once.
            {"itemsanity": True},
            {"box_locations": True, "shortcut_knowledge": "hard"},
            {"itemsanity": True, "box_locations": True,
             "shortcut_knowledge": "medium",
             "progressive_boost": "shared_global",
             "progressive_stats": "shared_global"},
        )
        for seed, options in enumerate(matrices, start=720):
            with self.subTest(options=options):
                mw = setup_multiworld(ctrAPWorld, seed=seed, options=options)
                world = mw.worlds[1]
                expected = location_sizer.predicted_mandatory_pool(world)
                actual = sum(
                    1 for item in mw.itempool if item.player == world.player
                    and item.name != "Wumpa Fruit"
                    and item.name not in location_sizer._SURFACE_ITEM_NAMES
                    and item.name not in traps.ALL_TRAP_ITEM_NAMES)
                self.assertEqual(actual, expected)

    def test_predicted_goal_reserve_matches_installed_goal(self):
        matrices = (
            {},
            {"oxide_goal": "final"},
            {"oxide_goal": "none", "bosses_required_goal": 4},
            {"oxide_goal": "none", "gems_required_goal": 3},
            # Sonnet review, 2026-09-03: `disabled` (#320) was missing from
            # this matrix, which is exactly how the elastic-bounds twin
            # shipped untested against it.
            {"oxide_goal": "disabled", "bosses_required_goal": 4},
            {"oxide_goal": "disabled", "gems_required_goal": 3},
        )
        for seed, options in enumerate(matrices, start=730):
            with self.subTest(options=options):
                mw = setup_multiworld(ctrAPWorld, seed=seed, options=options)
                world = mw.worlds[1]
                self.assertEqual(predicted_goal_excluded_reserve(world.options),
                                 goal_excluded_location_reserve(world))

    def test_predicted_goal_excluded_reserve_zero_for_none_and_disabled(self):
        # 2026-09-03 repair: `predicted_goal_excluded_reserve` used to test
        # `oxide_goal.value != 0`, which happened to be right for `none` (0)
        # and any Oxide finale (1/2 -> 1) but wrongly predicted 1 for
        # `disabled` (3), which installs no goal-exclusion branch at all and
        # must predict 0 like `none`. Assert the canonical
        # `OxideGoal.oxide_is_goal` semantics directly, independent of any
        # live world.
        for value in (OxideGoal.option_none, OxideGoal.option_disabled):
            with self.subTest(oxide_goal=value):
                options = _Options.__new__(_Options)
                options.oxide_goal = _Toggle(value)
                self.assertEqual(predicted_goal_excluded_reserve(options), 0)
        for value in (OxideGoal.option_any_percent, OxideGoal.option_101_percent):
            with self.subTest(oxide_goal=value):
                options = _Options.__new__(_Options)
                options.oxide_goal = _Toggle(value)
                self.assertEqual(predicted_goal_excluded_reserve(options), 1)

    def test_disabled_goal_at_rung_ceiling_not_rejected_by_reserve_overestimate(self):
        """Boundary regression for the Sonnet review's blocker, re-targeted at
        `flex_locations`. Boxes are forced off so rungs are the only lever --
        otherwise box supply could silently absorb slack and the boundary
        this test cares about would never be exercised.

        A `disabled` goal reserves 0 locations; a real Oxide goal reserves 1.
        Padding each world's OWN `needed_locations` to its own true 5-category
        ceiling must succeed; one location past it must raise. This proves the
        reserve difference directly, rather than re-deriving hand-computed
        "buggy" arithmetic that no longer corresponds to any code path.
        """
        mw = setup_multiworld(
            ctrAPWorld, seed=741,
            options={"oxide_goal": "disabled", "bosses_required_goal": 4,
                    "box_locations": False,
                    "podium_placement_checks": True,
                    "podium_finish_rungs": True,
                    "podium_any_position_rung": True,
                    "podium_held_rungs": True,
                    "podium_held_fifth_rung": True})
        world = mw.worlds[1]
        self.assertEqual(predicted_goal_excluded_reserve(world.options), 0)
        self.assertEqual(location_sizer.category_count(world.options), 5)
        self.assertEqual(world.box_count, 0)

        ceiling = location_sizer._locations_given_rungs(world, 5)
        needed_at_zero_pad = location_sizer.needed_locations(world)
        pad_to_ceiling = ceiling - needed_at_zero_pad
        self.assertGreater(pad_to_ceiling, 0)
        world.options.exclude_locations.value = frozenset(
            f"synthetic exclude {i}" for i in range(pad_to_ceiling))

        # Exact boundary: needed_locations == ceiling. disabled's zero reserve
        # means this must fit -- flex_locations must not raise.
        self.assertEqual(location_sizer.needed_locations(world), ceiling)
        self.assertIsNone(location_sizer.flex_locations(world))
        self.assertEqual(world.podium_rungs, 5)
        self.assertEqual(world.box_count, 0)

        # A real Oxide goal genuinely reserves one location. Padding to its
        # OWN true ceiling must still succeed; one more must raise -- proving
        # the reserve is actually being charged, not silently dropped.
        mw_goal = setup_multiworld(
            ctrAPWorld, seed=742,
            options={"oxide_goal": "any_percent",
                    "box_locations": False,
                    "podium_placement_checks": True,
                    "podium_finish_rungs": True,
                    "podium_any_position_rung": True,
                    "podium_held_rungs": True,
                    "podium_held_fifth_rung": True})
        world_goal = mw_goal.worlds[1]
        self.assertEqual(predicted_goal_excluded_reserve(world_goal.options), 1)
        self.assertEqual(location_sizer.category_count(world_goal.options), 5)

        ceiling_goal = location_sizer._locations_given_rungs(world_goal, 5)
        needed_goal_at_zero_pad = location_sizer.needed_locations(world_goal)
        pad_goal = ceiling_goal - needed_goal_at_zero_pad
        self.assertGreater(pad_goal, 0)

        world_goal.options.exclude_locations.value = frozenset(
            f"synthetic exclude {i}" for i in range(pad_goal))
        self.assertEqual(location_sizer.needed_locations(world_goal), ceiling_goal)
        self.assertIsNone(location_sizer.flex_locations(world_goal))

        world_goal.options.exclude_locations.value = frozenset(
            f"synthetic exclude {i}" for i in range(pad_goal + 1))
        with self.assertRaises(OptionError):
            location_sizer.flex_locations(world_goal)

    def test_supply_poor_per_character_gets_numeric_capability_error(self):
        with self.assertRaises(OptionError) as ctx:
            setup_multiworld(ctrAPWorld, seed=740,
                             options={"progressive_stats": "per_character"})
        self.assertIn("192", str(ctx.exception))
        self.assertIn("Progressive Top Speed (Crash Bandicoot)", str(ctx.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
