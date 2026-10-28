# Vampire

Run from the project folder in the monster-hack environment:

```sh
python vampire_detector.py --split Training
python vampire_detector.py --split Test
python -m unittest test_vampire_detector
```

The final section of `01_hunt_vampire.ipynb` runs this detector and displays the test candidates. The original HUNT exploration is preserved.

## Rule

Combine LMS and video activity for every person in the split's person dimension. Parse TIMESTAMP in UTC, matching the supplied Z timestamps. Count distinct UTC dates separately for night and day. A date with both kinds of activity counts once in each period. Repeated rows, chunks, and sources do not increase a period's distinct-day count.

Night is strictly after midnight through 05:00 inclusive. Other times are day, with exactly midnight assigned to day on its timestamp date. These timezone and boundary conventions are explicit interpretations of the guide. The original notebook omitted exactly 05:00 and the first minute after midnight from night activity; the new detector uses timestamp precision.

A Vampire must have more than 21 night-active days AND more night-active than day-active days. All supplied valid timestamps are used; there is no academic-year filter in this rule. Unknown person IDs and invalid timestamps are excluded and counted in the summary JSON. HUNT answers are read only after training prediction, for evaluation. TEST 1 was processed automatically using the fixed rule.

## Results

- Training: 14,951 people, 91 candidates. Against 99 supplied Vampire labels: 91 matches, no extra predictions, 8 missed labels. Precision 100%, recall 91.9%. These are training metrics, not official TEST 1 accuracy.
- All eight missed training labels have more day-active than night-active days; the supplied labels and this interpretation of the guide disagree for those students.
- TEST 1: 1,874 people, 12 candidates. Official accuracy is unknown.
- TEST 1: 1,104,759 rows scanned; 1,104,441 used. Excluded 318 video rows with IDs absent from the test person dimension. No invalid timestamps among known people.

## Files and handoff

- `test_predictions.csv`: full Monster Type + P_ID list.
- `test_evidence.csv`: night/day counts and decision for every test person.
- `training_evidence.csv` and summary JSON files: reproducible evaluation and processing counts.
- `Vampire_TEST1_Submission.xlsx`: template copy using the manual-combine route, with 12 rows in `TEST1_MANUAL_COMBINED!A4:B15`.
- `Vampire_BUILD_TEST1.pptx`: two editable BUILD/TEST slides.

This is the Vampire portion only. Merge these 12 rows with the Ghost and other detectors' rows in the team's combined workbook. Add team details and upload the code, slides and workbook to the private team channel. Files have not been posted to Teams. Confirm the training-label discrepancy with the organisers.
