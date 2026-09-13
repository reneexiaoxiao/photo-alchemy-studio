#!/usr/bin/env python3
"""Loopback-only, standard-library community skill importer.

Remote documents are untrusted data. This program never executes them.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import errno
import hashlib
import importlib.util
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlencode, urlsplit
import uuid
import webbrowser

VERSION = "1.0.0"
MAX_BODY = 16_384
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 12 * 1024 * 1024
MAX_FILES = 120
MAX_PREVIEW = 12 * 1024 * 1024
PREVIEW_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,150}\.(?:png|jpe?g|webp|gif)$", re.I)
CACHE_TTL = 30 * 60
ALLOWED_LICENSES = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "0BSD", "Unlicense"}
SHA = re.compile(r"^[0-9a-f]{40}$")
LICENSE_NAME = re.compile(r"^(?:licen[sc]e|copying)(?:[._-].*)?$", re.I)
NOTICE_NAME = re.compile(r"^(?:notice|copyright|authors)(?:[._-].*)?$", re.I)
CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".exe", ".dll", ".so", ".dylib", ".wasm", ".jar", ".rb", ".pl", ".ps1", ".bat", ".cmd"}
MANIFEST_NAMES = {"package.json", "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Cargo.toml", "Gemfile", "go.mod", "Makefile", ".gitmodules"}


class ImportErrorSafe(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def safe_repo(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 300:
        raise ImportErrorSafe("请填写 owner/repo 或 GitHub 仓库网址。")
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlsplit(value)
        if parsed.netloc != "github.com" or parsed.query or parsed.fragment:
            raise ImportErrorSafe("仅接受 https://github.com/owner/repo 仓库网址。")
        value = parsed.path.strip("/")
    if value.endswith(".git"):
        value = value[:-4]
    parts = value.split("/")
    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", parts[0]) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", parts[1]) or parts[1] in {".", ".."}:
        raise ImportErrorSafe("仓库地址无效；请使用仓库首页网址，不含分支、文件路径或登录信息。")
    return "/".join(parts)


def safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 500:
        raise ImportErrorSafe("源文件路径无效。")
    if value.startswith("/") or "\\" in value or ":" in value or "%" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ImportErrorSafe("源文件路径不安全。")
    parts = value.split("/")
    if any(p in {"", ".", ".."} or p.casefold() in {".git", ".local"} for p in parts):
        raise ImportErrorSafe("源文件路径不能包含目录跳转或保留目录。")
    return value


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def image_mime(header: bytes) -> str | None:
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24 and header[12:16] == b"IHDR":
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")) and len(header) >= 10:
        return "image/gif"
    if len(header) >= 16 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def source_preview(entry: str, files: dict[str, bytes]) -> tuple[str, bytes] | None:
    """Select an actual raster referenced in the pinned skill or its README."""
    folder = PurePosixPath(entry).parent
    documents = [entry] + sorted(p for p in files if PurePosixPath(p).parent == folder and PurePosixPath(p).name.lower() in {"readme.md", "readme.markdown"})
    for document in documents:
        text = files[document].decode("utf-8", errors="replace")
        text = re.sub(r"(?ms)^\s*(```|~~~).*?^\s*\1\s*$", "", text)
        candidates = re.findall(r"!\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)", text)
        candidates += re.findall(r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", text, re.I)
        for raw in candidates[:12]:
            target = unquote(raw.strip("<>"))
            try:
                parsed = urlsplit(target)
            except ValueError:
                continue
            if parsed.scheme or parsed.netloc or parsed.query or target.startswith("/") or "\\" in target:
                continue
            parts = list(PurePosixPath(document).parent.parts)
            for part in parsed.path.split("/"):
                if part in {"", "."}:
                    continue
                if part == "..":
                    if not parts:
                        break
                    parts.pop()
                else:
                    parts.append(part)
            else:
                path = "/".join(parts)
                data = files.get(path)
                if data and PREVIEW_NAME.fullmatch(PurePosixPath(path).name) and not re.search(r"logo|badge|icon|avatar|favicon|qrcode|sponsor|alipay|wechat", PurePosixPath(path).name, re.I) and image_mime(data[:32]):
                    return path, data
    return None


def decode_blob(payload: dict, expected_sha: str) -> bytes:
    if payload.get("encoding") != "base64" or not SHA.fullmatch(expected_sha):
        raise ImportErrorSafe("GitHub 文件格式或固定版本无效。", 502)
    raw = payload.get("content", "")
    if not isinstance(raw, str) or len(raw) > MAX_FILE * 2:
        raise ImportErrorSafe("源文件超过本地导入大小限制。")
    try:
        data = base64.b64decode("".join(raw.split()), validate=True)
    except (ValueError, TypeError):
        raise ImportErrorSafe("GitHub 文件编码校验失败。", 502) from None
    if len(data) > MAX_FILE or git_blob_sha(data) != expected_sha:
        raise ImportErrorSafe("GitHub 文件内容与固定版本不一致。", 502)
    return data


class GitHub:
    """Use gh's credential storage, never copy or print a token."""
    def api(self, endpoint: str) -> dict:
        try:
            result = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint],
                capture_output=True, timeout=35, check=False,
            )
        except FileNotFoundError:
            raise ImportErrorSafe("未找到 gh CLI。请先安装 GitHub CLI 并运行 gh auth login。", 503) from None
        except subprocess.TimeoutExpired:
            raise ImportErrorSafe("GitHub 请求超时，请稍后重试。", 504) from None
        if result.returncode:
            # gh stderr may include private details; it is intentionally discarded.
            raise ImportErrorSafe("GitHub 读取失败。请检查 gh 登录、仓库访问权限或 API 额度。", 502)
        if len(result.stdout) > 24 * 1024 * 1024:
            raise ImportErrorSafe("GitHub 响应超过安全大小限制。", 502)
        try:
            payload = json.loads(result.stdout)
        except (ValueError, UnicodeError):
            raise ImportErrorSafe("GitHub 返回了无法解析的结果。", 502) from None
        if not isinstance(payload, dict):
            raise ImportErrorSafe("GitHub 返回了意外的数据格式。", 502)
        return payload


