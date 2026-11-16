"""Tests for scripts/mpw_aistyle.py: the optional AI style pass.

No GPU, no network, no browser: the HTTP layer and the SVG rasteriser are replaced by fakes.
One live test runs only with MAPWRIGHT_LIVE=1 and a server in MAPWRIGHT_COMFYUI.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import mpw  # noqa: E402
import mpw_gen as G  # noqa: E402
import mpw_read as RD  # noqa: E402
import mpw_render as R  # noqa: E402
import mpw_aistyle as A  # noqa: E402

LAND, SEA, LAKE, RIVER = (206, 196, 150), (150, 190, 226), (120, 170, 220), (40, 90, 170)
SIZE = 256


def run_cli(*args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        mpw.main(list(args))
    return buf.getvalue()


def paint(world, w, h, shift=0, rivers=True, lakes=True):
    """A flat picture of the recipe's own geometry: land, sea, lakes, 3 px rivers. shift moves it right."""
    tr = A.truth(world, w, h)
    rows = []
    for y in range(h):
        land = format(tr["land"][y], "0%db" % w)
        lake = format(tr["lakes"][y], "0%db" % w)
        row = bytearray()
        for x in range(w):
            xs = min(w - 1, max(0, x - shift))
            row += bytes(LAKE if lakes and lake[xs] == "1" else LAND if land[xs] == "1" else SEA)
        rows.append(row)
    if rivers:
        for x, y, _, _, _ in tr["rivers"]:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    xi, yi = int(x) + dx + shift, int(y) + dy
                    if 0 <= xi < w and 0 <= yi < h:
                        rows[yi][3 * xi:3 * xi + 3] = bytes(RIVER)
    return G.png_bytes(w, h, rows, 8, 2)


class FakeServer:
    """Stands in for ComfyUI's HTTP API. `styled` turns the uploaded control picture into the result."""

    def __init__(self, styled=None, polls=2, fail=None, models=None):
        self.calls, self.uploads, self.prompts = [], {}, {}
        self.styled = styled or (lambda png: png)
        self.polls, self.fail = polls, fail
        self.models = models or {"UNETLoader": ["z_image_turbo_bf16.safetensors"], "CLIPLoader": ["qwen_3_4b.safetensors"],
                                 "VAELoader": ["ae.safetensors"]}

    def __call__(self, method, url, data=None, headers=None, timeout=30):
        self.calls.append((method, url))
        assert url.startswith("http://fake.test"), url
        path = url[len("http://fake.test"):]
        if path == "/system_stats":
            return 200, json.dumps({"system": {"comfyui_version": "9.9.9"}}).encode()
        if path.startswith("/object_info/"):
            node = path.split("/")[-1]
            field = {"UNETLoader": "unet_name", "CLIPLoader": "clip_name", "VAELoader": "vae_name"}[node]
            return 200, json.dumps({node: {"input": {"required": {field: [self.models[node]]}}}}).encode()
        if path == "/upload/image":
            assert "multipart/form-data; boundary=" in headers["Content-Type"]
            b = headers["Content-Type"].split("boundary=")[1].encode()
            part = data.split(b"--" + b)[1]
            head, body = part.split(b"\r\n\r\n", 1)
            name = head.split(b'filename="')[1].split(b'"')[0].decode()
            self.uploads[name] = body[:-2]
            return 200, json.dumps({"name": name, "subfolder": "", "type": "input"}).encode()
        if path == "/prompt":
            if self.fail == "queue":
                return 400, json.dumps({"error": {"type": "prompt_outputs_failed_validation"},
                                        "node_errors": {"1": "unet_name not in list"}}).encode()
            wf = json.loads(data.decode())["prompt"]
            pid = "job%d" % (len(self.prompts) + 1)
            self.prompts[pid] = dict(wf=wf, polls=0)
            return 200, json.dumps({"prompt_id": pid}).encode()
        if path.startswith("/history/"):
            pid = path.split("/")[-1]
            p = self.prompts[pid]
            p["polls"] += 1
            if self.fail == "never" or p["polls"] < self.polls:
                return 200, b"{}"
            if self.fail == "run":
                return 200, json.dumps({pid: {"outputs": {}, "status": {"status_str": "error", "messages": [
                    ["execution_error", {"exception_message": "out of memory"}]]}}}).encode()
            return 200, json.dumps({pid: {"outputs": {"10": {"images": [
                {"filename": "mapwright-aistyle_00001_.png", "subfolder": "", "type": "output"}]}},
                "status": {"status_str": "success", "completed": True}}}).encode()
        if path.startswith("/view?"):
            wf = list(self.prompts.values())[-1]["wf"]
            return 200, self.styled(self.uploads[wf["6"]["inputs"]["image"]])
        return 404, b"{}"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mpw-aistyle-")
        cls.world = os.path.join(cls.tmp, "w")
        G.gen_world(7, 3000, cls.world, raster_px=128)
        cls.real_svg_to = R.svg_to

        def fake_svg_to(svg_path, out, browser=None, timeout=120):
            root = ET.parse(svg_path).getroot()
            with open(out, "wb") as f:
                f.write(paint(cls.world, int(root.get("width")), int(root.get("height"))))
            return out
        R.svg_to = fake_svg_to

    @classmethod
    def tearDownClass(cls):
        R.svg_to = cls.real_svg_to
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def out(self, name):
        return os.path.join(self.tmp, name)

    def fresh_world(self, name):
        d = self.out(name)
        if not os.path.isdir(d):
            shutil.copytree(self.world, d)
        return d


