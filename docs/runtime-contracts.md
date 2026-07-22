# Runtime Contracts

This document records stable runtime invariants. It is additive to the existing API contracts and must describe behavior that the running code enforces.

## Context governance and compaction

Conversation context is assembled deterministically without a model or database call in the governance layer. Sources use this precedence:

```text
system safety boundary
> explicit user directive
> unresolved approval
> cited evidence identifier
> material tool failure
> confirmed inferred memory
> recent conversation
> old conversation summary
```

Every supplied source receives an `included`, `preserved`, `truncated`, or `dropped` decision in the versioned context assembly report. The report records character counts and estimated tokens, contains no raw tool arguments, and is attached to `context.compacted` metadata. Existing consumers may continue treating `AgentRequest.history_compaction` as an optional JSON object.

Critical items are individually bounded. API keys, bearer credentials, confirmation tokens, passwords, and secret assignments are redacted before an item can enter assembled context. Citation identifiers, pending approval summaries, and short stable tool-failure records may survive ordinary-history compaction; successful tool payloads do not. If governance itself fails, the runtime uses the original bounded conversation context rather than sending an empty context.
