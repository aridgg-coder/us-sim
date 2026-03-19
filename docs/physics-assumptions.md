# Physics Assumptions

This document is the working home for the first baseline simulation assumptions.

## Baseline Model Scope

- 3D anatomical head model
- probe pose represented by position and orientation in world coordinates
- parameterized ultrasound settings including focal depth, gain, frequency, and intensity
- grayscale image generation from simulated signal response
- semi-quantitative summaries derived from the simulated field and image

## To Be Filled In

- material property tables by tissue class
- propagation model choice
- beamforming assumptions
- attenuation and reflection handling
- image reconstruction assumptions
- numerical stability and runtime tradeoffs
- translation rules from project phantom inputs into the TUSX handoff payload