class TestWorkflow(Base):
    def test_looks_and_template(self):
        for name in ("painted-atlas", "ink-and-parchment", "satellite", "watercolour"):
            lk = A.look(name)
            self.assertIn(lk["base"], R.STYLES)
            self.assertGreater(len(lk["prompt"]), 80)
        with self.assertRaises(ValueError):
            A.look("nope")
        t = A.load_template()
        self.assertEqual(t["model"]["licence"], "Apache-2.0")
        self.assertEqual(t["model"]["licence_class"], "ok-commercial")
        out = run_cli("aistyle", "--list")
        self.assertIn("painted-atlas", out)
        self.assertIn("watercolour", out)

    def test_fill_types_and_unknown_slot(self):
        wf = A.fill({"8": {"inputs": {"seed": "{SEED}", "denoise": "{DENOISE}", "text": "{PROMPT}", "k": ["4", 0]}}},
                    dict(SEED=7, DENOISE=0.45, PROMPT="a {map}"))
        self.assertEqual(wf["8"]["inputs"], {"seed": 7, "denoise": 0.45, "text": "a {map}", "k": ["4", 0]})
        with self.assertRaises(ValueError):
            A.fill({"a": "{NOPE}"}, {})

    def test_hash_is_stable_and_sensitive(self):
        p = A.plan(self.world, "painted-atlas", out=self.out("h.svg"), seed=3, size=SIZE)
        a = A.build_workflow(p, "x.png")
        self.assertEqual(A.workflow_hash(a), A.workflow_hash(json.loads(json.dumps(a))))
        p2 = A.plan(self.world, "painted-atlas", out=self.out("h.svg"), seed=4, size=SIZE)
        self.assertNotEqual(A.workflow_hash(a), A.workflow_hash(A.build_workflow(p2, "x.png")))
        self.assertEqual(len(A.workflow_hash(a)), 64)

    def test_denoise_runs_on_the_step_grid(self):
        self.assertAlmostEqual(A.effective_denoise(9, 0.45), 0.45)
        self.assertAlmostEqual(A.effective_denoise(9, 0.55), 0.5625)
        self.assertAlmostEqual(A.effective_denoise(9, 0.65), 9 / 13.0)
        self.assertEqual(A.effective_denoise(9, 1.0), 1.0)

    def test_model_size(self):
        self.assertEqual(A.model_size(1000, 1000), (1024, 1024))
        self.assertEqual(A.model_size(1000, 600), (1024, 608))
        self.assertEqual(A.model_size(600, 1000), (608, 1024))
        self.assertEqual(A.model_size(1000, 1000, 250), (256, 256))

    def test_model_override_marks_the_licence_unstated(self):
        p = A.plan(self.world, "satellite", out=self.out("m.svg"), model="other.safetensors")
        self.assertEqual(p["model"]["unet"], "other.safetensors")
        self.assertTrue(p["model"]["licence_class"].startswith("unstated"))
        with self.assertRaises(ValueError):
            A.plan(self.world, "satellite", out=self.out("m.bmp"))
        with self.assertRaises(ValueError):
            A.plan(self.world, "satellite", out=self.out("m.svg"), denoise=0)


