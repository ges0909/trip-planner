# Konzept:Plattformübergreifende KI-Agenten-Architektur

Dieses Dokument definiert den standardisierten, werkzeugunabhängigen Umgang mit KI-Instruktionen (`CLAUDE.md`, `AGENTS.md`, etc.) und modularen Erweiterungen (`SKILL.md`) im Projekt. Ziel ist eine Architektur, die ohne fehleranfällige Dateiverknüpfungen (Symlinks) auskommt, auf allen Betriebssystemen (`Windows`, `macOS`, `Linux`) identisch funktioniert und die Token-Kosten durch intelligentes On-Demand-Loading minimiert.

---

## 1. Die Ausgangslage und das Problem

Moderne KI-Entwicklungswerkzeuge wie Kiro, Claude Code, Cursor oder Windsurf unterstützen den offenen "Agent Skills"-Standard. Sie fragmentieren das Projekt jedoch durch unterschiedliche Anforderungen an die Ordnerstruktur:

- **Pfad-Konflikte**: Jedes Tool sucht standardmäßig in einem anderen, proprietären Verzeichnis (z. B. `.claude/skills/` vs. `.agents/skills/`).
- **Schnittstellen-Konflikte**: Einige Tools erwarten zwingend eine CLAUDE.md, andere verlangen eine AGENTS.md im Hauptverzeichnis.
- **Betriebssystem-Barrieren**: Die Verknüpfung dieser Ordner via Symbolische Links (ln -s) bricht auf Windows-Systemen ohne Administratorrechte oder den Windows-Entwicklermodus.
- **Kontext-Verschwendung (Token-Kosten)**: Werden alle Anweisungen unbesehen in eine einzige globale Datei kopiert, ist der System-Prompt bei jeder trivialen Anfrage überladen. Das erhöht die Kosten, verlangsamt die Antwortzeiten und verwirrt die KI.

---

## 2. Die Ziel-Architektur: "Single Source of Truth" via Konfiguration

Wir trennen **statische, globale Anweisungen** (immer im Kontext) von **dynamischen, modularen Fachkenntnissen** (nur bei Bedarf im Kontext). Als Datenbasis dient ein herstellerneutrales Verzeichnis.

```text
mein-projekt/
├── .skills/                      <-- SINGLE SOURCE OF TRUTH (In Git versioniert)
│   ├── api-tester/
│   │   └── SKILL.md              <-- Modularer API-Skill mit YAML-Kopf
│   └── db-helper/
│       └── SKILL.md              <-- Modularer Datenbank-Skill mit YAML-Kopf
├── .vscode/
│   └── settings.json             <-- Pfad-Konfiguration für VS Code & Kiro
├── AGENTS.md                     <-- Die echte Single Source für globale Regeln
└── CLAUDE.md                     <-- Die Brückendatei (Automatisch verknüpft)
```

## 3. Umsetzung und Konfiguration

### Globale & Statische Regeln (`CLAUDE.md` / `AGENTS.md`)

Für grundlegende Projektinfos (Build-Befehle, Tech-Stack, Code-Style) nutzen wir eine `AGENTS.md` im Root-Verzeichnis.

```markdown
# Projektanweisungen (Core Context)

## Tech-Stack

- Node.js v24, TypeScript, Vitest

## Build & Test Befehle

- Build: `npm run build`
- Tests: `npm run test`
```

Die Datei `AGENTS.md` dient als einzige, echte Quelle (_Source of Truth_). Für Werkzeuge wie Claude Code, die explizit nach einer `CLAUDE.md` suchen, nutzen wir die native Import-Syntax des Standards.

```markdown
# Claude Code Instruktionen

# Importiert die globalen Kern-Regeln vollautomatisch:

@AGENTS.md

## Claude-spezifische Parameter

- CLI-Startbefehl: `claude --skills-path .skills`
```

### Schritt 2: Modulare Skills herstellerneutral anlegen

