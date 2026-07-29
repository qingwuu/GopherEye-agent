## Current Tool Module

```text
tools/wiki_tools.py
tools/session_archiver.py
```

Supported commands:

```bash
python tools/wiki_tools.py list-pages
python tools/wiki_tools.py search "powdery mildew"
python tools/wiki_tools.py read wiki/procedures/image_and_evidence_sop.md
python tools/wiki_tools.py links wiki/index.md
python tools/wiki_tools.py check-links
python tools/wiki_tools.py validate-json schemas/diagnosis_output.schema.json result.json
python tools/session_archiver.py
python tools/session_archiver.py list-pending
python tools/session_archiver.py capture-turn --session-path sessions/frontier/<session>.json
python tools/session_archiver.py build-reviewed-index
```
