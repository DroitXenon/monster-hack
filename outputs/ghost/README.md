# Ghost

Run from the project folder in the `monster-hack` Conda environment:

```sh
python ghost_detector.py --split Training
python ghost_detector.py --split Test
python -m unittest test_ghost_detector
```

The last section of `01_hunt_ghost.ipynb` runs the same detector and displays its evidence.

## Rule and data flow

The split's person dimension supplies the population. LMS session and video view CSVs supply activity rows. The calendar maps each DATE to its academic week. Count rows (not INTERACTION_COUNT, minutes, or distinct days), retaining duplicates because the guide specifies activity rows.

For each student, include all four early weeks and all 48 later weeks, even those with no activity. Classify as Ghost when at least three early weeks have activity and `later_average < 0.1 * early_average`. This uses academic year 2023, weeks 1–52. Rows outside the supplied calendar or with IDs absent from the person dimension are excluded; each summary JSON records the counts. Unknown people are not treated as enrolled students.

HUNT labels never enter detection. They are read only after training predictions have been produced for evaluation. TEST 1 was processed automatically with the same fixed rule, without manually hunting or adjusting the rule to test students.

## Results and limitation

- Training: 14,951 students, 148 candidates. Only 5 match the 58 supplied Ghost answers; 143 additional candidates and 53 missed labels. This reproduces the original notebook's finding that only 5 supplied Ghost answers meet the guide rule. Confirm the discrepancy with the organisers. Do not describe this as a validated high-accuracy detector.
- TEST 1: 1,874 students, 14 candidates. Official TEST 1 labels and accuracy are unavailable.
- TEST 1 input: 1,104,759 rows; 1,103,242 used and 1,517 excluded.

`test_predictions.csv` is the full Monster Type + P_ID list. `test_evidence.csv` contains the features and decision for every test student. Summary JSON files record processing counts and training evaluation.

`Ghost_TEST1_Submission.xlsx` is a copy of the supplied workbook, using its manual-combine route. Ghost predictions occupy `TEST1_MANUAL_COMBINED!A4:B17`. Other monster tabs are blank. Add team details and merge these rows into your team's submission if other detectors already have results. Do not submit a Ghost-only copy in place of a combined team workbook.

`Ghost_BUILD_TEST1.pptx` contains two editable slides for the team's BUILD/TEST section. The original templates are unchanged.

The local deliverables have not been posted to Teams. Add team details, save the code/workbook/slides in your private team channel, and demonstrate the detector to the organisers. The guide/answer discrepancy remains unresolved.
