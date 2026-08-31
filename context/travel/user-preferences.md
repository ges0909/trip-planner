---
inclusion: fileMatch
fileMatchPattern: "trips/**"
---

# Universal Travel Preferences

Rules for all trip types.

## User profile

- home base: Berlin / S Blankenfelde (TF) Bhf
- group size: 2 people
- trip styles: cycling day trips and multi-day road trips

## Language

- write user-facing content in the user's language
- use English kebab-case for code and file artifacts

## Core content rules

- no fabrication; only use verified sources or API results
- deduplicate POIs within ~200 m
- flag closures, seasonal limits, and opening-hour risks
- prefer official websites and sources
- add `ℹ️ Zuletzt geprüft: YYYY-MM-DD` for web-sourced data
- mark unverifiable info as `ℹ️ Nicht verifiziert.`

## Interest categories

- 🥾 hiking
- 🏊 swimming
- 🍷 regional food
- 🌿 botanical gardens
- 🎨 art
- 🏛️ landmarks

## Delivery expectations

Each trip should end with:

- a markdown file under `trips/.../`
- route data / GPX output where relevant
- map output or route visuals when needed

Everything more specific belongs in the type-specific context or skill files.
