---
inclusion: fileMatch
fileMatchPattern: "trips/bike/**"
---

# Bike Tour Preferences

Rules for cycling day trips in Berlin/Brandenburg.

## Default trip profile

- distance: 40–80 km, ideal 55–65 km
- duration: 4–6 hours riding
- terrain: flat preferred, max ~400 m total climb
- start: around 09:00 from S Blankenfelde (TF) Bhf
- group: 2 people + 2 bikes
- transit: VBB regional trains, no long detours

## Priority order

When a stop offers multiple interests, keep this order:

1. 🏊 swimming
2. 🍷 food / beer garden / café
3. 🌿 botanical gardens
4. 🎨 art
5. 🏛️ landmarks

## Hard rules

- prefer official sources and current web checks
- flag seasonal closures and booking needs with `⚠️`
- deduplicate nearby POIs within ~200 m
- use `ℹ️ Zuletzt geprüft: YYYY-MM-DD` for web-sourced content
- do not recommend chains or generic fast food
- keep route and POI map markers aligned

## Output expectations

For each tour:

- include a few strong swimming and food stops
- keep the route simple and realistic for the home base
- note transit and weather briefly but clearly
- include GPX + map outputs in `trips/bike/`

This file is intentionally short; the detailed operational steps live in the skill and output template files.
