import unittest
import pandas as pd
from ghost_detector import classify


class GhostRuleTests(unittest.TestCase):
    def test_rule_boundaries_and_inactive_weeks(self):
        # First four weeks; two later weeks. Exactly 10% must NOT match.
        weekly = pd.DataFrame([
            [10, 10, 10, 10, 0, 1],
            [10, 10, 10, 10, 1, 1],
            [10, 10, 0, 0, 0, 0],
            [10, 10, 10, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
        ], index=pd.Index(['low', 'boundary', 'two_weeks', 'three_weeks', 'inactive'], name='P_ID'), columns=range(1, 7))
        result = classify(weekly, [1, 2, 3, 4], [5, 6]).set_index('P_ID')
        self.assertEqual(result.index[result.is_ghost].tolist(), ['low', 'three_weeks'])
        self.assertEqual(result.loc['three_weeks', 'early_average'], 7.5)
        self.assertEqual(result.loc['low', 'later_average'], 0.5)


if __name__ == '__main__':
    unittest.main()
