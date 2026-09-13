#!/usr/bin/env python3
"""Build the ignored personal file:// entry from the shared public frontend."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile


def _atomic_text(path: Path, text: str) -> None:
    fd, filename = tempfile.mkstemp(prefix=path.name + "-", suffix=".tmp", dir=path.parent)
    temporary = Path(filename)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_local_gallery(root: Path, studio=None) -> dict:
    root = root.resolve()
    if studio is None:
        from studio_server import Studio
        studio = Studio(root)
    if studio.root != root:
        raise ValueError("Offline export must use the same project root")
    with studio.lock:
        source = studio._safe_local(root / "index.html")
        if not source.is_file() or source.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Shared index.html is missing or too large")
        html = source.read_text(encoding="utf-8")
        pattern = re.compile(r"(<script\b[^>]*\bsrc\s*=\s*[\"'](?:\./)?catalog\.js[\"'][^>]*>\s*</script\s*>)", re.I)
        if len(pattern.findall(html)) != 1 or ".local/gallery-catalog.js" in html:
            raise ValueError("Shared index must contain exactly one public catalog.js script")
        local_html = pattern.sub(lambda match: match.group(1) + '<script src=".local/gallery-catalog.js"></script>', html, count=1)
        styles = {item["id"]: dict(item) for item in studio._catalog(canonical=True)["styles"]}
        for item in studio.catalog()["styles"]:
            previous = styles.get(item["id"], {})
            combined = {**previous, **item}
            if not item.get("image") and previous.get("image"):
                combined["image"] = previous["image"]
            styles[item["id"]] = combined
        preview_count = 0
        for item in styles.values():
            value = item.get("image")
            if isinstance(value, str) and value.startswith("/local-previews/"):
                name = value[len("/local-previews/"):]
                # Reuse the route's exact registration/type/path validation.
                studio.local_preview(name)
                item["image"] = ".local/previews/" + name
                preview_count += 1
            elif isinstance(value, str) and (value.startswith(("/", "file:")) or "\\" in value):
                item["image"] = None
        data = json.dumps(list(styles.values()), ensure_ascii=False, indent=2)
        data = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        script = "window.PHOTO_ALCHEMY_PERSONAL = true;\nwindow.PHOTO_ALCHEMY_CATALOG = " + data + ";\n"
        output = studio._safe_local(root / "local.html")
        catalog_output = studio._safe_local(studio.local / "gallery-catalog.js")
        studio._mkdir(studio.local)
        # Complete validation before replacing either generated artifact. Each
        # file is replaced atomically; public source files are never modified.
        _atomic_text(catalog_output, script)
        _atomic_text(output, local_html)
        return {"path": str(output), "catalogPath": str(catalog_output), "count": len(styles), "previewCount": preview_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="重建可直接双击打开的个人离线风格库")
    parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    try:
        result = build_local_gallery(root)
    except Exception:
        parser.exit(1, "个人离线页生成失败。请确认 index.html、catalog.json 和本地索引完整，且项目目录可写；现有安装未被更改。\n")
    print(f"个人离线页：{result['path']}\n{result['count']} 个风格，{result['previewCount']} 张本地参考图。")


if __name__ == "__main__":
    main()
