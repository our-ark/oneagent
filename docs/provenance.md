# Implementation provenance

OneAgent's pre-existing starting point is commit `503ecd0`, an Enoch-derived agent
created with Genesis. Its runtime, identity, memory, provider system and existing
tests are inherited building blocks.

The `oneagent.collaboration` package, notes round-trip example, integration guide,
and collaboration tests are newly written for this project. Ruth and the
One Agent, Anywhere position paper are architectural references. No Ruth source
files were copied into this implementation.

The travel scenario was built on the merged reusable core (PR #1): fictional
catalogs, trip rules and tools, a browser gateway, a bounded agent loop, a new
React/TypeScript website, and travel integration tests. Its images are licensed
reference photography; attribution is in docs/travel-demo.md.
The Telegram handoff adds three independent site entry points, an activities
catalog, reusable scoped connection links, a bridge to the normal bot's existing
conversation, and website reply delivery through its durable notification service.
Record actual event dates and newly built components in the hackathon submission;
this document does not certify eligibility or the official build window.
