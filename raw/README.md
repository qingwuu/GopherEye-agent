# Raw Sources

Put original sources here through `add_source.py`.

Examples:

```bash
python add_source.py ~/notes/pi_meeting.md --source-type meeting --title "PI meeting"
python add_source.py ~/notes/expert_notes.md --source-type expert_information --title "Expert notes"
python add_source.py ~/sources/treatment_guide.pdf --source-type treatment_resources --title "Treatment guide"
```

Raw sources are preserved. Curated knowledge belongs in `wiki/`.

## Manual Collection Folders

Use these folders for materials that need manual search or expert collection:

```text
sources/expert_information/
sources/expert_examples/
sources/treatment_resources/
sources/diagnosis_scripts/
sources/procedure_notes/
sources/dialog_trees/
sources/disease_information/
```

See `system/source_requirements/raw_source_intake_rules.md` and
`system/source_requirements/manual_source_backlog.md`.
