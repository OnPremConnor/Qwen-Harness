# Qwen harness: learning platform vision

This is a living goal for an ambitious product and for Connor's hands-on engineering education. The [README](README.md) describes the code that exists today. A small local milestone in this document is a way to learn and test an idea; it is not the intended limit of the product.

## Purpose and quality bar

Build a sophisticated learning platform that can use a student's own course material, diagnose what they understand, teach through conversation and useful visuals, and improve its work through review. The aim is a high-value experience that can compete with ordinary chatbot tutoring. We will test that claim with learner outcomes instead of assuming that more agents make a better tutor.

The same repository is Connor's main place to learn Python, APIs, databases, Docker, model serving, retrieval, agent workflows, deployment, and operation on the DGX Spark. `connorboetig.com` is intended to be where Connor hosts services for family, friends, and themself (Connor, 2026-10-31). Tutoring comes first. Image editing or generation and live conversation may follow as separate services on the same site. Each service pairs a model with a harness built for one task. For example, an uncle who finds chat assistants weak at math would get an account and a math-tutor harness that uses a hosted model through a server-side key, so he can see what the harness adds beyond the model. A learner who uses the finished product learns more than one who hears about the backend. There is no deadline; the goals are learning the full stack in depth, useful tools for people Connor knows, and forward deployed engineer (FDE) confidence. The old career-fair portfolio that still serves the domain is a past idea and not part of this project.

## A learner's experience

Connor manually creates an account for an invited learner. She has her own courses, source materials, conversations, and learning record. She can upload material she can obtain from Canvas or elsewhere: course pages, a syllabus, PDFs, notes, slides, and videos, along with course and assignment context. The platform processes these sources so a later question can find the relevant material and show where an explanation came from.

Suppose she uploads biology and nutrition material, then brings a confusing passage to the tutor. The tutor asks her to explain what she already thinks it means. It uses that attempt, her prior learning evidence, and the relevant course sources to find the missing foundation. It explains the next useful idea, chooses a visual or interaction when that helps, and responds to her next attempt. A check might ask her to apply the idea to a new case rather than repeat the tutor's wording. The tutor records what she demonstrated, what remained uncertain, and what help she needed.

The same experience should work for a code topic: a learner who knows FastAPI's broad purpose but cannot picture a request path could describe their current understanding, then see a source-linked diagram or interactive trace of the actual code. Speech-to-text input and optional text-to-speech replies should eventually let a learner have that exchange by voice.

## Capabilities to build toward

- **Accounts and course workspaces:** Manually provision accounts at first. Keep each learner's materials, chat history, and learning evidence separate. The browser talks to our FastAPI backend; model servers and API keys stay behind it.
- **Material ingestion:** Accept the files and pages a learner provides. Extract text from documents, transcribe audio from videos, and inspect useful visual content when needed. Keep the original source and location information alongside the processed text so the tutor can point back to it.
- **Retrieval:** Index processed material for search, including embeddings (numeric representations used to find related content). Retrieval-augmented generation, or RAG, means finding relevant course material and supplying it to the model for a particular answer. The tutor should distinguish what a source actually says from its own inference and notice when the available material does not answer the question.
- **Context engineering:** Assemble the right source excerpts, learner evidence, conversation history, task instructions, and tool results for each step. A tutor, a visual generator, and a reviewer may need different context. Keep the selected context inspectable so we can diagnose why a response worked or failed; uploading a whole course into every model call is not the design.
- **Adaptive tutoring and learning context:** Use the learner's own explanation to choose the next teaching step. Keep a learning record separate from the chat transcript: demonstrated understanding, misconceptions, assistance, confidence when volunteered, and later retention. A fluent model response is not proof that the learner learned.
- **Visual and interactive work:** Generate two-dimensional diagrams, browser interactions, animations, and eventually three-dimensional scenes when they explain a specific mechanism better than text. A Blender specialist is one possible generator. Review the rendered or interactive artifact the learner will actually see, not just its source code or the generator's description.
- **Agent orchestration and background work:** Use LangGraph for purposeful interactive and background workflows, with specialists for tutoring, planning, source use, visual generation, and review where they add value. After each completed chat, a background reviewer examines the exchange for unresolved confusion and useful visual opportunities. When it proposes an artifact, a specialist creates it; a multimodal adversarial reviewer inspects the actual output against the source material and teaching goal, identifies errors or weak explanations, and sends it back for revision. Define when a job creates work, how many revisions it may make, what counts as acceptable, and when a person should review it.
- **Model choice:** Start with local Qwen where it performs well. For tasks where careful context design, retrieval, and the local model still fall short, route a specific step to a stronger hosted model through a server-side API key. Judge this choice by quality, privacy, latency, and cost for that task; do not assume every agent needs the same model.
- **Deployment and operation:** Grow from the local Spark app to an invited-user service with secure access, background jobs, storage, logs, recovery, and a clear way to observe failures. Choose infrastructure when the capability requires it, and learn each layer while building it.

