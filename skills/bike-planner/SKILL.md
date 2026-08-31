---
name: bike-planner
description: >-
  Plan a cycling day trip in Berlin/Brandenburg with route, transit, POIs, weather, and GPX export.
---

# Bike Tour Planner

Use this for cycling day trips near Berlin/Brandenburg. Keep the workflow compact and grounded in the repo rules.

## Start here

Always read first:

- `trips/AGENTS.md`
- `trips/bike/AGENTS.md`
- `skills/bike-planner/references/output-template.md`

## Hard rules

- Use `[longitude, latitude]` for all coordinates.
- Use absolute paths for map/export tools.
- Query Overpass sequentially; never parallelize.
- Verify transit with VBB before claiming connections or travel times.
- Keep map markers and text in sync.
- Never invent facts; if something is unknown, say so.
- Flag seasonal closures and booking requirements with `⚠️`.

## Scope

- region: Berlin/Brandenburg
- home base: S Blankenfelde (TF) Bhf
- preferred trip profile: 40–80 km, 4–6 hours riding, mostly flat, around 09:00 start

## Allowed servers

- `brouter`
- `overpass`
- `open-meteo`
- `vbb`
- `waymarkedtrails`

## Preferred workflow

1. Search a route or region in `waymarkedtrails` if useful.
2. Geocode and calculate the route in `brouter`.
3. Check POIs along the route with `overpass`.
4. Verify public transport and disruptions with `vbb`.
5. Fetch weather for the route date with `open-meteo`.
6. Write the final tour markdown and save the outputs under `trips/bike/`.

## Output needs

Every tour should include:

- route summary
- transit notes
- relevant POIs
- weather note
- final markdown in the required output template
- GPX + map files in `trips/bike/`

## Content priorities

Use the order in `trips/bike/AGENTS.md` and emphasize:

- 🏊 swimming
- 🍷 food / beer garden / cafe
- 🌿 botanical gardens
- 🎨 art
- 🏛️ landmarks

## Good defaults

- Prefer safe bike routes and clear route logic.
- Keep POIs curated and deduplicated.
- Prefer official websites and verified data.
- Add `ℹ️ Zuletzt geprüft: YYYY-MM-DD` for web-sourced content.

If the user asks for a trip, keep the task centered on route quality, reliability, and final output structure rather than exploring unrelated tool details.
