# AGENTS.md

## Project Overview

Cicada is a self-hosted API load and performance testing platform built with FastAPI and k6. The backend generates k6 scripts, launches disposable k6 Docker containers, collects live metrics, and streams results to the frontend via WebSockets.

## Technology Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker
- k6
- Vanilla JavaScript frontend

## Repository Structure

backend/
frontend/
data/
scripts/

## Architecture

- Keep API routes thin.
- Business logic belongs outside routers.
- Database access should remain centralized.
- k6 scripts are generated automatically.
- Each test run launches a disposable Docker container.

## Coding Guidelines

- Prefer clear, readable code over clever abstractions.
- Reuse existing helpers before introducing new ones.
- Follow the existing project structure.
- Avoid unnecessary dependencies.
- Keep functions focused on a single responsibility.

## Before Making Changes

- Read the surrounding code before modifying it.
- Search for existing implementations.
- Maintain backwards compatibility where possible.
- Update documentation when behavior changes.

## Do Not

- Commit generated files.
- Modify generated k6 scripts manually.
- Change API contracts without updating both backend and frontend.
- Introduce breaking architectural changes without clear justification.

## Testing

Verify that:

- Docker Compose starts successfully.
- Test execution still works.
- WebSocket updates remain functional.
- Existing endpoints continue to behave correctly.