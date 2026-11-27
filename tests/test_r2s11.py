"""Tests for stronghold plans, home-base shifts, trap and lair-home lints, and hexcrawl anchors and risk rings."""
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
import mpw_grow as G  # noqa: E402
import mpw_hexcrawl as H  # noqa: E402
import mpw_lint as L  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def texts(res, check):
    return [w["text"] for w in res["warnings"] if w["check"] == check]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-r2s11-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lint(self, plan):
        with open(os.path.join(self.tmp, "recipe.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": "plan", "plan": plan}, f)
        return L.lint(self.tmp)


class TestStronghold(Base):
    def test_styles_shape_and_storeys(self):
        for style, ((rl, rh), (sl, sh)) in G.STYLES.items():
            p = G.stronghold_plan(5, style)
            s = p["stronghold"]
            self.assertIn(s["shape"], G.SHAPES)
            self.assertTrue(sl <= s["storeys"] <= sh and rl <= s["rooms"] <= rh)
            self.assertEqual(len(p["rooms"]), s["rooms"] + 2)
            self.assertEqual(max(r.get("floor", 0) for r in p["rooms"]), s["storeys"] - 1)
        self.assertEqual(G.stronghold_plan(9, "tower"), G.stronghold_plan(9, "tower"))
        with self.assertRaises(ValueError):
            G.stronghold_plan(1, "pagoda")

    def test_facade_only_and_base_lint_clean(self):
        p = G.stronghold_plan(3, "concentric", facade_only=True)
        self.assertEqual([r["id"] for r in p["rooms"]], ["out", "g0"])
        out = run_cli("grow", "--seed", "4", "--out", self.tmp, "--stronghold", "courtyard")
        self.assertIn("courtyard footprint", out)
        res = L.lint(self.tmp)
        self.assertEqual(texts(res, "base") + texts(res, "traps"), [])
        plan = json.load(open(os.path.join(self.tmp, "recipe.json")))["plan"]
        self.assertTrue(all("break" in l for l in plan["links"] if l["kind"] in ("door", "window")))


class TestBaseLint(Base):
    def test_shift_gaps_and_break(self):
        plan = {"rooms": [{"id": "a", "floor": 0, "entrance": True}, {"id": "b", "floor": 1}],
                "links": [{"a": "a", "b": "b", "kind": "door"}],
                "base": {"shifts": {"night": {"a": "watch", "zz": "cook"}}}}
        self.assertEqual(texts(self.lint(plan), "base"), [
            "shift night names unknown room zz", "floor 1 has nobody on the night shift",
            "door a - b has no break value"])


class TestTrapLint(Base):
    def test_trigger_effect_lockdown_bypass(self):
        plan = {"rooms": [{"id": "a", "entrance": True}, {"id": "b", "trap": {"trigger": ["1,1"]}},
                          {"id": "c", "lockdown": True, "trap": {"trigger": ["2,2"], "effect": ["3,3"]}}],
                "links": [["a", "b"], {"a": "b", "b": "c", "door": True}, {"a": "a", "b": "c"}],
                "owner_route": ["a", "c"]}
        self.assertEqual(texts(self.lint(plan), "traps"), [
            "trap in room b needs separate trigger and effect areas",
            "lockdown room c has a link to a with no door drawn",
            "trap in room c sits on the owner route with no bypass"])
        plan["rooms"][2]["trap"]["bypass"] = "owner's ring"
        plan["links"][2]["door"] = True
        plan["rooms"][1]["trap"]["effect"] = ["1,2"]
        self.assertEqual(texts(self.lint(plan), "traps"), [])


class TestLairHome(Base):
    def test_missing_hazard_and_route(self):
        plan = {"rooms": [{"id": "a", "entrance": True}, {"id": "b", "entrance": True}],
                "links": [["a", "b"]], "lair": {}, }
        plan["lair"] = {"owner": 2}
        w = texts(self.lint(plan), "lair")
        self.assertTrue(any("no home_hazard" in t for t in w) and any("resident_only" in t for t in w))
        plan["rooms"][0]["home_hazard"] = {"gate": "size"}
        self.assertTrue(any("give gate weight or size" in t for t in texts(self.lint(plan), "lair")))


class TestHexAnchorsRisk(Base):
    def test_hex_dist_and_rings(self):
        self.assertEqual(H.hex_dist((0, 0), (0, 0)), 0)
        self.assertEqual(H.hex_dist((0, 0), (1, 0)), 1)
        self.assertEqual(H.hex_dist((0, 0), (0, 3)), 3)
        t = H.risk_rings(12, 12, [(5, 5)])
        self.assertEqual(t[(5, 5)], 0)
        self.assertEqual(t[(5, 9)], 2)
        self.assertEqual(t[(5, 0)], 2)
        self.assertEqual(H.risk_rings(12, 12, [], roads=[(0, 0)])[(0, 1)], 1)

    def test_anchors_only_and_risk_regen(self):
        run_cli("gen", "hexcrawl", "--seed", "7", "--out", self.tmp, "--anchors-only", "--risk-rings")
        sb = json.load(open(os.path.join(self.tmp, "sandbox.json")))
        hc = json.load(open(os.path.join(self.tmp, "hexcrawl.json")))
        self.assertTrue(sb["overview"]["anchors_only"])
        self.assertTrue(all(k["detail"] == "on arrival" for k in sb["keys"]))
        feats = [k["feature"] for k in sb["keys"] if not k.get("landmark")]
        self.assertEqual(len(feats), len(set(feats)))
        self.assertTrue(all(x["risk"] in (0, 1, 2, 3) for x in hc["hexes"]))
        self.assertTrue(all(ok for _, ok, _ in H.bars(self.tmp)))
        tmp2 = os.path.join(self.tmp, "re")
        H.regenerate(self.tmp, tmp2)
        self.assertEqual(open(os.path.join(tmp2, "sandbox.json")).read(),
                         open(os.path.join(self.tmp, "sandbox.json")).read())
        self.assertEqual(L.lint(self.tmp)["warnings"], [])


if __name__ == "__main__":
    unittest.main()
