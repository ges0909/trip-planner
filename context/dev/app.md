---
inclusion: fileMatch
fileMatchPattern: ["app/**"]
---

# App Development Guidelines

Rules for the web app in `app/`.

## Purpose

- IDE-native trip planning workflow
- standalone web UI for the same workflow
- results saved under `trips/`

## Core principles

- keep code simple and readable
- keep preferences in `context/` and workflows in `skills/`
- prefer short functions and clear state handling
- keep generated trips reproducible and commit-worthy

## Stack

- backend: FastAPI + Python
- frontend: Vue 3 + TypeScript + Vite + Tailwind
- map: Leaflet
- transport: SSE
- LLM: OpenRouter via its OpenAI-compatible API (model configurable with `LLM_MODEL`)

## Conventions

- typed backend functions
- structured tool results, not formatted strings at the tool boundary
- catch errors and emit `error` events instead of leaking exceptions
- keep user-facing text through i18n
- keep `.env` at project root; never commit it

## Important implementation rule

`core/context.py` assembles the runtime system prompt from the repo context and skill files.

Everything else is implementation detail.
