# Agent guide: Qwen Harness

Connor (they/them) is learning full-stack work from close to zero through this repo, which is also the seed of a larger platform ([PROJECT.md](PROJECT.md)). Judge code here first as **a baseline Connor can read, trace, and extend**, then as working software. Claude Code reads `CLAUDE.md`, which imports this file; edit only `AGENTS.md`.

## Before you work
1. Read `~/misc/learning/CURRENT.md` (where Connor is now) and `~/misc/learning/AGENTS.md` (teaching rules, what counts as evidence). Code you write or run here is tutor work, never evidence of Connor's skill.
2. Read [README.md](README.md) for the file map and run command. Inspect live state (`git status`, listeners, containers) instead of trusting any note.

## Rules for code (Connor's decisions)
- **Simplest correct baseline to learn from:** one job per file, unique descriptive file names, the fewest layers that separate real jobs, a comment on every non-obvious line. No new layers, frameworks, databases, or features beyond the core loop unless Connor asks (an upload and retrieval prototype and a `/health` route were removed for exactly this).
- **Names are role-based and protocol-true:** use vLLM's own words (`content`, `id`, `model`, `finish_reason`, `usage`) end to end, and keep the model's brand out of code names (`call_model_server.py`, `get_model_answer()`, `ModelReplyError`). In `answer_question()` the incoming text is `question` and the reply is `content`.
- **Connor's turn:** when Connor should write the next piece, leave one clearly marked `TODO(human)` and don't fill it in.
- **Logs hold sizes, lengths, ids, and counts, not question or reply text** (tutor's call, open to Connor; text belongs in the database later, where access can be controlled).

## Commands
| Task | Command (from the repo root) |
|---|---|
| Install or refresh packages | `cd backend && uv sync` |
| Run the app on 127.0.0.1:8001 | `cd backend && uv run uvicorn qwen_harness.main:app --host 127.0.0.1 --port 8001` |
| Python prompt with the project's packages | `cd backend && uv run python` |
| Is the model server up? | `curl -s http://127.0.0.1:8000/v1/models` |
| Send one question by hand | `curl -s -X POST http://127.0.0.1:8001/chat -H 'Content-Type: application/json' -d '{"content":"Hi"}'` |

The model server is separate: vLLM in Docker, started with `docker compose up -d` in `~/serving/qwen38-27b`; it took 466 seconds (until `/v1/models` answered) on 2026-10-31. There is no test suite yet: verify a change by restarting Uvicorn, sending a question, and reading the log line.

## Gotchas (observed)
- **A running Uvicorn keeps the code it loaded.** After any edit, stop it by process id (never `pkill -f` with a pattern that can match your own shell) and start it again.
- **`uv run python` outside `backend/` uses `/usr/bin/python3`, which has no `httpx`.** `uv` finds the project by looking for `pyproject.toml` in the current folder and its parents; only `backend/` has one.
- **Logging needs `logging.basicConfig`** (set in `main.py`); without it Python drops the INFO line. Each model call logs one JSON record from `call_model_server.py`.
- **Qwen's reply:** `content` starts with 2 newline characters (`.strip()` removes them); `reasoning_effort: "low"` does not cap thinking (118 of 128 generated tokens on one logged call); the first request after a container start was slow (34.009 seconds versus about 6.8 seconds for the identical second; cause unknown).
- **`backend/captured-request-trace.html` is a snapshot pinned to commit `e9abddb`** and predates logging. Regenerate it with checked line numbers rather than hand-editing.

## Git
Commit at checkpoints with a message saying what changed and why. Push `main` to `origin` at the end of a session, after `git status` shows no stray or sensitive files (`.env*` and `*.log` are ignored). Never force-push.
