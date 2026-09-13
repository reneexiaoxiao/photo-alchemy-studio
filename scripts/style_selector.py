#!/usr/bin/env python3
"""List and select available style modules without executing source code."""
import argparse
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parent.parent

def load_styles():
    all_styles=json.loads((ROOT/'catalog.json').read_text())
    local=ROOT/'.local/catalog.json'
    by_id={s['id']:s for s in all_styles}
    if local.exists():
        by_id.update({s['id']:s for s in json.loads(local.read_text()).get('styles',[])})
    return list(by_id.values())

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['list','show','random','recommend']);p.add_argument('--style');p.add_argument('--count',type=int,default=3);p.add_argument('--features',default='');p.add_argument('--seed');args=p.parse_args()
    if not 1<=args.count<=6:p.error('--count must be 1-6')
    styles=load_styles()
    if args.mode=='show':
        out=[s for s in styles if s['id']==args.style]
        if not out:p.error('Unknown style ID')
    elif args.mode=='list':out=styles
    else:
        candidates=[s for s in styles if s.get('installed') and not s.get('manualOnly') and s.get('selection')!='manual-only']
        features={x.strip().lower() for x in args.features.split(',') if x.strip()}
        if {'identity-critical','faithful-photo'} & features:
            candidates=[s for s in candidates if s.get('fidelity')=='high']
        if args.mode=='random':
            random.Random(args.seed).shuffle(candidates)
            out=candidates[:args.count]
        else:
            for s in candidates:
                tags={t.lower() for t in s.get('best',[])}
                s['matched_features']=sorted(features&tags)
            out=sorted(candidates,key=lambda s:-len(s['matched_features']))[:args.count]
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
