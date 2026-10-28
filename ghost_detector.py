"""Repeatable Ghost detector. Labels are used only for training evaluation."""
from pathlib import Path
import argparse
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent


def classify(weekly, early_weeks, later_weeks):
    """Count every calendar week, including weeks with zero activity."""
    early = weekly.reindex(columns=early_weeks, fill_value=0)
    later = weekly.reindex(columns=later_weeks, fill_value=0)
    result = pd.DataFrame(index=weekly.index)
    result['early_active_weeks'] = early.gt(0).sum(axis=1)
    result['early_average'] = early.mean(axis=1)
    result['later_average'] = later.mean(axis=1)
    result['later_to_early_ratio'] = result.later_average.div(result.early_average.where(result.early_average.gt(0)))
    result['is_ghost'] = (result.early_active_weeks >= 3) & (result.later_average < 0.1 * result.early_average)
    return result.reset_index()


def detect(data_dir, split, chunksize=300_000):
    folder = Path(data_dir) / split
    prefix = split.lower()
    calendar = pd.read_csv(folder / 'la_mmh_calendar_dim.csv')
    if calendar.ACADEMIC_YEAR.nunique() != 1:
        raise ValueError('Expected one academic year; choose the target year explicitly.')
    if calendar.DATE.duplicated().any():
        raise ValueError('Calendar dates must be unique.')
    autumn = calendar.loc[calendar.TERM.str.lower().eq('autumn')]
    early_weeks = sorted(autumn.WEEK_NUMBER.unique())[:4]
    if len(early_weeks) != 4:
        raise ValueError('Four Autumn weeks required.')
    later_weeks = sorted(calendar.loc[calendar.WEEK_NUMBER.gt(max(early_weeks)), 'WEEK_NUMBER'].unique())
    if not later_weeks:
        raise ValueError('Later weeks are required.')
    people = pd.read_csv(folder / f'la_mmh_{prefix}_person_dim.csv', usecols=['P_ID'], dtype='string')
    if people.P_ID.isna().any() or people.P_ID.duplicated().any():
        raise ValueError('Person dimension must contain unique non-null IDs.')
    ids = pd.Index(people.P_ID, name='P_ID')
    week_map = calendar.set_index('DATE').WEEK_NUMBER
    parts, counts = [], {}
    for source in ['lms_item_activity_by_session', 'video_activity_by_view']:
        rows = 0
        outside_calendar = unknown_person = excluded = 0
        path = folder / f'la_mmh_{prefix}_{source}_fact.csv'
        for chunk in pd.read_csv(path, usecols=['P_ID', 'DATE'], dtype='string', chunksize=chunksize):
            rows += len(chunk)
            chunk['week'] = chunk.DATE.map(week_map)
            outside_calendar += int(chunk.week.isna().sum())
            unknown_person += int((~chunk.P_ID.isin(ids)).sum())
            valid = chunk.week.notna() & chunk.P_ID.isin(ids)
            excluded += int((~valid).sum())
            chunk = chunk.loc[valid]
            parts.append(chunk.groupby(['P_ID', 'week']).size())
        counts[source] = dict(total=rows, outside_calendar=outside_calendar,
                              unknown_person=unknown_person, excluded=excluded, used=rows-excluded)
    if parts:
        totals = pd.concat(parts).groupby(level=[0, 1]).sum()
        weekly = totals.unstack(fill_value=0).reindex(index=ids, columns=early_weeks + later_weeks, fill_value=0)
    else:
        weekly = pd.DataFrame(0, index=ids, columns=early_weeks + later_weeks)
    result = classify(weekly, early_weeks, later_weeks).sort_values('P_ID').reset_index(drop=True)
    metadata = dict(split=split, people=len(ids), predicted_ghosts=int(result.is_ghost.sum()),
                    academic_year=int(calendar.ACADEMIC_YEAR.iloc[0]), early_weeks=[int(w) for w in early_weeks],
                    later_week_count=len(later_weeks), activity_rows=counts)
    return result, metadata


def evaluate(result, answers_path):
    answers = pd.read_csv(answers_path, dtype='string')
    key = answers.Monster.str.lower().str.replace(r'[^a-z]', '', regex=True)
    truth = set(answers.loc[key.eq('ghost'), 'P_ID'].dropna())
    universe = set(result.P_ID)
    if not truth <= universe:
        raise ValueError('Training answers contain IDs outside the training population.')
    predicted = set(result.loc[result.is_ghost, 'P_ID'])
    tp, fp, fn = len(predicted & truth), len(predicted - truth), len(truth - predicted)
    return dict(true_positives=tp, false_positives=fp, false_negatives=fn,
                true_negatives=len(universe - predicted - truth),
                precision=tp / (tp + fp) if tp + fp else None,
                recall=tp / (tp + fn) if tp + fn else None,
                false_positive_ids=sorted(predicted-truth), false_negative_ids=sorted(truth-predicted))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['Training', 'Test'], default='Test')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'Dataset/Dataset')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/ghost')
    args = parser.parse_args()
    result, summary = detect(args.data_dir, args.split)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.split.lower()
    result.to_csv(args.output_dir / f'{stem}_evidence.csv', index=False)
    predictions = result.loc[result.is_ghost, ['P_ID']].assign(**{'Monster Type': 'Ghost'})[['Monster Type', 'P_ID']]
    predictions.to_csv(args.output_dir / f'{stem}_predictions.csv', index=False)
    if args.split == 'Training':
        summary['training_evaluation'] = evaluate(result, ROOT / 'HUNT_P_IDs.csv')
    else:
        summary['official_accuracy'] = 'Not available: TEST 1 labels have not been provided.'
    (args.output_dir / f'{stem}_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
