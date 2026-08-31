---
name: road-planner
description: >-
  Plan a multi-day European car trip with route, flights, daily stops, and travel notes.
---

# Road Trip Planner

Use this for multi-day car road trips across Europe. Keep the workflow targeted and grounded in the repo preferences.

## Start here

Always read first:

- `trips/AGENTS.md`
- `trips/road/AGENTS.md`
- `skills/road-planner/references/output-template.md`

## Hard rules

- Use `[longitude, latitude]` for all route and geocode calls.
- Route every segment through `osrm` before finalizing the day plan.
- Keep driving days under ~4 hours if possible.
- Validate major facts with web search or API data; never invent details.
- Keep route text, maps, and stop names aligned.
- Respect the same-city / buffer rules from `trips/road/AGENTS.md`.

## Allowed servers

- `ors`
- `osrm`
- `overpass`
- `open-meteo`
- `wikivoyage`
- `waymarkedtrails`
- `serpapi-flights`
- `podcasts` (optional enrichment)

## Preferred workflow

1. Check travel advisories and flight options first.
2. Build a logical stop sequence and geocode each stop.
3. Route each day with `osrm` and flag long segments.
4. Enrich each stop with Wikivoyage and local web research.
5. Add weather, hiking, swimming, and cultural notes where relevant.
6. Save the trip under `trips/road/` using the required template.

## What to prioritize

- route logic and day structure
- realistic travel times
- verifiable POIs and attractions
- weather and seasonal risks
- proper output format and file naming

## Output requirements

Every road trip should include:

- daily drive plan
- stop-by-stop highlights
- flight note if relevant
- weather note
- final markdown in the required template
- GPX files and maps under `trips/road/`

## Good defaults

- Prefer logical loops and compact route design.
- Take a conservative approach to driving time and stop density.
- Prefer informative, well-sourced notes over broad filler.
- Add `ℹ️ Zuletzt geprüft: YYYY-MM-DD` when refreshing trip content.

Keep the work driven by route quality, user preferences, and final-document quality rather than exhaustive tool-detail exploration.
