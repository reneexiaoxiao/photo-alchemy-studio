"""Shared, inspectable compatibility rules; no image analysis or quality scores."""
ALIASES = {
    '建筑':'architecture','风景':'landscape','街景':'street','街巷':'street','物件':'object','食物':'food','美食':'food','植物':'plant','宠物':'pet','人物':'person',
    'strong-silhouette':'clear-silhouette','clear-shapes':'clear-silhouette','geometric':'strong-geometry','color-blocks':'strong-color','isolated-subject':'single-subject','exact-pixels':'faithful-photo',
}
SUBJECTS = {'architecture','landscape','street','object','food','plant','pet','person'}
FAMILIES = {'minimal-zine':'sparse-paper','muted-zine':'sparse-paper','photo-revival':'small-illustration','pixel-bitmap':'halftone','deconstructed-duotone':'grid-abstraction','morandi-cinematic':'photo-editorial','scene-distillation':'semantic-abstraction','gathered-scenes':'photo-collage','zine-blend':'photo-collage','dual-field-poster':'photo-print','threefold-memory':'sequence','travel-abstraction':'photo-abstraction','photo-relic':'photo-editorial','photo-abstract':'photo-abstraction','visual-memory':'memory-collage','photo-postcard':'postcard','surreal-library':'medium-experiment'}

def normalize(values):
    return {ALIASES.get(str(v).strip().lower(),str(v).strip().lower()) for v in values if str(v).strip()}

def assess(style, features, input_count=None):
    features=normalize(features);contract=style.get('contract') or {};best=normalize(contract.get('bestFeatures',style.get('features',style.get('best',[]))))
    reasons=[]
    avoid=normalize(contract.get('avoidFeatures',[]))
    blocked=features & avoid
    if blocked:reasons.append('与保留要求冲突：'+', '.join(sorted(blocked)))
    if {'identity-critical','faithful-photo'} & features and (style.get('origin')=='original' or style.get('fidelity')!='high') and not blocked:
        reasons.append('这个方法需要重绘，不能满足当前保留要求')
    needs=normalize(contract.get('needsAny',[]))
    if features and needs and not features & needs:reasons.append('尚未观察到所需特征：'+', '.join(sorted(needs)))
    input_range=contract.get('inputCount') or {}
    if input_count is not None and (input_count < input_range.get('min',1) or input_count > input_range.get('max',99)):
        reasons.append('照片数量不符合这个方法的输入条件')
    return {'compatible':not reasons,'matched_features':sorted(features & best),'reasons':reasons}

def family(style):
    return (style.get('contract') or {}).get('family') or FAMILIES.get(style['id'],style.get('family',style['id']))

def diverse_take(candidates,count):
    selected=[];remaining=list(candidates)
    # Ranking order is preserved; only defer repeated visual families.
    while remaining and len(selected)<count:
        seen={family(x) for x in selected}
        idx=next((i for i,x in enumerate(remaining) if family(x) not in seen),0)
        selected.append(remaining.pop(idx))
    return selected