def skill_metadata(content: bytes, fallback: str) -> tuple[str, str]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeError:
        raise ImportErrorSafe("SKILL.md 必须使用 UTF-8 编码。") from None
    if "\0" in text or len(text) > 250_000:
        raise ImportErrorSafe("SKILL.md 内容格式不受支持。")
    name, description = fallback, ""
    front = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.S)
    if front:
        body = front.group(1)
        for key in ("name", "description"):
            match = re.search(r"^" + key + r":\s*(.*)$", body, re.M)
            if match:
                value = match.group(1).strip().strip("\"'")
                if value in {"|", ">", "|-", ">-"}:
                    following = body[match.end():]
                    value = " ".join(line.strip() for line in re.split(r"\n(?=\S)", following, maxsplit=1)[0].splitlines() if line.strip())
                if key == "name" and value:
                    name = value[:120]
                if key == "description":
                    description = value[:800]
    if not description:
        prose = text[front.end():] if front else text
        lines = [line.strip() for line in prose.splitlines() if line.strip() and not line.lstrip().startswith(("#", "```", "---"))]
        description = " ".join(lines[:2])[:800]
    return name, description or "社区技能文档；请先阅读原始内容。"


def license_text_ok(spdx: str, data: bytes) -> bool:
    """Require the actual standard grant and disclaimer, beyond the API label."""
    try:
        text = " ".join(data.decode("utf-8-sig").lower().split())
    except UnicodeError:
        return False
    required = {
        "MIT": ["permission is hereby granted, free of charge", "the above copyright notice and this permission notice", 'the software is provided "as is"', "other dealings in the software"],
        "BSD-2-Clause": ["redistribution and use in source and binary forms", "redistributions of source code must retain", "redistributions in binary form must reproduce", 'this software is provided by', "even if advised of the possibility of such damage"],
        "BSD-3-Clause": ["redistribution and use in source and binary forms", "redistributions of source code must retain", "redistributions in binary form must reproduce", "neither the name", "even if advised of the possibility of such damage"],
        "Apache-2.0": ["apache license", "version 2.0, january 2004", "grant of patent license", "redistribution", "limitation of liability", "end of terms and conditions"],
        "ISC": ["permission to use, copy, modify, and/or distribute", "this permission notice appear in all copies", 'the software is provided "as is"', "resulting from loss of use, data or profits"],
        "0BSD": ["permission to use, copy, modify, and/or distribute", "for any purpose with or without fee is hereby granted", 'the software is provided "as is"', "resulting from loss of use, data or profits"],
        "Unlicense": ["this is free and unencumbered software released into the public domain", "anyone is free to copy, modify, publish, use, compile, sell, or", 'the software is provided "as is"', "for more information, please refer to"],
    }
    if spdx not in required or len(text) < 300 or not all(s in text for s in required[spdx]):
        return False
    if re.search(r"non[- ]commercial|research[- ]only|all rights reserved except|no commercial use|commercial use requires|additional (?:license )?terms|licensing fee|禁止商用|仅供学习|不得商用", text):
        return False
    # MIT is the common simple-document path: compare its complete grant so a
    # modified license with an added condition is not accepted as standard MIT.
    if spdx == "MIT":
        start = text.find("permission is hereby granted, free of charge")
        prefix = re.split(r"permission is hereby granted, free of charge", data.decode("utf-8-sig"), maxsplit=1, flags=re.I)[0]
        for line in prefix.splitlines():
            line = line.strip().lstrip("# ")
            if line and not re.fullmatch(r"(?:the )?mit license(?: \(mit\))?|copyright\b.*|\(c\).*|spdx-license-identifier:\s*mit", line, re.I):
                return False
        expected = 'permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "software"), to deal in the software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, and to permit persons to whom the software is furnished to do so, subject to the following conditions: the above copyright notice and this permission notice shall be included in all copies or substantial portions of the software. the software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. in no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.'
        if text[start:] != expected:
            return False
    return True


