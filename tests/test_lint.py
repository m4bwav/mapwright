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
            {"id": "b", "entrance": True, "danger": 1, "empty": True, "level": 0},
            {"id": "c", "role": "puzzle", "danger": 2, "empty": False, "level": 0},
            {"id": "d", "role": "setback", "danger": 3, "empty": True, "combat": True, "terrain": ["pit"],
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
