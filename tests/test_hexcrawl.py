"""Tests for gen hexcrawl: terrain features, keyed share, sandbox kit, check bars and the sandbox lint."""
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
import mpw_hexcrawl as H  # noqa: E402
import mpw_lint  # noqa: E402
import mpw_space as S  # noqa: E402


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


class HexcrawlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mpw-hex-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gen(self, seed=3, **kw):
        out = os.path.join(self.tmp, "hc%d" % seed)
        H.gen_hexcrawl(seed, out, **kw)
        with open(os.path.join(out, "sandbox.json"), encoding="utf-8") as f:
            return out, json.load(f)

    def test_bars_pass_and_regen(self):
        for seed in (1, 2, 3, 7):
            out, _ = self.gen(seed)
            bars = S.check(out, labels=False)
            self.assertEqual([b for b in bars if b[2] is False], [], bars)

    def test_kit_shape(self):
        _, sb = self.gen(5)
        self.assertEqual(sorted(sb), ["encounters", "geography", "keys", "overview", "rumors", "terrain"])
        for k in sb["keys"]:
            self.assertRegex(k["hex"], r"^\d{4}$")
        letters = [g["letter"] for g in sb["geography"]]
        self.assertEqual(letters[:3], ["A", "B", "C"])
        self.assertTrue(all(len(g["hexes"]) >= 2 for g in sb["geography"]))
        self.assertTrue(any(k.get("landmark") and k["sight"] >= 2 for k in sb["keys"]))
        self.assertEqual(len(sb["rumors"]), 8)
        self.assertEqual({r["truth"] for r in sb["rumors"]}, {"true", "false", "half"})
        self.assertEqual(sum(1 for e in sb["encounters"] if e["kind"] == "clash"), 1)
        for t in sb["terrain"].values():
            self.assertTrue(t["hazard"] and t["predator"] and 1 <= t["hazard_in_10"] <= 10)

    def test_keyed_share_configurable(self):
        for share in (0.1, 0.33, 0.6):
            _, sb = self.gen(4, keyed=share)
            ov = sb["overview"]
            self.assertLessEqual(abs(ov["keyed_share"] - share) * ov["land_hexes"], 1.0)

    def test_terrain_coherent(self):
        out, sb = self.gen(6)
        # region growing: far fewer features than hexes, and most hexes inside a multi-hex feature
        n = sb["overview"]["hexes"]
        self.assertLess(len(sb["geography"]), n / 6)
        self.assertGreater(sum(len(g["hexes"]) for g in sb["geography"]), 0.8 * n)

    def test_hex_ids_and_letters(self):
        self.assertEqual(H.hex_id(0, 0), "0101")
        self.assertEqual(H.parse_hex("0307"), (2, 6))
        self.assertEqual([H.letter(i) for i in (0, 25, 26)], ["A", "Z", "AA"])
        self.assertRaises(ValueError, H.parse_hex, "37")

    def test_bad_args(self):
        self.assertRaises(ValueError, H.gen_hexcrawl, 1, os.path.join(self.tmp, "x"), keyed=0.95)
        self.assertRaises(ValueError, H.gen_hexcrawl, 1, os.path.join(self.tmp, "x"), cols=3)

    def test_sandbox_lint(self):
        out, sb = self.gen(8)
        self.assertEqual(mpw_lint.lint(out)["warnings"], [])
        sb["keys"].append(dict(hex="9999", kind="ruin", title="far ruin"))
        sb["keys"].append(dict(sb["keys"][0]))
        sb["encounters"] = [e for e in sb["encounters"] if e["kind"] != "clash"]
        sb["rumors"][0].update(truth="true", hex="0101" if "0101" not in [k["hex"] for k in sb["keys"]] else "0102")
        for k in sb["keys"]:
            k.pop("sight", None)
        unk = {k["hex"] for k in sb["keys"]}
        sb["rumors"][0]["hex"] = next(H.hex_id(c, r) for c in range(20) for r in range(16) if H.hex_id(c, r) not in unk)
        with open(os.path.join(out, "sandbox.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(sb, f)
        txt = " | ".join(w["text"] for w in mpw_lint.lint(out)["warnings"])
        for frag in ("outside the 20x16 map", "keyed more than once", "no clash result", "points at unkeyed",
                     "no sight radius"):
            self.assertIn(frag, txt)

    def test_cli(self):
        out = os.path.join(self.tmp, "cli")
        txt = run_cli("gen", "hexcrawl", "--seed", "2", "--cols", "12", "--rows", "10", "--miles", "3",
                      "--out", out)
        self.assertIn("keyed", txt)
        with open(os.path.join(out, "map.svg"), encoding="utf-8") as f:
            self.assertIn("1 hex = 3 miles", f.read())
        self.assertIn("0 warning(s)", run_cli("lint", out))


if __name__ == "__main__":
    unittest.main()
