# Implementation provenance

OneAgent's pre-existing starting point is commit `503ecd0`, an Enoch-derived agent
created with Genesis. Its runtime, identity, memory, provider system and existing
tests are inherited building blocks.

The `oneagent.collaboration` package, notes round-trip example, integration guide,
and collaboration tests are newly written for this project. The
One Agent, Anywhere position paper is an architectural reference.

The travel scenario was built on the merged reusable core (PR #1): fictional
catalogs and catalog tools, a browser gateway, a bounded agent loop,
React/TypeScript websites, and travel integration tests. Preferences and choices
now live in the normal agent conversation, with no separate itinerary store or
save/confirmation workflow. Its images are licensed reference photography;
attribution is in [the travel walkthrough](travel-demo.md).
The Telegram handoff adds three independent site entry points, an activities
catalog, reusable scoped connection links, a bridge to the normal bot's existing
conversation, and website reply delivery through its durable notification service.
Record actual event dates and newly built components in the hackathon submission;
this document does not certify eligibility or the official build window.
