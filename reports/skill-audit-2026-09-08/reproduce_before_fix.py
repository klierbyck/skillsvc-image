"""离线审计复现：只用假密钥、模拟 HTTP 和临时文件，不调用生图服务。

历史证据：这些测试断言的是修复前的缺陷行为，不用于当前回归。
当前修复验证请运行同目录 reproduce.py。
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("audited_generate_image", ROOT / "scripts/generate_image.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=")
FAKE_RESULT = (PNG, "image/png", "https://api.example/v1/images/generations")


def args(*values):
    return g.build_parser().parse_args(list(values))


class AuditReproductions(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.env = patch.dict(os.environ, {"GPT_IMAGE_API_KEY": "audit-fake-key"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.loader = patch.object(g, "load_environment", return_value=[])
        self.loader.start()
        self.addCleanup(self.loader.stop)
        # 防止新增复现意外走真实网络；只有指定测试会覆盖为 HTTP mock。
        self.network = patch.object(g.requests.sessions.Session, "request", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_01_cwd_env_redirects_credentialed_request(self):
        self.loader.stop()
        (self.root / ".env").write_text("IMAGE_API_BASE_URL=http://untrusted.example\n", encoding="utf-8")
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"b64_json": base64.b64encode(PNG).decode()}]}
        with patch.object(Path, "cwd", return_value=self.root), patch.object(g.requests, "post", return_value=response) as post:
            g.run(args("generate", "--prompt", "audit", "--output-dir", str(self.root)))
        self.assertEqual(post.call_args.args[0], "http://untrusted.example/v1/images/generations")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer audit-fake-key")

    def test_02_parallel_manifest_loses_one_completed_asset(self):
        barrier = threading.Barrier(2)
        manifest = self.root / "manifest.json"

        def fake_api(*unused):
            barrier.wait(timeout=10)
            return FAKE_RESULT

        def worker(asset):
            return g.run(args("generate", "--prompt", "audit", "--manifest", str(manifest), "--asset-id", asset, "--output", asset + ".png"))

        with patch.object(g, "call_gpt", side_effect=fake_api), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, ["card-01", "card-02"]))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(Path(result["image"]).exists() for result in results))
        self.assertEqual(len(json.loads(manifest.read_text())["assets"]), 1)

    def test_03_session_path_can_overwrite_new_image(self):
        same = self.root / "result.png"
        with patch.object(g, "call_gpt", return_value=FAKE_RESULT):
            result = g.run(args("generate", "--prompt", "audit", "--output", str(same), "--session", str(same)))
        self.assertEqual(result["image"], result["session"])
        self.assertEqual(json.loads(same.read_text(encoding="utf-8"))["version"], 1)
        self.assertIsNone(g.detected_image_extension(same.read_bytes()))

    def test_04_truncated_png_is_marked_complete(self):
        manifest = self.root / "manifest.json"
        with patch.object(g, "call_gpt", return_value=(PNG[:8], "image/png", "https://api.example")):
            result = g.run(args("generate", "--prompt", "audit", "--manifest", str(manifest), "--asset-id", "broken"))
        self.assertEqual(Path(result["image"]).stat().st_size, 8)
        self.assertEqual(json.loads(manifest.read_text())["assets"]["broken"]["status"], "complete")

    def test_05_manifest_write_failure_advances_session(self):
        manifest = self.root / "manifest.json"
        with patch.object(g, "call_gpt", return_value=FAKE_RESULT):
            first = g.run(args("generate", "--prompt", "original", "--manifest", str(manifest), "--asset-id", "card", "--output", "v1.png"))
        original_manifest = manifest.read_bytes()
        atomic_write = g.write_json_atomic

        def fail_manifest(path, payload):
            if path == manifest:
                raise PermissionError("simulated manifest write failure")
            return atomic_write(path, payload)

        with patch.object(g, "call_gpt", return_value=FAKE_RESULT), patch.object(g, "write_json_atomic", side_effect=fail_manifest):
            with self.assertRaises(PermissionError):
                g.run(args("edit", "--prompt", "change", "--manifest", str(manifest), "--asset-id", "card", "--output", "v2.png"))
        self.assertEqual(manifest.read_bytes(), original_manifest)
        session = json.loads(Path(first["session"]).read_text(encoding="utf-8"))
        self.assertEqual(len(session["turns"]), 2)
        plan = g.run(args("edit", "--prompt", "retry", "--manifest", str(manifest), "--asset-id", "card", "--dry-run"))
        self.assertEqual(Path(plan["source_image"]).name, "v2.png")

    def test_06_moved_bundle_cannot_edit_relative_manifest(self):
        old = self.root / "old"
        new = self.root / "new"
        with patch.object(g, "call_gpt", return_value=FAKE_RESULT):
            g.run(args("generate", "--prompt", "audit", "--manifest", str(old / "manifest.json"), "--asset-id", "card"))
        old.rename(new)
        with self.assertRaisesRegex(ValueError, "edit 需要"):
            g.run(args("edit", "--prompt", "audit", "--manifest", str(new / "manifest.json"), "--asset-id", "card", "--dry-run"))

    def test_07_invalid_session_field_raises_unhandled_type_error(self):
        session = self.root / "session.json"
        session.write_text(json.dumps({"version": 1, "parameters": None}), encoding="utf-8")
        with self.assertRaises(AttributeError):
            g.run(args("edit", "--prompt", "audit", "--session", str(session), "--dry-run"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
