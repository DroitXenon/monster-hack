import unittest
import pandas as pd
from vampire_detector import activity_dates, classify


class VampireTests(unittest.TestCase):
    def test_exact_time_boundaries(self):
        frame = pd.DataFrame({'P_ID': ['a']*5, 'TIMESTAMP': [
            '2023-10-01T00:00:00Z', '2023-10-01T00:00:00.001Z',
            '2023-10-01T05:00:00Z', '2023-10-01T05:00:00.001Z', 'invalid']})
        dates, invalid = activity_dates(frame)
        self.assertEqual(dates.period.tolist(), ['day', 'night', 'night', 'day'])
        self.assertEqual(invalid, 1)

    def test_distinct_dates_threshold_tie_and_inactive(self):
        rows = []
        for pid, nights, days in [('yes',22,21),('only21',21,0),('tie',22,22)]:
            for period, count in [('night',nights),('day',days)]:
                for date in pd.date_range('2023-10-01',periods=count):
                    rows.extend([(pid,str(date.date()),period)]*3)
        dates = pd.DataFrame(rows,columns=['P_ID','date','period'])
        result = classify(dates,['yes','only21','tie','inactive']).set_index('P_ID')
        self.assertEqual(result.index[result.is_vampire].tolist(),['yes'])
        self.assertEqual(result.loc['yes','night_active_days'],22)
        self.assertEqual(result.loc['inactive','night_active_days'],0)


if __name__ == '__main__':
    unittest.main()
