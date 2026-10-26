"""Enrich the frozen source catalog without fetching or modifying original images."""
import json,re,csv,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from bs4 import BeautifulSoup
from import_archive import ROOT,date_key,save,volume_map

def finalize():
 c=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
 s=BeautifulSoup((ROOT/'data/sources/manga.html').read_text(encoding='utf-8'),'html.parser')
 boxes=s.select('li.gallerybox')+s.select('aside')
 sections={}
 for idx,box in enumerate(boxes):
  headings=box.find_all_previous(['h2','h3'])
  heading=next((h for h in headings if not h.find_parent('aside')),None)
  sections[f'manga-{idx:04}']=heading.get_text(' ',strip=True) if heading else ''
 for e in c['entries']:
  if e['chapter'] and e['chapter']['key'].startswith('episode-'):
   n=int(e['chapter']['key'].split('-')[1]);e['chapter']['volume']=volume_map.get(n) if n!=83 else None
  e['sortDate']=date_key(e['date'])
  e['dateBasis']='Data indicata da Frosti; prima pubblicazione o data dell’opera secondo la fonte.'
  e['dateApproximate']=not bool(re.fullmatch(r'[A-Za-z]+ \d{1,2}, \d{4}',e['date']))
  if e['id'] in sections:
   e['sourceSection']=sections[e['id']]
   box=boxes[int(e['id'].split('-')[1])]
   caption=box.select_one('.gallerytext') or box.select_one('.pi-title')
   caption=caption.get_text(' ',strip=True) if caption else ''
   e['description']=(e['sourceSection']+' — '+caption).strip(' —')
 # Link equivalent scans to the dated chronological source before falling back to a collection date.
 dated=defaultdict(list)
 for e in c['entries']:
  if e['id'].startswith('art-') and e['sortDate']:
   for aid in e['assetIds']:dated[aid].append(e)
 collection_dates={'Berserk French Art book':'November 25, 2020','Clean Manga Posters':'November 25, 2020','Berserk Illustration File':'February 28, 1997','Berserk War Cry':'August 25, 1998'}
 for e in c['entries']:
  if e['sortDate'] or not e['id'].startswith('manga-'):continue
  matches=[d for aid in e['assetIds'] for d in dated[aid]]
  if matches:
   best=min(matches,key=lambda d:d['sortDate']);e.update(date=best['date'],sortDate=best['sortDate'],dateApproximate=best['dateApproximate'],dateBasis='Data ricavata dalla stessa immagine nella galleria cronologica.',dateSourceEntry=best['id'])
  elif e.get('sourceSection') in collection_dates:
   e['date']=collection_dates[e['sourceSection']];e['sortDate']=date_key(e['date']);e['dateApproximate']=False;e['dateBasis']='Data di uscita della raccolta indicata nell’infobox di Frosti; data originale dell’opera non determinata.'
  else:e['dateBasis']='Data non documentata nella fonte; nessuna data dedotta dal nome del file o dalla data di upload.'
 # Supplementary galleries remain in the full metadata. The UI suppresses exact duplicate entries.
 seen=set()
 for e in c['entries']:
  ids=set(e['assetIds'])
  e['duplicateInChronologicalGallery']=bool(e['id'].startswith('manga-') and ids and ids.issubset(seen))
  if e['id'].startswith('art-'):seen.update(ids)
 c['mappingSources']=[{'url':'https://www.skullknight.net/encyclopedia/merchandise/manga/index.html','scope':'Indice dei volumi 1–42; numerazione originale REVENGE, inclusi episodi divisi tra più uscite.'},{'url':'https://berserk.fandom.com/wiki/Releases_(Manga)','scope':'Volume 43: episodi 374–382. Episodio 83 escluso dai volumi; oltre 382 non assegnato.'},{'url':'https://www.animeclick.it/manga/9607/berserk/edizioni','scope':'Identificazione dell’edizione italiana Collection, con numerazione dei tankobon; non Maximum né Deluxe.'}]
 c['qualityPolicy']='Original upload URL reconstructed from the exact MediaWiki thumbnail URL by removing /thumb/ and the final thumbnail component; source bytes preserved. All distinct linked variants retained. Sample original-file pages checked. This is the maximum upload available at these gallery URLs, not a claim about unseen scans elsewhere.'
 c['scope']='All file-linked illustrations and source scans from Frosti Berserk Art Gallery and Berserk Gallery, including supplementary infobox art; navigation icons and separate TCG/Tribute galleries excluded.'
 c['dateNotes']=['Dates are reproduced from the gallery; imprecise years, decades and ranges use their first year for sorting, and remain visibly marked as approximate.','The source labels a 1991 magazine preview May 25, 1989; preserved verbatim rather than silently corrected.','Undated supplementary entries use exact shared-image matches or an explicitly documented collection publication date; otherwise they remain undated.']
 byid={e['id']:e for e in c['entries']}
 for a in c['assets'].values():
  a['roles']=sorted(set(o['role'] for o in a['occurrences']))
  a['attribution']=c['attribution']
  a['sources']=[{k:byid[o['entryId']].get(k) for k in ['id','description','date','dateBasis','sourcePage','sourceLinks','chapter']}|{'role':o['role']} for o in a['occurrences']]
  if a['status']=='downloaded':
   p=ROOT/a['path'];p.with_suffix(p.suffix+'.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
 stats=save(c)
 # Lightweight data for the app avoids repeating lengthy sidecar metadata for every variant.
 ui=dict(c);ui['assets']={aid:{k:v for k,v in a.items() if k not in ('sources','attribution','occurrences')}for aid,a in c['assets'].items()}
 (ROOT/'data/catalog.js').write_text('window.BERSERK_ARCHIVE = '+json.dumps(ui,ensure_ascii=False)+';\n',encoding='utf-8')
 with (ROOT/'reports/image-inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['id','status','originalName','path','width','height','bytes','sha256','originalUrl','filePageUrl']);w.writeheader()
  for a in c['assets'].values():w.writerow({k:a.get(k,'') for k in w.fieldnames})
 missing='\n'.join('- '+m['file'] for m in c['missingSourceFiles'])
 failures='\n'.join('- '+a['originalName']+': '+a.get('error','') for a in c['assets'].values() if a['status']=='failed') or 'Nessun errore di download.'
 current={aid for e in c['entries'] if e['section']=='chapters' and e['chapter']['order']<=19 for aid in e['assetIds']}
 text=f'''# Rapporto dell’archivio locale

- Originali distinti individuati: {stats['totalOriginals']}.
- Originali scaricati e validati: {stats['downloaded']}.
- Dimensioni complessive: {stats['bytes']:,} byte ({stats['bytes']/1024**3:.2f} GiB).
- File distinti associati ai capitoli fino a L’età dell’oro 8: {len(current)}.
- Righe di catalogo: {len(c['entries'])}; includono riferimenti ripetuti alla stessa illustrazione.
- Tavole mancanti nella fonte: {len(c['missingSourceFiles'])} riferimenti. Alcune righe conservano altre varianti disponibili.

## Riferimenti mancanti nella galleria originale

{missing}

## Download falliti

{failures}

## Verifica e limiti

Tutti i file scaricati sono immagini decodificabili, con dimensioni, numero di byte e SHA-256 registrati. Nessuna miniatura remota è usata nell’app. Le varianti editoriali sono mantenute; “file” non equivale a “illustrazione unica”. Le date incerte sono dichiarate e i non datati restano in fondo. I crediti puntuali e la provenienza si trovano nel catalogo e nei file JSON accanto alle immagini.

Le gallerie dedicate alle TCG e ai Tribute non fanno parte di questa importazione. Nessuna pubblicazione, sincronizzazione Git o distribuzione esterna effettuata.
'''
 (ROOT/'reports/SUMMARY.md').write_text(text,encoding='utf-8')
 print(json.dumps(stats));print('Current-progress files:',len(current));print('Undated entries:',sum(not e['sortDate'] for e in c['entries']))
if __name__=='__main__':finalize()