class TestLayers(Base):
    def test_parts_join_to_the_full_render(self):
        for st in R.STYLES:
            p, _ = R.render_parts(self.world, st)
            svg, _ = R.render_svg(self.world, st)
            self.assertEqual("\n".join(p["head"] + p["ground"] + p["water"] + p["coast"] + p["over"] + ["</svg>"]) + "\n",
                             svg, st)

    def test_control_has_no_text_or_symbols(self):
        p, _ = R.render_parts(self.world, "atlas")
        svg = A.control_svg(p, 1024, 1024)
        root = ET.fromstring(svg.encode("utf-8"))
        self.assertEqual((root.get("width"), root.get("height")), ("1024", "1024"))
        self.assertEqual(root.get("viewBox"), "0 0 1000 1000")
        self.assertEqual(len(list(root.iter(R.SVGNS + "text"))), 0)
        self.assertEqual(len(list(root.iter(R.SVGNS + "circle"))), 0)
        for cls in ('class="lbl"', 'class="legend"', 'class="scalebar"', 'class="north"', 'class="title"'):
            self.assertNotIn(cls, svg)
        self.assertIn('class="rivers"', svg)
        self.assertIn('class="coast"', svg)

    def test_overlay_is_the_labelled_renders_own_layer(self):
        """Bars 14 and 15 hold by construction: the code-set layer is the labelled render's, line for line."""
        png = paint(self.world, 64, 64)
        for st in ("atlas", "ink-and-parchment"):
            p, _ = R.render_parts(self.world, st)
            full, _ = R.render_svg(self.world, st)
            comp = A.composite_svg(p, png, 1024, 1024)
            for cls in ("labels", "rivers", "legend", "scalebar", "north"):
                layer = A.layer_of(full, cls)
                self.assertGreater(len(layer), 2, cls)
                self.assertEqual(A.layer_of(comp, cls), layer, (st, cls))
            self.assertEqual(comp.split("\n")[2:], full.split("\n")[len(p["head"] + p["ground"]):][:len(p["water"])]
                             + full.split("\n")[len(p["head"] + p["ground"] + p["water"] + p["coast"]):])
            self.assertNotIn('class="coast"', comp)
            self.assertEqual(comp.count("<image "), 1)
            a, b = R.label_bars(full), R.label_bars(comp)
            self.assertEqual(a, b)
            self.assertTrue(b[0][1] and b[1][1])
            if not shutil.which("tesseract"):
                self.assertIsNone(b[2][1])
                self.assertIn("skipped: tesseract not found", b[2][2])

    def test_label_boxes_use_viewbox_units(self):
        p, _ = R.render_parts(self.world, "atlas")
        comp = A.composite_svg(p, paint(self.world, 32, 32), 2048, 2048)
        labs, w, h = R.labels_from_svg(comp)
        self.assertEqual((w, h), (1000.0, 1000.0))
        self.assertGreater(len(labs), 5)


