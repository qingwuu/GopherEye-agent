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

For disease diagnosis, one side may be sufficient or insufficient depending on
the visible disease-specific evidence. The workflow should be able to diagnose
from one side when high-signal evidence is present and ask for the missing side
only when it resolves a specific uncertainty.

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

## GopherEye Data Agent Boundary

The independent GopherEye Data Agent is a CLI-first data workspace, not a chat
session archive. It imports explicit image-pair folders and writes its own
instances, jobs, artifacts, indexes, and review queues under:

```text
gophereye_data_workspace/
```

The frontier chat system may discuss data collection strategy, but it should not
drive or own this workspace. GopherEye Data Agent commands handle leaf-pair
import, instance JSON modification, grape disease label proposals, segmentation,
embedding, augmentation, review export, and experiment/versioning integrations.

Unreviewed model proposals are not ground-truth disease labels until human
review accepts or corrects them.
