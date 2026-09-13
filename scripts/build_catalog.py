#!/usr/bin/env python3
"""Build browser and agent catalogs from the two maintained registries."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent.parent

def build(check=False):
    entries = json.loads((ROOT/'originals.json').read_text())
    community = ROOT/'community-catalog.json'
    if community.exists():
        entries += json.loads(community.read_text())
    ids = set()
    for item in entries:
        if item['id'] in ids:
            raise ValueError('Duplicate style ID: '+item['id'])
        ids.add(item['id'])
        for key in ('entry','image'):
            if item.get(key):
                path = (ROOT/item[key]).resolve()
                if not path.is_relative_to(ROOT) or not path.is_file():
                    raise ValueError('Missing or unsafe '+key+': '+item[key])
        if item.get('installed') and not item.get('entry'):
            raise ValueError('Installed style has no entry: '+item['id'])
    payload=json.dumps(entries,ensure_ascii=False,indent=2)+'\n'
    outputs={'catalog.json':payload,'catalog.js':'window.PHOTO_ALCHEMY_CATALOG = '+payload.rstrip()+';\n'}
    for name,content in outputs.items():
        path=ROOT/name
        if check:
            if not path.exists() or path.read_text()!=content:
                raise ValueError(name+' is stale; run scripts/build_catalog.py')
        else:
            path.write_text(content,encoding='utf-8')
    print(f'{len(entries)} styles; '+str(sum(bool(s.get('installed')) for s in entries))+' bundled; references checked')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    try:build(args.check)
    except (ValueError,KeyError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)
