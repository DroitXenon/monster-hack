"""Seven repeatable detectors. HUNT labels are used only after prediction."""
from pathlib import Path
import argparse
import hashlib
import json
import unicodedata
from collections import defaultdict
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
NAMES = {'phantom':'Phantom', 'zombie':'Zombie', 'undead':'Undead Student',
         'doppelganger':'Doppelgänger', 'werewolf':'Werewolf',
         'web_crawler':'Web Crawler', 'shapeshifter':'Shape-shifter'}
RULES = {
 'phantom':'Exact duplicate activity fields within either source, excluding its row primary key.',
 'zombie':'Combined LMS/video timestamp chain lasting >3 hours with every consecutive gap <=15 minutes.',
 'undead':'Activity DATE strictly after deregistration calendar date; UK day-first person dates.',
 'doppelganger':'Identical complete nonempty activity histories within LMS or video, excluding person ID and row primary key. Compare all remaining fields and row multiplicity; include every partner.',
 'werewolf':'At least two weekly spikes in each of Autumn and Spring. Spike > median + 3*MAD; when MAD=0 use >95th percentile. Include zero weeks. Exploratory heuristic.',
 'web_crawler':'More than 200 distinct LMS items OR more than 200 distinct videos within an inclusive rolling 12-hour window. Sources evaluated separately.',
 'shapeshifter':'Unique majority department (>50% of distinct registered modules) changes between observed terms. Registration department is a programme proxy, not a confirmed programme change.'}


def zombie_run(times):
    """Input sorted int64 milliseconds; return longest chain bounds and size."""
    if not len(times): return (0, 0, 0, 0)
    starts = np.r_[0, np.flatnonzero(np.diff(times) > 900_000)+1]
    ends = np.r_[starts[1:]-1, len(times)-1]
    durations = times[ends]-times[starts]
    best = int(np.argmax(durations))
    left, right = int(starts[best]), int(ends[best])
    return int(durations[best]), int(times[left]), int(times[right]), right-left+1


def resource_burst(times, resources):
    """First >200 distinct resources in a <=12-hour window; repeated hits count once."""
    counts, left = {}, 0
    for right, resource in enumerate(resources):
        resource = int(resource)
        counts[resource] = counts.get(resource, 0)+1
        while times[right]-times[left] > 43_200_000:
            old = int(resources[left]); counts[old] -= 1
            if not counts[old]: del counts[old]
            left += 1
        if len(counts) > 200:
            return len(counts), int(times[left]), int(times[right])
    return 0, 0, 0


def spike_score(counts):
    counts = np.asarray(counts, dtype=float)
    median = float(np.median(counts))
    mad = float(np.median(np.abs(counts-median)))
    threshold = median+3*mad if mad else float(np.quantile(counts,.95))
    return int((counts > threshold).sum()), threshold


def department_changes(registrations, modules, people):
    merged = registrations.drop_duplicates(['P_ID','MODULE_INSTANCE_ID']).merge(
        modules[['MODULE_INSTANCE_ID','TERM','DEPARTMENT_ID']],on='MODULE_INSTANCE_ID',how='left',validate='many_to_one')
    if merged[['TERM','DEPARTMENT_ID']].isna().any().any():
        raise ValueError('Module registration lacks a term or department mapping.')
    counts = merged.groupby(['P_ID','TERM','DEPARTMENT_ID']).size().rename('modules').reset_index()
    counts['total'] = counts.groupby(['P_ID','TERM']).modules.transform('sum')
    dominant = counts.loc[counts.modules > .5*counts.total].sort_values(['P_ID','TERM'])
    records=[]
    for pid,g in dominant.groupby('P_ID',sort=False):
        departments = g.DEPARTMENT_ID.tolist()
        changes = sum(a!=b for a,b in zip(departments,departments[1:]))
        records.append(dict(P_ID=pid,dominant_terms=len(g),department_changes=changes,
                            term_departments='; '.join(f'{r.TERM}:{r.DEPARTMENT_ID} ({r.modules}/{r.total})' for r in g.itertuples())))
    frame=pd.DataFrame(records,columns=['P_ID','dominant_terms','department_changes','term_departments'])
    out=pd.DataFrame({'P_ID':people}).merge(frame,on='P_ID',how='left')
    out[['dominant_terms','department_changes']]=out[['dominant_terms','department_changes']].fillna(0).astype(int)
    out['is_monster']=out.department_changes.gt(0)
    return out


