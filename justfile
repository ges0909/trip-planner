# Submodules for frontend and backend
mod frontend 'app/frontend/justfile'
mod backend 'app/backend/justfile'

# List available development commands.
[private]
default:
    @just --list

# Install all dependencies (run once after cloning).
install: frontend::install

# Start frontend and backend together.
[parallel]
dev: backend::dev frontend::dev

# Kill all running dev processes (uvicorn + vite).
[parallel]
kill: backend::kill frontend::kill

# Format frontend and backend source files.
[parallel]
format: backend::format frontend::format

# Check linting and formatting without modifying files.
[parallel]
lint: backend::lint frontend::lint

# Run all available tests.
[parallel]
test: backend::test frontend::test

# Run full project checks (lint, format, types, tests).
[parallel]
check: backend::check frontend::check

# Run backend test coverage with terminal report.
coverage *args: backend::coverage

# Run backend test coverage and generate HTML report.
coverage-html: backend::coverage-html

# Run security audit on frontend dependencies.
audit *args:
    just frontend::audit {{ args }}

# Automatically fix security vulnerabilities in frontend packages.
audit-fix *args:
    just frontend::audit-fix {{ args }}