def dependency_problem(entry: str, files: dict[str, bytes], license_path: str, spdx: str) -> str | None:
    parent = str(PurePosixPath(entry).parent)
    prefix = "" if parent == "." else parent + "/"
    available = set(files)
    # Only the entry and its referenced documents define runtime requirements.
    # Repository README installation instructions are not a skill dependency.
    instruction_paths = {entry}
    pending = [entry]
    while pending:
        current = pending.pop()
        raw = files.get(current, b"").decode("utf-8-sig", errors="replace")
        prose = re.sub(r"```[^\n]*\n[\s\S]*?```", "", raw)
        targets = re.findall(r"\]\(([^)\n]+)\)", prose)
        targets += re.findall(r"`([^`\n]+\.(?:md|markdown|txt))`", prose)
        for ref in targets:
            ref = ref.strip().split()[0].strip("<>") if ref.strip() else ""
            if not ref or ref.startswith(("#", "http:", "https:", "mailto:", "data:")):
                continue
            parts = list(PurePosixPath(current).parent.parts)
            for part in unquote(ref.split("#", 1)[0]).split("/"):
                if part in {"", "."}:
                    continue
                if part == "..":
                    if parts:
                        parts.pop()
                else:
                    parts.append(part)
            resolved = "/".join(parts)
            if resolved in files and resolved not in instruction_paths:
                instruction_paths.add(resolved)
                pending.append(resolved)
    for path, data in files.items():
        if path == license_path or ("/" not in path and NOTICE_NAME.match(path)):
            continue
        if LICENSE_NAME.match(PurePosixPath(path).name) and data != files[license_path]:
            return "所选技能包含独立许可证，当前服务无法确认组合许可；请人工审核。"
        if PurePosixPath(path).suffix.lower() in CODE_EXTENSIONS or PurePosixPath(path).name in MANIFEST_NAMES:
            return "技能包含脚本或运行依赖；当前服务只安装可独立使用的文档技能。"
        if PurePosixPath(path).suffix.lower() not in {".md", ".markdown", ".txt", ".yaml", ".yml", ".json", ".toml"}:
            continue
        try:
            text = data.decode("utf-8-sig")
        except UnicodeError:
            return "技能中的文本附件无法按 UTF-8 读取。"
        tags = re.findall(r"SPDX-License-Identifier:\s*([^\r\n]+)", text)
        if any(tag.strip(" */\t") != spdx for tag in tags):
            return "技能文件声明了不同或复合许可证，需要人工审核。"
        if path not in instruction_paths:
            continue
        if re.search(r"(?:\$\{|\$)(?:CLAUDE|CODEX|SKILL|AGENT)[A-Z_]*(?:ROOT|DIR)|(?:~|\$HOME|%USERPROFILE%)/\.(?:codex|agents|claude)|(?:^|[\s`])(?:pip3? install|npm (?:install|ci)|pnpm (?:add|install)|yarn add|npx |uv (?:sync|add|run)|git clone)|```(?:bash|sh|shell|python|javascript|typescript|powershell)\b", text, re.M | re.I):
            return "技能文档需要外部环境、命令或全局模块，当前服务无法保证完整运行。"
        # Detect path references even outside Markdown links.
        if re.search(r"(?:\.\./|\.\.\\)|(?:file://|/(?:Users|home|opt|usr)/)", text):
            return "技能引用了目录外的本地资源，无法作为独立技能完整安装。"
        # Fenced output examples are literal Markdown, not required source assets.
        prose = re.sub(r"```[^\n]*\n[\s\S]*?```", "", text)
        references = re.findall(r"\]\(([^)\n]+)\)", prose)
        references += re.findall(r"`((?:\./)?(?:references|assets|templates|examples|scripts)/[^`\n]+)`", text)
        for target in references:
            target = target.strip().split()[0].strip("<>") if target.strip() else ""
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            if target.startswith("/") or "\\" in target or ":" in target:
                return "技能包含无法安全解析的资源链接。"
            base = PurePosixPath(path).parent
            parts = [] if str(base) == "." else list(base.parts)
            for component in target.split("/"):
                if component in {"", "."}:
                    continue
                if component == "..":
                    if not parts:
                        return "技能链接越过仓库根目录。"
                    parts.pop()
                else:
                    parts.append(component)
            resolved = "/".join(parts).rstrip("/")
            if prefix and not resolved.startswith(prefix) and resolved != license_path:
                return "技能引用了所在模块以外的文件；请使用完整上游项目。"
            if resolved not in available and not any(p.startswith(resolved + "/") for p in available):
                return "技能引用的本地附件缺失，无法完成独立安装。"
    return None


