"""Tests for mpw lint: design warnings on a recipe's optional room plan."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import mpw  # noqa: E402
import mpw_lint as L  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "dungeon-070-bsp")


def texts(res, check=None):
    return [w["text"] for w in res["warnings"] if check is None or w["check"] == check]


def good_dungeon():
    return {
        "rooms": [
            {"id": "a", "entrance": True, "main": True, "role": "entrance", "danger": 1, "empty": False,
             "level": 0},
            {"id": "b", "entrance": True, "danger": 1, "empty": True, "level": 0, "hook": "dry fountain"},
            {"id": "c", "role": "puzzle", "danger": 2, "empty": False, "level": 0, "vertical": True},
            {"id": "d", "role": "setback", "danger": 3, "empty": True, "hook": "claw marks", "combat": True,
             "terrain": ["pit"],
             "level": 1},
            {"id": "e", "role": "climax", "danger": 5, "empty": False, "combat": True, "terrain": ["pillars"],
             "level": 1},
            {"id": "f", "role": "reward", "danger": 4, "empty": False, "treasure": True, "level": 1,
             "name": "Old Well"},
        ],
        "links": [["a", "c"], ["b", "c"], ["c", "d", 2], ["b", "d", 3], ["d", "e"], ["e", "f"]],
        "landmarks": ["Old Well", "Mak"],
    }


def tavern():
    return {
        "rooms": [
            {"id": "tap", "kind": "taproom", "area": 60, "door": "front"},
            {"id": "snug", "kind": "snug", "area": 12},
            {"id": "kit", "kind": "kitchen", "area": 20, "door": "rear"},
            {"id": "vault", "kind": "vault", "area": 4},
            {"id": "hall", "kind": "corridor", "stairs": True},
        ],
        "links": [["tap", "snug"], ["tap", "kit"], ["kit", "vault"], ["tap", "hall"]],
    }


class LintBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-lint-")
        for f in os.listdir(FIX):
            shutil.copy(os.path.join(FIX, f), self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, plan):
        p = os.path.join(self.tmp, "recipe.json")
        with open(p, encoding="utf-8") as f:
            rc = json.load(f)
        rc["plan"] = plan
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rc, f)
        return L.lint(self.tmp)


class TestOldRecipe(LintBase):
    def test_no_plan_lints_clean(self):
        res = L.lint(self.tmp)
        self.assertEqual(res["warnings"], [])
        self.assertIn("no plan", res["info"][0])

    def test_landmark_flag_without_plan(self):
        res = L.lint(self.tmp, ["Mak", "Ghost Tower"])
        self.assertEqual(texts(res), ["landmark not on the map: Ghost Tower"])

    def test_area_from_grid(self):
        p = L.Plan({"rooms": [{"id": 0}, {"id": 1}]}, L._load(FIX, "grid.json"))
        self.assertEqual(p.rooms[0]["area"], 84)


class TestLayout(LintBase):
    def test_good_plan_has_no_warnings(self):
        res = self.put(good_dungeon())
        self.assertEqual(res["warnings"], [], res)

    def test_single_entrance(self):
        pl = good_dungeon()
        pl["rooms"][1]["entrance"] = False
        self.assertTrue(any("only one entrance" in t for t in texts(self.put(pl), "layout")))

    def test_danger_falls(self):
        pl = good_dungeon()
        for r, v in zip(pl["rooms"], (5, 5, 4, 2, 1, 1)):
            r["danger"] = v
        self.assertTrue(any("danger does not rise" in t for t in texts(self.put(pl), "layout")))

    def test_one_route_between_levels(self):
        pl = good_dungeon()
        pl["links"] = [l for l in pl["links"] if l[:2] != ["b", "d"]]
        self.assertTrue(any("1 route(s) between level 0 and level 1" in t for t in texts(self.put(pl))))

    def test_empty_share(self):
        pl = good_dungeon()
        for r in pl["rooms"]:
            r["empty"] = False
        self.assertTrue(any("outside 15-50%" in t for t in texts(self.put(pl))))
        for r in pl["rooms"]:
            r["empty"] = True
        self.assertTrue(any("outside 15-50%" in t for t in texts(self.put(pl))))

    def test_combat_without_terrain(self):
        pl = good_dungeon()
        del pl["rooms"][4]["terrain"]
        self.assertIn("combat room e has no terrain feature (cover, height, hazard)", texts(self.put(pl)))

    def test_unknown_link_room(self):
        pl = good_dungeon()
        pl["links"].append(["a", "zz"])
        with self.assertRaises(ValueError):
            self.put(pl)


class TestRoles(LintBase):
    def test_order_broken(self):
        pl = good_dungeon()
        pl["rooms"][2]["role"], pl["rooms"][3]["role"] = "setback", "puzzle"
        self.assertTrue(any("role order broken" in t for t in texts(self.put(pl), "roles")))

    def test_two_climaxes(self):
        pl = good_dungeon()
        pl["rooms"][3]["role"] = "climax"
        ws = texts(self.put(pl), "roles")
        self.assertIn("2 climax rooms: want exactly one", ws)
        self.assertIn("no setback room on the entrance-to-goal path", ws)

    def test_setback_off_path(self):
        pl = good_dungeon()
        pl["rooms"].append({"id": "g", "role": "setback"})
        pl["rooms"][3]["role"] = None
        pl["links"].append(["a", "g"])
        self.assertIn("no setback room on the entrance-to-goal path", texts(self.put(pl), "roles"))

    def test_no_roles_no_role_warnings(self):
        pl = good_dungeon()
        for r in pl["rooms"]:
            r.pop("role", None)
        self.assertEqual(texts(self.put(pl), "roles"), [])


class TestTavern(LintBase):
    def test_good_tavern(self):
        self.assertEqual(texts(self.put(tavern()), "tavern"), [])

    def test_taproom_not_largest(self):
        pl = tavern()
        pl["rooms"][1]["area"] = 80
        self.assertIn("taproom tap is not the largest public room (snug is)", texts(self.put(pl)))

    def test_kitchen_not_adjacent(self):
        pl = tavern()
        pl["links"] = [["tap", "snug"], ["snug", "kit"], ["kit", "vault"]]
        self.assertIn("kitchen is not next to the taproom", texts(self.put(pl)))

    def test_missing_rear_door(self):
        pl = tavern()
        del pl["rooms"][2]["door"]
        self.assertIn("no rear door", texts(self.put(pl)))

    def test_vault_unstaffed(self):
        pl = tavern()
        pl["links"] = [["tap", "snug"], ["tap", "kit"], ["snug", "vault"]]
        self.assertIn("vault vault is not next to a staffed room", texts(self.put(pl)))

    def test_stairs_in_drinking_room(self):
        pl = tavern()
        pl["rooms"][1]["stairs"] = True
        self.assertIn("stairs in drinking room snug", texts(self.put(pl)))


class TestLandmarksEscape(LintBase):
    def test_missing_landmark(self):
        pl = good_dungeon()
        pl["landmarks"].append("Sunken Bell")
        self.assertEqual(texts(self.put(pl), "landmarks"), ["landmark not on the map: Sunken Bell"])

    def test_escape_distance(self):
        res = self.put(good_dungeon())
        # f > e > d > b (3) : 1 + 1 + 3 = 5, shorter than via c and a (1 + 1 + 2 + 1 = 5 ties); exit is b or a
        self.assertEqual(len(res["escape"]), 1)
        self.assertEqual(res["escape"][0]["distance"], 5)

    def test_escape_unreachable(self):
        pl = good_dungeon()
        pl["rooms"].append({"id": "h", "treasure": True})
        res = self.put(pl)
        self.assertIn({"treasure": "h", "exit": None, "distance": None}, res["escape"])


class TestCli(LintBase):
    def test_cli_strict_and_json(self):
        pl = good_dungeon()
        pl["landmarks"].append("Nowhere")
        self.put(pl)
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit) as cm:
            mpw.main(["lint", self.tmp, "--strict"])
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("WARN landmarks: landmark not on the map: Nowhere", buf.getvalue())
        buf = io.StringIO()
        with redirect_stdout(buf):
            mpw.main(["lint", self.tmp, "--json"])
        self.assertEqual(len(json.loads(buf.getvalue())["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()


class TestKoboldChecks(LintBase):
    def test_good_plan_clean(self):
        self.assertEqual(texts(self.put(good_dungeon()), "layout"), [])

    def test_dead_end_climax(self):
        plan = good_dungeon()
        plan["links"] = [l for l in plan["links"] if l != ["e", "f"]]
        self.assertTrue(any("climax room e has 1 link" in t for t in texts(self.put(plan), "layout")))

    def test_level_without_vertical(self):
        plan = good_dungeon()
        plan["rooms"][2].pop("vertical")
        self.assertTrue(any("level 0 has no room with a vertical" in t for t in texts(self.put(plan))))

    def test_vertical_terrain_counts(self):
        plan = good_dungeon()
        plan["rooms"][2].pop("vertical")
        plan["rooms"][0]["terrain"] = ["Balcony"]
        self.assertFalse(any("vertical" in t for t in texts(self.put(plan))))

    def test_empty_room_without_hook(self):
        plan = good_dungeon()
        plan["rooms"][1].pop("hook")
        self.assertIn("empty room b has no hook (something to notice, use or wonder about)",
                      texts(self.put(plan), "layout"))

    def test_factions_need_eats_and_tolerates(self):
        plan = good_dungeon()
        plan["factions"] = [{"name": "kobolds", "eats": "cave fish", "tolerates": "goblin iron"},
                            {"name": "goblins", "eats": "rats"}, "ghouls"]
        w = texts(self.put(plan), "factions")
        self.assertEqual(len(w), 3)
        self.assertTrue(any("goblins has no tolerates" in t for t in w))
        self.assertTrue(any("ghouls has no eats" in t for t in w))


class TestRouteAndDistrictChecks(LintBase):
    def test_good_plan_clean(self):
        res = self.put(good_dungeon())
        self.assertEqual(texts(res, "routes") + texts(res, "districts"), [])

    def test_parallel_routes_without_trade_off(self):
        plan = good_dungeon()
        plan["links"] += [{"a": "a", "b": "c", "length": 3}, {"a": "c", "b": "a", "length": 3}]
        self.assertTrue(any("rooms c and a are joined by two routes" in t for t in texts(self.put(plan), "routes")))

    def test_parallel_routes_with_trade_off(self):
        plan = good_dungeon()
        plan["links"] += [{"a": "a", "b": "c", "length": 3}, {"a": "a", "b": "c", "length": 3, "hazard": 2}]
        self.assertEqual(texts(self.put(plan), "routes"), [])

    def test_hub_cue_opt_in(self):
        plan = {"rooms": [{"id": h} for h in "hxyz"],
                "links": [{"a": "h", "b": "x", "cue": "bell tower"}, {"a": "h", "b": "y"}, ["h", "z"]]}
        w = texts(self.put(plan), "routes")
        self.assertEqual(sorted(w), ["hub h: link to y has no cue the players can see",
                                     "hub h: link to z has no cue the players can see"])
        plan["links"] = [["h", "x"], ["h", "y"], ["h", "z"]]
        self.assertEqual(texts(self.put(plan), "routes"), [])

    def test_districts(self):
        plan = {"rooms": [{"id": "tan", "kind": "tannery", "tags": ["nuisance"]},
                          {"id": "homes", "kind": "residential"},
                          {"id": "mkt", "kind": "market"},
                          {"id": "mkt2", "kind": "market"},
                          {"id": "g", "kind": "gate"}],
                "links": [["tan", "homes"], ["mkt", "homes"], ["mkt2", "g"]]}
        w = texts(self.put(plan), "districts")
        self.assertEqual(sorted(w), ["market mkt has no link to a gate, dock or main road",
                                     "nuisance district tan borders residential district homes"])


class TestSupplyChecks(LintBase):
    """Domains at War: Campaigns (Autarch; p. 55 nested hexes, p. 58 supply lines). Weights are test input."""
    W = {"road": 1, "settled": 2, "wild": 3, "desert": 6, "river": 1}

    def plan(self, **sup):
        return {"rooms": [{"id": "base", "ground": "settled"}, {"id": "r1", "ground": "road"},
                          {"id": "w1", "ground": "wild"}, {"id": "camp", "ground": "wild", "army": True}],
                "links": [["base", "r1"], ["r1", "camp"], ["base", "w1"], ["w1", "camp"]],
                "supply": dict(weights=self.W, bases=["base"], **sup)}

    def test_hex_scale(self):
        s = L.hex_scale(6)
        self.assertEqual((s["weekly_hex"], s["daily_per_weekly"]), (24.0, 16))
        with self.assertRaises(ValueError):
            L.hex_scale(6, 1)

    def test_cheapest_line(self):
        res = self.put(self.plan(max=10, daily_hex=6))
        self.assertEqual(texts(res, "supply"), [])
        self.assertIn("supply line camp: cost 4 via base > r1 > camp", res["info"])
        self.assertTrue(any("weekly hex 24" in i for i in res["info"]))

    def test_over_max_and_cut(self):
        self.assertEqual(texts(self.put(self.plan(max=3)), "supply"),
                         ["army at camp: supply line costs 4, over the max 3"])
        plan = self.plan()
        plan["links"] = [["base", "r1"]]
        self.assertEqual(texts(self.put(plan), "supply"), ["army at camp has no supply line to a base"])

    def test_missing_weights(self):
        plan = self.plan()
        plan["supply"]["weights"] = {}
        self.assertTrue(texts(self.put(plan), "supply")[0].startswith("supply has no weights"))
        plan = self.plan()
        plan["rooms"][2]["ground"] = "swamp"
        self.assertIn("hex w1 ground 'swamp' has no supply weight", texts(self.put(plan), "supply"))

    def test_no_supply_is_silent(self):
        self.assertEqual(texts(self.put({"rooms": [{"id": "a"}]}), "supply"), [])


class TestLayerChecks(LintBase):
    """Manual of the Planes p. 9 (arrive on the outer layer), p. 21-22 (special terrain costs and pays)."""

    def plan(self, arrival="outer", tag=True):
        link = {"a": "m", "b": "c"}
        if tag:
            link["portal"] = True
        return {"rooms": [{"id": "o", "layer": "outer"}, {"id": "m", "layer": "middle"},
                          {"id": "c", "layer": "core"}],
                "links": [{"a": "o", "b": "m", "tags": ["guarded"]}, link],
                "layers": {"order": ["outer", "middle", "core"], "arrival": arrival}}

    def test_clean(self):
        self.assertEqual(texts(self.put(self.plan()), "layers"), [])

    def test_arrival_not_outer(self):
        self.assertEqual(texts(self.put(self.plan(arrival="middle")), "layers"),
                         ["arrival layer middle is not the outer layer outer: travellers should land on the outside"])

    def test_deeper_layer_untagged(self):
        self.assertEqual(texts(self.put(self.plan(tag=False)), "layers"),
                         ["layer core has no link from a shallower layer tagged portal or guarded"])

    def test_special_terrain_one_sided(self):
        plan = {"rooms": [{"id": "a", "terrain": ["pit", {"name": "ash", "special": True, "cost": "slow"}]}],
                "terrain": [{"name": "glass", "special": True, "boon": "heal 1"},
                            {"name": "moss", "special": True, "cost": "slick", "boon": "silent"},
                            {"name": "rock", "cost": "slow"}]}
        self.assertEqual(sorted(texts(self.put(plan), "terrain")),
                         ["special terrain ash (a) has only a cost: give it both a price and a payoff",
                          "special terrain glass (plan) has only a boon: give it both a price and a payoff"])


class TestLairChecks(LintBase):
    """Draconomicon p. 93 (two ways out, a gap too small for the owner), p. 61 (hoard footprint)."""

    def plan(self):
        return {"rooms": [{"id": "mouth", "entrance": True, "opening": 4},
                          {"id": "crack", "entrance": True, "opening": 1},
                          {"id": "hoard", "treasure": True, "area": 36}],
                "links": [["mouth", "hoard"], ["crack", "hoard"]],
                "lair": {"owner": "gargantuan", "hoard": 16}}

    def test_clean_reports_area(self):
        res = self.put(self.plan())
        self.assertEqual(texts(res, "lair"), [])
        self.assertIn("lair: treasure room hoard area 36 squares vs hoard 16 (44%)", res["info"])

    def test_one_entrance_none_small_hoard_too_big(self):
        plan = self.plan()
        plan["rooms"][1] = {"id": "crack"}
        plan["lair"]["hoard"] = 49
        self.assertEqual(texts(self.put(plan), "lair"), [
            "lair has 1 entrance(s): the owner wants at least 2 ways out",
            "no lair entrance is narrower than the owner (4 squares): add a gap only small intruders can use",
            "treasure room hoard (36 squares) is smaller than the hoard (49 squares)"])

    def test_bad_size_and_silent(self):
        plan = self.plan()
        plan["lair"]["owner"] = "enormous"
        with self.assertRaises(ValueError):
            self.put(plan)
        self.assertEqual(texts(self.put({"rooms": [{"id": "a"}]}), "lair"), [])

    def test_cli_strict(self):
        plan = self.plan()
        plan["rooms"][1] = {"id": "crack"}
        self.put(plan)
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            mpw.main(["lint", self.tmp, "--strict"])
        self.assertIn("WARN lair:", buf.getvalue())


class TestLockChecks(LintBase):
    """Deep Carbon Observatory p. 21, 31 (keys dropped by wanderers), p. 34-35 (decoy door), p. 46-47 (toll, words)."""

    def plan(self):
        return {"rooms": [{"id": "gate", "entrance": True}, {"id": "hall"}, {"id": "shrine"},
                          {"id": "vault"}, {"id": "fake", "decoy": True}, {"id": "nook", "secret": True}],
                "links": [["gate", "hall"], {"id": "door", "a": "hall", "b": "vault"},
                          ["gate", "shrine"], ["hall", "fake"], ["fake", "nook"],
                          {"id": "troll", "a": "shrine", "b": "vault", "oneway": True}],
                "locks": [{"at": "door", "key": "red", "key_in": "shrine", "kind": "key"},
                          {"at": "vault", "key": "word", "key_in": "hall", "kind": "word"},
                          {"at": "troll", "key": "life", "key_in": "wander", "kind": "toll",
                           "drop_from": "guardian"}]}

    def test_clean(self):
        self.assertEqual(texts(self.put(self.plan()), "locks"), [])

    def test_softlock_one_room_toll_wander_decoy(self):
        plan = self.plan()
        plan["locks"][0]["key_in"] = "vault"
        plan["locks"][1]["key_in"] = "vault"
        del plan["locks"][2]["drop_from"]
        del plan["links"][5]["oneway"]
        plan["rooms"][5] = {"id": "nook"}
        self.assertEqual(texts(self.put(plan), "locks"), [
            "key word in vault cannot be reached with lock at vault closed: softlock",
            "wandering key life has no drop_from foe: say who carries it",
            "toll lock at troll is not marked oneway: say whether the far side pays",
            "all 2 keys sit in room vault: spread them out",
            "decoy fake has no secret door within 2 rooms: hide the real way nearby"])

    def test_secret_link_and_lock_oneway(self):
        plan = self.plan()
        plan["rooms"][5] = {"id": "nook"}
        plan["links"][4] = {"a": "fake", "b": "nook", "secret": True}
        del plan["links"][5]["oneway"]
        plan["locks"][2]["oneway"] = True
        self.assertEqual(texts(self.put(plan), "locks"), [])

    def test_bad_refs_and_silent(self):
        for k, v in (("at", "nowhere"), ("key_in", "nowhere"), ("kind", "riddle")):
            plan = self.plan()
            plan["locks"][0][k] = v
            with self.assertRaises(ValueError):
                self.put(plan)
        self.assertEqual(texts(self.put({"rooms": [{"id": "a"}]}), "locks"), [])

    def test_cli_strict(self):
        plan = self.plan()
        plan["locks"][1]["key_in"] = "vault"
        self.put(plan)
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            mpw.main(["lint", self.tmp, "--strict"])
        self.assertIn("WARN locks:", buf.getvalue())
