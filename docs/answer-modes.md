# Answer modes

Mneme does not infer an answer mode from the user's question text. The client sends an explicit `answer_mode`, and the Agent maps that value to one fixed pipeline. Requests from older clients that omit the field use `kb_qa`.

| `answer_mode` | UI label | Retrieval sources | Prompt or formatter | Citations | Fallback |
| --- | --- | --- | --- | --- | --- |
| `kb_qa` | Knowledge base | Vector chunks, keyword-ranked chunks, and long-term memory | Evidence RAG prompt | Validated citations to retrieved sources | Low-confidence empty-evidence response |
| `memory_query` | Long-term memory | Long-term memory entries only | Long-term-memory evidence prompt | Validated citations to memory-backed sources | Low-confidence empty-evidence response |
| `profile_query` | Profile | Profile projection built from owned memory entries | Profile formatter | None | Low confidence with a no-memory explanation |
| `analysis_query` | Growth | Growth projection built from owned memory entries from the recent 30-day window | Growth formatter | None | Low confidence with a no-memory explanation |
| `general_chat` | General chat | None | General chat prompt | None | Model response without knowledge-base evidence |

## Contract

- The UI must send `answer_mode` with both session messages and one-shot chat queries.
- `kb_qa` uses the `hybrid` retrieval scope.
- `memory_query` uses the `memory_only` retrieval scope and must not call vector or chunk keyword retrieval.
- Profile, growth, and general chat return before retrieval context construction.
- Assistant messages store the selected route so the UI can display how an answer was produced.
- Adding a new mode requires updating the backend `AnswerMode` type, fixed route mapping, frontend `AnswerMode` type, selector metadata, and mode matrix test.
