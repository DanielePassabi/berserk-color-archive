"""Build a compact, self-contained offline website; preserve archival originals."""
from pathlib import Path
import json,re,hashlib,shutil,sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image,ImageOps
from import_archive import ROOT,volume_map
VERSION=3

def score(a,e):
 n=a['originalName'].lower();roles={o['role'] for o in a.get('occurrences',[]) if o['entryId']==e['id']}
 points=100 if 'artwork' in roles else 0
 # JP_BSK are flat digital page scans; source magazine images often show paper/folds.
 if n.startswith('jp_bsk_'):points+=1000
 if 'clean' in n:points+=700
 if 'artwork_of_berserk' in n:points+=350
 if 'illus_file' in n:points+=250
 if 'yaremix' in n:points+=180
 if re.search(r'photo|camera|dsc\d|img_\d',n):points-=500
 return (points,min(a.get('width',0)*a.get('height',0),100_000_000))

def encode(winner,e):
  aid=winner['id']
  folder='chapters/volume-'+str(e['chapter']['volume'] or 'unassigned').zfill(2)+'/'+e['chapter']['key'] if e['section']=='chapters' else 'extras/'+(e.get('sortDate') or 'undated')[:4]
  stem=Path(winner['path']).stem
  path=f'assets/images/{folder}/{stem}.webp';dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True)
  cache=dest.with_suffix('.webp.json')
  cacheok=False
  if dest.exists() and cache.exists():
   prev=json.loads(cache.read_text(encoding='utf-8'));cacheok=prev.get('sourceSha256')==winner.get('sha256') and prev.get('version')==VERSION
  if not cacheok:
   with Image.open(ROOT/winner['path']) as source:
    icc=source.info.get('icc_profile');im=ImageOps.exif_transpose(source)
    if im.mode not in ('RGB','RGBA'):im=im.convert('RGBA' if 'transparency' in source.info else 'RGB')
    # Web copies use up to 3200 pixels; the archival source remains untouched.
    if max(im.size)>3200:im.thumbnail((3200,3200),Image.Resampling.LANCZOS)
    kwargs={'format':'WEBP','quality':88,'method':3}
    if icc:kwargs['icc_profile']=icc
    im.save(dest,**kwargs)
   cache.write_text(json.dumps({'version':VERSION,'sourceSha256':winner.get('sha256')}),encoding='utf-8')
  with Image.open(dest) as im:w,h=im.size
  return {'id':aid,'originalName':winner['originalName'],'path':path,'status':'downloaded','width':w,'height':h,'format':'WebP','bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'filePageUrl':winner['filePageUrl'],'originalUrl':winner['originalUrl'],'originalWidth':winner.get('width'),'originalHeight':winner.get('height'),'originalBytes':winner.get('bytes'),'originalSha256':winner.get('sha256'),'encoding':'WebP qualità 88, lato lungo massimo 3200 px; originale in piena risoluzione conservato in archivio privato.'}

def build():
 c=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
 selected={};entries=[];seen={};audit=[];pool=ThreadPoolExecutor(max_workers=4);jobs={}
 cover_groups=defaultdict(list)
 cover_pattern=re.compile(r'^BSK_Vol\._(\d+)(?:_(?:Clean|\(JP\)|Raw|Full_Canvas))?\.(?:png|jpg|jpeg)$',re.I)
 for a in c['assets'].values():
  match=cover_pattern.fullmatch(a['originalName'])
  if match and a['status']=='downloaded':cover_groups[match.group(1)].append(a)
 # Chapters take precedence when the same image is also in an artbook or extras.
 ordered=sorted(c['entries'],key=lambda e:(e['section']!='chapters',e.get('sortDate') or '9999',e['id']))
 for raw in ordered:
  e=dict(raw)
  if e.get('duplicateInChronologicalGallery'):continue
  candidates=[c['assets'][aid] for aid in e['assetIds'] if c['assets'][aid]['status']=='downloaded']
  if not candidates:
   e['assetIds']=[];entries.append(e);continue
  winner=max(candidates,key=lambda a:score(a,e))
  match=cover_pattern.fullmatch(winner['originalName'])
  if e['section']!='chapters' and match:
   candidates=cover_groups[match.group(1)]
   winner=max(candidates,key=lambda a:score(a,e))
   e['assetIds']=list(dict.fromkeys(e['assetIds']+[a['id'] for a in candidates]))
  alternate_ids=list(e['assetIds']);aid=winner['id']
  scope=e['chapter']['key'] if e['section']=='chapters' else 'extra'
  # Any image already shown in a chapter also stays out of the supplementary gallery.
  duplicate=seen.get(aid)
  if duplicate and (scope=='extra' or duplicate.get('chapter',{} ) and duplicate.get('chapter') and duplicate['chapter']['key']==scope):
   duplicate.setdefault('relatedSources',[]).append({k:e.get(k) for k in ('id','description','date','sourcePage')})
   continue
  e['assetIds']=[aid];e['selectionReason']='Una versione per voce Frosti: priorità alle scansioni JP_BSK, poi alle versioni Clean, agli artbook e alle altre scansioni; a parità di tipo, maggiore risoluzione.'
  e['alternativeVersions']=[{k:c['assets'][other].get(k) for k in ['id','originalName','filePageUrl','originalUrl','width','height']} for other in alternate_ids if other!=aid]
  entries.append(e);seen.setdefault(aid,e)
  audit.append({'entryId':e['id'],'primary':winner['originalName'],'alternatives':len(e['alternativeVersions']),'ruleScore':score(winner,e)[0]})
  if aid in selected:continue
  selected[aid]=None
  jobs[pool.submit(encode,winner,e)]=aid
 for number,future in enumerate(as_completed(jobs),1):
  selected[jobs[future]]=future.result()
  if number%50==0:print('OPTIMIZED',number,len(jobs),flush=True)
 pool.shutdown()
 ui={k:v for k,v in c.items() if k not in ('assets','entries')};ui.update(defaultProgress=0,progressLabel='Non ho ancora iniziato',assets=selected,entries=entries)
 ui['progressChapters']=[{'key':f'episode-{n:03}','order':n+19,'volume':volume_map.get(n),'label':f'Episodio {n:03}'} for n in range(1,387)]
 ui['packageInfo']={'originalArchiveFiles':len(c['assets']),'originalArchiveBytes':sum(a.get('bytes',0) for a in c['assets'].values()),'imageCount':len(selected),'imageBytes':sum(a['bytes'] for a in selected.values()),'selectionRulesVersion':VERSION}
 (ROOT/'data/site-catalog.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'data/site-catalog.js').write_text('window.BERSERK_ARCHIVE = '+json.dumps(ui,ensure_ascii=False)+';\n',encoding='utf-8')
 dist=ROOT/'dist';dist.mkdir(exist_ok=True)
 for f in ['index.html','styles.css','model.js','app.js','README.md']:
  shutil.copy2(ROOT/f,dist/f)
 (dist/'README.md').write_text('''# Berserk Color Archive — sito locale

Apri `index.html` in un browser. Non serve connessione: tutte le immagini visualizzate sono incluse nel pacchetto.

Il segnalibro iniziale è **Non ho ancora iniziato**. Ogni lettore può aggiornarlo sul proprio browser. Le immagini restano nascoste fino all’apertura esplicita; i materiali successivi al segnalibro richiedono un avviso spoiler. Il viewer naviga solo nello stesso capitolo, anche con le frecce della tastiera; Esc lo chiude.

Una versione principale per tavola, selezionata dalle gallerie di Fr0stiFusionZ, privilegiando scansioni pulite. Copie WebP di qualità 88, lato lungo massimo 3200 px. Gli originali e le versioni alternative sono raggiungibili tramite i link espliciti alle fonti. Gli originali master non fanno parte di questo pacchetto e restano nell’archivio privato del progetto.

Attribuzione: Kentaro Miura / Hakusensha; Studio Gaga e Kouji Mori per la continuazione, altri autori e staff secondo le fonti. Curatela Fr0stiFusionZ / @Frosti811. Diritti dei rispettivi titolari, nessuna licenza di redistribuzione implicita.

Fonti: https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Art_Gallery e https://jojowiki.com/User:Fr0stiFusionZ/Berserk_Gallery. Catalogo e provenienza in `data/site-catalog.json`; dimensioni in `reports/site-package.json`; riferimenti mancanti in `reports/download-report.json`. Nessuna pubblicazione effettuata.
''',encoding='utf-8')
 (dist/'data').mkdir(exist_ok=True);(dist/'reports').mkdir(exist_ok=True)
 shutil.copy2(ROOT/'data/site-catalog.js',dist/'data/site-catalog.js');shutil.copy2(ROOT/'data/site-catalog.json',dist/'data/site-catalog.json')
 for f in ['download-report.json','SUMMARY.md']:
  if (ROOT/'reports'/f).exists():shutil.copy2(ROOT/'reports'/f,dist/'reports'/f)
 for a in selected.values():
  dest=dist/a['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/a['path'],dest)
 (ROOT/'reports/selection-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
 expected={(dist/a['path']).resolve() for a in selected.values()}
 image_root=(dist/'assets/images').resolve()
 if image_root.exists():
  for old in image_root.rglob('*'):
   if old.is_file() and old.resolve().is_relative_to(image_root) and old.resolve() not in expected:old.unlink()
 total=sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
 report=ui['packageInfo']|{'packageBytes':total,'underOneGB':total<1_000_000_000,'entries':len(entries),'exportDirectory':'dist'}
 (ROOT/'reports/site-package.json').write_text(json.dumps(report,indent=2),encoding='utf-8');shutil.copy2(ROOT/'reports/site-package.json',dist/'reports/site-package.json')
 print('PACKAGE',json.dumps(report),flush=True)
 if total>=1_000_000_000:raise SystemExit('Package exceeds 1 GB; adjust encoding before delivery.')
if __name__=='__main__':build()
