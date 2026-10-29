# All nine monsters

**These are detector candidates, not verified answers.** Official TEST 1 labels are unavailable. Werewolf and Shape-shifter are exploratory rules with poor training agreement. Ghost, Zombie and Web Crawler also disagree substantially with supplied HUNT labels. Do not claim high accuracy for the combined system.

## Results

| Monster | TEST 1 candidates | Training matched | Training extra | Training missed |
|---|---:|---:|---:|---:|
| Ghost | 14 | 5 | 143 | 53 |
| Vampire | 12 | 91 | 0 | 8 |
| Phantom | 13 | 62 | 15 | 0 |
| Zombie | 1 | 2 | 23 | 57 |
| Undead Student | 11 | 92 | 0 | 0 |
| Doppelgänger | 10 | 60 | 0 | 12 |
| Werewolf | 128 | 1 | 1125 | 7 |
| Web Crawler | 0 | 14 | 1 | 33 |
| Shape-shifter | 36 | 11 | 247 | 69 |

Training metrics compare against the supplied HUNT answer list. Six Doppelgänger label IDs are absent from all training input tables; they remain counted as missed labels. The seven new detectors retain activity-only IDs, so their population is larger than the person dimension. Ghost and Vampire preserve their previously documented person-dimension scope.

## Main deliverables

[Combined workbook](TEST1_Submission.xlsx) uses TEST1_MANUAL_COMBINED. It contains all nine detectors, including exploratory candidates. [Combined slides](BUILD_TEST1.pptx) provide a four-slide BUILD/TEST section for the team template. Use that section instead of concatenating all standalone decks into the 15-slide team submission. [CSV](test_predictions.csv) contains the same classifications. Different monsters may flag the same person.

## Per-monster files

- Phantom: [notebook](../../01_hunt_phantom.ipynb), [evidence and instructions](../phantom/README.md), [workbook](../phantom/TEST1_Submission.xlsx), [slides](../phantom/BUILD_TEST1.pptx).
- Zombie: [notebook](../../01_hunt_zombie.ipynb), [evidence and instructions](../zombie/README.md), [workbook](../zombie/TEST1_Submission.xlsx), [slides](../zombie/BUILD_TEST1.pptx).
- Undead Student: [notebook](../../01_hunt_undead.ipynb), [evidence and instructions](../undead/README.md), [workbook](../undead/TEST1_Submission.xlsx), [slides](../undead/BUILD_TEST1.pptx).
- Doppelgänger: [notebook](../../01_hunt_doppelganger.ipynb), [evidence and instructions](../doppelganger/README.md), [workbook](../doppelganger/TEST1_Submission.xlsx), [slides](../doppelganger/BUILD_TEST1.pptx).
- Werewolf: [notebook](../../01_hunt_werewolf.ipynb), [evidence and instructions](../werewolf/README.md), [workbook](../werewolf/TEST1_Submission.xlsx), [slides](../werewolf/BUILD_TEST1.pptx).
- Web Crawler: [notebook](../../01_hunt_web_crawler.ipynb), [evidence and instructions](../web_crawler/README.md), [workbook](../web_crawler/TEST1_Submission.xlsx), [slides](../web_crawler/BUILD_TEST1.pptx).
- Shape-shifter: [notebook](../../01_hunt_shapeshifter.ipynb), [evidence and instructions](../shapeshifter/README.md), [workbook](../shapeshifter/TEST1_Submission.xlsx), [slides](../shapeshifter/BUILD_TEST1.pptx).

## Reproduce

From the project root, with the monster-hack Python environment active:

```sh
python remaining_detectors.py --split Training
python remaining_detectors.py --split Test
python ghost_detector.py --split Test
python vampire_detector.py --split Test
python -m unittest test_remaining_detectors test_ghost_detector test_vampire_detector
```

The shared engine computes the seven new detectors together and writes evidence, predictions and summary JSON files. The final notebook sections display executed saved outputs; set REBUILD=True to recompute both splits. Spreadsheet and slide files are snapshots of the checked run. Regenerating CSVs does not automatically rewrite these snapshots.

Boundary tests cover strict thresholds, inclusive windows, duplicate handling across chunks, exact partner matching, activity-only IDs, UK dates, department ties and inactive students. Every new notebook section was executed.

Add team details before using the workbook. Review label/rule disagreements with organisers, save the code and artifacts in the private team channel, and demonstrate the detector. No files or messages have been sent to Teams.
