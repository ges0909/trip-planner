# Konzept: Plattformübergreifende KI-Agenten-Architektur

**STATUS: Konzeptuell.** Dieses Dokument beschreibt das ideale Architektur-Design. Die praktische Implementierung im Projekt nutzt eine vereinfachte Variante mit AGENTS.md Symlinks und der `skills/` + `context/` Struktur — siehe [README.md](../README.md) und [AGENTS.md](../AGENTS.md) für die aktuelle Realität.

Dieses Dokument definiert den standardisierten, werkzeugunabhängigen Umgang mit KI-Instruktionen (`AGENTS.md`, `CLAUDE.md`, etc.), MCP-Servern (`.mcp.json`) und modularen Erweiterungen (`SKILL.md`) im Projekt. Ziel ist eine Architektur, auf allen Betriebssystemen (`Windows`, `macOS`, `Linux`) identisch funktioniert und die Token-Kosten durch intelligentes On-Demand-Loading minimiert.

---

## 1. Die Ausgangslage

Moderne KI-Entwicklungswerkzeuge wie `Kiro`, `Claude Code`, `Cursor`, `Windsurf` oder `Antigravity` unterstützen den offenen [Agent Skills](https://agentskills.io/home)-Standard und Verzeichniskontexte. Sie fragmentieren das Projekt jedoch oft durch unterschiedliche Anforderungen:

- **Pfad-Konflikte**: Jedes Tool sucht standardmäßig in proprietären Unterverzeichnissen (z. B. `.claude/skills/` vs. `.kiro/skills/`).
- **Schnittstellen-Konflikte**: Einige Tools erwarten zwingend eine `CLAUDE.md`, andere eine `AGENTS.md` Root-Verzeichnis.
- **Betriebssystem-Barrieren**: Die Verknüpfung dieser Ordner via Symbolische Links (`ln -s`) bricht auf Windows-Systemen ohne Administratorrechte oder den Windows-Entwicklermodus (`core.symlinks = false`).
- **Kontext-Verschwendung (Token-Kosten)**: Werden alle Anweisungen unbesehen in eine einzige globale Datei kopiert, wird der System-Prompt überladen. Das erhöht Kosten, verlangsamt Antworten und verwirrt die KI.

---

## 2. Das Ziel: "Single Source of Truth" via Konfiguration

Wir trennen **statische, globale Anweisungen** (immer im Kontext) von **lokalen Verzeichnis-Regeln** und **dynamischen, modularen Fachkenntnissen** (nur bei Bedarf im Kontext). Als Datenbasis dienen herstellerneutrale Verzeichnisse im Repository-Root:

```text
mein-projekt/
├── skills/                       <-- SINGLE SOURCE OF TRUTH für Workflows (In Git versioniert)
│   ├── bike-planner/
│   │   ├── SKILL.md              <-- Modularer Fahrradtour-Skill mit YAML-Kopf
│   │   └── references/           <-- Vorlagen & Schema-Referenzen (optional)
│   └── road-planner/
│       ├── SKILL.md              <-- Modularer Roadtrip-Skill mit YAML-Kopf
│       ├── references/           <-- Vorlagen & Schema-Referenzen (optional)
│       └── scripts/              <-- Ausführbare Hilfsskripte & Assets (optional)
├── context/                      <-- SINGLE SOURCE OF TRUTH für Travel- & Dev-Preferences
│   ├── dev/
│   └── travel/
├── .vscode/
│   └── settings.json             <-- Pfad-Konfiguration für VS Code & Copilot
├── .mcp.json                     <-- SINGLE SOURCE OF TRUTH für MCP-Server (Alle Tools)
├── AGENTS.md                     <-- Die echte Source of Truth für globale Kern-Regeln
└── CLAUDE.md                     <-- Brückendatei mit Import (@AGENTS.md)
```

---

## 3. Umsetzung und Konfiguration

### Schritt 1: Globale & Verzeichnisbezogene Regeln (`AGENTS.md` / `CLAUDE.md`)

1. **Globale Regeln (`AGENTS.md` in Root):**
   Gilt universell für alle KI-Assistenten (Build-Befehle, Tech-Stack, Commit-Richtlinien, Rollenverteilung).

2. **Brückendatei für Claude Code (`CLAUDE.md` in Root):**
   Für Werkzeuge, die explizit nach einer `CLAUDE.md` suchen, nutzen wir die native Import-Syntax:

   ```markdown
   # Claude Code Instruktionen

   # Importiert die globalen Kern-Regeln vollautomatisch:

   @AGENTS.md
   ```

3. **Verzeichnis-spezifische Regeln (mit AGENTS.md Symlinks):**
   In Unterverzeichnissen (z.B. `trips/AGENTS.md`, `app/AGENTS.md`, `mcp/AGENTS.md`) platzieren wir echte Dateien als Symlinks zur Verzeichnis-Ebene (oder echte Dateien), die per `@context/...` auf die kanonischen Preferences verweisen:

   ```markdown
   # Web App Architecture & Guidelines

   @context/dev/app.md
   ```

**Rolle des Verzeichnisses `context/` (Wissen & Präferenzen):**

Das Verzeichnis `context/` dient als herstellerneutrale **Single Source of Truth für alle Fach- und Entwicklungs-Präferenzen**. Es trennt statische Regeln (Wissen) von aktiven Handlungsanweisungen (Workflows in `skills/`).

- **`context/travel/`**: Beinhaltet universelle und tour-spezifische Reisepräferenzen (`user-preferences.md`, `bike/bike-preferences.md`, `road/road-preferences.md`).
- **`context/dev/`**: Beinhaltet technische Architektur- und Entwickler-Guidelines (`app.md`, `mcp.md`).

**Duale Nutzung:**

1. **Für KI-Assistenten im Editor:** Verzeichnis-lokale `AGENTS.md`-Dateien binden diese Vorgaben per `@context/...` ein.
2. **Für das Web-App Backend:** Das Python-Backend (`app/backend/core/context.py`) liest exakt dieselben Dateien aus `context/travel/`, um den System-Prompt für das LLM in der Web-Anwendung dynamisch zusammenzubauen. Dadurch haben KI-Editor und Web-App einheitliches Wissen.

---

### Schritt 2: Modulare Skills herstellerneutral anlegen (`skills/`)

Jeder Skill liegt in einem eigenen Unterordner innerhalb des sichtbaren Top-Level-Ordners `skills/`. Ein Skill kann neben dem zentralen `SKILL.md` auch zwei optionale Unterordner enthalten:

- **`references/`**: Für zusätzliche Dokumentation, Schemas und Ausgabe-Templates.
- **`scripts/`**: Für auszuführende Hilfsskripte und zugehörige Assets (z. B. Karten-Render-Skripte), die exklusiv zu diesem Workflow gehören.

Das Herzstück ist der YAML-Kopf (Frontmatter) am Anfang der `SKILL.md`. Dieser steuert das **Progressive Disclosure** (schrittweise Offenlegung): Die KI liest beim Starten der Session nur die Metadaten. Der eigentliche, tokenintensive Inhalt wird erst geladen, wenn der Skill aktiv wird.

**Beispiel für `skills/bike-planner/SKILL.md`:**

```markdown
---
name: bike-planner
description: Aktivieren, wenn der Nutzer eine Radtour planen, BRouter-Routen berechnen oder ÖPNV/VBB-Anreisen prüfen möchte.
when_to_use:
  - Planung von Mehrtages- oder Tages-Radtouren
  - Berechnung von GPX-Tracks & Höhenprofilen
---

# 🚴 Bike Tour Planning Workflow

...
```

---

### Schritt 3: Werkzeuge auf die Source of Truth verweisen (Konfiguration & Symlinks)

#### 1. Konfiguration für VS Code, Kiro und Copilot (`.vscode/settings.json`)

Die Einstellung `chat.agentSkillsLocations` weist VS Code, Kiro und kompatible Agenten an, den neutralen `skills/`-Ordner anzusteuern:

```json
{
  "chat.agentSkillsLocations": ["skills"]
}
```

#### 2. Konfiguration für MCP-Server (`.mcp.json` im Root)

Die `.mcp.json` im Root-Verzeichnis dient als direkte Anlaufstelle für Claude Code, Cursor, Windsurf, Antigravity und VS Code MCP-Clients. Sie benötigt keine Symlinks in `.claude/` oder `.kiro/`.

---

## 4. Funktionsweise im Entwicklungsalltag

Nachdem die Konfiguration hinterlegt ist, werden die Skills auf zwei Wegen aktiviert:

1. **Automatische Aktivierung (KI-gesteuert):** Der Entwickler gibt eine Anfrage ein, z. B. _"Plane eine Radtour von Potsdam nach Brandenburg"_. Kiro, Claude Code oder Antigravity scannen die kurzen Beschreibungen im YAML-Kopf aller Skills in `skills/`. Die KI erkennt das Match mit `bike-planner`, aktiviert den Skill autonom und lädt die detaillierten Workflow-Regeln in den Chat-Kontext.
2. **Manuelle Aktivierung (Mensch-gesteuert):** Tippen von `/` (Slash) im Chat öffnet eine Autocomplete-Liste aller Skills aus `skills/`. Die Auswahl von `/bike-planner` erzwingt das Regelwerk sofort.

---

## 5. Git-Hygiene (`.gitignore`)

Damit herstellerspezifische Cache-Verzeichnisse oder lokale Tool-Konfigurationen nicht im gemeinsamen Git-Repository landen, werden lokale Tool-Ordner ignoriert. Die Single-Source-Ordner und Konfigurationsdateien bleiben explizit versioniert:

```gitignore
# Lokale KI-Tool-Verzeichnisse und Caches ignorieren
.claude/
.kiro/settings/mcp.json  # Aber .kiro/settings/ selbst ignorieren? Oder Symlink zulassen?
.cursor/
.windsurf/
.agents/

# Ausnahmen für globale Konfigurationsdateien
!.mcp.json
!.vscode/settings.json

# Die Single Source of Truth explizit einschließen
!skills/
!context/
```

---

## 6. Unterstützte KI-Agenten & Kompatibilitätsmatrix

| KI-Agent              | globale Regeln (`AGENTS.md`) | Unterordner-Regeln (`@context/...`) | Skills & Workflows (`skills/`)    | MCP-Server (`.mcp.json`) |
| :-------------------- | :--------------------------- | :---------------------------------- | :-------------------------------- | :----------------------- |
| **Antigravity**       | ✅ Nativ (User Rules)        | ✅ Nativ via `@import`              | ✅ Nativ (On-Demand & `scripts/`) | ✅ Nativ                 |
| **Claude Code**       | ✅ Nativ / `@AGENTS.md`      | ✅ Nativ via `@import`              | ✅ Nativ via `skills/`            | ✅ Nativ                 |
| **Kiro**              | ✅ Nativ                     | ✅ Nativ via `@import`              | ✅ Via `.vscode/settings.json`    | ⚠️ Symlink nötig         |
| **Cursor / Windsurf** | ✅ Nativ                     | ✅ Nativ via `@import`              | ✅ Nativ via `skills/`            | ✅ Nativ                 |

---

## Praktische Implementierung: Wie Copilot/Claude Code damit arbeitet

Das Projekt setzt dieses Konzept in einer vereinfachten Form um:

1. **Globale Regeln**: `AGENTS.md` (root) → Wird von Copilot/Claude Code automatisch gelesen
2. **CLAUDE.md Alias**: `CLAUDE.md` (root) → Importiert `@AGENTS.md`
3. **Verzeichnis-Regeln**: `trips/AGENTS.md`, `app/AGENTS.md`, `mcp/AGENTS.md` → Echte Dateien oder Symlinks, importieren via `@context/...`
4. **Preferences**: `context/travel/`, `context/dev/` → Echte Quellen, referenziert von AGENTS.md Dateien
5. **Workflows**: `skills/bike-planner/`, `skills/road-planner/` → SKILL.md mit YAML-Header, registriert in `.vscode/settings.json`
6. **MCP-Server**: `.mcp.json` (root) → Wird von Copilot/Claude Code nativ gelesen

**Resultat:** Copilot kennt alle Regeln, Präferenzen und Workflows über die Kombination aus globaler Basis (`AGENTS.md`) + Verzeichnis-Kontext (`AGENTS.md` lokal) + automatische Skill-Aktivierung (`skills/`) + MCP-Server (`.mcp.json`).

### Kiro: MCP-Server-Konfiguration

**Stand:** August 2026

Kiro liest MCP-Server-Konfigurationen ausschließlich aus `.kiro/settings/mcp.json` und ignoriert die etablierte `.mcp.json` im Projekt-Root. Dies erfordert aktuell einen Workaround:

```bash
# Symlink von Kiros Config-Pfad zur Single Source of Truth
ln -s ../../.mcp.json .kiro/settings/mcp.json
```

**Einschränkungen dieses Workarounds:**

- Symlinks funktionieren unter Windows nur mit Administratorrechten oder aktiviertem Entwicklermodus
- Git muss mit `core.symlinks = true` konfiguriert sein (nicht der Default unter Windows)
- Team-Mitglieder auf Windows müssen den Symlink ggf. manuell neu anlegen

**Empfehlung:** Wir akzeptieren den Symlink in der Hoffnung, dass Kiro den etablierten Standard `.mcp.json` im Projekt-Root künftig nativ unterstützt — wie es Claude Code, Cursor und Windsurf bereits tun.

**Alternative für Windows-Teams:** Falls Symlinks nicht praktikabel sind, kann ein Pre-Commit-Hook die Synchronisation übernehmen:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: sync-kiro-mcp
      name: Sync MCP config to Kiro
      entry: cp .mcp.json .kiro/settings/mcp.json
      language: system
      files: ^\.mcp\.json$
```
