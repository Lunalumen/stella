"""Codex subscription MCP bridge. Subscription usage limits and charges still apply.

Claude Code가 이 서버를 MCP로 띄우면, `ask_chatgpt` 도구 호출 시
공식 Codex CLI의 `codex exec`를 실행해 ChatGPT 구독 계정으로 답을 받아온다.
API 키를 쓰지 않도록 OPENAI_API_KEY 등은 자식 프로세스 환경에서 제거한다.

표준 라이브러리만 사용. MCP stdio(줄 단위 JSON-RPC 2.0) 프로토콜.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SERVER_NAME = "codex-chatgpt"
SERVER_VERSION = "0.1.0"
DEFAULT_TIMEOUT = 600  # 초
LOG_PATH = Path(__file__).with_name("server.log")

# API 과금 경로를 막기 위해 자식 프로세스에서 지울 환경변수
BLOCKED_ENV = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY", "AZURE_OPENAI_API_KEY")


def log(msg: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def find_codex_command() -> list[str]:
    """Windows의 .cmd 래퍼(shim) 문제를 피하려고 node + codex.js를 직접 실행한다."""
    override = os.environ.get("CODEX_JS")
    candidates = [Path(override)] if override else []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "npm" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js")
    node = os.environ.get("NODE_EXE") or shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    for js in candidates:
        if js.is_file() and Path(node).is_file():
            return [node, str(js)]
    codex = shutil.which("codex")
    if codex:
        return [codex]
    raise RuntimeError("Codex CLI를 찾을 수 없습니다. `npm i -g @openai/codex` 후 `codex login`을 하세요.")


TOOLS = [
    {
        "name": "ask_chatgpt",
        "description": (
            "ChatGPT(OpenAI Codex CLI, 사용자의 ChatGPT 구독)에게 질문·검토·두 번째 의견을 요청한다. "
            "기본은 읽기 전용 샌드박스라 파일을 바꾸지 않는다. 응답까지 수십 초 걸릴 수 있다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "ChatGPT에게 보낼 요청 전문"},
                "cwd": {"type": "string", "description": "Codex가 참고할 작업 폴더(선택)"},
                "sandbox": {
                    "type": "string",
                    "enum": ["read-only", "workspace-write"],
                    "default": "read-only",
                    "description": "workspace-write는 cwd 안 파일 수정을 허용한다",
                },
                "model": {"type": "string", "description": "모델 지정(선택, 비우면 Codex 기본값)"},
                "timeout_sec": {"type": "integer", "default": DEFAULT_TIMEOUT},
            },
            "required": ["prompt"],
        },
    }
]


def run_codex(args: dict) -> tuple[str, bool]:
    prompt = str(args.get("prompt", "")).strip()
    if not prompt:
        return "prompt가 비어 있습니다.", True
    sandbox = args.get("sandbox") or "read-only"
    if sandbox not in ("read-only", "workspace-write"):
        return f"허용되지 않는 sandbox 값: {sandbox}", True
    cwd = args.get("cwd") or os.getcwd()
    if not Path(cwd).is_dir():
        return f"cwd 폴더가 없습니다: {cwd}", True
    timeout = int(args.get("timeout_sec") or DEFAULT_TIMEOUT)

    env = {k: v for k, v in os.environ.items() if k not in BLOCKED_ENV}
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "last.txt"
        cmd = find_codex_command() + [
            "exec", "--skip-git-repo-check", "-s", sandbox, "-C", cwd,
            "-o", str(out_file),
        ]
        if args.get("model"):
            cmd += ["-m", str(args["model"])]
        cmd.append("-")  # 프롬프트는 stdin으로 (한글·긴 문장 안전)
        log(f"run: sandbox={sandbox} cwd={cwd} chars={len(prompt)}")
        try:
            proc = subprocess.run(
                cmd, input=prompt.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=cwd, env=env, timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return f"Codex 응답이 {timeout}초 안에 오지 않았습니다.", True
        answer = out_file.read_text(encoding="utf-8", errors="replace").strip() if out_file.exists() else ""
    if proc.returncode != 0 or not answer:
        err = (proc.stderr or proc.stdout).decode("utf-8", errors="replace")[-2000:]
        log(f"fail rc={proc.returncode}: {err}")
        return f"Codex 실행 실패 (exit {proc.returncode}).\n{err}", True
    return answer, False


def handle(req: dict) -> dict | None:
    method = req.get("method")
    rid = req.get("id")
    if rid is None:  # 알림(notification)은 응답하지 않음
        return None
    if method == "initialize":
        client_ver = (req.get("params") or {}).get("protocolVersion") or "2025-06-18"
        result = {
            "protocolVersion": client_ver,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = req.get("params") or {}
        if params.get("name") != "ask_chatgpt":
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": "unknown tool"}}
        try:
            text, is_err = run_codex(params.get("arguments") or {})
        except Exception as e:  # noqa: BLE001
            text, is_err = f"서버 오류: {e}", True
        result = {"content": [{"type": "text", "text": text}], "isError": is_err}
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def main() -> None:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    log("server start")
    for raw in stdin:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            stdout.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout.flush()


if __name__ == "__main__":
    main()
