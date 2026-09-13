#!/usr/bin/env python3
"""Choose compatible, visibly different workflows from observed photo features."""
import argparse
import json
from pathlib import Path
import random
from selection_rules import assess, diverse_take, normalize

ROOT=Path(__file__).resolve().parent.parent

def load_styles():
    by_id={s['id']:s for s in json.loads((ROOT/'catalog.json').read_text())}
    for name in ('legacy-catalog.json','catalog.json'):
        local=ROOT/'.local'/name
        if local.exists():
            for s in json.loads(local.read_text()).get('styles',[]):by_id[s['id']]={**by_id.get(s['id'],{}),**s}
    return list(by_id.values())

def select(styles,mode,features,count,input_count=None,seed=None):
    candidates=[]
    for source in styles:
        if not source.get('installed') or source.get('manualOnly') or source.get('selection')=='manual-only':continue
        result=assess(source,features,input_count)
        if not result['compatible']:continue
        style={**source,**result}
        if features and not style['matched_features']:continue
        candidates.append(style)
    if mode=='random':random.Random(seed).shuffle(candidates)
    else:candidates.sort(key=lambda s:-len(s['matched_features']))
    return diverse_take(candidates,count)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['list','show','random','recommend']);p.add_argument('--style');p.add_argument('--count',type=int,default=3);p.add_argument('--features',default='');p.add_argument('--input-count',type=int);p.add_argument('--seed');args=p.parse_args()
    if not 1<=args.count<=6:p.error('--count must be 1-6')
    if args.input_count is not None and args.input_count<1:p.error('--input-count must be positive')
    styles=load_styles()
    if args.mode=='show':
        sid='jiuerli-sketch' if args.style=='jiuerli-visual-director' else args.style
        out=[s for s in styles if s['id']==sid]
        if not out:p.error('Unknown style ID')
    elif args.mode=='list':out=styles
    else:out=select(styles,args.mode,normalize(args.features.split(',')),args.count,args.input_count,args.seed)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