Jeder Skill liegt in einem eigenen Unterordner innerhalb von `.skills/`. Das Herzstück ist der YAML-Kopf (Frontmatter) am Anfang der `SKILL.md`. Dieser steuert das **Progressive Disclosure** (schrittweise Offenlegung): Die KI liest beim Starten der Session nur die Metadaten. Der eigentliche, tokenintensive Inhalt wird erst geladen, wenn der Skill aktiv wird. 

**Beispiel für `.skills/api-tester/SKILL.md`:** 

```markdown
---
name: api-tester
description: Aktivieren, wenn der Nutzer API-Endpunkte testen, HTTP-Requests simulieren oder Integrationstests schreiben möchte.
when_to_use:
  - Erstellen von Endpunkt-Tests mit Supertest
  - Debugging von HTTP-Statuscodes und REST-Schnittstellen
---

# 🛠️ API Testing Workflow

## 1. Test-Struktur

- Nutze für jeden Endpunkt einen separaten `describe`-Block, z. B. `describe('GET /api/v1/users')`.
- Mocke externe Dienste konsequent über `msw` (Mock Service Worker).

## 2. Sicherheits-Vorgaben

- Teste jeden geschützten Endpunkt explizit auf ein fehlendes oder ungültiges Bearer-Token (erwarteter Status: 401 Unauthorized).
```

### Schritt 3: Werkzeuge auf die Source of Truth verweisen

Anstatt Dateien im Dateisystem zu duplizieren, teilen wir den Werkzeugen über ihre Konfiguration mit, wo sie nach den Skills suchen sollen. Dies eliminiert Symlink-Probleme. 

#### 1. Konfiguration für VS Code und Kiro

Erstellen oder erweitern Sie die Datei `.vscode/settings.json` im Projekt. Die Einstellung `chat.agentSkillsLocations` zwingt Kiro und alle VS-Code-basierten Agenten dazu, den neutralen Ordner direkt anzusteuern: 

```json
{
  "chat.agentSkillsLocations": [".skills"]
}
```

#### 2. Konfiguration für Claude Code (CLI)

Claude Code wird beim Start im Terminal über einen expliziten Parameter an den projektweiten Ordner gekoppelt: 

```bash
claude --skills-path .skills
```

### 4. Funktionsweise im Entwicklungsalltag

Nachdem die Konfiguration hinterlegt ist, werden die Skills auf zwei Wegen aktiviert: 

1. **Automatische Aktivierung (KI-gesteuert):** Sie geben im Chat eine Prompt-Eingabe ein, wie zum Beispiel: _"Schreibe einen Test für die Registrierungs-Route"_. `Kiro` oder `Claude Code` scannen die kurzen Beschreibungen im YAML-Kopf aller Skills. Die KI erkennt das Match mit dem `api-tester`, aktiviert den Skill autonom und lädt die detaillierten Workflow-Regeln genau in diesem Moment in den Chat-Kontext.
2. **Manuelle Aktivierung (Mensch-gesteuert):** Sie möchten sicherstellen, dass die Regeln sofort gelten. Sie tippen im Chat ein **/** (Slash). Der Editor öffnet eine Autocomplete-Liste aller Skills aus `.skills/`. Wählen Sie `/api-tester` aus, um das gesamte Expertenwissen für die aktuelle Session sofort zu erzwingen.

### 5. Git-Hygiene (.gitignore)

Damit herstellerspezifische Cache-Verzeichnisse oder lokale Tool-Konfigurationen nicht im gemeinsamen Git-Repository landen, wird die `.gitignore` wie folgt angepasst. Der neutrale `.skills/`-Ordner bleibt hiervon unberührt und wird ganz normal versioniert: 

```text
# Lokale KI-Tool-Verzeichnisse und Caches ignorieren

.claude/
.cursor/
.windsurf/
.agents/

# Ausnahmen für globale Konfigurationsdateien (falls benötigt)

!.claude.json

# Die Single Source of Truth explizit einschließen

!.skills/
```
