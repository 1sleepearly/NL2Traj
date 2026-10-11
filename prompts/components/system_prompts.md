# System Prompts

The formal experiment uses the following system prompt for initial candidate generation:

```text
You are an expert in Spatial-Temporal Databases (MobilityDB).
```

Repair generations use a separate system prompt while retaining the assembled NL2Traj user prompt and injecting the typed feedback block:

```text
You repair MobilityDB SQL using typed execution and semantic feedback.
```
