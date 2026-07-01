# One Pond — Stage-B rubric

The deterministic checks already guarantee the config is legal and solvent. Stage B judges
whether it reads as a *functioning, legible pond*, anchored to `iso_camera.json` renders:

- **Economy legibility** — a player can see where bread comes from (a producer) and where it
  goes (the geese economy). A pond that is technically solvent but has no producer, or is all
  storage, fails.
- **On-model buildings** — bakery / hatchery / granary are distinguishable low-poly forms at
  the fixed iso camera, not identical boxes.
- **Composition** — buildings sit on the pond grid without reading as random scatter.

A criterion PASSes only with concrete evidence (default-FAIL). The visual gate
(`harness/review/visual_gate.py`) scores the render before a model reviewer is asked.
