#!/usr/bin/env python3
"""Idempotent macOS launcher; no background scheduler or launch agent."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser

APP_ID = "photo-alchemy-studio"
_BACKGROUND_PROCESSES: list[subprocess.Popen] = []


class LaunchError(Exception):
    pass


def fingerprint(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()


def safe_local(root: Path, path: Path) -> Path:
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise LaunchError("启动文件路径超出项目目录。") from None
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise LaunchError("启动文件路径包含符号链接，已停止操作。")
    if not path.resolve().is_relative_to(root):
        raise LaunchError("启动文件路径超出项目目录。")
    return path


def status_at(port: int, identity: str, timeout: float = 0.3) -> dict | None:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET", "/api/status", headers={"Host": f"127.0.0.1:{port}", "Accept": "application/json"})
        response = connection.getresponse()
        body = response.read(16_385)
        if response.status != 200 or len(body) > 16_384:
            return None
        result = json.loads(body)
        if isinstance(result, dict) and result.get("connected") is True and result.get("appId") == APP_ID and result.get("rootFingerprint") == identity:
            return result
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        connection.close()
    return None


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


@contextmanager
def launch_lock(root: Path, deadline: float):
    path = safe_local(root, root / ".local" / "launcher.lock")
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "a") as stream:
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LaunchError("另一个启动窗口仍在准备图库，请稍后再点一次。") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def read_state(root: Path) -> dict:
    path = safe_local(root, root / ".local" / "launcher-state.json")
    try:
        if path.stat().st_size > 4096:
            return {}
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def write_state(root: Path, info: dict) -> None:
    path = safe_local(root, root / ".local" / "launcher-state.json")
    descriptor, name = tempfile.mkstemp(prefix="launcher-state-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(info, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _spawn(root: Path, port: int) -> subprocess.Popen:
    script = safe_local(root, root / "scripts" / "studio_server.py")
    if not script.is_file():
        raise LaunchError("缺少 scripts/studio_server.py，请重新下载完整项目。")
    log_path = safe_local(root, root / ".local" / "studio-server.log")
    descriptor = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "ab", buffering=0) as log:
        return subprocess.Popen(
            [sys.executable, str(script), "--port", str(port), "--no-open"],
            cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )


def _stop_own_child(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)


def ensure_service(root: Path, ports=tuple(range(8796, 8801)), timeout: float = 10.0) -> dict:
    root = root.resolve()
    if not ports or any(type(port) is not int or not 1024 <= port <= 65535 for port in ports):
        raise LaunchError("启动端口无效。")
    private = safe_local(root, root / ".local")
    private.mkdir(mode=0o700, exist_ok=True)
    private.chmod(0o700)
    _BACKGROUND_PROCESSES[:] = [process for process in _BACKGROUND_PROCESSES if process.poll() is None]
    identity = fingerprint(root)
    deadline = time.monotonic() + timeout
    with launch_lock(root, deadline):
        previous = read_state(root)
        cached = previous.get("port") if previous.get("rootFingerprint") == identity else None
        candidates = list(dict.fromkeys(([cached] if cached in ports else []) + list(ports)))
        for port in candidates:
            result = status_at(port, identity)
            if result:
                info = {"appId": APP_ID, "rootFingerprint": identity, "port": port, "pid": result.get("pid"), "url": f"http://127.0.0.1:{port}/", "started": False}
                write_state(root, info)
                return info
        for port in candidates:
            if time.monotonic() >= deadline:
                break
            if not port_available(port):
                continue
            child = _spawn(root, port)
            while time.monotonic() < deadline:
                result = status_at(port, identity)
                if result:
                    info = {"appId": APP_ID, "rootFingerprint": identity, "port": port, "pid": result.get("pid"), "url": f"http://127.0.0.1:{port}/", "started": result.get("pid") == child.pid}
                    write_state(root, info)
                    # Retain the handle while this launcher process exists;
                    # start_new_session keeps the service alive after it exits.
                    _BACKGROUND_PROCESSES.append(child)
                    return info
                if child.poll() is not None:
                    break
                time.sleep(0.15)
            _stop_own_child(child)
        raise LaunchError(f"图库未能在 {ports[0]}–{ports[-1]} 端口启动。请查看 .local/studio-server.log，或稍后重试；没有停止其他程序。")


def open_browser(url: str) -> bool:
    if sys.platform == "darwin":
        apps = [Path("/Applications/Tabbit.app"), Path.home() / "Applications" / "Tabbit.app"]
        for app in apps:
            if app.is_dir():
                try:
                    result = subprocess.run(["/usr/bin/open", "-a", str(app), url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
                    if result.returncode == 0:
                        return True
                except (OSError, subprocess.TimeoutExpired):
                    pass
        try:
            return subprocess.run(["/usr/bin/open", url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    return bool(webbrowser.open(url))


def main() -> None:
    parser = argparse.ArgumentParser(description="在后台启动或复用当前照片风格库")
    parser.add_argument("--no-open", action="store_true", help="只启动服务，不打开浏览器")
    parser.add_argument("--port", type=int, default=8796, help="首选端口；冲突时尝试后续 4 个端口")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65531:
        parser.error("首选端口必须介于 1024 和 65531。")
    root = Path(__file__).resolve().parent.parent
    try:
        info = ensure_service(root, ports=tuple(range(args.port, args.port + 5)))
    except (LaunchError, OSError) as error:
        message = str(error) if isinstance(error, LaunchError) else "本地启动文件不可写或服务无法启动，请检查项目目录权限。"
        parser.exit(1, f"{message}\n离线后备：直接打开 {root / 'local.html'}\n")
    print(("图库已在后台启动：" if info["started"] else "已找到当前图库：") + info["url"], flush=True)
    print("可以关闭此终端窗口。", flush=True)
    if not args.no_open and not open_browser(info["url"]):
        print("浏览器未能自动打开，请复制上面的本机网址，或打开项目中的 local.html。", flush=True)


if __name__ == "__main__":
    main()
