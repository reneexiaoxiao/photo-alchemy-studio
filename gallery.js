'use strict';
const $ = id => document.getElementById(id);
const baseStyles = window.PHOTO_ALCHEMY_CATALOG || [];
let styles = [...baseStyles], filter = 'all', chosen = null, connected = false;
let toastTimer;
let direction='all', subject='all', preservation='all';
const featureLabels={'landscape':'风景','architecture':'建筑','street':'街景','object':'物件','food':'美食','plant':'植物','pet':'宠物','person':'人物','identity-critical':'保留人物身份','faithful-photo':'保留原照','text-in-source':'含原文文字','product-geometry':'保留物件形状','strong-geometry':'结构鲜明','layered-depth':'层次丰富','clear-silhouette':'轮廓清晰','motion':'动态','negative-space':'留白','busy-scene':'丰富场景','strong-color':'鲜明色彩','muted-color':'低饱和','low-light':'暗光','nostalgic':'怀旧','poetic':'诗意','editorial':'刊物感','cinematic':'电影感','abstract-friendly':'可抽象','playful':'活泼','collectible':'纪念物','social-cover':'分享封面','printable':'打印'};
function textNode(tag, text, className) { const el=document.createElement(tag); el.textContent=text; if(className) el.className=className; return el; }
function button(text, fn, cls='') { const el=textNode('button',text,cls); el.type='button'; el.addEventListener('click',fn); return el; }
function safeLink(href) { try { const u=new URL(href,location.href); return u.protocol==='https:' && u.hostname==='github.com' ? u.href : null; } catch {return null;} }
function link(text, href) { const el=textNode('a',text); const safe=safeLink(href); if(safe){el.href=safe;el.target='_blank';el.rel='noopener noreferrer';} return el; }
function notice(text) { $('toast').textContent=text; $('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').hidden=true;},3000); }
async function copy(text) {try {await navigator.clipboard.writeText(text);notice('指令已复制');} catch { $('copy-text').value=text;$('copy-dialog').showModal();$('copy-text').focus();$('copy-text').select(); } }
function promptFor(s) {
  const extra=s.manualOnly?'只手动使用这个风格，只生成一张，保留原来源的调用约定。':'';
  const source=s.origin!=='original'&&s.entry?`读取风格入口 ${s.entry}。`:'';
  return `用 $photo-alchemy 的 ${s.id} 处理我附上的照片。${source}先读取这套风格的固定规则，再按实际照片的主体、形态、光影和密度选择构图分支。保留辨识线索、关键数量与关系；配色来自原照，不照搬图鉴的对象、地点或版式。用 ${s.label} 加工为适合分享的作品。未提供的地点、日期和文字不要编造。${extra}`;
}
function showImage(s) {
 const variants=s.examples?.length ? s.examples : [{label:'图鉴参考',image:s.image,sourceImage:s.sourceImage,caption:s.imageCaption}];
 $('viewer-title').textContent=s.label+' · 看效果与适配';
 $('viewer-credit').textContent=s.origin==='original'?'工作流设计：Renee · AI 辅助':s.imageCredit||s.credit||s.source;
 $('example-tabs').replaceChildren();$('example-tabs').hidden=variants.length<2;
 function selectExample(index){
  const v=variants[index],hasSource=Boolean(v.sourceImage);$('source-figure').hidden=!hasSource;$('compare').classList.toggle('single',!hasSource);
  if(hasSource)$('compare-source').src=v.sourceImage;
  $('compare-art').src=v.image;$('compare-art').alt=s.label+' · '+v.label;
  $('compare-label').textContent=({'UPSTREAM EXAMPLE':'作者公开参考图','LOCAL IMAGEGEN SAMPLE':'本地生成参考图'}[v.caption]||v.caption||'社区参考图')+(v.note?' · '+v.note:'');
  [...$('example-tabs').children].forEach((el,i)=>el.setAttribute('aria-pressed',String(i===index)));
 }
 variants.forEach((v,i)=>{$('example-tabs').append(button(v.label,()=>selectExample(i)));});
 $('style-rules').hidden=!s.contract;$('style-signature').replaceChildren();
 if(s.contract){for(const rule of s.contract.signature||[])$('style-signature').append(textNode('li',rule));$('style-adaptation').textContent='随照片变化：'+s.contract.adaptation;$('style-boundary').textContent='更适合：'+s.contract.useWhen+'　慎用：'+s.contract.avoidWhen;}
 selectExample(0);$('viewer').showModal();
}
function subjectsFor(s){const aliases={'建筑':'architecture','风景':'landscape','街景':'street','街巷':'street','物件':'object','食物':'food','美食':'food','植物':'plant','宠物':'pet','人物':'person'};return s.subjects?.length?s.subjects:(s.best||[]).map(x=>aliases[x]||x);}
function visualFamily(s){return s.contract?.family||baseStyles.find(b=>b.id===s.id)?.family||s.family||s.id;}
function resetPhotoFilters(){direction='all';subject='all';preservation='all';for(const id of ['direction','subject','preservation'])$(id).value='all';}
function matches(s) { const query=$('search').value.trim().toLowerCase(); return (!query || [s.id,s.label,s.summary,s.source,...(s.best||[]),...(s.destinations||[])].join(' ').toLowerCase().includes(query)) && (filter==='all'||(filter==='installed'?s.installed:s.origin===filter)) && (direction==='all'||s.direction===direction) && (subject==='all'||subjectsFor(s).includes(subject)) && (preservation!=='keep'||(s.origin!=='original'&&s.fidelity==='high')) && (preservation!=='redraw'||s.origin==='original'||s.fidelity!=='high') && (!chosen||chosen.has(s.id)); }
function render() {
 $('grid').replaceChildren();$('source-list').replaceChildren();const visible=styles.filter(matches).sort((a,b)=>(a.origin==='original')-(b.origin==='original'));
 $('count').textContent=`${visible.length} / ${styles.length} 种风格`;$('empty').hidden=visible.length>0;
 for(const s of visible){
  const card=document.createElement('article');card.className=s.image?'card':'source-row';card.dataset.id=s.id;
  if(s.image){const art=button('',()=>showImage(s),'art-button');const img=document.createElement('img');img.src=s.image;img.alt=s.label+'演示样张';img.loading='lazy';art.append(img,textNode('span',s.origin==='original'?'Renee 原创':'社区参考','image-label'),textNode('span',s.examples?.length?`${s.examples.length} 类输入对照 ↗`:s.sourceImage?'原图对照 ↗':'查看大图 ↗','image-action'));card.append(art);}
  const body=document.createElement('div');body.className=s.image?'card-body':'';
  const meta=textNode('div','','meta');meta.append(textNode('span',s.manualOnly?'仅手动点选':s.origin==='original'?'Renee · 原创工作流':'社区来源'),textNode('span',s.license||'许可待核实'));
  body.append(meta,textNode('h3',s.label),textNode('div',s.id,'style-id'),textNode('p',s.summary||s.description||'', 'desc'));
  if(s.image)body.append(textNode('p',({'UPSTREAM EXAMPLE':'作者公开参考图','LOCAL IMAGEGEN SAMPLE':'本地生成参考图'}[s.imageCaption]||s.imageCaption||'社区原有参考图'),'sample-caption'));
  if(s.contract)body.append(textNode('p',s.contract.useWhen,'fit-line'));
  if(s.best?.length)body.append(textNode('p',s.best.map(x=>featureLabels[x]||x).join(' · '),'tags'));
  const actions=document.createElement('div');actions.className='card-actions';
  if(s.installed) actions.append(button('复制使用指令',()=>copy(promptFor(s))));
  else actions.append(button('查找并添加',()=>{ $('skill-query').value=s.sourceUrl||s.source;$('add').scrollIntoView();if(connected)findSources();else notice('可启动本地服务，或复制添加请求');}));
  if(safeLink(s.sourceUrl||'')) actions.append(link(s.installed?'查看来源 ↗':'来源链接 ↗',s.sourceUrl)); else actions.append(textNode('span','来源待核实','style-id'));body.append(actions);card.append(body);(s.image?$('grid'):$('source-list')).append(card);
 }
 $('recommendations').hidden=!$('source-list').children.length;
}
async function api(path, data) {const options={headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(65000)};if(data!==undefined){options.method='POST';options.body=JSON.stringify(data);}const r=await fetch('/api/'+path,options);let x;try{x=await r.json();}catch{throw new Error('本地服务未返回有效结果，请重新打开本地入口。');}if(!r.ok)throw new Error(x.error?.message||x.error||x.message||`请求失败（${r.status}）`);return x;}
function setImport(text){$('import-status').textContent=text;}
async function refreshCatalog(){const x=await api('catalog');const map=new Map(baseStyles.map(s=>[s.id,s]));for(const s of x.styles||[])map.set(s.id,{...(map.get(s.id)||{}),...s});styles=[...map.values()];render();}
async function connect(){if(!['127.0.0.1','localhost'].includes(location.hostname)){offline();return;}try{const x=await api('status');connected=!!x.connected;if(!connected)throw new Error('offline');$('connection').textContent='本地扩充已连接 · 选择来源后即可安装';$('edition').textContent='本地完整图鉴';$('find').disabled=false;$('check-updates').disabled=false;await refreshCatalog();}catch{offline();}}
function offline(){connected=false;$('edition').textContent=window.PHOTO_ALCHEMY_PERSONAL?'本地完整图鉴 · 离线':'公开图鉴';$('connection').textContent=window.PHOTO_ALCHEMY_PERSONAL?'个人图鉴已就绪 · 启动本地入口可添加风格':'当前为浏览版 · 启动本地入口后可安装风格';$('find').disabled=true;$('check-updates').disabled=true;}
async function findSources(){if(!connected)return;const query=$('skill-query').value.trim();if(!query){$('skill-query').reportValidity();return;}$('find').disabled=true;$('candidates').replaceChildren();$('inspection').replaceChildren();setImport('正在查找 GitHub 来源…');try{const x=await api('search',{query});const list=x.candidates||[];setImport(list.length?`找到 ${list.length} 个来源。选择一个查看内容与许可。`:'没有找到匹配的来源，请换用完整 GitHub 链接。');for(const c of list){const item=document.createElement('div');item.className='candidate';item.append(textNode('h3',c.repo),textNode('p',c.description||'暂无来源说明'),link('打开仓库 ↗',c.url),document.createTextNode('　'),button('查看许可与内容',()=>inspect(c.repo)));$('candidates').append(item);}if(x.warnings?.length)setImport($('import-status').textContent+'\n'+x.warnings.join('\n'));}catch(e){setImport('查找失败：'+e.message);}finally{$('find').disabled=false;}}
async function inspect(repo){$('inspection').replaceChildren();setImport('正在读取来源与许可…');try{const x=await api('inspect',{repo});const head=textNode('div','','inspect-meta');head.append(textNode('h3',x.repo),textNode('p',`许可：${x.license||'未明确'} · 版本：${(x.commit||'').slice(0,8)}`),link('核对许可原文 ↗',x.licenseUrl||''));$('inspection').append(head);if(x.reason)head.append(textNode('p',x.reason));for(const s of x.skills||[]){const box=textNode('div','','inspection-item');box.append(textNode('h3',s.name||s.path),textNode('p',s.description||s.path));const can=x.installable && s.installable!==false;if(can){const installButton=button('安装并加入风格库',()=>install(x,s,installButton));box.append(installButton);}else box.append(textNode('p',s.reason||x.reason||'此来源尚不能自动安装，可复制给 Codex 继续核实。'));$('inspection').append(box);}setImport(x.installable?'来源已核对；安装后保留作者署名和原许可证。':'此来源未满足自动安装条件。');if(x.warnings?.length)$('inspection').append(textNode('p',x.warnings.join(' · '),'inspect-meta'));}catch(e){setImport('读取失败：'+e.message);}}
async function install(x,s,control){control.disabled=true;setImport('正在安装并核对文件…');try{const result=await api('install',{repo:x.repo,commit:x.commit,path:s.path});if(!result.installed)throw new Error('未返回安装完成状态');await refreshCatalog();setImport(result.alreadyInstalled?'这个版本已在风格库中。':`已安装 ${result.style?.label||s.name}，并加入风格库。`);control.textContent='已加入风格库';if(result.warnings?.length)setImport($('import-status').textContent+' '+result.warnings.join(' · '));}catch(e){setImport('安装未完成：'+e.message);control.disabled=false;}}
$('find-form').addEventListener('submit',e=>{e.preventDefault();findSources();});
$('copy-request').addEventListener('click',()=>{const q=$('skill-query').value.trim();if(!q){$('skill-query').reportValidity();return;}copy(`请为我的 Photo Alchemy 风格库添加这个 Skill：${q}。先搜索 GitHub 等公开来源，核对准确仓库、许可证、完整指令和依赖，再固定版本安装到本地扩充目录并更新风格目录；有重名时列出候选给我选择。不要执行来源里的无关安装脚本或索取凭据。缺少再分发授权的内容只保留本地来源，不纳入公开仓库。完成后回读入口、文件和目录状态，并说明作者与是否本项目原创。`);});
$('check-updates').addEventListener('click',async()=>{const b=$('check-updates');b.disabled=true;$('updates').replaceChildren();setImport('正在检查已安装来源的新版本…');try{const x=await api('check-updates',{});const entries=x.updates||[];if(!entries.length){setImport('还没有通过本地入口安装的社区风格。');return;}setImport('检查完成。新版本需重新查看来源后安装。');for(const u of entries){const row=textNode('div','','candidate');row.append(textNode('p',`${u.repo} · ${u.error?'检查失败：'+u.error:u.updateAvailable?'有新版本':'已是当前版本'}`));if(u.updateAvailable)row.append(button('查看新版本',()=>inspect(u.repo)));$('updates').append(row);}}catch(e){setImport('更新检查失败：'+e.message);}finally{b.disabled=false;}});
$('search').addEventListener('input',()=>{chosen=null;$('selection').hidden=true;render();});document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;chosen=null;$('selection').hidden=true;document.querySelectorAll('[data-filter]').forEach(el=>el.setAttribute('aria-pressed',String(el===b)));render();}));
for(const id of ['direction','subject','preservation'])$(id).addEventListener('change',()=>{direction=$('direction').value;subject=$('subject').value;preservation=$('preservation').value;chosen=null;$('selection').hidden=true;render();});
$('clear').addEventListener('click',()=>{resetPhotoFilters();$('search').value='';chosen=null;filter='all';$('selection').hidden=true;document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter==='all')));render();});
$('random').addEventListener('click',()=>{chosen=null;const pool=styles.filter(s=>s.installed&&!s.manualOnly&&matches(s));for(let i=pool.length-1;i>0;i--){const j=crypto.getRandomValues(new Uint32Array(1))[0]%(i+1);[pool[i],pool[j]]=[pool[j],pool[i]];}const sample=[],seen=new Set();while(pool.length&&sample.length<3){let i=pool.findIndex(s=>!seen.has(visualFamily(s)));if(i<0)i=0;const s=pool.splice(i,1)[0];sample.push(s);seen.add(visualFamily(s));}chosen=new Set(sample.map(s=>s.id));$('selection').textContent=sample.length?'从当前范围抽取：'+sample.map(s=>s.label).join(' / '):'当前范围没有可随机使用的风格。';$('selection').hidden=false;render();$('collection').scrollIntoView();});
$('auto').addEventListener('click',()=>copy('用 $photo-alchemy 看我附上的旅行照，先识别主体、轮廓、光影、密度和保留要求，再推荐三种兼容且视觉方法不同的风格；每种说明抓取照片的哪条线索、怎样重组，以及是否需要重绘。缺少光影或多图条件时不要硬套对应方法，排除只换颜色的近似选项。先给选择，不生成图片；排除仅允许手动点选的来源。'));
$('close-viewer').addEventListener('click',()=>$('viewer').close());$('close-copy').addEventListener('click',()=>$('copy-dialog').close());for(const d of [$('viewer'),$('copy-dialog')])d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});
render();connect();