class TestMeasure(Base):
    def test_true_picture_scores_high_and_drift_fails(self):
        d = self.world
        good = RD.decode_png(paint(d, SIZE, SIZE))
        m = A.measure(d, good, control=good)
        self.assertGreaterEqual(m["land_iou"], 0.99)
        self.assertLessEqual(m["coast_p95_px"], 1)
        self.assertGreaterEqual(m["river_on_land"], 0.99)
        self.assertGreaterEqual(m["towns_on_land"], 0.99)
        self.assertGreaterEqual(m["river_line"], 0.95)
        self.assertGreaterEqual(m["lakes_kept"], 0.9)
        self.assertTrue(A.judge(m, m)[0])
        bad = RD.decode_png(paint(d, SIZE, SIZE, shift=9))
        mb = A.measure(d, bad, control=good)
        self.assertLess(mb["land_iou"], A.TOL_LAND_IOU)
        ok, detail = A.judge(mb, m)
        self.assertFalse(ok)
        self.assertIn("land IoU", detail)

    def test_lost_rivers_and_lakes_are_reported(self):
        d = self.world
        good = RD.decode_png(paint(d, SIZE, SIZE))
        bare = RD.decode_png(paint(d, SIZE, SIZE, rivers=False, lakes=False))
        m = A.measure(d, bare, control=good)
        self.assertLess(m["river_line"], 0.1)
        self.assertLess(m["lakes_kept"], 0.1)
        self.assertGreaterEqual(m["land_iou"], 0.99)     # lakes and rivers are code-set: left out of the IoU
        self.assertTrue(A.judge(m)[0])
        self.assertIsNone(A.measure(d, bare)["river_line"])      # no clean render at hand: not measured

    def test_flat_picture_is_not_measured(self):
        one = RD.Image(64, 64, [bytearray(b"\x80" * 192) for _ in range(64)])
        tr = dict(land=[0] * 64, lakes=[0] * 64, rivers=[], towns=[], w=64, h=64)
        m = A.measure(self.world, one, tr)
        self.assertIsNone(m["land_iou"])
        self.assertIsNone(A.judge(m)[0])

    def test_masks(self):
        rows = [0, 0, 0b00100, 0, 0]
        self.assertEqual(A._dilate(rows, 5, 1), [0, 0b01110, 0b01110, 0b01110, 0])
        self.assertEqual(A._erode(A._dilate(rows, 5, 1), 5, 1), rows)
        self.assertEqual(A._erode([0b11111] * 3, 5, 1), [0b11111] * 3)     # the picture edge does not erode
        self.assertEqual(A._edge([0, 0b01110, 0b01110, 0b01110, 0], 5), [0, 0b01110, 0b01010, 0b01110, 0])
        self.assertEqual(A._pc([0b1011, 0b1]), 4)
        r = [0, 0]
        A._set(r, 4, 0, 1)
        self.assertEqual(r, [0, 0b1000])
        self.assertEqual(A._get(r, 4, 0, 1), 1)
        self.assertEqual(A._get(r, 4, 9, 9), 0)


