"""Explicit task-scoped Codex CLI bridge. No API-key fallback or automatic retry."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
TASK_RE = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}\Z')
MODEL_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z')
SAFE_ENV = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'APPDATA', 'LOCALAPPDATA',
            'USERPROFILE', 'HOME', 'HOMEDRIVE', 'HOMEPATH', 'TEMP', 'TMP', 'LANG', 'LC_ALL'}
MAX_STREAM = 2_000_000
MAX_LINE = 200_000
MAX_ANSWER = 100_000


def stamp():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with os.fdopen(os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def session_uuid(value):
    if not isinstance(value, str):
        raise ValueError('session_format')
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise ValueError('session_format') from None
    if canonical != value.lower():
        raise ValueError('session_format')
    return canonical


def codex_launcher():
    override = os.environ.get('CODEX_EXE')
    if override:
        path = Path(override).resolve(strict=True)
        if not path.is_file() or (os.name == 'nt' and path.suffix.lower() != '.exe') or (os.name != 'nt' and path.suffix.lower() in {'.cmd', '.bat', '.ps1'}):
            raise ValueError('invalid_codex_executable')
        return [str(path)]
    js = os.environ.get('CODEX_JS')
    if js:
        entry = Path(js).resolve(strict=True)
        node = os.environ.get('NODE_EXE') or shutil.which('node')
        if entry.suffix.lower() != '.js' or not entry.is_file() or not node or not Path(node).is_file():
            raise ValueError('invalid_codex_node_entrypoint')
        return [str(Path(node).resolve()), str(entry)]
    found = shutil.which('codex')
    if not found:
        raise ValueError('codex_not_found_set_CODEX_EXE_or_install_official_CLI')
    path = Path(found).resolve(strict=True)
    if path.suffix.lower() == '.exe' or (os.name != 'nt' and path.suffix.lower() not in {'.cmd', '.bat', '.ps1'}):
        return [str(path)]
    if path.suffix.lower() in {'.cmd', '.ps1'}:
        entry = path.parent / 'node_modules/@openai/codex/bin/codex.js'
        node = os.environ.get('NODE_EXE') or shutil.which('node')
        if entry.is_file() and node and Path(node).is_file():
            return [str(Path(node).resolve()), str(entry)]
    raise ValueError('unsupported_codex_launcher_no_shell_fallback')


def stop_tree(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        killer = Path(os.environ.get('SYSTEMROOT', 'C:/Windows')) / 'System32/taskkill.exe'
        subprocess.run([str(killer), '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10, check=False,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def bounded_process(command, *, env, cwd, prompt='', timeout=20, on_line=None, merge_stderr=False, output_limit=MAX_STREAM):
    """Bounded stdout processing. stderr is discarded; raw event streams are never retained."""
    options = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT if merge_stderr else subprocess.DEVNULL, **options)
    lines = queue.Queue(maxsize=16)
    stopped = threading.Event()

    def offer(item):
        while not stopped.is_set():
            try:
                lines.put(item, timeout=0.1)
                return
            except queue.Full:
                pass

    def reader():
        try:
            while not stopped.is_set():
                line = process.stdout.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE:
                    offer(ValueError('output_line_limit'))
                    return
                offer(line)
        finally:
            offer(None)

    def writer():
        try:
            process.stdin.write(prompt.encode('utf-8'))
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    read_thread = threading.Thread(target=reader, daemon=True)
    write_thread = threading.Thread(target=writer, daemon=True)
    read_thread.start()
    write_thread.start()
    deadline = time.monotonic() + timeout
    used = 0
    text = []
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('codex_timeout_no_retry')
            try:
                item = lines.get(timeout=min(remaining, 0.2))
            except queue.Empty:
                continue
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            used += len(item)
            if used > output_limit:
                raise ValueError('output_stream_limit')
            decoded = item.decode('utf-8', errors='strict').strip()
            if on_line:
                on_line(decoded)
            else:
                text.append(decoded)
        try:
            code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ValueError('codex_timeout_no_retry') from None
        return code, '\n'.join(text)
    finally:
        stopped.set()
        stop_tree(process)
        read_thread.join(timeout=2)
        write_thread.join(timeout=2)
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()


class CodexClient:
    def __init__(self, command=None):
        self.command = command or codex_launcher()

    def env(self):
        return {k: v for k, v in os.environ.items() if k.upper() in SAFE_ENV}

    def checked_status(self):
        # This official CLI command emits only account mode; do not read auth.json or return raw diagnostics.
        code, text = bounded_process(self.command + ['login', 'status'], env=self.env(), cwd=ROOT,
                                     merge_stderr=True, output_limit=32_000)
        if code != 0 or not any(line.strip().lower() == 'logged in using chatgpt' for line in text.splitlines()):
            raise ValueError('chatgpt_login_required_no_API_fallback')
        code, help_text = bounded_process(self.command + ['exec', '--help'], env=self.env(), cwd=ROOT)
        if code or any(flag not in help_text for flag in ('--ignore-user-config', '--json', 'resume')):
            raise ValueError('unsupported_CLI_update_official_Codex')
        code, resume_help = bounded_process(self.command + ['exec', 'resume', '--help'], env=self.env(), cwd=ROOT)
        if code or 'SESSION_ID' not in resume_help:
            raise ValueError('unsupported_CLI_resume')
        return {'authenticated_chatgpt': True, 'resume_supported': True, 'model_called': False}

    def ask(self, prompt, session, cwd, sandbox, model, timeout):
        self.checked_status()
        state = {'session': None, 'completed': False, 'usage': {}}

        def event(line):
            if not line:
                return
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                raise ValueError('codex_event_format') from None
            if not isinstance(data, dict):
                raise ValueError('codex_event_format')
            kind = data.get('type')
            if kind == 'thread.started':
                sid = session_uuid(data.get('thread_id'))
                if state['session'] not in (None, sid) or session and sid != session:
                    raise ValueError('unexpected_session_id')
                state['session'] = sid
            elif kind == 'turn.completed':
                state['completed'] = True
                usage = data.get('usage', {})
                if isinstance(usage, dict):
                    state['usage'] = {k: v for k, v in usage.items() if k in
                        {'input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens'} and type(v) is int and v >= 0}
            elif kind in {'turn.failed', 'error'}:
                raise ValueError('codex_turn_failed_no_retry')
            # Deliberately ignore item/reasoning/tool messages; never serialize the event stream.

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'answer.txt'
            command = self.command + ['exec', '--ignore-user-config', '--skip-git-repo-check', '--json',
                '-s', sandbox, '-C', str(cwd), '-o', str(output),
                '-c', 'forced_login_method="chatgpt"', '-c', 'model_provider="openai"']
            if model:
                command += ['-m', model]
            command += ['resume', session_uuid(session), '-'] if session else ['-']
            code, _ = bounded_process(command, env=self.env(), cwd=cwd, prompt=prompt, timeout=timeout, on_line=event)
            if code or not state['session'] or not state['completed'] or not output.is_file():
                raise ValueError('codex_incomplete_result_no_retry')
            if output.stat().st_size > MAX_ANSWER:
                raise ValueError('answer_size_limit')
            answer = output.read_text('utf-8').strip()
            if not answer:
                raise ValueError('empty_answer')
            return {'session_id': state['session'], 'answer': answer, 'usage': state['usage']}


class Bridge:
    def __init__(self, root=None, client=None):
        self.root = Path(root or os.environ.get('STELLA_CODEX_ROOT') or ROOT).resolve(strict=True)
        self.client = client

    def task_dir(self, task):
        if not isinstance(task, str) or not TASK_RE.fullmatch(task):
            raise ValueError('task_id_required_1_to_64_lowercase_letters_digits_hyphens_underscores')
        path = (self.root / '.bridge/codex/tasks' / task).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('state_path_outside_root')
        return path

    def ask(self, task, prompt, *, cwd=None, sandbox='read-only', model=None, timeout=120, new_session=False):
        folder = self.task_dir(task)
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 32_000:
            raise ValueError('prompt_must_be_1_to_32000_characters')
        if type(timeout) is not int or not 10 <= timeout <= 180:
            raise ValueError('timeout_must_be_10_to_180_seconds')
        if type(new_session) is not bool:
            raise ValueError('new_session_must_be_boolean')
        if sandbox not in ('read-only', 'workspace-write'):
            raise ValueError('invalid_sandbox')
        if model is not None and (not isinstance(model, str) or not MODEL_RE.fullmatch(model)):
            raise ValueError('invalid_model')
        directory = Path(cwd) if cwd else self.root
        directory = (directory if directory.is_absolute() else self.root / directory).resolve(strict=True)
        if not directory.is_dir() or not directory.is_relative_to(self.root):
            raise ValueError('cwd_outside_operator_root')
        fingerprint = {'cwd': directory.relative_to(self.root).as_posix(), 'sandbox': sandbox, 'model': model}
        folder.mkdir(parents=True, exist_ok=True)
        lock = folder / 'turn.lock'
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ValueError('task_busy_or_stale_lock_inspect_manually') from None
        try:
            os.write(descriptor, json.dumps({'pid': os.getpid(), 'created': stamp()}).encode('utf-8'))
        finally:
            os.close(descriptor)
        try:
            state_file = folder / 'state.json'
            state = json.loads(state_file.read_text('utf-8')) if state_file.exists() else {}
            if state.get('status') in {'failed', 'inflight'} and not new_session:
                raise ValueError('previous_turn_incomplete_explicit_new_session_required')
            resume = bool(state.get('session_id')) and not new_session
            if resume and state.get('configuration') != fingerprint:
                raise ValueError('session_configuration_changed_explicit_new_session_required')
            session = session_uuid(state['session_id']) if resume else None
            turn = int(state.get('turn', 0)) + 1
            turn_dir = folder / f'{turn:04d}'
            turn_dir.mkdir(exist_ok=False)
            if state:
                atomic_json(turn_dir / 'previous-state.json', state)
            atomic_json(turn_dir / 'request.json', {'task': task, 'turn': turn, 'prompt': prompt,
                        'configuration': fingerprint, 'resume': resume, 'created': stamp()})
            state = {'schema': 1, 'task': task, 'turn': turn, 'session_id': session, 'status': 'inflight',
                     'configuration': fingerprint, 'updated': stamp()}
            atomic_json(state_file, state)
            try:
                result = (self.client or CodexClient()).ask(prompt, session, directory, sandbox, model, timeout)
                sid = session_uuid(result['session_id'])
                if resume and sid != session:
                    raise ValueError('unexpected_session_id')
                answer = result['answer']
                if not isinstance(answer, str) or not answer.strip() or len(answer.encode('utf-8')) > MAX_ANSWER:
                    raise ValueError('invalid_answer')
                with (turn_dir / 'answer-codex.md').open('x', encoding='utf-8') as stream:
                    stream.write(answer + '\n')
                safe_usage = {k: v for k, v in result.get('usage', {}).items() if k in
                    {'input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens'} and type(v) is int and v >= 0}
                atomic_json(turn_dir / 'result.json', {'status': 'completed', 'usage': safe_usage, 'finished': stamp()})
                state.update(status='completed', session_id=sid, updated=stamp())
                atomic_json(state_file, state)
                return {'status': 'completed', 'task': task, 'turn': turn, 'resumed': resume, 'answer': answer, 'usage': safe_usage}
            except Exception:
                atomic_json(turn_dir / 'result.json', {'status': 'failed', 'error': 'turn_failed_no_retry', 'finished': stamp()})
                state.update(status='failed', updated=stamp())
                atomic_json(state_file, state)
                raise
        finally:
            lock.unlink()

    def history(self, task):
        folder = self.task_dir(task)
        state_file = folder / 'state.json'
        if not state_file.exists():
            return {'task': task, 'status': 'not_started', 'turns': []}
        state = json.loads(state_file.read_text('utf-8'))
        turns = []
        for path in sorted(folder.glob('[0-9][0-9][0-9][0-9]/result.json')):
            result = json.loads(path.read_text('utf-8'))
            turns.append({'turn': int(path.parent.name), 'status': result['status'], 'usage': result.get('usage', {})})
        return {'task': task, 'status': state['status'], 'turns': turns}


TOOLS = [{'name': 'ask_chatgpt', 'description': 'Explicit task-scoped Codex request; same task_id resumes its session.',
    'inputSchema': {'type': 'object', 'properties': {
        'task_id': {'type': 'string'}, 'prompt': {'type': 'string'}, 'cwd': {'type': 'string'},
        'sandbox': {'type': 'string', 'enum': ['read-only', 'workspace-write'], 'default': 'read-only'},
        'model': {'type': 'string'}, 'timeout_sec': {'type': 'integer', 'minimum': 10, 'maximum': 180},
        'new_session': {'type': 'boolean', 'default': False}}, 'required': ['task_id', 'prompt'], 'additionalProperties': False}},
    {'name': 'codex_bridge_status', 'description': 'Check local CLI/account readiness without a model call.',
     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'codex_bridge_history', 'description': 'Read task turn metadata, excluding session IDs and prompt text.',
     'inputSchema': {'type': 'object', 'properties': {'task_id': {'type': 'string'}}, 'required': ['task_id']}}]


def handle(req, bridge=None):
    if not isinstance(req, dict) or req.get('jsonrpc') != '2.0' or not isinstance(req.get('method'), str):
        return {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'invalid request'}}
    if 'id' not in req:
        return None
    rid, method = req['id'], req['method']
    params = req.get('params', {})
    if not isinstance(params, dict):
        return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32602, 'message': 'invalid params'}}
    if method == 'initialize':
        supported = {'2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25'}
        version = params.get('protocolVersion')
        result = {'protocolVersion': version if version in supported else '2025-06-18',
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'codex-chatgpt', 'version': '0.2.0'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': TOOLS}
    elif method == 'tools/call':
        args = params.get('arguments', {})
        name = params.get('name')
        if not isinstance(args, dict):
            return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32602, 'message': 'arguments must be object'}}
        try:
            bridge = bridge or Bridge()
            if name == 'ask_chatgpt':
                data = bridge.ask(args.get('task_id'), args.get('prompt'), cwd=args.get('cwd'),
                    sandbox=args.get('sandbox', 'read-only'), model=args.get('model'),
                    timeout=args.get('timeout_sec', 120), new_session=args.get('new_session', False))
            elif name == 'codex_bridge_status':
                data = CodexClient().checked_status()
            elif name == 'codex_bridge_history':
                data = bridge.history(args.get('task_id'))
            else:
                return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32602, 'message': 'unknown tool'}}
            result = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}], 'isError': False}
        except ValueError as exc:
            # Only controlled identifiers; never return exception paths/raw provider stderr.
            code = str(exc)
            message = code if re.fullmatch('[A-Za-z0-9_]+', code) else 'bridge_request_failed'
            result = {'content': [{'type': 'text', 'text': message}], 'isError': True}
        except Exception:
            result = {'content': [{'type': 'text', 'text': 'bridge_request_failed_no_retry'}], 'isError': True}
    else:
        return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32601, 'message': 'method not found'}}
    return {'jsonrpc': '2.0', 'id': rid, 'result': result}


def main():
    while True:
        raw = sys.stdin.buffer.readline(100_001)
        if not raw:
            break
        if len(raw) > 100_000:
            return 1  # Do not interpret the tail as a second request.
        try:
            response = handle(json.loads(raw))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}}
        if response is not None:
            sys.stdout.buffer.write((json.dumps(response, ensure_ascii=False) + '\n').encode('utf-8'))
            sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
