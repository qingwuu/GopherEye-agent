## Current Tool Module

```text
tools/wiki_tools.py
tools/data_agent.py
```

Supported commands:

```bash
python tools/wiki_tools.py list-pages
python tools/wiki_tools.py search "powdery mildew"
python tools/wiki_tools.py read wiki/grape_leaf/image_guidance.md
python tools/wiki_tools.py links wiki/index.md
python tools/wiki_tools.py check-links
python tools/wiki_tools.py validate-json schemas/diagnosis_output.schema.json result.json
python tools/data_agent.py capture-turn --session-path Frontier_model/sessions/<session>.json
python tools/data_agent.py list-pending
python tools/data_agent.py import-review --instance-id <instance_id>
python tools/data_agent.py build-reviewed-index
```