class TestRun(Base):
    def test_dry_run_contacts_no_server(self):
        d = self.fresh_world("dry")

        def boom(*a, **k):
            raise AssertionError("dry run contacted a server")
        real = A.http
        A.http = boom
        try:
            j = json.loads(run_cli("aistyle", d, "--look", "painted-atlas", "--dry-run", "--seed", "5",
                                   "--denoise", "0.55", "--size", str(SIZE), "--json"))
        finally:
            A.http = real
        self.assertTrue(j["dry_run"])
        self.assertEqual(j["size"], [SIZE, SIZE])
        self.assertAlmostEqual(j["denoise_effective"], 0.5625)
        img = RD.load_image(os.path.join(d, "aistyle-painted-atlas.control.png"))
        self.assertEqual((img.w, img.h), (SIZE, SIZE))
        with open(os.path.join(d, "aistyle-painted-atlas.workflow.json"), encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("\r", raw)
        wf = json.loads(raw)
        self.assertEqual(wf["8"]["inputs"]["seed"], 5)
        self.assertEqual(wf["8"]["inputs"]["denoise"], 0.55)
        self.assertEqual(wf["8"]["inputs"]["steps"], 9)
        self.assertEqual(wf["1"]["inputs"]["unet_name"], "z_image_turbo_bf16.safetensors")
        self.assertTrue(wf["6"]["inputs"]["image"].startswith("mapwright-aistyle-"))
        self.assertEqual(wf["4"]["inputs"]["text"], A.LOOKS["painted-atlas"]["prompt"])
        self.assertEqual(j["workflow_sha256"], A.workflow_hash(wf))
        self.assertFalse(os.path.exists(os.path.join(d, "aistyle-painted-atlas.aistyle.json")))
        self.assertFalse(os.path.exists(os.path.join(d, "aistyle-painted-atlas.png")))
        out = run_cli("aistyle", d, "--look", "painted-atlas", "--dry-run", "--denoise", "0.65", "--size", str(SIZE))
        self.assertIn("warning: denoise 0.65 is above the measured ceiling", out)
        self.assertIn("no server contacted", out)

    def test_full_pass_writes_picture_and_sidecar(self):
        d = self.fresh_world("full")
        srv = FakeServer()
        out = os.path.join(d, "aistyle-ink-and-parchment.svg")
        res = A.run(d, "ink-and-parchment", out=out, host="http://fake.test/", seed=11, size=SIZE, call=srv,
                    sleep=lambda s: None)
        self.assertEqual([c[1].split("?")[0][len("http://fake.test"):] for c in srv.calls],
                         ["/system_stats", "/upload/image", "/prompt", "/history/job1", "/history/job1", "/view"])
        self.assertTrue(res["overlap"]["ok"], res["overlap"]["detail"])
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        full, _ = R.render_svg(d, "ink-and-parchment")
        self.assertEqual(A.layer_of(svg, "labels"), A.layer_of(full, "labels"))
        self.assertIn('<image class="aistyle" href="data:image/png;base64,', svg)
        with open(os.path.join(d, "aistyle-ink-and-parchment.aistyle.json"), encoding="utf-8") as f:
            sc = json.load(f)
        self.assertEqual(sc["tool_version"], mpw.VERSION)
        self.assertEqual((sc["look"], sc["seed"], sc["steps"], sc["denoise"]), ("ink-and-parchment", 11, 9, 0.45))
        self.assertEqual(sc["prompt"], A.LOOKS["ink-and-parchment"]["prompt"])
        self.assertEqual(sc["model"]["unet"], "z_image_turbo_bf16.safetensors")
        self.assertEqual(sc["model"]["licence_class"], "ok-commercial")
        self.assertEqual(sc["workflow"]["sha256"], A.workflow_hash(srv.prompts["job1"]["wf"]))
        self.assertEqual(sc["server"], {"comfyui": "9.9.9"})
        self.assertNotIn("fake.test", json.dumps(sc))            # the server address stays out of the sidecar
        for k in ("land_iou", "coast_within_3px", "river_on_land", "towns_on_land", "river_line", "lakes_kept"):
            self.assertIsNotNone(sc["overlap"]["styled"][k], k)
        self.assertEqual(sc["overlap"]["tolerance"]["land_iou"], A.TOL_LAND_IOU)
        with open(os.path.join(d, sc["files"]["styled"]), "rb") as f:
            self.assertEqual(A.sha(f.read()), sc["sha256"]["styled"])
        # the optional check bar: present, passing, and it catches a swapped or drifted picture
        bars = A.bars(d)
        self.assertEqual(len(bars), 1)
        self.assertTrue(bars[0][1], bars[0][2])
        chk = json.loads(run_cli("check", d, "--no-regen", "--no-labels", "--json"))
        self.assertTrue(chk[-1]["name"].startswith("aistyle aistyle-ink-and-parchment"))
        self.assertTrue(chk[-1]["ok"])
        self.assertEqual(chk[-1]["bar"], chk[-2]["bar"] + 1)
        self.assertFalse(any("aistyle" in b["name"] for b in
                             json.loads(run_cli("check", d, "--no-regen", "--no-labels", "--no-aistyle", "--json"))))
        styled = os.path.join(d, sc["files"]["styled"])
        with open(styled, "wb") as f:
            f.write(paint(d, SIZE, SIZE, shift=9))
        self.assertFalse(A.bars(d)[0][1])
        self.assertIn("sha256 differs", A.bars(d)[0][2])
        sc["sha256"]["styled"] = A.sha(A._read(styled))
        with open(os.path.join(d, "aistyle-ink-and-parchment.aistyle.json"), "w", encoding="utf-8") as f:
            json.dump(sc, f)
        ok, detail = A.bars(d)[0][1:]
        self.assertFalse(ok)
        self.assertIn("land IoU", detail)
        with self.assertRaises(SystemExit):
            run_cli("check", d, "--no-regen", "--no-labels")
        os.remove(styled)
        self.assertIsNone(A.bars(d)[0][1])
        self.assertIn("skipped", A.bars(d)[0][2])

    def test_no_sidecar_no_bar(self):
        self.assertEqual(A.bars(self.world), [])
        names = [b["name"] for b in json.loads(run_cli("check", self.world, "--no-regen", "--no-labels", "--json"))]
        self.assertFalse(any("aistyle" in n for n in names))

    def test_drifted_result_fails_the_cli(self):
        d = self.fresh_world("drift")
        srv = FakeServer(styled=lambda png: paint(d, SIZE, SIZE, shift=9))
        real = A.http
        A.http = srv
        try:
            buf = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stdout(buf):
                mpw.main(["aistyle", d, "--look", "satellite", "--host", "http://fake.test", "--size", str(SIZE),
                          "-o", os.path.join(d, "s.svg"), "--timeout", "5"])
        finally:
            A.http = real
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("FAIL: land IoU", buf.getvalue())
        self.assertTrue(os.path.isfile(os.path.join(d, "s.aistyle.json")))

    def test_host_comes_from_flag_or_environment(self):
        self.assertEqual(A.resolve_host("http://a.test:1/", {}), "http://a.test:1")
        self.assertEqual(A.resolve_host(None, {A.ENV_HOST: "https://b.test"}), "https://b.test")
        self.assertEqual(A.ENV_HOST, "MAPWRIGHT_COMFYUI")
        with self.assertRaises(ValueError) as cm:
            A.resolve_host(None, {})
        self.assertIn("MAPWRIGHT_COMFYUI", str(cm.exception))
        with self.assertRaises(ValueError):
            A.resolve_host("fake.test:8188", {})
        with self.assertRaises(ValueError):
            A.run(self.world, "satellite", out=self.out("nohost.svg"), size=SIZE, env={})
        self.assertFalse(os.path.exists(self.out("nohost.control.png")))    # failed before any work

    def test_server_errors_are_plain(self):
        d = self.world
        for fail, text in (("queue", "server answered 400"), ("run", "out of memory")):
            with self.assertRaises(RuntimeError) as cm:
                A.run(d, "satellite", out=self.out("e-%s.svg" % fail), host="http://fake.test", size=SIZE,
                      call=FakeServer(fail=fail), sleep=lambda s: None)
            self.assertIn(text, str(cm.exception))
        ticks = iter(range(0, 1000, 3))
        c = A.Comfy("http://fake.test", FakeServer(fail="never"))
        pid = c.queue({"1": {}})
        with self.assertRaises(RuntimeError) as cm:
            c.wait(pid, timeout=10, sleep=lambda s: None, clock=lambda: next(ticks))
        self.assertIn("no result after 10 s", str(cm.exception))
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            run_cli("aistyle", d, "--look", "nope", "--dry-run")
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            run_cli("aistyle", d)
        city = self.out("city")
        run_cli("gen", "city", "--seed", "1", "--out", city)
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            run_cli("aistyle", city, "--look", "satellite", "--dry-run")

    def test_measure_cli(self):
        p = self.out("flat.png")
        with open(p, "wb") as f:
            f.write(paint(self.world, SIZE, SIZE))
        j = json.loads(run_cli("aistyle", self.world, "--measure", p, "--json"))
        self.assertTrue(j["ok"])
        self.assertGreaterEqual(j["overlap"]["land_iou"], 0.99)


class TestControlNet(Base):
    def test_canny_hint_is_the_coast(self):
        tr = A.truth(self.world, SIZE, SIZE)
        png = A.hint_png(self.world, "canny", SIZE, SIZE, tr)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        rows = A.canny_rows(tr["land"], SIZE, SIZE)
        edge = A._dilate(A._edge(tr["land"], SIZE), SIZE, 1)
        white = sum(1 for r in rows for v in r if v == 255)
        self.assertGreater(white, 0)
        self.assertEqual(white, A._pc(edge))
        self.assertTrue(all(v in (0, 255) for r in rows for v in r))

    def test_depth_hint_sea_black_land_grey(self):
        tr = A.truth(self.world, SIZE, SIZE)
        rows = A.depth_rows(self.world, SIZE, SIZE)
        self.assertEqual((len(rows), len(rows[0])), (SIZE, SIZE))
        land = sea = 0
        for y, r in enumerate(rows):
            for x, v in enumerate(r):
                if A._get(tr["land"], SIZE, x, y):
                    land += v >= 96
                else:
                    sea += v == 0
        n_land = A._pc(tr["land"])
        self.assertEqual(land, n_land)
        self.assertEqual(sea, SIZE * SIZE - n_land)

    def test_default_is_unchanged_and_flags_are_checked(self):
        d = self.fresh_world("cnet-dry")
        p = A.plan(d, "painted-atlas", size=SIZE)
        self.assertEqual(p["control"], "none")
        self.assertNotIn("hint", p["files"])
        wf = A.build_workflow(p, "x.png")
        self.assertEqual(sorted(wf, key=int), [str(i) for i in range(1, 11)])
        self.assertEqual(wf["8"]["inputs"]["model"], ["1", 0])
        with self.assertRaises(ValueError):
            A.plan(d, "painted-atlas", size=SIZE, strength=0.6)
        with self.assertRaises(ValueError):
            A.plan(d, "painted-atlas", size=SIZE, control="sketch")
        j = json.loads(run_cli("aistyle", d, "--look", "painted-atlas", "--dry-run", "--control", "depth",
                               "--strength", "0.6", "--denoise", "0.75", "--size", str(SIZE), "--json"))
        self.assertEqual((j["controlnet"], j["strength"]), ("depth", 0.6))
        self.assertNotIn("warning", j)
        self.assertTrue(os.path.isfile(j["hint"]))
        with open(j["workflow"], encoding="utf-8") as f:
            wf = json.load(f)
        self.assertEqual(wf["8"]["inputs"]["model"], ["13", 0])
        self.assertEqual(wf["13"]["class_type"], "ZImageFunControlnet")
        self.assertEqual(wf["13"]["inputs"]["strength"], 0.6)
        self.assertTrue(wf["12"]["inputs"]["image"].startswith("mapwright-aistyle-hint-"))
        self.assertEqual(wf["11"]["inputs"]["name"], A.load_template(A.CNET_TEMPLATE)["model"]["patch"])

    def test_full_pass_with_canny_uploads_the_hint(self):
        d = self.fresh_world("cnet-full")
        srv = FakeServer()
        out = os.path.join(d, "c.png")
        res = A.run(d, "watercolour", out=out, host="http://fake.test", seed=3, size=SIZE, call=srv,
                    sleep=lambda s: None, control="canny", denoise=0.75)
        self.assertEqual(len(srv.uploads), 2)
        wf = srv.prompts["job1"]["wf"]
        self.assertIn(wf["12"]["inputs"]["image"], srv.uploads)
        self.assertEqual(srv.uploads[wf["12"]["inputs"]["image"]], A._read(res["hint"]))
        self.assertEqual(wf["13"]["inputs"]["strength"], A.DEFAULT_CNET_STRENGTH)
        with open(res["sidecar"], encoding="utf-8") as f:
            sc = json.load(f)
        self.assertEqual(sc["controlnet"]["kind"], "canny")
        self.assertEqual(sc["files"]["hint"], "c.hint.png")
        self.assertTrue(res["overlap"]["ok"], res["overlap"]["detail"])


class TestDoctor(Base):
    def test_unset_is_not_probed(self):
        def boom(*a, **k):
            raise AssertionError("doctor contacted a server with no host set")
        r = A.doctor(None, call=boom, env={})
        self.assertIsNone(r["host"])
        self.assertIn("MAPWRIGHT_COMFYUI", r["note"])

    def test_reports_server_and_model(self):
        r = A.doctor("http://fake.test", call=FakeServer())
        self.assertTrue(r["answers"])
        self.assertEqual(r["comfyui"], "9.9.9")
        self.assertEqual(r["files"], {"clip": True, "unet": True, "vae": True})
        r = A.doctor("http://fake.test", call=FakeServer(models={"UNETLoader": ["other.safetensors"],
                                                                 "CLIPLoader": ["qwen_3_4b.safetensors"],
                                                                 "VAELoader": ["ae.safetensors"]}))
        self.assertFalse(r["files"]["unet"])

        def dead(*a, **k):
            raise OSError("refused")
        r = A.doctor("http://fake.test", call=dead)
        self.assertFalse(r["answers"])
        real = A.http
        A.http = FakeServer(models={"UNETLoader": [], "CLIPLoader": ["qwen_3_4b.safetensors"], "VAELoader": ["ae.safetensors"]})
        try:
            out = run_cli("doctor", "--host", "http://fake.test")
            self.assertIn("MISSING on the server: unet", out)
            A.http = FakeServer()
            self.assertIn("ComfyUI 9.9.9 answers; model z_image_turbo_bf16.safetensors present",
                          run_cli("doctor", "--host", "http://fake.test"))
            self.assertIn("aistyle", json.loads(run_cli("doctor", "--host", "http://fake.test", "--json")))
        finally:
            A.http = real


class TestPublicFiles(unittest.TestCase):
    def test_no_private_hosts_or_optional_imports(self):
        import re
        lan = re.compile(r"\b(192\.168|10\.\d+|172\.(1[6-9]|2\d|3[01]))\.\d+\.\d+\b")
        for folder in ("scripts", "skills", "references"):
            for base, _, files in os.walk(os.path.join(ROOT, folder)):
                for n in files:
                    if not n.endswith((".py", ".md", ".json")):
                        continue
                    with open(os.path.join(base, n), encoding="utf-8") as f:
                        src = f.read()
                    self.assertIsNone(lan.search(src), n)
        for n in ("README.md", "TESTS.md", "CHANGELOG.md", "LEARNINGS.md"):
            with open(os.path.join(ROOT, n), encoding="utf-8") as f:
                self.assertIsNone(lan.search(f.read()), n)
        with open(os.path.join(ROOT, "scripts", "mpw_aistyle.py"), encoding="utf-8") as f:
            src = f.read()
        for mod in ("numpy", "PIL", "requests"):
            self.assertNotIn("import " + mod, src)


@unittest.skipUnless(os.environ.get("MAPWRIGHT_LIVE") == "1" and os.environ.get("MAPWRIGHT_COMFYUI")
                     and mpw.find_browser(), "live: set MAPWRIGHT_LIVE=1 and MAPWRIGHT_COMFYUI, needs Chrome or Edge")
class TestLive(unittest.TestCase):
    def test_one_real_pass_holds_the_coast(self):
        tmp = tempfile.mkdtemp(prefix="mpw-aistyle-live-")
        try:
            world = os.path.join(tmp, "w")
            G.gen_world(7, 16000, world)
            res = A.run(world, "painted-atlas", seed=1, denoise=0.45)
            self.assertTrue(res["overlap"]["ok"], res["overlap"]["detail"])
            self.assertTrue(os.path.isfile(res["out"]))
            self.assertEqual(len(A.bars(world)), 1)
            self.assertTrue(A.bars(world)[0][1])
            res = A.run(world, "watercolour", seed=1, denoise=0.75, control="canny",
                        out=os.path.join(world, "cnet.png"))
            self.assertTrue(res["overlap"]["ok"], res["overlap"]["detail"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
