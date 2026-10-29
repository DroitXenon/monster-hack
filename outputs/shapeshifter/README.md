# Shape-shifter

Rule: Unique majority department (>50% of distinct registered modules) changes between observed terms. Registration department is a programme proxy, not a confirmed programme change.

Exploratory proxy with poor agreement with HUNT labels. No programme or programme-change date is supplied. A department majority change can also reflect normal module choices.

Run from the project folder in the monster-hack Python environment:

```sh
python remaining_detectors.py --split Training
python remaining_detectors.py --split Test
python -m unittest test_remaining_detectors
```

The engine runs all seven remaining detectors together. It never reads answer IDs during prediction. Training answers are loaded only after prediction. People absent from the person dimension but present in activity are retained so anomalous copies can be detected. Unknown deregistration dates cannot support Undead detection. Invalid dates/timestamps are excluded only from rules that require them and counted in the summary JSON. Calendar-unmapped rows are excluded from Werewolf weekly counts. UTC is used for timestamp rules.

Training: 258 candidates, 11 matching the 80 supplied labels, 247 additional candidates and 69 missed labels. 0 labelled IDs are absent from all input data. These are training comparisons, not official TEST 1 scores.

TEST 1: 36 candidates among 1879 person/activity IDs (1874 registered and 5 activity-only). Official accuracy is unknown.

`test_predictions.csv` contains the full Monster Type + P_ID list. `test_evidence.csv` contains features and decisions for every ID. Summary JSON files contain the rule, row audits and evaluation. `TEST1_Submission.xlsx` is a fresh template copy using the MANUAL COMBINED route. `BUILD_TEST1.pptx` contains two editable slides. The final notebook section displays these executed outputs; REBUILD=True regenerates them.

This is one detector's contribution. The consolidated workbook and four-slide BUILD/TEST section are in `outputs/all_monsters/`. The standalone decks are alternatives for focused discussion, not slides to concatenate into the 15-slide team template. Add team details before submitting. Nothing has been sent to Teams. Investigate disagreements with the organisers before treating the outputs as verified detections.
