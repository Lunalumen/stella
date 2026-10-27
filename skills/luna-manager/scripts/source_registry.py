"""Fingerprint explicit local sources; report changes without loading text into chat."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import os


def fingerprint(path):
    source = Path(path).resolve(strict=True)
    if not source.is_file():
        raise ValueError(f'Not a file: {source}')
    before = source.stat()
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Source changed while hashing: {source}')
    return {'path': source.as_posix(), 'sha256': digest.hexdigest(), 'bytes': after.st_size}


def load_registry(path):
    if not path.exists():
        return {'version': 1, 'projects': {}}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('version') != 1 or not isinstance(data.get('projects'), dict):
        raise ValueError('Unsupported registry format')
    return data


def save_registry(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temp_name = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temp_name, path)
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()


def duplicate_groups(files):
    groups = {}
    for item in files:
        groups.setdefault(item['sha256'], []).append(item['path'])
    return [paths for paths in groups.values() if len(paths) > 1]


def register(registry, project, paths, refresh=False):
    if project in registry['projects'] and not refresh:
        raise ValueError('Project already registered; check it first. Refresh requires --refresh.')
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise ValueError('Paths must be a nonempty JSON list of file paths')
    files = [fingerprint(p) for p in dict.fromkeys(str(Path(p).resolve()) for p in paths)]
    registry['projects'][project] = {'files': files}
    return {'project': project, 'registered': len(files), 'duplicates': duplicate_groups(files), 'content_reviewed': False}


def check(registry, project):
    if project not in registry['projects']:
        raise ValueError('Project is not registered')
    files = registry['projects'][project]['files']
    changed, missing, errors = [], [], []
    unchanged = 0
    current_files = []
    for item in files:
        try:
            current = fingerprint(item['path'])
            current_files.append(current)
            if current['sha256'] == item['sha256']:
                unchanged += 1
            else:
                changed.append(item['path'])
        except FileNotFoundError:
            missing.append(item['path'])
        except (OSError, ValueError) as error:
            errors.append({'path': item['path'], 'error': str(error)})
    return {'project': project, 'checked': len(files), 'unchanged': unchanged,
            'changed': changed, 'missing': missing, 'errors': errors,
            'duplicates': duplicate_groups(current_files), 'content_reviewed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register', 'check'])
    parser.add_argument('--registry', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--paths-json')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
        path = Path(args.registry)
        registry = load_registry(path)
        if args.action == 'register':
            if not args.paths_json:
                parser.error('register requires --paths-json')
            result = register(registry, args.project,
                              json.loads(Path(args.paths_json).read_text(encoding='utf-8-sig')), args.refresh)
            save_registry(path, registry)
        else:
            if args.refresh or args.paths_json:
                parser.error('check does not accept --refresh or --paths-json')
            result = check(registry, args.project)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if any(result.get(key) for key in ('changed', 'missing', 'errors')) else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
