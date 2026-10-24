# Failure drills: break it on purpose

Each drill breaks one thing and tells you what you should see in three places: the page, the Uvicorn terminal, and the `model_requests` table. Finding the layer that broke (router, service, repository, or client) from the evidence is the skill. Run drills with a scratch copy of the code or revert the change afterwards; none of them should touch your saved chats.

Look at the table after each drill, choosing columns by name (`reasoning_text` can be very long):

```sql
SELECT id, status, error, seconds_total FROM model_requests ORDER BY id DESC LIMIT 3;
SELECT COUNT(*) FROM messages;
```

"Checked" means the tutor ran the drill against the real vLLM server on 2026-10-23 and the result matched. "Expected" means it follows from the code and the unit tests, but was not run live.

| # | Break | How | Layer | Page shows | `model_requests` row | `messages` rows | Status |
|---|---|---|---|---|---|---|---|
| 1 | Wrong vLLM port | in `clients/vllm_client.py`, make `VLLM_CHAT_URL` use port 8999 (nothing listens there) | client | `Failed: ConnectError: All connection attempts failed. Nothing was saved…` | `error`, `ConnectError: All connection attempts failed`, about 0.03 seconds | unchanged | Checked |
| 2 | Mistyped model name | in `settings.py`, change `VLLM_MODEL` to `qwen-typo` | client / vLLM | `Failed: VllmError: vLLM replied HTTP 404 …The model 'qwen-typo' does not exist…` | `error`, the same 404 text, about 0.02 seconds | unchanged | Checked |
| 3 | Prompt longer than the model's limit | paste about 2.4 million characters (about 400,000 repetitions of "hello ") | client / vLLM | `Failed: VllmError: vLLM replied HTTP 400 …maximum context length is 262144 tokens…` | `error`, the 400 text, `prompt_chars` about 2,399,999 | unchanged | Checked |
| 4 | Stop button | send a long request, press Stop after a few seconds | service | `Stopped. This turn was not saved to the chat.` | `stopped`, thinking text so far kept | unchanged | Checked (with `curl` disconnecting; the button itself was not clicked) |
| 5 | Unknown conversation | `POST /chat` with `"conversation_id": "nope"` | router | `Failed: Conversation not found` | no row (rejected before streaming) | unchanged | Checked |
| 6 | Bad thinking level | `POST /chat` with `"reasoning_effort": "extreme"` | router (Pydantic) | `Failed:` followed by the validation detail | no row | unchanged | Checked in unit tests |
| 7 | Model finishes with no answer | long task at `low`; the model stops inside its thinking | service | `Failed: NoAnswerText: finish_reason=stop` | `error`, whole thinking kept in `reasoning_text` | unchanged | Happened for real (the 31-minute review) |
| 8 | Stop vLLM entirely | `docker stop qwen38-27b`, then send | client | `ConnectError`, as drill 1 | like drill 1 | unchanged | Expected, not run |

## What each drill teaches

- Drills 1 to 3 differ only in where the failure is born. A `ConnectError` means no HTTP reply existed; an `HTTP 404` or `HTTP 400` means vLLM answered and refused. Both arrive as a `VllmError` or `httpx` error from `clients/`.
- Drill 4 shows that a request can end without an error: the row says `stopped`.
- Drill 5 and 6 are rejected by the router before any streaming starts, so there is no `model_requests` row. Compare with drill 1, which does leave a row.
- Drill 7 is why the harness refuses to save an empty assistant message.
- After every drill, `SELECT COUNT(*) FROM messages;` should not change. If it does, history was polluted by a failed turn.