class Studio:
    def __init__(self, root: Path, github: GitHub | None = None):
        self.root = root.resolve()
        self.local = self.root / ".local"
        self.github = github or GitHub()
        self.lock = threading.RLock()
        self.cache: dict[tuple[str, str], dict] = {}
        self.offline_warning: str | None = None

    def _safe_local(self, path: Path) -> Path:
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            raise ImportErrorSafe("本地写入路径越界。") from None
        cursor = self.root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ImportErrorSafe("本地存储路径包含符号链接，已停止写入。")
        if not path.resolve().is_relative_to(self.root):
            raise ImportErrorSafe("本地存储路径越界。")
        return path

    def _mkdir(self, path: Path) -> None:
        self._safe_local(path).mkdir(parents=True, exist_ok=True, mode=0o700)

    def _catalog(self, *, legacy: bool = False, canonical: bool = False, preview: bool = False) -> dict:
        source = self.root / "catalog.json" if canonical else self.local / ("preview-catalog.json" if preview else "legacy-catalog.json" if legacy else "catalog.json")
        path = self._safe_local(source)
        if not path.exists():
            return {"version": 1, "styles": []}
        try:
            if path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError()
            result = json.loads(path.read_text(encoding="utf-8"))
            if (canonical or preview) and isinstance(result, list):
                result = {"styles": result}
            if not isinstance(result, dict) or not isinstance(result.get("styles"), list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in result["styles"]):
                raise ValueError()
            return result
        except (OSError, ValueError):
            label = "本地预览索引" if preview else "内置风格索引" if canonical else "旧风格兼容索引" if legacy else "本地目录索引"
            raise ImportErrorSafe(f"{label}损坏；请恢复备份后重试，现有内容未被覆盖。", 409) from None

    def catalog(self) -> dict:
        with self.lock:
            merged = {item["id"]: dict(item) for item in self._catalog(legacy=True)["styles"]}
            for item in self._catalog()["styles"]:
                previous = merged.get(item["id"], {})
                combined = {**previous, **item}
                if not item.get("image") and previous.get("image"):
                    combined["image"] = previous["image"]
                merged[item["id"]] = combined
            for preview in self._catalog(preview=True)["styles"]:
                item = merged.get(preview["id"])
                if item is None:
                    continue
                for key in ("label", "summary"):
                    if isinstance(preview.get(key), str) and preview[key].strip():
                        item[key] = preview[key][:800 if key == "summary" else 120]
                current = self._preview_target(item.get("image"))
                candidate = self._preview_target(preview.get("image"))
                if candidate and not current:
                    item["image"] = "/local-previews/" + candidate[0].name
                    for key in ("imageCaption", "credit"):
                        if isinstance(preview.get(key), str):
                            item[key] = preview[key][:500]
            for item in merged.values():
                preview = self._preview_target(item.get("image"))
                if preview:
                    item["image"] = "/local-previews/" + preview[0].name
                elif isinstance(item.get("image"), str) and item["image"].startswith("/"):
                    item["image"] = None
            return {"styles": list(merged.values())}

    def _preview_target(self, value: object) -> tuple[Path, str] | None:
        if not isinstance(value, str):
            return None
        if value.startswith("/local-previews/"):
            name = value[len("/local-previews/"):]
            target = self.local / "previews" / name
        else:
            target = Path(value)
            name = target.name
            if not target.is_absolute() or target.parent != self.local / "previews":
                return None
        if not PREVIEW_NAME.fullmatch(name) or ".." in name:
            return None
        try:
            target = self._safe_local(target)
            if not target.is_file() or not 0 < target.stat().st_size <= MAX_PREVIEW:
                return None
            with target.open("rb") as stream:
                mime = image_mime(stream.read(32))
            if mime:
                return target, mime
        except (ImportErrorSafe, OSError):
            pass
        return None

    def local_preview(self, name: str) -> tuple[bytes, str]:
        if not PREVIEW_NAME.fullmatch(name) or ".." in name:
            raise ImportErrorSafe("本地预览不存在。", 404)
        with self.lock:
            rows = self._catalog(preview=True)["styles"] + self._catalog()["styles"]
            for row in rows:
                found = self._preview_target(row.get("image"))
                if found and found[0].name == name:
                    data = found[0].read_bytes()
                    if len(data) <= MAX_PREVIEW and image_mime(data[:32]) == found[1]:
                        return data, found[1]
        raise ImportErrorSafe("本地预览未登记或无法读取。", 404)

    def status(self) -> dict:
        return {"connected": True, "version": VERSION, "installedCount": len(self.catalog()["styles"]), "githubReady": shutil.which("gh") is not None, "warnings": [self.offline_warning] if self.offline_warning else []}

    def refresh_offline(self) -> list[str]:
        try:
            specification = importlib.util.spec_from_file_location("_photo_alchemy_offline_builder", Path(__file__).with_name("build_local_gallery.py"))
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            module.build_local_gallery(self.root, studio=self)
            self.offline_warning = None
        except Exception:
            self.offline_warning = "个人离线页未更新；现有安装未受影响。可运行 python3 scripts/build_local_gallery.py 重新生成。"
        return [self.offline_warning] if self.offline_warning else []

    def search(self, query: object) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 160 or any(ord(c) < 32 for c in query):
            raise ImportErrorSafe("请输入不超过 160 字的技能名称或 GitHub 仓库网址。")
        query = query.strip()
        if "/" in query or ":" in query:
            repo = safe_repo(query)
            metadata = self.github.api(f"repos/{repo}")
            canonical = safe_repo(metadata.get("full_name", repo))
            return {"candidates": [{"repo": canonical, "url": f"https://github.com/{canonical}", "description": str(metadata.get("description") or "")[:800]}], "warnings": []}
        # Quote the user phrase so qualifiers cannot change the search scope.
        query = query.replace('"', " ").strip()
        endpoints = [
            "search/repositories?" + urlencode({"q": '"' + query + '" in:name', "per_page": 6}),
            "search/code?" + urlencode({"q": '"' + query + '" filename:SKILL.md', "per_page": 6}),
        ]
        candidates, warnings, seen = [], [], set()
        for endpoint in endpoints:
            try:
                response = self.github.api(endpoint)
            except ImportErrorSafe:
                warnings.append("部分 GitHub 搜索未成功，结果可能不完整；可直接填写仓库网址。")
                continue
            for item in response.get("items", []):
                source = item.get("repository", item)
                try:
                    repo = safe_repo(source.get("full_name"))
                except ImportErrorSafe:
                    continue
                if repo.lower() in seen:
                    continue
                seen.add(repo.lower())
                candidates.append({"repo": repo, "url": f"https://github.com/{repo}", "description": str(source.get("description") or "")[:800]})
                if len(candidates) == 6:
                    break
            if len(candidates) == 6:
                break
        if not candidates and len(warnings) == 2:
            raise ImportErrorSafe("GitHub 搜索失败。请检查 gh auth status 或稍后重试。", 502)
        return {"candidates": candidates, "warnings": list(dict.fromkeys(warnings))}

    def inspect(self, value: object) -> dict:
        repo = safe_repo(value)
        with self.lock:
            return self._inspect(repo)

    def _inspect(self, repo: str) -> dict:
        metadata = self.github.api(f"repos/{repo}")
        repo = safe_repo(metadata.get("full_name", repo))
        branch = metadata.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise ImportErrorSafe("仓库没有可读取的默认分支。")
        commit = self.github.api(f"repos/{repo}/commits/{quote(branch, safe='')}").get("sha", "")
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            raise ImportErrorSafe("无法固定仓库 commit。", 502)
        tree = self.github.api(f"repos/{repo}/git/trees/{commit}?recursive=1")
        if tree.get("truncated") or not isinstance(tree.get("tree"), list) or len(tree["tree"]) > 20_000:
            raise ImportErrorSafe("仓库文件树过大或不完整；请使用独立技能仓库。")
        entries, folded = {}, set()
        for item in tree["tree"]:
            path = safe_path(item.get("path"))
            if path.casefold() in folded:
                raise ImportErrorSafe("仓库存在大小写冲突文件，无法安全安装。")
            folded.add(path.casefold())
            if item.get("type") == "tree":
                continue
            entries[path] = item
        skills = [path for path, item in entries.items() if PurePosixPath(path).name == "SKILL.md" and item.get("type") == "blob"]
        skills.sort(key=lambda p: (p.count("/"), p))
        warnings = ["第三方文档属于未受信内容；请阅读后使用，不要把其中的指令自动执行。", "仅支持文档及附件可独立使用的技能；外部服务、模型和付费工具的可用性未验证。"]
        result = {"repo": repo, "commit": commit, "license": None, "licenseUrl": None, "installable": False, "reason": "", "skills": [], "warnings": warnings}
        if not skills:
            result["reason"] = "仓库中未发现 SKILL.md。"
            return result
        if len(skills) > 30:
            result["reason"] = "仓库包含超过 30 个技能；请使用独立技能仓库。"
            return result
        try:
            license_info = self.github.api(f"repos/{repo}/license?ref={commit}")
        except ImportErrorSafe:
            result["reason"] = "未能读取明确许可证文件；不自动安装。"
            return result
        spdx = (license_info.get("license") or {}).get("spdx_id")
        result["license"] = spdx
        license_path = license_info.get("path")
        if spdx not in ALLOWED_LICENSES:
            result["reason"] = "许可未知、限制使用或不在自动安装白名单中。"
            return result
        if not isinstance(license_path, str) or "/" in license_path or license_path not in entries or not LICENSE_NAME.match(license_path):
            result["reason"] = "缺少可核对的仓库根许可证文件。"
            return result
        license_entry = entries[license_path]
        if license_entry.get("mode") not in {"100644", "100755"} or license_info.get("sha") != license_entry.get("sha"):
            result["reason"] = "许可证文件不属于当前固定版本，或不是普通文件。"
            return result
        license_data = decode_blob(license_info, license_entry["sha"])
        if not license_text_ok(spdx, license_data):
            result["reason"] = "许可证正文无法确认为完整的标准许可；需要人工审核。"
            return result
        result["licenseUrl"] = f"https://github.com/{repo}/blob/{commit}/{quote(license_path)}"
        root_notices = [p for p in entries if "/" not in p and NOTICE_NAME.match(p)]
        root_licenses = [p for p in entries if "/" not in p and LICENSE_NAME.match(p)]
        if any(p != license_path for p in root_licenses):
            result["reason"] = "仓库根目录包含多份许可证；需要人工确认组合许可。"
            return result
        plans, wanted = {}, {license_path}
        for entry in skills:
            folder = str(PurePosixPath(entry).parent)
            prefix = "" if folder == "." else folder + "/"
            paths = {p for p in entries if not prefix or p.startswith(prefix)} | {license_path, *root_notices}
            reason = None
            if len(paths) > MAX_FILES or sum(entries[p].get("size", MAX_FILE + 1) for p in paths) > MAX_TOTAL:
                reason = "技能文件数量或体积超过本地导入上限。"
            elif any(entries[p].get("mode") not in {"100644", "100755"} or entries[p].get("type") != "blob" for p in paths):
                reason = "技能包含符号链接、子模块或特殊文件，无法安全完整安装。"
            elif any(entries[p].get("size", MAX_FILE + 1) > MAX_FILE for p in paths):
                reason = "技能包含超过 2 MB 的文件。"
            plans[entry] = {"paths": paths, "reason": reason}
            wanted.add(entry)
            if not reason:
                wanted.update(paths)
        if len(wanted) > MAX_FILES or sum(entries[p].get("size", MAX_FILE + 1) for p in wanted) > MAX_TOTAL:
            result["reason"] = "仓库待审核内容超过 120 个文件或 12 MB；请使用较小的独立技能仓库。"
            return result
        blobs = {license_path: license_data}

        def fetch(path: str) -> tuple[str, bytes]:
            item = entries[path]
            if item.get("mode") not in {"100644", "100755"} or not SHA.fullmatch(str(item.get("sha", ""))) or item.get("size", MAX_FILE + 1) > MAX_FILE:
                raise ImportErrorSafe("源文件不是安全的普通文件或超过大小限制。")
            data = decode_blob(self.github.api(f"repos/{repo}/git/blobs/{item['sha']}"), item["sha"])
            return path, data

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for path, data in pool.map(fetch, sorted(wanted - {license_path})):
                blobs[path] = data
        cached_skills = {}
        for entry, plan in plans.items():
            fallback = PurePosixPath(entry).parent.name if "/" in entry else repo.split("/")[1]
            try:
                name, description = skill_metadata(blobs[entry], fallback)
            except ImportErrorSafe as error:
                name, description = fallback, ""
                plan["reason"] = str(error)
            files = {path: blobs[path] for path in plan["paths"] if path in blobs}
            reason = plan["reason"] or dependency_problem(entry, files, license_path, spdx)
            summary = {"path": entry, "name": name, "description": description, "installable": reason is None, "reason": reason or "许可证明确，文档和附件可完整保留。"}
            result["skills"].append(summary)
            if not reason:
                cached_skills[entry] = {"summary": summary, "files": files}
        result["installable"] = bool(cached_skills)
        result["reason"] = "可选择已通过检查的技能安装。" if cached_skills else "未找到可由当前服务完整安装的技能；请查看各技能原因。"
        now = time.monotonic()
        self.cache = {key: item for key, item in self.cache.items() if now - item["at"] < CACHE_TTL}
        self.cache[(repo.lower(), commit)] = {"at": now, "result": result, "skills": cached_skills}
        return result

    def _write_catalog(self, catalog: dict) -> None:
        self._mkdir(self.local)
        destination = self._safe_local(self.local / "catalog.json")
        fd, filename = tempfile.mkstemp(prefix="catalog-", suffix=".tmp", dir=self.local)
        temporary = Path(filename)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(catalog, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _verify_files(self, destination: Path, files: dict[str, bytes]) -> bool:
        for path, expected in files.items():
            target = self._safe_local(destination / safe_path(path))
            if not target.is_file() or target.stat().st_size != len(expected) or target.read_bytes() != expected:
                return False
        return True

    def install(self, value: object, commit: object, path: object) -> dict:
        repo = safe_repo(value)
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            raise ImportErrorSafe("安装必须指定 inspect 返回的完整 commit。", 409)
        path = safe_path(path)
        with self.lock:
            cached = self.cache.get((repo.lower(), commit))
            if not cached or time.monotonic() - cached["at"] > CACHE_TTL:
                raise ImportErrorSafe("此版本尚未检查或检查已过期；请先重新检查仓库。", 409)
            selected = cached["skills"].get(path)
            if not selected:
                raise ImportErrorSafe("所选路径未通过本次检查，不能安装。", 409)
            result = cached["result"]
            repo = result["repo"]
            identity = repo.lower() + ":" + path
            slug = re.sub(r"[^a-z0-9-]+", "-", selected["summary"]["name"].lower()).strip("-")[:44] or "skill"
            identifier = slug + "-" + hashlib.sha256(identity.encode()).hexdigest()[:12]
            catalog = self._catalog()

            def matches_source(item: dict) -> bool:
                return isinstance(item.get("source"), str) and item["source"].lower() == repo.lower() and item.get("sourcePath") == path

            old = next((item for item in catalog["styles"] if matches_source(item)), None)
            existing = old
            if old:
                # The same upstream path retains its identity when its label changes.
                identifier = old["id"]
                if not re.fullmatch(r"[a-z0-9-]{1,80}", identifier):
                    raise ImportErrorSafe("已有条目标识无效，已停止覆盖。", 409)
            else:
                known = {item["id"]: item for item in self._catalog(canonical=True)["styles"]}
                known.update({item["id"]: item for item in self._catalog(legacy=True)["styles"]})
                matches = [item for item in known.values() if matches_source(item)]
                if len(matches) == 1 and re.fullmatch(r"[a-z0-9-]{1,80}", matches[0]["id"]) and not any(item["id"] == matches[0]["id"] for item in catalog["styles"]):
                    existing = matches[0]
                    identifier = existing["id"]
            label = existing.get("label") if existing else None
            if not isinstance(label, str) or not label.strip():
                label = selected["summary"]["name"]
            destination = self._safe_local(self.local / "extensions" / identifier)
            files = selected["files"]
            if old and old.get("commit") == commit and destination.is_dir() and self._verify_files(destination, files):
                return {"installed": True, "alreadyInstalled": True, "style": old, "historyPath": None, "warnings": self.refresh_offline()}
            self._mkdir(self.local / "staging")
            self._mkdir(destination.parent)
            staging = Path(tempfile.mkdtemp(prefix="import-", dir=self.local / "staging"))
            backup = None
            created_preview = None
            promoted = False
            try:
                for relative, content in files.items():
                    target = self._safe_local(staging / safe_path(relative))
                    self._mkdir(target.parent)
                    with target.open("xb") as stream:
                        stream.write(content)
                    target.chmod(0o600)
                provenance = {"repo": repo, "commit": commit, "path": path, "license": result["license"], "files": {p: git_blob_sha(data) for p, data in files.items()}, "installedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                (staging / ".provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
                if not self._verify_files(staging, files):
                    raise ImportErrorSafe("安装暂存文件读回不一致，未替换当前版本。", 500)
                if destination.exists():
                    revision = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
                    backup = self.local / "history" / identifier / revision
                    self._mkdir(backup)
                    (backup / "style.json").write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
                    os.replace(destination, backup / "extension")
                os.replace(staging, destination)
                promoted = True
                style = {
                    "id": identifier, "label": label[:120], "origin": "community",
                    "source": repo, "sourceUrl": f"https://github.com/{repo}/blob/{commit}/{quote(path, safe='/')}",
                    "license": result["license"], "licenseUrl": result["licenseUrl"], "summary": selected["summary"]["description"],
                    "entry": str(destination / path), "sourcePath": path, "commit": commit,
                    "installed": True, "best": (existing or {}).get("best", []), "fidelity": (existing or {}).get("fidelity", "medium"), "image": None,
                    "manualOnly": bool((existing or {}).get("manualOnly") or (existing or {}).get("selection") == "manual-only" or any(p.endswith("agents/openai.yaml") and re.search(rb"(?m)^\s*allow_implicit_invocation:\s*false\s*$", data) for p, data in files.items())),
                    "installedAt": provenance["installedAt"],
                }
                for key in ("image", "imageCaption", "credit", "previewSourceUrl"):
                    if (existing or {}).get(key):
                        style[key] = existing[key]
                selected_preview = source_preview(path, files)
                if selected_preview:
                    source_path, image_data = selected_preview
                    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}[image_mime(image_data[:32])]
                    name = "imported-" + hashlib.sha256(image_data).hexdigest()[:24] + "." + extension
                    target = self._safe_local(self.local / "previews" / name)
                    self._mkdir(target.parent)
                    if target.exists():
                        if target.read_bytes() != image_data:
                            raise ImportErrorSafe("已有预览文件内容不一致，安装已停止。", 409)
                    else:
                        with target.open("xb") as stream:
                            created_preview = target
                            stream.write(image_data)
                        target.chmod(0o600)
                    style.update({"image": "/local-previews/" + name, "imageCaption": "上游参考图", "credit": repo, "previewSourceUrl": f"https://github.com/{repo}/blob/{commit}/{quote(source_path, safe='/')}"})
                updated = {"version": 1, "styles": [item for item in catalog["styles"] if item["id"] != identifier] + [style]}
                self._write_catalog(updated)
                return {"installed": True, "alreadyInstalled": False, "style": style, "historyPath": str(backup) if backup else None, "warnings": self.refresh_offline()}
            except Exception:
                if promoted and destination.exists():
                    shutil.rmtree(destination)
                if backup and (backup / "extension").exists():
                    os.replace(backup / "extension", destination)
                if created_preview:
                    created_preview.unlink(missing_ok=True)
                raise
            finally:
                if staging.exists():
                    shutil.rmtree(staging)

    def check_updates(self) -> dict:
        with self.lock:
            styles = list(self._catalog()["styles"])
        latest, updates = {}, []
        for item in styles:
            try:
                repo = safe_repo(item.get("source"))
                if repo not in latest:
                    metadata = self.github.api(f"repos/{repo}")
                    branch = metadata.get("default_branch")
                    if not isinstance(branch, str) or not branch:
                        raise ImportErrorSafe("上游默认分支不可用。")
                    pin = self.github.api(f"repos/{repo}/commits/{quote(branch, safe='')}").get("sha", "")
                    if not SHA.fullmatch(str(pin)):
                        raise ImportErrorSafe("上游 commit 无效。")
                    latest[repo] = pin
                updates.append({"id": item["id"], "repo": repo, "installedCommit": item.get("commit"), "latestCommit": latest[repo], "updateAvailable": latest[repo] != item.get("commit"), "error": None})
            except ImportErrorSafe as error:
                updates.append({"id": item["id"], "repo": item.get("source"), "installedCommit": item.get("commit"), "latestCommit": None, "updateAvailable": None, "error": str(error)})
        return {"updates": updates, "automaticInstall": False}


class StudioHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], studio: Studio):
        if address[0] != "127.0.0.1":
            raise ValueError("Only 127.0.0.1 is supported")
        self.studio = studio
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "PhotoAlchemyLocal/" + VERSION

    def log_message(self, format: str, *args: object) -> None:
        # Do not print request bodies, upstream text, paths, or credentials.
        pass

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
        self.end_headers()

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(data))
        if self.command != "HEAD":
            self.wfile.write(data)

    def _host(self, writing: bool = False) -> None:
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        values = self.headers.get_all("Host", [])
        if len(values) != 1 or values[0] not in hosts:
            raise ImportErrorSafe("仅接受本机服务地址。", 403)
        if writing:
            origins = self.headers.get_all("Origin", [])
            if len(origins) != 1 or origins[0] != "http://" + values[0]:
                raise ImportErrorSafe("请从同一个本地网页发起操作；不接受外部网页或 file:// 写入。", 403)
            if self.headers.get("Sec-Fetch-Site") not in {None, "same-origin", "none"}:
                raise ImportErrorSafe("不接受跨站请求。", 403)

    def do_OPTIONS(self) -> None:
        self._json({"error": "不开放跨来源访问。"}, 403)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        try:
            self._host()
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc:
                raise ImportErrorSafe("请求路径无效。", 400)
            path = unquote(parsed.path)
            if path == "/api/status":
                self._json(self.server.studio.status())
            elif path == "/api/catalog":
                self._json(self.server.studio.catalog())
            elif path.startswith("/local-previews/"):
                data, mime = self.server.studio.local_preview(path[len("/local-previews/"):])
                self._headers(200, mime, len(data))
                if self.command != "HEAD":
                    self.wfile.write(data)
            else:
                relative = "index.html" if path == "/" else safe_path(path.lstrip("/"))
                if relative not in {"index.html", "gallery.js", "gallery.css", "catalog.js"} and not relative.startswith("assets/"):
                    raise ImportErrorSafe("此路径不对浏览器开放。", 404)
                root = self.server.studio.root
                target = root / relative
                cursor = root
                for part in Path(relative).parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        raise ImportErrorSafe("不开放符号链接文件。", 404)
                if not target.resolve().is_relative_to(root) or not target.is_file():
                    raise ImportErrorSafe("文件不存在。", 404)
                data = target.read_bytes()
                mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                if mime.startswith("text/") or mime in {"application/javascript", "application/json"}:
                    mime += "; charset=utf-8"
                self._headers(200, mime, len(data))
                if self.command != "HEAD":
                    self.wfile.write(data)
        except ImportErrorSafe as error:
            self._json({"error": str(error)}, error.status)
        except (OSError, ValueError):
            self._json({"error": "本地文件读取失败。"}, 500)

    def do_POST(self) -> None:
        try:
            self._host(writing=True)
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                raise ImportErrorSafe("请求必须提供唯一的 Content-Length。", 411)
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise ImportErrorSafe("仅接受 JSON 请求。", 415)
            try:
                length = int(self.headers["Content-Length"])
            except (ValueError, TypeError):
                raise ImportErrorSafe("Content-Length 无效。") from None
            if length < 0 or length > MAX_BODY:
                raise ImportErrorSafe("请求内容超过 16 KB 限制。", 413)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ImportErrorSafe("请求内容不完整。")
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ImportErrorSafe("JSON 内容无效。") from None
            if not isinstance(data, dict):
                raise ImportErrorSafe("JSON 请求必须是对象。")
            studio = self.server.studio
            if self.path == "/api/search":
                result = studio.search(data.get("query"))
            elif self.path == "/api/inspect":
                result = studio.inspect(data.get("repo"))
            elif self.path == "/api/install":
                result = studio.install(data.get("repo"), data.get("commit"), data.get("path"))
            elif self.path == "/api/check-updates":
                result = studio.check_updates()
            else:
                raise ImportErrorSafe("接口不存在。", 404)
            self._json(result)
        except ImportErrorSafe as error:
            self._json({"error": str(error)}, error.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self._json({"error": "本地操作失败；未完成的安装已回滚，请检查本地磁盘与权限后重试。"}, 500)


def main() -> None:
    parser = argparse.ArgumentParser(description="Photo Alchemy Studio 本地扩充服务（不执行第三方代码）")
    parser.add_argument("--port", type=int, default=8796)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("端口必须介于 1024 和 65535。")
    root = Path(__file__).resolve().parent.parent
    try:
        server = StudioHTTPServer(("127.0.0.1", args.port), Studio(root))
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            message = f"本机端口 {args.port} 已被其他程序占用。请关闭对应程序，或使用其他端口启动："
        else:
            message = f"无法监听本机端口 {args.port}。请检查本机监听权限，或使用其他端口启动："
        alternate = 8797 if args.port != 8797 else 8798
        parser.exit(1, f"{message}\npython3 scripts/studio_server.py --port {alternate}\n")
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Photo Alchemy Studio {VERSION}: {url}", flush=True)
    print("仅限本机；按 Ctrl+C 停止。第三方源文件不会被自动执行。", flush=True)
    for warning in server.studio.refresh_offline():
        print("提示：" + warning, flush=True)
    if not args.no_open:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
