"""Public-input-only RET01 exposure; no weights, gold, or active DB writes."""
import hashlib,json,os,tempfile,time
from pathlib import Path
from dataclasses import replace
from collections import Counter
from transformers import AutoTokenizer
from decision_memory.config import Config
from decision_memory.memory import Memory
from decision_memory.store import Store,iso_date
from decision_memory.chunks import chunk_turns
from decision_memory.evidence import keywords,extract_options
PROJECT=Path('/Users/kacperwarych/Desktop/hackathon reactive ai')
PUBLIC=PROJECT/'salesgen_dataset_fail/public'
SNAPSHOT=PROJECT/'.data/models/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots/97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
start=time.monotonic(); cfg=Config(); tok=AutoTokenizer.from_pretrained(str(SNAPSHOT),local_files_only=True)
histories=[json.loads(l) for l in (PUBLIC/'histories.jsonl').read_text().splitlines() if l.strip()]
questions=[json.loads(l) for l in (PUBLIC/'questions.jsonl').read_text().splitlines() if l.strip()]
counts=Counter(); exposure=[]; byhistory={}; controls=[]; late_structures=[]; checked_controls=set()
with tempfile.TemporaryDirectory(prefix='ret01-public-') as td:
 os.environ['MEMORY_DATA_DIR']=td
 store=Store(Path(td)/'memory.sqlite'); memory=Memory(store,tok,'real-tokenizer-'+SNAPSHOT.name)
 for history in histories:
  sessions=[]
  for source in history['sessions']:
   counts['sessions']+=1; counts['turns']+=len(source['turns'])
   full=''; spans=[]; units=[]
   for turn in source['turns']:
    a=len(full); prefix=f"{turn['role']}: ";full+=prefix+turn['content']+'\n';spans.append((a,len(full),turn))
    for u in memory.records(turn):
     lo=a+len(prefix)+u['start'];hi=a+len(prefix)+u['end']
     units.append({'start':a if u['start']==0 else lo,'end':hi,'turn_index':len(spans)-1,'content_start':u['start']})
   counts['units']+=len(units); affected=False
   for u in units:
    lo,hi=u['start'],u['end'];unitlo,unithi=lo,hi;current=u['turn_index'];n=len(tok.encode(full[lo:hi],add_special_tokens=False))
    u['keywords']=keywords(full[lo:hi]);u['clipped']=False;u['absent']=False
    late_short=current>0 and u['content_start']>0 and n<=cfg.context_tokens;u['late_short']=late_short
    if late_short:counts['short_late_units_with_preceding_turn']+=1
    if current and cfg.context_tokens and n<=cfg.context_tokens:
     a,b,_=spans[current-1];prev=tok(full[a:b],add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
     lo=a if len(prev)<=cfg.context_tokens else a+prev[-cfg.context_tokens][0]
    if current+1<len(spans):
     a,b,_=spans[current+1]
     if len(tok.encode(full[a:b],add_special_tokens=False))<=cfg.context_tokens:hi=b
    a,b,t=next(x for x in spans if x[0]<=lo<x[1]);prefix='' if lo==a else f"{t['role']} (continued): "
    offsets=tok(prefix+full[lo:hi],add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
    if late_short:late_structures.append({'source':hashlib.sha256(source['session_id'].encode()).hexdigest()[:16], 'turn_index':current, 'selected_unit_tokens':n, 'expanded_tokens_before_cap':len(offsets), 'tokens_through_selected_unit_end':len(tok.encode(prefix+full[lo:unithi],add_special_tokens=False))})
    if len(offsets)>cfg.excerpt_tokens:hi=lo+offsets[cfg.excerpt_tokens-1][1]-len(prefix)
    if late_short and hi<unithi:
     counts['late_units_partially_or_fully_clipped']+=1;u['clipped']=True;affected=True
     if hi<=unitlo:counts['late_units_entirely_absent']+=1;u['absent']=True
     exposure.append({'source':hashlib.sha256(source['session_id'].encode()).hexdigest()[:16], 'turn_index':current,'unit_tokens':n,'entirely_absent':u['absent']})
   if affected:counts['sessions_with_clipped_late_unit']+=1
   chunks=[{**c,'session_id':source['session_id'],'date':source['date'],'iso':iso_date(source['date'])} for c in chunk_turns(source['turns'],tok,cfg)]
   counts['chunks']+=len(chunks)
   sessions.append((source,full,units,chunks))
  byhistory[history['history_id']]=sessions
 affected_questions=set();affected_sources=set();affected_turns=set()
 for q in questions:
  query=keywords(q['question']);qt=iso_date(q['question_date'])
  for source,full,units,chunks in byhistory[q['history_id']]:
   if iso_date(source['date'])>qt:continue
   for i,c in enumerate(chunks):
    counts['eligible_question_chunk_pairs']+=1
    eligible=[u for u in units if u['end']>c['start'] and u['start']<c['end']]
    eligible.sort(key=lambda u:(-len(query&u['keywords']),u['start']))
    proposed=eligible[:2];counts['proposed_unit_options_across_question_chunks']+=len(proposed)
    bad=[(n,u) for n,u in enumerate(proposed) if u['clipped']]
    for n,u in enumerate(proposed):
     key=(source['session_id'],u['start'])
     if u['late_short'] and key not in checked_controls:
      checked_controls.add(key)
      opts=extract_options(q,[0],[c],{source['session_id']:source['turns']},tok,cfg,memory)
      noctx=extract_options(q,[0],[c],{source['session_id']:source['turns']},tok,replace(cfg,context_tokens=0),memory)
      original=full[u['start']:u['end']]
      controls.append({'source':hashlib.sha256(source['session_id'].encode()).hexdigest()[:16], 'selected_late_unit_clipped':u['clipped'], 'default_offsets_cover_unit':opts[n]['start']<=u['start'] and opts[n]['end']>=u['end'], 'context0_offsets_cover_unit':noctx[n]['start']<=u['start'] and noctx[n]['end']>=u['end'], 'original_selected_unit_present_default':original in opts[n]['text'], 'original_selected_unit_present_context0':original in noctx[n]['text']})
    if not bad:continue
    counts['question_chunk_pairs_proposing_clipped_late_unit']+=1
    counts['proposed_clipped_late_unit_options']+=len(bad)
    affected_questions.add(q['question_id']);affected_sources.add(source['session_id'])
    for n,u in bad:affected_turns.add((source['session_id'],u['turn_index']))
    if len(controls)<10:
     opts=extract_options(q,[0],[c],{source['session_id']:source['turns']},tok,cfg,memory)
     noctx=extract_options(q,[0],[c],{source['session_id']:source['turns']},tok,replace(cfg,context_tokens=0),memory)
     for n,u in bad:
      original=full[u['start']:u['end']]
      controls.append({'source':hashlib.sha256(source['session_id'].encode()).hexdigest()[:16],
       'default_offsets_cover_unit':opts[n]['start']<=u['start'] and opts[n]['end']>=u['end'], 'context0_offsets_cover_unit':noctx[n]['start']<=u['start'] and noctx[n]['end']>=u['end'], 'original_selected_unit_present_default':original in opts[n]['text'],
       'original_selected_unit_present_context0':original in noctx[n]['text']})
 counts['questions_with_at_least_one_exposed_candidate']=len(affected_questions)
 counts['sources_with_question_proposed_exposure']=len(affected_sources)
 counts['turns_with_question_proposed_exposure']=len(affected_turns)
 store.close()
for key in ['late_units_partially_or_fully_clipped','late_units_entirely_absent','sessions_with_clipped_late_unit','question_chunk_pairs_proposing_clipped_late_unit','proposed_clipped_late_unit_options']:counts.setdefault(key,0)
result={'model_role':'Inherited GPT-6.1 Sol / high; no separate runtime introspection','public_only':True,'gold_read':False,
 'tokenizer_revision':SNAPSHOT.name,'default_excerpt_tokens':cfg.excerpt_tokens,'default_context_tokens':cfg.context_tokens,
 'questions':len(questions),'histories':len(histories),'counts':dict(counts),'structural_exposure_examples':exposure[:10], 'late_unit_structural_candidates':late_structures,
 'real_extract_options_controls':controls,'runtime_seconds':round(time.monotonic()-start,3),
 'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [PUBLIC/'histories.jsonl',PUBLIC/'questions.jsonl']},
 'source_sha256':{n:hashlib.sha256((PROJECT/'src/decision_memory'/n).read_bytes()).hexdigest() for n in ['evidence.py','memory.py','chunks.py','config.py']}}
Path(__file__).with_name('ret01-public-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
