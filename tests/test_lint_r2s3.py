"""Tests for mpw lint families from the r2s3 book batch: hostile, doom, questions, omens, portals, cue."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_lint import LintBase, texts  # noqa: E402


def base():
    return {
        "rooms": [
            {"id": "gate", "kind": "gate", "entrance": True, "main": True, "cue": 1},
            {"id": "wall", "baffle": True, "cue": 2},
            {"id": "hall", "lethal": True, "warning": "scorched floor", "cue": 3},
            {"id": "fake", "decoy": True, "cue": 3},
            {"id": "vault", "treasure": True, "cue": 5},
        ],
        "links": [["gate", "wall"], ["wall", "hall"], ["hall", "fake"], ["hall", "vault"], ["fake", "vault"]],
        "goal": "vault",
        "hostile": True,
    }


class TestHostile(LintBase):
    def test_clean(self):
        self.assertEqual(texts(self.put(base()), "hostile"), [])

    def test_missing_fields_warn(self):
        plan = base()
        del plan["rooms"][2]["warning"]
        plan["rooms"][1].pop("baffle")
        plan["rooms"][3].pop("decoy")
        w = texts(self.put(plan), "hostile")
        self.assertEqual(len(w), 3)
        self.assertTrue(any("warning cue" in x for x in w))
        self.assertTrue(any("baffle" in x for x in w))
        self.assertTrue(any("decoy" in x for x in w))

    def test_opt_in(self):
        plan = base()
        plan["hostile"] = False
        del plan["rooms"][2]["warning"]
        self.assertEqual(texts(self.put(plan), "hostile"), [])


class TestDoom(LintBase):
    def test_circle_closes(self):
        plan = base()
        plan["doom"] = {"track": ["hall", "fake", "vault"]}
        res = self.put(plan)
        self.assertEqual(texts(res, "doom"), [])
        self.assertIn("doom track: hall > fake > vault > hall", res["info"])

    def test_broken_and_short(self):
        plan = base()
        plan["doom"] = {"track": ["gate", "hall", "vault"]}
        w = texts(self.put(plan), "doom")
        self.assertTrue(any("gate > hall" in x for x in w))
        self.assertTrue(any("vault > gate" in x for x in w))
        plan["doom"] = {"track": ["gate", "wall"]}
        self.assertTrue(any("2 steps" in x for x in texts(self.put(plan), "doom")))

    def test_unknown_room_raises(self):
        plan = base()
        plan["doom"] = {"track": ["gate", "nowhere", "vault"]}
        with self.assertRaises(ValueError):
            self.put(plan)


class TestQuestions(LintBase):
    def test_features_get_questions(self):
        plan = base()
        plan["rooms"][1]["locked"] = True
        plan["rooms"][2]["terrain"] = ["pit"]
        plan["rooms"][3]["secret"] = True
        plan["links"][0] = {"a": "gate", "b": "wall", "secret": True}
        qs = [i for i in self.put(plan)["info"] if i.startswith("open question")]
        self.assertEqual(len(qs), 5)
        self.assertTrue(any("goal vault" in q for q in qs))

    def test_answer_silences(self):
        plan = base()
        plan["rooms"][4]["answer"] = "the founder's tomb"
        qs = [i for i in self.put(plan)["info"] if i.startswith("open question")]
        self.assertEqual(qs, [])


class TestOmens(LintBase):
    def test_kind_without_omens(self):
        plan = base()
        plan["rooms"][2]["kind"] = "crypt"
        plan["omens"] = {"gate": ["ravens on the arch"]}
        w = texts(self.put(plan), "omens")
        self.assertEqual(w, ["site kind crypt has no omens: give a sign that it is near"])
        plan["omens"]["crypt"] = ["cold draft"]
        self.assertEqual(texts(self.put(plan), "omens"), [])


class TestPortals(LintBase):
    def plan(self):
        return {"rooms": [{"id": "a", "entrance": True}, {"id": "b"}, {"id": "c"}],
                "links": [["a", "b"], {"a": "b", "b": "c", "oneway": True, "portal": True}]}

    def test_no_return_warns(self):
        self.assertEqual(texts(self.put(self.plan()), "portals"),
                         ["one-way portal b > c: c states no return exit"])

    def test_return_field_or_path_clears(self):
        plan = self.plan()
        plan["rooms"][2]["return"] = "the mirror in the cellar"
        self.assertEqual(texts(self.put(plan), "portals"), [])
        plan = self.plan()
        plan["links"].append(["c", "a"])
        self.assertEqual(texts(self.put(plan), "portals"), [])

    def test_oneway_back_does_not_count(self):
        plan = self.plan()
        plan["links"].append({"a": "a", "b": "c", "oneway": True})
        self.assertEqual(len(texts(self.put(plan), "portals")), 1)


class TestCue(LintBase):
    def test_rising_clean(self):
        self.assertEqual(texts(self.put(base()), "cue"), [])

    def test_drop_and_range(self):
        plan = base()
        plan["rooms"][2]["cue"] = 0
        plan["rooms"][3]["cue"] = 9
        w = texts(self.put(plan), "cue")
        self.assertTrue(any("cue drops from wall (2) to hall (0)" in x for x in w))
        self.assertTrue(any("fake cue 9" in x for x in w))


if __name__ == "__main__":
    unittest.main()