def label_key(value):
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower()
    return ''.join(c for c in value if c.isalpha())


def evaluation(evidence, name, answers):
    aliases={'undead':{'undead','undeadstudent'},'doppelganger':{'doppleganger','doppelganger'}}
    keys=aliases.get(name,{label_key(NAMES[name])})
    truth=set(answers.loc[answers.Monster.map(label_key).isin(keys),'P_ID'])
    universe=set(evidence.P_ID)
    predicted=set(evidence.loc[evidence.is_monster,'P_ID'])
    tp,fp,fn=len(predicted&truth),len(predicted-truth),len(truth-predicted)
    return dict(labelled=len(truth),labels_absent_from_inputs=sorted(truth-universe),true_positives=tp,false_positives=fp,false_negatives=fn,
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                false_positive_ids=sorted(predicted-truth),false_negative_ids=sorted(truth-predicted))


def run(data_dir, split, output_dir, chunksize=300_000):
    folder=Path(data_dir)/split; prefix=split.lower()
    people=pd.read_csv(folder/f'la_mmh_{prefix}_person_dim.csv',dtype='string')
    if people.P_ID.isna().any() or people.P_ID.duplicated().any(): raise ValueError('Invalid person dimension')
    registered=set(people.P_ID)
    activity_ids=set()
    for kind in ['lms_item_activity_by_session','video_activity_by_view']:
        for chunk in pd.read_csv(folder/f'la_mmh_{prefix}_{kind}_fact.csv',usecols=['P_ID'],dtype='string',chunksize=chunksize):
            activity_ids.update(chunk.P_ID.dropna())
    # Data anomalies may introduce activity IDs missing from the person dimension.
    ids=sorted(registered|activity_ids); index=pd.Index(ids); size=len(ids)
    people=people.set_index('P_ID').reindex(ids).reset_index()
    calendar=pd.read_csv(folder/'la_mmh_calendar_dim.csv',dtype={'DATE':'string'})
    if calendar.DATE.duplicated().any() or calendar.ACADEMIC_YEAR.nunique()!=1: raise ValueError('Expected one unambiguous academic calendar')
    dates=pd.to_datetime(calendar.DATE,errors='raise').to_numpy(dtype='datetime64[D]').astype('int64')
    term_week=calendar[['TERM','WEEK_NUMBER']].drop_duplicates()
    tw_index=pd.MultiIndex.from_frame(term_week)
    calendar_code=pd.Series(tw_index.get_indexer(pd.MultiIndex.from_frame(calendar[['TERM','WEEK_NUMBER']])),index=calendar.DATE)
    weekly=np.zeros((size,len(term_week)),dtype=np.int64)
    dereg=pd.to_datetime(people.deregistration_date,dayfirst=True,format='mixed',errors='raise').to_numpy(dtype='datetime64[D]').astype('int64')
    undead_rows=np.zeros(size,dtype=np.int64)
    first_after=np.full(size,np.iinfo(np.int64).max,dtype=np.int64)
    last_after=np.full(size,np.iinfo(np.int64).min,dtype=np.int64)
    all_events=[]; hash_parts={}; source_paths=[]; audit={}
    for source,kind,resource,row_id in [(0,'lms_item_activity_by_session','LMS_ITEM_ID','PIT_ID'),(1,'video_activity_by_view','VIDEO_ID','PVT_ID')]:
        path=folder/f'la_mmh_{prefix}_{kind}_fact.csv'; source_paths.append((path,row_id))
        resource_map={}; hash_parts[source]=[]
        stats=dict(total=0,unknown_person=0,activity_only_person_rows=0,invalid_timestamp=0,invalid_date=0,missing_resource=0,outside_calendar=0)
        for chunk in pd.read_csv(path,dtype='string',chunksize=chunksize):
            stats['total']+=len(chunk)
            person=index.get_indexer(chunk.P_ID); known=person>=0
            stats['unknown_person']+=int((~known).sum())
            stats['activity_only_person_rows']+=int((~chunk.P_ID.isin(registered)&chunk.P_ID.notna()).sum())
            chunk=chunk.loc[known].reset_index(drop=True); person=person[known]
            # Hashes find possible duplicates. Full fields are rechecked below.
            h=pd.util.hash_pandas_object(chunk.drop(columns=row_id),index=False).to_numpy()
            hash_parts[source].append(pd.DataFrame({'person':person,'hash':h}))
            timestamp=pd.to_datetime(chunk.TIMESTAMP,utc=True,format='mixed',errors='coerce')
            date=pd.to_datetime(chunk.DATE,format='%Y-%m-%d',errors='coerce')
            stats['invalid_timestamp']+=int(timestamp.isna().sum());stats['invalid_date']+=int(date.isna().sum())
            stats['missing_resource']+=int(chunk[resource].isna().sum())
            codes=chunk.DATE.map(calendar_code).fillna(-1).to_numpy(dtype=int)
            valid=codes>=0;stats['outside_calendar']+=int((~valid).sum())
            np.add.at(weekly,(person[valid],codes[valid]),1)
            day=date.to_numpy(dtype='datetime64[D]').astype('int64')
            after=date.notna().to_numpy() & (dereg[person]!=np.iinfo(np.int64).min) & (day>dereg[person])
            np.add.at(undead_rows,person[after],1)
            np.minimum.at(first_after,person[after],day[after]); np.maximum.at(last_after,person[after],day[after])
            for value in chunk[resource].dropna().unique():
                if value not in resource_map: resource_map[value]=len(resource_map)
            resources=chunk[resource].map(resource_map).fillna(-1).to_numpy(dtype=np.int32)
            all_events.append(pd.DataFrame({'person':person.astype(np.int32),'time':timestamp.to_numpy(dtype='datetime64[ms]').astype('int64'),
                                            'date':day,'resource':resources,'source':np.full(len(chunk),source,dtype=np.int8)}))
        audit[kind]=stats
        print(f'{split}: scanned {kind}: {stats["total"]:,} rows',flush=True)
    events=pd.concat(all_events,ignore_index=True);del all_events
    phantom_counts=np.zeros(size,dtype=np.int64)
    for source,(path,row_id) in enumerate(source_paths):
        hashes=pd.concat(hash_parts.pop(source),ignore_index=True)
        candidates=hashes.loc[hashes.duplicated(['person','hash'],keep=False),'person'].unique()
        del hashes
        candidate_ids=set(index[candidates]);pieces=[]
        if candidate_ids:
            for chunk in pd.read_csv(path,dtype='string',chunksize=chunksize):
                pieces.append(chunk.loc[chunk.P_ID.isin(candidate_ids)].drop(columns=row_id))
            full=pd.concat(pieces,ignore_index=True)
            repeats=full.loc[full.duplicated(keep=False)].groupby('P_ID').size()
            phantom_counts[index.get_indexer(repeats.index)]+=repeats.to_numpy()
    results={}
    results['phantom']=pd.DataFrame({'P_ID':ids,'duplicate_group_rows':phantom_counts,'is_monster':phantom_counts>0})
    def date_text(values,valid):
        return [str(np.datetime64(int(v),'D')) if ok else '' for v,ok in zip(values,valid)]
    results['undead']=pd.DataFrame({'P_ID':ids,'deregistration_date':people.deregistration_date,
        'activity_rows_after':undead_rows,'first_activity_after':date_text(first_after,undead_rows>0),
        'last_activity_after':date_text(last_after,undead_rows>0),'is_monster':undead_rows>0})
    # Exact sorted byte representations retain every distinct source/date/resource.
    tokens=events.loc[(events.date!=np.iinfo(np.int64).min)&events.resource.ge(0),['person','date','source','resource']].drop_duplicates().sort_values(['person','date','source','resource'])
    groups=defaultdict(list)
    for (source,person),group in tokens.groupby(['source','person'],sort=False):
        exact=group[['date','source','resource']].to_numpy(dtype='<i8').tobytes()
        groups[(int(source),hashlib.sha256(exact).digest())].append((int(person),exact,len(group)))
    pair_records=[]
    for (source,_),group in groups.items():
        if len(group)<2:continue
        exact_groups=defaultdict(list)
        for person,exact,count in group:exact_groups[exact].append((person,count))
        for matches in exact_groups.values():
            if len(matches)<2:continue
            for person,count in matches:
                pair_records.append({'P_ID':ids[person],'partners':'; '.join(ids[other] for other,_ in matches if other!=person),'source':'LMS' if source==0 else 'Video','distinct_activity_items':count})
    # Coarse signatures only shortlist candidates. Verify the COMPLETE activity
    # multiset (including timestamps, measures, and multiplicity) within a source.
    candidate_ids={row['P_ID'] for row in pair_records}
    pair_records=[]
    for source,(path,row_id) in enumerate(source_paths):
        if not candidate_ids:continue
        pieces=[]
        for chunk in pd.read_csv(path,dtype='string',chunksize=chunksize):
            selected=chunk.loc[chunk.P_ID.isin(candidate_ids)].drop(columns=row_id)
            if not selected.empty:pieces.append(selected)
        if not pieces:continue
        full=pd.concat(pieces,ignore_index=True)
        exact_groups=defaultdict(list)
        for pid,group in full.groupby('P_ID',sort=False):
            # JSON encodes null distinctly from literal strings and retains duplicates.
            rows=[json.dumps([None if pd.isna(v) else str(v) for v in row],separators=(',',':'))
                  for row in group.drop(columns='P_ID').itertuples(index=False,name=None)]
            exact=tuple(sorted(rows))
            exact_groups[exact].append(pid)
        for exact,matches in exact_groups.items():
            if len(matches)<2:continue
            for pid in matches:
                pair_records.append(dict(P_ID=pid,partners='; '.join(other for other in matches if other!=pid),source='LMS' if source==0 else 'Video',matched_activity_rows=len(exact)))
    pairs=pd.DataFrame(pair_records,columns=['P_ID','partners','source','matched_activity_rows'])
    if not pairs.empty:
        pairs=pairs.groupby('P_ID',as_index=False).agg(partners=('partners',lambda x:'; '.join(sorted(set('; '.join(x).split('; '))))),source=('source',lambda x:'; '.join(sorted(set(x)))),matched_activity_rows=('matched_activity_rows','max'))
    results['doppelganger']=pd.DataFrame({'P_ID':ids}).merge(pairs,on='P_ID',how='left')
    results['doppelganger']['is_monster']=results['doppelganger'].partners.notna()
    del tokens,groups
    # Sort once across both sources: sessions may span midnight or source changes.
    ordered=events.loc[events.time!=np.iinfo(np.int64).min].sort_values(['person','time'])
    zombie=[];crawler=[]
    for person,group in ordered.groupby('person',sort=False):
        times=group.time.to_numpy();duration,start,end,count=zombie_run(times)
        zombie.append(dict(P_ID=ids[person],longest_session_hours=duration/3_600_000,
                           session_start=pd.to_datetime(start,unit='ms',utc=True),session_end=pd.to_datetime(end,unit='ms',utc=True),
                           session_rows=count,is_monster=duration>10_800_000))
        for source,part in group.loc[group.resource.ge(0)].groupby('source',sort=False):
            if part.resource.nunique()<=200:continue
            distinct,start,end=resource_burst(part.time.to_numpy(),part.resource.to_numpy())
            if distinct:
                crawler.append(dict(P_ID=ids[person],source='LMS' if source==0 else 'Video',distinct_resources=distinct,
                                    window_start=pd.to_datetime(start,unit='ms',utc=True),window_end=pd.to_datetime(end,unit='ms',utc=True)))
                break
    results['zombie']=pd.DataFrame({'P_ID':ids}).merge(pd.DataFrame(zombie,columns=['P_ID','longest_session_hours','session_start','session_end','session_rows','is_monster']),on='P_ID',how='left')
    results['zombie']['is_monster']=results['zombie'].is_monster.eq(True)
    results['web_crawler']=pd.DataFrame({'P_ID':ids}).merge(pd.DataFrame(crawler,columns=['P_ID','source','distinct_resources','window_start','window_end']),on='P_ID',how='left')
    results['web_crawler']['is_monster']=results['web_crawler'].distinct_resources.gt(200)
    werewolf=[]
    for person in range(size):
        record={'P_ID':ids[person]}
        for term in ['Autumn','Spring']:
            counts=weekly[person,term_week.TERM.eq(term).to_numpy()]
            if not len(counts): raise ValueError(f'Missing {term} calendar weeks')
            spikes,threshold=spike_score(counts)
            record[f'{term.lower()}_spikes']=spikes;record[f'{term.lower()}_threshold']=threshold
        record['is_monster']=record['autumn_spikes']>=2 and record['spring_spikes']>=2
        werewolf.append(record)
    results['werewolf']=pd.DataFrame(werewolf)
    registrations=pd.read_csv(folder/f'la_mmh_{prefix}_person_module_instance_fact.csv',dtype='string')
    modules=pd.read_csv(folder/'la_mmh_module_instance_dim.csv',dtype='string')
    audit['registration_unknown_people']=int((~registrations.P_ID.isin(ids)).sum())
    results['shapeshifter']=department_changes(registrations.loc[registrations.P_ID.isin(ids)],modules,ids)
    # Prediction is complete before training labels are loaded.
    answers=pd.read_csv(ROOT/'HUNT_P_IDs.csv',dtype='string') if split=='Training' else None
    summaries={}
    for name,result in results.items():
        out=Path(output_dir)/name;out.mkdir(parents=True,exist_ok=True)
        result=result.sort_values('P_ID').reset_index(drop=True)
        result.to_csv(out/f'{prefix}_evidence.csv',index=False)
        predictions=result.loc[result.is_monster,['P_ID']].assign(**{'Monster Type':NAMES[name]})[['Monster Type','P_ID']]
        predictions.to_csv(out/f'{prefix}_predictions.csv',index=False)
        summary=dict(split=split,monster=NAMES[name],people=size,registered_people=len(registered),activity_only_people=len(activity_ids-registered),predicted=len(predictions),rule=RULES[name],
                     timezone='UTC',activity_audit=audit,official_test_accuracy='Unknown; TEST 1 labels unavailable')
        if answers is not None:summary['training_evaluation']=evaluation(result,name,answers)
        (out/f'{prefix}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        summaries[name]=summary
        print(f'{name}: {len(predictions)} candidates'+(f'; training TP/FP/FN: {summary["training_evaluation"]["true_positives"]}/{summary["training_evaluation"]["false_positives"]}/{summary["training_evaluation"]["false_negatives"]}' if answers is not None else ''),flush=True)
    return summaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['Training','Test'],default='Test')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'Dataset/Dataset')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    args=parser.parse_args();run(args.data_dir,args.split,args.output_dir)


if __name__=='__main__':main()
