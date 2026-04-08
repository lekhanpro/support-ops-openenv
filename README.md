---
title: SupportOps OpenEnv
emoji: 🧾
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8000
tags:
  - openenv
---

# SupportOps OpenEnv

`support_ops_env` is a real-world OpenEnv environment for customer-support operations. It simulates the kind of queue work that human support agents actually do: triage tickets, read policy articles, decide whether a case belongs in billing, returns, risk, or safety, write internal notes, send customer-facing replies, and close or escalate each ticket correctly.

The environment is intentionally designed for agent training and evaluation rather than generic chat. Success depends on operational accuracy, policy compliance, and efficient workflow management across progressively harder tasks.

## Why this environment is useful

- It models a genuine business workflow instead of a toy interaction loop.
- It combines classification, policy retrieval, decision-making, and communication.
- It rewards partial progress, so RL agents receive dense feedback before the end of the episode.
- It exposes common failure modes for agents: wrong queue assignment, unsafe refunds, skipped escalations, and vague replies.

## Environment API

The environment follows the standard OpenEnv simulation contract:

- `reset(task_id=...) -> observation`
- `step(action) -> observation, reward, done`
- `state() -> current internal state`

### Action space

`SupportOpsAction` is a typed Pydantic model with these main fields:

- `action_type`: one of `view_ticket`, `read_article`, `update_ticket`, `send_reply`, `resolve_ticket`, `finish`
- `ticket_id`: ticket to inspect or modify
- `article_id`: policy article to open
- `queue`: one of `general`, `returns`, `billing`, `risk`, `safety`
- `priority`: one of `low`, `medium`, `high`, `urgent`
- `status`: one of `open`, `pending_customer`, `resolved`, `escalated`
- `resolution`: one of `none`, `replacement`, `refund`, `store_credit`, `safety_escalation`, `risk_escalation`
- `refund_amount`: optional refund or store-credit amount
- `tags`: operational labels
- `internal_note`: internal support note
- `message`: customer-facing response

### Observation space

`SupportOpsObservation` includes:

- `task`: task metadata and step budget
- `inbox`: current ticket queue summary
- `current_ticket`: expanded ticket details for the selected ticket
- `knowledge_base`: policy article previews
- `visible_article`: full article contents after a read action
- `last_action_result`: environment response to the previous action
- `warnings`: structured warnings for invalid or redundant behavior
- `remaining_steps`, `resolved_tickets`, `total_tickets`
- `metadata.current_score`: current task score from the deterministic grader

### State space

`SupportOpsState` exposes the full mutable workspace:

- active task and difficulty
- active ticket id
- full ticket state
- viewed ticket ids
- read article ids
- action history
- current grader score and per-ticket breakdown

## Tasks

The repo ships with 3 deterministic tasks and graders:

1. `easy_damage_replacement`
   Damaged lamp replacement with one ticket and one relevant policy article.
2. `medium_billing_and_shipping`
   Two-ticket queue with duplicate billing and wrong-item resolution paths.
3. `hard_safety_risk_policy_mix`
   Three-ticket queue mixing safety escalation, fraud-risk review, and a premium policy exception.

The difficulty progression is intentional:

- Easy: one clear operational path.
- Medium: multiple tickets with different queues.
- Hard: several tickets where the wrong action can be unsafe or policy-violating.

## Reward design

Reward is shaped from task-score deltas rather than a single terminal pass/fail:

- Positive reward when an action improves the deterministic grader score.
- Small bonuses for first-time useful exploration like opening a new ticket or reading a relevant article.
- Penalties for repeated or invalid actions and for finishing early while tickets remain open.
- Final task quality is exposed as `state().current_score` in `[0.0, 1.0]`.

This keeps the reward meaningful throughout the full trajectory.

## Graders

Each ticket has a deterministic target rubric covering:

- queue assignment
- priority
- final status
- resolution choice
- tags
- refund or store-credit amount when relevant
- required phrases in the internal note
- required and forbidden phrases in the customer reply

Per-ticket scores are averaged into the task score. All graders are deterministic and bounded to `[0.0, 1.0]`.

## Local setup

### Python

```bash
python -m pip install -U pip
python -m pip install .
```

### Run the server locally

```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Validate the environment

```bash
openenv validate
```

### Build and run with Docker

```bash
docker build -t support-ops-env:latest .
docker run -p 8000:8000 support-ops-env:latest
```

## Baseline inference

The required baseline script is [inference.py](/D:/New%20folder%20(3)/inference.py). It:

- uses the OpenAI client for LLM calls
- reads `API_BASE_URL`, `API_KEY`, and `MODEL_NAME`
- uses the injected `API_BASE_URL` and `API_KEY` directly for all LLM calls
- makes a guaranteed OpenAI client request before task execution starts
- emits structured `[START]`, `[STEP]`, and `[END]` stdout logs
- runs all three tasks by default
- uses deterministic action selection, with the LLM limited to customer-facing reply drafting

Run it with:

```bash
set API_BASE_URL=https://api.openai.com/v1
set MODEL_NAME=gpt-4o-mini
set API_KEY=your_key_here
python inference.py
```

Optional:

```bash
set TASK_ID=hard_safety_risk_policy_mix
python inference.py
```

## Baseline scores

The bundled heuristic-plus-LLM baseline is designed to be reproducible because the operational decisions are deterministic and the LLM is only used to polish reply text with `temperature=0`.

Reference baseline targets:

- Easy: `~1.00`
- Medium: `~1.00`
- Hard: `~1.00`

If the API is unavailable, the script falls back to deterministic message templates and still reproduces the same action choices.

## Hugging Face Space deployment

This repo is ready for Docker-based HF Spaces.

Recommended deployment path:

```bash
huggingface-cli login
openenv push --repo-id <your-username>/support-ops-env
```

Required environment variables for the Space settings:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`
- `OPENAI_API_KEY`

## Submission assets

- [openenv.yaml](/D:/New%20folder%20(3)/openenv.yaml)
- [models.py](/D:/New%20folder%20(3)/models.py)
- [client.py](/D:/New%20folder%20(3)/client.py)
- [server/app.py](/D:/New%20folder%20(3)/server/app.py)
- [server/support_ops_env_environment.py](/D:/New%20folder%20(3)/server/support_ops_env_environment.py)
- [tasks.py](/D:/New%20folder%20(3)/tasks.py)
- [graders.py](/D:/New%20folder%20(3)/graders.py)
- [Dockerfile](/D:/New%20folder%20(3)/Dockerfile)
- [inference.py](/D:/New%20folder%20(3)/inference.py)
