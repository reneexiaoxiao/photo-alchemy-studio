"""Security, pinning and transactional importer tests; no network access."""
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SPEC = importlib.util.spec_from_file_location("studio_server", Path(__file__).resolve().parents[1] / "scripts" / "studio_server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)

MIT = b'''MIT License

Copyright (c) 2026 Test Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
SKILL_PATH = "styles/watercolor/SKILL.md"
SKILL = b'''---
name: watercolor-test
description: A self-contained watercolor prompt.
---
# Watercolor test

Read [the prompt](references/prompt.md), then describe the image.
'''
PIN_A = "a" * 40
PIN_B = "b" * 40


class FakeGitHub:
    def __init__(self):
        self.commit = PIN_A
        self.files = {"LICENSE": MIT, "NOTICE": b"Test authors retain attribution.\n", SKILL_PATH: SKILL, "styles/watercolor/references/prompt.md": b"Use a soft wash and a simple shape.\n"}
        self.license = "MIT"
        self.modes = {}
        self.missing_license = False
        self.calls = []
        self.truncated = False
        self.bad_blob = False

    def api(self, endpoint):
        self.calls.append(endpoint)
        if endpoint == "repos/demo/watercolor":
            return {"full_name": "demo/watercolor", "default_branch": "main", "description": "Test repository"}
        if endpoint == "repos/demo/watercolor/commits/main":
            return {"sha": self.commit}
        if endpoint.startswith("repos/demo/watercolor/git/trees/"):
            return {"truncated": self.truncated, "tree": [{"path": path, "type": "blob", "mode": self.modes.get(path, "100644"), "size": len(data), "sha": server.git_blob_sha(data)} for path, data in self.files.items()]}
        if endpoint.startswith("repos/demo/watercolor/license?"):
            if self.missing_license:
                raise server.ImportErrorSafe("Unavailable", 502)
            data = self.files.get("LICENSE", MIT)
            return {"path": "LICENSE", "sha": server.git_blob_sha(data), "license": {"spdx_id": self.license}, "encoding": "base64", "content": base64.b64encode(data).decode()}
        if "/git/blobs/" in endpoint:
            sha = endpoint.rsplit("/", 1)[-1]
            for data in self.files.values():
                if server.git_blob_sha(data) == sha:
                    return {"encoding": "base64", "content": base64.b64encode(b"changed" if self.bad_blob else data).decode()}
        if endpoint.startswith("search/repositories?"):
            return {"items": [{"full_name": f"demo/style-{i}", "description": f"Style {i}"} for i in range(10)]}
        if endpoint.startswith("search/code?"):
            return {"items": []}
        raise AssertionError("Unexpected read-only API endpoint: " + endpoint)


class ImporterTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.github = FakeGitHub()
        self.studio = server.Studio(self.root, self.github)

    def tearDown(self):
        self.temporary.cleanup()

    def inspect(self):
        return self.studio.inspect("demo/watercolor")

    def install(self, commit=PIN_A):
        return self.studio.install("demo/watercolor", commit, SKILL_PATH)

    def test_repo_url_validation(self):
        self.assertEqual(server.safe_repo("https://github.com/demo/watercolor.git"), "demo/watercolor")
        self.assertEqual(server.safe_repo("demo/watercolor"), "demo/watercolor")
        for value in ["http://github.com/a/b", "https://github.com.evil.test/a/b", "https://user:secret@github.com/a/b", "https://github.com:443/a/b", "https://github.com/a/b/tree/main", "https://github.com/a/b?x=1", "a/..", "-a/b", "a/b;id", "a/b%2f..", "file:///tmp/a", "$(touch /tmp/unsafe)"]:
            with self.subTest(value=value), self.assertRaises(server.ImportErrorSafe):
                server.safe_repo(value)

    def test_source_path_traversal_validation(self):
        for value in ["../SKILL.md", "a/../../b", "/tmp/SKILL.md", "C:/SKILL.md", "a\\b", "a/%2e%2e/SKILL.md", ".git/config", "a/.GIT/config", "a//b", "a/./b", "a/\0b", ".local/catalog.json"]:
            with self.subTest(value=value), self.assertRaises(server.ImportErrorSafe):
                server.safe_path(value)
        self.assertEqual(server.safe_path("水彩/refs/prompt.md"), "水彩/refs/prompt.md")

    def test_search_limit_and_repository_url(self):
        self.assertEqual(len(self.studio.search("watercolor")["candidates"]), 6)
        direct = self.studio.search("https://github.com/demo/watercolor")["candidates"]
        self.assertEqual(direct[0]["repo"], "demo/watercolor")
        self.assertTrue(all("token" not in json.dumps(item).lower() for item in direct))

    def test_missing_or_restricted_license_is_not_installable(self):
        self.github.missing_license = True
        self.assertFalse(self.inspect()["installable"])
        self.github.missing_license = False
        for license_id in ["NOASSERTION", "GPL-3.0", "CC-BY-NC-4.0", None]:
            self.github.license = license_id
            self.assertFalse(self.inspect()["installable"])
        self.github.license = "MIT"
        self.github.files.pop("LICENSE")
        self.assertFalse(self.inspect()["installable"])

    def test_modified_mit_or_fake_short_license_is_rejected(self):
        self.github.files["LICENSE"] = MIT + b"Commercial use requires written permission.\n"
        self.assertFalse(self.inspect()["installable"])
        self.github.files["LICENSE"] = b"MIT License"
        self.assertFalse(self.inspect()["installable"])
        self.github.files["LICENSE"] = b"You may only use this with written approval.\n" + MIT
        self.assertFalse(self.inspect()["installable"])

    def test_different_nested_license_is_rejected(self):
        self.github.files["styles/watercolor/LICENSE"] = b"All rights reserved."
        result = self.inspect()
        self.assertFalse(result["installable"])
        self.assertIn("独立许可证", result["skills"][0]["reason"])

    def test_tree_traversal_and_case_collision_are_rejected(self):
        self.github.files["../escape.md"] = b"no"
        with self.assertRaises(server.ImportErrorSafe):
            self.inspect()
        self.github.files.pop("../escape.md")
        self.github.files["styles/watercolor/skill.md"] = b"conflict"
        with self.assertRaises(server.ImportErrorSafe):
            self.inspect()

    def test_symlinks_and_modules_are_rejected(self):
        self.github.files["styles/watercolor/external"] = b"/etc/passwd"
        for mode in ["120000", "160000"]:
            self.github.modes["styles/watercolor/external"] = mode
            result = self.inspect()
            self.assertFalse(result["installable"])
            self.assertIn("符号链接", result["skills"][0]["reason"])

    def test_cross_module_and_missing_references_are_rejected(self):
        for reference in ["../shared/prompt.md", "missing.md", "/etc/passwd", "file:///tmp/prompt.md"]:
            self.github.files[SKILL_PATH] = SKILL + f"\n[extra]({reference})\n".encode()
            self.assertFalse(self.inspect()["installable"], reference)
        self.github.files[SKILL_PATH] = SKILL + b"\nRead `references/missing.md` first.\n"
        self.assertFalse(self.inspect()["installable"])

    def test_fenced_output_image_template_is_not_a_missing_input(self):
        self.github.files[SKILL_PATH] = SKILL + b"\nExample final response:\n```markdown\n![art](absolute-image-path-or-rendered-image)\n```\n"
        self.assertTrue(self.inspect()["installable"])
        self.assertTrue(self.install()["installed"])

    def test_explicit_only_source_policy_survives_install(self):
        self.github.files["styles/watercolor/agents/openai.yaml"] = b"policy:\n  allow_implicit_invocation: false\n"
        self.assertTrue(self.inspect()["installable"])
        self.assertTrue(self.install()["style"]["manualOnly"])

    def test_unreferenced_readme_install_instructions_are_not_runtime_dependencies(self):
        readme = "styles/watercolor/README.md"
        self.github.files[readme] = b"# Installation\n```sh\ngit clone https://github.com/demo/watercolor\n```\n"
        self.assertTrue(self.inspect()["installable"])
        self.github.files[SKILL_PATH] = SKILL + b"\nRead [the required runtime](README.md) before use.\n"
        self.assertFalse(self.inspect()["installable"])

    def test_runtime_dependencies_are_rejected(self):
        self.github.files["styles/watercolor/scripts/run.py"] = b"print('never execute')"
        self.assertFalse(self.inspect()["installable"])
        self.github.files.pop("styles/watercolor/scripts/run.py")
        self.github.files[SKILL_PATH] = SKILL + b"\nRun `npm install dangerous-package` first.\n"
        self.assertFalse(self.inspect()["installable"])

    def test_pin_requires_inspection_and_exact_path(self):
        with self.assertRaises(server.ImportErrorSafe):
            self.install()
        self.inspect()
        for commit, path in [("main", SKILL_PATH), (PIN_B, SKILL_PATH), (PIN_A, "SKILL.md"), (PIN_A, "../SKILL.md")]:
            with self.subTest(commit=commit, path=path), self.assertRaises(server.ImportErrorSafe):
                self.studio.install("demo/watercolor", commit, path)
        self.studio.cache[("demo/watercolor", PIN_A)]["at"] = time.monotonic() - server.CACHE_TTL - 1
        with self.assertRaises(server.ImportErrorSafe):
            self.install()

    def test_blob_hash_verification(self):
        self.github.bad_blob = True
        with self.assertRaisesRegex(server.ImportErrorSafe, "固定版本"):
            self.inspect()

    def test_install_readback_and_deduplication(self):
        result = self.inspect()
        self.assertTrue(result["installable"])
        installed = self.install()
        entry = Path(installed["style"]["entry"])
        self.assertEqual(entry.read_bytes(), SKILL)
        extension = entry.parents[2]
        self.assertEqual((extension / "LICENSE").read_bytes(), MIT)
        self.assertEqual((extension / "NOTICE").read_bytes(), self.github.files["NOTICE"])
        self.assertEqual((entry.parent / "references" / "prompt.md").read_bytes(), self.github.files["styles/watercolor/references/prompt.md"])
        self.assertEqual(self.studio.status()["installedCount"], 1)
        self.assertTrue(self.install()["alreadyInstalled"])
        self.assertEqual(len(self.studio.catalog()["styles"]), 1)
        self.assertFalse((self.root / ".local" / "history").exists())
        self.assertEqual(entry.stat().st_mode & 0o111, 0)

    def test_install_copies_inspected_bytes_without_further_network(self):
        self.inspect()
        calls = len(self.github.calls)
        self.github.files[SKILL_PATH] = b"Modified after inspection"
        installed = self.install()
        self.assertEqual(Path(installed["style"]["entry"]).read_bytes(), SKILL)
        self.assertEqual(len(self.github.calls), calls)

    def test_upgrade_retains_recoverable_previous_version_and_stable_identity(self):
        self.inspect()
        first = self.install()
        self.github.commit = PIN_B
        changed = SKILL.replace(b"watercolor-test", b"watercolor-new-name")
        self.github.files[SKILL_PATH] = changed
        self.inspect()
        upgraded = self.install(PIN_B)
        self.assertEqual(upgraded["style"]["id"], first["style"]["id"])
        self.assertEqual(Path(upgraded["style"]["entry"]).read_bytes(), changed)
        backup = Path(upgraded["historyPath"])
        self.assertEqual((backup / "extension" / SKILL_PATH).read_bytes(), SKILL)
        self.assertEqual(json.loads((backup / "style.json").read_text())["commit"], PIN_A)
        self.assertEqual(len(self.studio.catalog()["styles"]), 1)

    def test_failed_catalog_write_rolls_back_directory_and_catalog(self):
        self.inspect()
        first = self.install()
        catalog_before = (self.root / ".local" / "catalog.json").read_bytes()
        self.github.commit = PIN_B
        self.github.files[SKILL_PATH] = SKILL + b"\nA new paragraph.\n"
        self.inspect()
        with patch.object(self.studio, "_write_catalog", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.install(PIN_B)
        self.assertEqual(Path(first["style"]["entry"]).read_bytes(), SKILL)
        self.assertEqual((self.root / ".local" / "catalog.json").read_bytes(), catalog_before)
        self.assertEqual(list((self.root / ".local" / "staging").iterdir()), [])

    def test_first_install_failure_does_not_leave_catalog_or_extension(self):
        self.inspect()
        with patch.object(self.studio, "_write_catalog", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(self.studio.catalog(), {"styles": []})
        self.assertEqual(list((self.root / ".local" / "extensions").iterdir()), [])

    def test_symlinked_local_storage_is_not_written(self):
        self.inspect()
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".local").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(server.ImportErrorSafe, "符号链接"):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_updates_are_read_only_and_do_not_change_pin(self):
        self.inspect()
        self.install()
        before = (self.root / ".local" / "catalog.json").read_bytes()
        self.github.commit = PIN_B
        result = self.studio.check_updates()
        self.assertTrue(result["updates"][0]["updateAvailable"])
        self.assertFalse(result["automaticInstall"])
        self.assertEqual((self.root / ".local" / "catalog.json").read_bytes(), before)
        self.assertEqual(self.studio.catalog()["styles"][0]["commit"], PIN_A)

    def test_legacy_catalog_readonly_and_excluded_from_updates(self):
        self.studio._mkdir(self.studio.local)
        legacy = {"styles": [{"id": "legacy-watercolor", "label": "Existing watercolor", "entry": "/existing/skills/watercolor/SKILL.md", "source": "legacy/restricted", "license": "restricted", "installed": True}]}
        path = self.root / ".local" / "legacy-catalog.json"
        path.write_text(json.dumps(legacy), encoding="utf-8")
        before = path.read_bytes()
        self.assertEqual(self.studio.catalog(), legacy)
        self.assertEqual(self.studio.status()["installedCount"], 1)
        self.assertEqual(self.studio.check_updates(), {"updates": [], "automaticInstall": False})
        self.assertEqual(self.github.calls, [])
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / ".local" / "catalog.json").exists())

    def test_imported_catalog_wins_over_legacy_id(self):
        self.inspect()
        installed = self.install()["style"]
        legacy = {"styles": [{"id": installed["id"], "label": "Old duplicate", "entry": "/old/SKILL.md"}, {"id": "legacy-only", "label": "Existing style", "entry": "/existing/SKILL.md"}]}
        path = self.root / ".local" / "legacy-catalog.json"
        path.write_text(json.dumps(legacy), encoding="utf-8")
        before = path.read_bytes()
        catalog = self.studio.catalog()["styles"]
        self.assertEqual(len(catalog), 2)
        self.assertEqual(next(item for item in catalog if item["id"] == installed["id"]), installed)
        self.assertEqual(self.studio.status()["installedCount"], 2)
        self.assertEqual(len(self.studio.check_updates()["updates"]), 1)
        self.assertEqual(path.read_bytes(), before)

    def test_install_reuses_exact_canonical_or_legacy_identity_without_writing_indexes(self):
        canonical = [{"id": "watercolor-builtin", "label": "原有水彩", "source": "DEMO/Watercolor", "sourcePath": SKILL_PATH}]
        root_index = self.root / "catalog.json"
        root_index.write_text(json.dumps(canonical), encoding="utf-8")
        self.studio._mkdir(self.studio.local)
        legacy_index = self.root / ".local" / "legacy-catalog.json"
        legacy_index.write_text(json.dumps({"styles": canonical}), encoding="utf-8")
        before = (root_index.read_bytes(), legacy_index.read_bytes())
        self.inspect()
        installed = self.install()
        self.assertEqual(installed["style"]["id"], "watercolor-builtin")
        self.assertEqual(installed["style"]["label"], "原有水彩")
        self.assertFalse(installed["alreadyInstalled"])
        self.assertEqual(Path(installed["style"]["entry"]).read_bytes(), SKILL)
        self.assertEqual(len(self.studio.catalog()["styles"]), 1)
        self.assertEqual((root_index.read_bytes(), legacy_index.read_bytes()), before)
        # An installed identity remains authoritative even if the read-only
        # indexes later advertise a different ID for the exact upstream path.
        changed = [{**canonical[0], "id": "another-canonical-id"}]
        root_index.write_text(json.dumps(changed), encoding="utf-8")
        legacy_index.write_text(json.dumps({"styles": changed}), encoding="utf-8")
        self.assertEqual(self.install()["style"]["id"], "watercolor-builtin")


class HTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        (cls.root / "index.html").write_text("<!doctype html><title>Test</title>")
        (cls.root / "assets").mkdir()
        (cls.root / ".local").mkdir()
        (cls.root / ".local" / "secret.txt").write_text("PRIVATE")
        (cls.root / "assets" / "leak.txt").symlink_to(cls.root / ".local" / "secret.txt")
        cls.httpd = server.StudioHTTPServer(("127.0.0.1", 0), server.Studio(cls.root, FakeGitHub()))
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = "http://127.0.0.1:" + str(cls.httpd.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def request(self, path, data=None, headers=None, method=None):
        request = Request(self.origin + path, data=data, headers=headers or {}, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def test_status_and_static_allowlist(self):
        status, body, headers = self.request("/api/status")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["connected"])
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))
        self.assertEqual(self.request("/")[0], 200)
        for path in ["/.local/secret.txt", "/scripts/studio_server.py", "/assets/../.local/secret.txt", "/assets/%2e%2e/.local/secret.txt", "/assets/leak.txt"]:
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertNotEqual(status, 200)
                self.assertNotIn(b"PRIVATE", body)

    def test_host_rebinding_and_cross_origin_writes_rejected(self):
        self.assertEqual(self.request("/api/status", headers={"Host": "attacker.example"})[0], 403)
        payload = b'{"query":"watercolor"}'
        for origin in [None, "null", "https://attacker.example", "http://localhost:" + str(self.httpd.server_address[1])]:
            headers = {"Content-Type": "application/json"}
            if origin:
                headers["Origin"] = origin
            self.assertEqual(self.request("/api/search", payload, headers)[0], 403)
        self.assertEqual(self.request("/api/search", payload, {"Content-Type": "application/json", "Origin": self.origin})[0], 200)

    def test_json_body_limit_and_content_type(self):
        headers = {"Content-Type": "application/json", "Origin": self.origin}
        self.assertEqual(self.request("/api/search", b"x" * (server.MAX_BODY + 1), headers)[0], 413)
        self.assertEqual(self.request("/api/search", b"not json", headers)[0], 400)
        self.assertEqual(self.request("/api/search", b"[]", headers)[0], 400)
        self.assertEqual(self.request("/api/search", b"{}", {"Content-Type": "text/plain", "Origin": self.origin})[0], 415)


if __name__ == "__main__":
    unittest.main(verbosity=2)
