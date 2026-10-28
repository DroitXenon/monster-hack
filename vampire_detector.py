"""Detect Vampires from distinct UTC night/day activity dates, without labels."""
from pathlib import Path
import argparse
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent


def activity_dates(frame):
    """Night is (00:00, 05:00]; midnight belongs to day on its timestamp date."""
    timestamp = pd.to_datetime(frame.TIMESTAMP, utc=True, errors='coerce', format='mixed')
    valid = timestamp.notna()
    timestamp = timestamp.loc[valid]
    elapsed = timestamp - timestamp.dt.floor('D')
    night = elapsed.gt(pd.Timedelta(0)) & elapsed.le(pd.Timedelta(hours=5))
    return pd.DataFrame({'P_ID': frame.loc[valid, 'P_ID'],
                         'date': timestamp.dt.floor('D'),
                         'period': night.map({True: 'night', False: 'day'})}), int((~valid).sum())


def classify(dates, people):
    counts = dates.drop_duplicates(['P_ID', 'date', 'period']).groupby(['P_ID', 'period']).size().unstack(fill_value=0)
    counts = counts.reindex(index=pd.Index(people, name='P_ID'), columns=['night', 'day'], fill_value=0)
    counts = counts.rename(columns={'night': 'night_active_days', 'day': 'day_active_days'})
    counts['is_vampire'] = (counts.night_active_days > 21) & (counts.night_active_days > counts.day_active_days)
    return counts.reset_index().sort_values('P_ID').reset_index(drop=True)


def detect(data_dir, split, chunksize=300_000):
    folder = Path(data_dir) / split
    people = pd.read_csv(folder / f'la_mmh_{split.lower()}_person_dim.csv', usecols=['P_ID'], dtype='string').P_ID
    if people.isna().any() or people.duplicated().any():
        raise ValueError('Person dimension must have unique non-null P_IDs.')
    parts, audit = [], {}
    for source in ['lms_item_activity_by_session', 'video_activity_by_view']:
        total = unknown = invalid = 0
        for chunk in pd.read_csv(folder / f'la_mmh_{split.lower()}_{source}_fact.csv', usecols=['P_ID', 'TIMESTAMP'], dtype='string', chunksize=chunksize):
            total += len(chunk)
            known = chunk.P_ID.isin(people)
            unknown += int((~known).sum())
            dates, bad = activity_dates(chunk.loc[known])
            invalid += bad
            parts.append(dates.drop_duplicates())
        audit[source] = dict(total=total, unknown_person=unknown, invalid_timestamp_among_known_people=invalid,
                             used=total-unknown-invalid)
    dates = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=['P_ID', 'date', 'period'])
    result = classify(dates, people)
    summary = dict(split=split, people=len(people), predicted_vampires=int(result.is_vampire.sum()),
                   timezone='UTC', night_window='00:00 < time <= 05:00',
                   midnight_policy='Day activity on its UTC calendar date',
                   date_scope='All supplied valid timestamps; no calendar-year filter', activity_rows=audit)
    return result, summary


def evaluate(result, answers_path):
    answers = pd.read_csv(answers_path, dtype='string')
    key = answers.Monster.str.lower().str.replace(r'[^a-z]', '', regex=True)
    truth = set(answers.loc[key.eq('vampire'), 'P_ID'].dropna())
    universe = set(result.P_ID)
    if not truth <= universe:
        raise ValueError('HUNT IDs outside training population')
    predicted = set(result.loc[result.is_vampire, 'P_ID'])
    tp, fp, fn = len(predicted & truth), len(predicted-truth), len(truth-predicted)
    return dict(true_positives=tp, false_positives=fp, false_negatives=fn,
                true_negatives=len(universe-predicted-truth), precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,
                false_positive_ids=sorted(predicted-truth), false_negative_ids=sorted(truth-predicted))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['Training', 'Test'], default='Test')
    parser.add_argument('--data-dir', type=Path, default=ROOT/'Dataset/Dataset')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'outputs/vampire')
    args = parser.parse_args()
    result, summary = detect(args.data_dir, args.split)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.split.lower()
    result.to_csv(args.output_dir/f'{stem}_evidence.csv', index=False)
    predictions = result.loc[result.is_vampire, ['P_ID']].assign(**{'Monster Type': 'Vampire'})[['Monster Type', 'P_ID']]
    predictions.to_csv(args.output_dir/f'{stem}_predictions.csv', index=False)
    if args.split == 'Training':
        summary['training_evaluation'] = evaluate(result, ROOT/'HUNT_P_IDs.csv')
    else:
        summary['official_accuracy'] = 'Unknown: TEST 1 labels unavailable.'
    (args.output_dir/f'{stem}_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
