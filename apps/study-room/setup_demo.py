"""Create missing empty local registries only; never overwrite existing study data."""
import json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent / 'private'
    root.mkdir(exist_ok=True)
    for name in ('sources.json', 'bank.json', 'major-sources.json', 'major-bank.json'):
        path = root / name
        try:
            with path.open('x', encoding='utf-8') as stream:
                json.dump([], stream)
            print('Created empty registry:', name)
        except FileExistsError:
            print('Preserved existing registry:', name)
    print('Ready: the server supplies synthetic demo questions. No course content was imported.')

if __name__ == '__main__':
    main()
