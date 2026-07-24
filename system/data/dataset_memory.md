# Dataset Memory Direction

## Core Entities

```text
image
observation
front/back pair
track
temporal window
model output
```

## Important IDs

```text
group_id
plant_id
leaf_id
observation_id
pair_id
track_id
window_id
```

These IDs allow the system to connect a current image to prior observations from
the same group, plant, or leaf.

## Side And Evidence

Leaf side matters:

```text
adaxial
abaxial
mixed
uncertain
not_leaf
```

For disease diagnosis, one side may be insufficient. The workflow should be able
to ask for the missing side when needed.

## Temporal Reasoning

Past information can support current estimation:

```text
past observations
-> current image
-> current disease and severity estimate
```

Past and current information can support future prediction:

```text
past observations + current observation
-> temporal window
-> future disease/severity/risk prediction
```

The model should not rely only on generated text. It should read structured
fields such as severity trend, side coverage, disease history, and evidence
sufficiency.

## Runtime Data Agent

The first runtime data layer lives outside the model call:

```text
existing diagnosis/chat session
-> tools/data_agent.py capture-turn
-> machine_generated / unreviewed model_label
-> human_review.submitted.json
-> reviewed_dataset_index.jsonl
```

The Data Agent records insufficient-evidence cases too. These cases are useful
for review queues and data collection planning, but they are not ground-truth
disease labels until human review accepts or corrects them.

See [Data Agent Workflow](data_agent_workflow.md).
