#!/usr/bin/env python3
"""Build browser and agent catalogs from the two maintained registries."""
from pathlib import Path
import argparse
import json
import sys
from selection_rules import family

ROOT = Path(__file__).resolve().parent.parent

def build(check=False):
    entries = json.loads((ROOT/'originals.json').read_text())
    community = ROOT/'community-catalog.json'
    if community.exists():
        entries += json.loads(community.read_text())
    contracts_path = ROOT/'style-contracts.json'
    contracts = {}
    if contracts_path.exists():
        contracts = {item['id']:item for item in json.loads(contracts_path.read_text())['styles']}
    trials_path = ROOT/'transfer-examples.json'
    trials = {item['id']:item for item in json.loads(trials_path.read_text())} if trials_path.exists() else {}
    for item in entries:
        if item['id'] in contracts:
            item['contract'] = contracts[item['id']]
            item['features'] = item['contract']['bestFeatures']
            item['subjects'] = item['contract'].get('subjects', [])
        if item['id'] in trials:
            item['examples'] = trials[item['id']]['examples']
    previews_path = ROOT/'gallery-previews.json'
    if previews_path.exists():
        previews = json.loads(previews_path.read_text())
        if isinstance(previews, dict):
            previews = previews.get('styles', [])
        by_id = {p['id']:p for p in previews}
        for item in entries:
            preview = by_id.get(item['id'], {})
            for key in ('image', 'imageCaption', 'imageCredit', 'imageSourceUrl', 'imageLicense', 'imageLicenseUrl', 'publicExample', 'credit', 'summary'):
                if preview.get(key):
                    item[key] = preview[key]
    ids = set()
    for item in entries:
        item['family'] = family(item)
        if item['id'] in ids:
            raise ValueError('Duplicate style ID: '+item['id'])
        ids.add(item['id'])
        for key in ('entry','image','sourceImage'):
            if item.get(key):
                path = (ROOT/item[key]).resolve()
                if not path.is_relative_to(ROOT) or not path.is_file():
                    raise ValueError('Missing or unsafe '+key+': '+item[key])
        for example in item.get('examples', []):
            for key in ('image', 'sourceImage'):
                path = (ROOT/example[key]).resolve()
                if not path.is_relative_to(ROOT) or not path.is_file():
                    raise ValueError('Missing or unsafe trial image: '+example[key])
        if item.get('publicExample'):
            for key in ('image', 'sourceImage'):
                value = item['publicExample'].get(key)
                if value:
                    path = (ROOT/value).resolve()
                    if not path.is_relative_to(ROOT) or not path.is_file() or '.local' in path.relative_to(ROOT).parts:
                        raise ValueError('Missing or unsafe public example: '+value)
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
