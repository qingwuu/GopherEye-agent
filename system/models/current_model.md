# Current GopherEye Model

## Current Capability

GopherEye currently has a single-image grape leaf vision-language model.

Current task:

```text
leaf image + prompt
-> disease
-> visual indicators
-> recommended checks
-> evidence
```

It is not yet a temporal, memory-based, front/back paired, or agentic diagnostic
system.

## Architecture

Conceptual model flow:

```text
leaf image
-> visual encoder / Q-Former
-> projected visual prefix
-> Qwen language model
-> structured diagnostic answer
```

## Output Schema

The current answer can be represented as:

```json
{
  "disease": "downy_mildew",
  "indicators": ["chlorosis", "necrotic spots"],
  "recommended_checks": ["inspect abaxial side"],
  "evidence": "..."
}
```

## Limitations

- single image only;
- no reliable front/back pairing;
- no structured memory by itself;
- no group, plant, or leaf temporal track by itself;
- no future prediction by itself;
- evidence may be incomplete if only one leaf side is provided.