The intended shape is:

```text
course uploads -> extraction and transcription -> source-linked search
learner chat + learning record + retrieved sources -> tutor workflow -> reply or visual
each completed chat -> background review -> selected specialist work -> multimodal review -> revision
```

These capabilities are a direction, not a promise that every idea belongs in the first release or that this exact workflow will prove best. We can change the design as results come in.

## How we will judge progress

Use real course and code-learning tasks. Check source accuracy, whether an explanation addresses the learner's actual gap, whether a visual is correct and useful, and what the learner can explain or apply afterward. Revisit some ideas later to test retention. Compare the added retrieval, visuals, specialist agents, and model routing with a simpler chat baseline. Keep the parts that measurably help.

## Current foundation and next slice

Today the repository has a local text-only page, a FastAPI backend, and a client for separately served vLLM. Each question is an independent model request. The page displays the exchanges while it stays open but saves nothing; its history sidebar is a placeholder and its login button is disabled. PostgreSQL is installed on the host but unused by this app. The upload and retrieval prototype was removed because it skipped ahead of Connor's current learning path. This is a working request path, not yet a conversational or measured learning product.

The next learning step is to trace the current path: browser → FastAPI → local model → browser. Connor will then build conversation context and durable history deliberately, learning what is held in a running page, what is sent in a request, and what a database actually saves. That foundation comes before course ingestion, generated visuals, or background agent workflows.

## Near-term build and learning path

1. **Trace the clean request path.** Connor follows one question from the page through FastAPI and the vLLM HTTP request to the displayed answer. The current request has no earlier messages.
2. **Build conversations deliberately.** Learn how sending earlier user and assistant messages changes Qwen's next reply. Choose where active conversation state belongs before adding it to the code.
3. **Learn PostgreSQL and add history.** Inspect the installed server together, design simple conversation and message tables, create them explicitly, then add the Python client and read/write path. Only then make the sidebar list and reopen saved chats.
4. **Login and ownership.** Add a minimal user account, password verification, and a server-side login session. Tie each conversation to its owner, and check ownership on every conversation read and chat write. Start with local accounts; remote access comes only after this boundary works. A login screen by itself does not protect chat data.
5. **First LangGraph lesson.** Put the model call in a small graph and inspect the state entering and leaving each step. Add one purposeful step and compare it with the plain chat path. Only add specialist agents when a real task needs different roles or context.
6. **Learning features.** Add a small learner-evidence loop, then bring back uploads, retrieval, transcription, visuals, and background review as separate features when we can explain and evaluate each one. Preserve the broader vision above while changing the order to match what Connor is ready to build.

## Design questions to answer through use

- Which upload formats and course relationships matter most to the first invited learner?
- What evidence is strong enough to add to a learner's record, and what should remain only in chat history?
- Which teaching tasks benefit from background generation, a visual, or a stronger hosted model?
- How will an adversarial review catch both factual mistakes and a visual that looks polished but teaches the wrong thing?
- What result would convince us that this platform helped a learner more than a simpler chat session?
