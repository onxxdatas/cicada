# Cicada

A self-hosted API load & performance testing platform. Point it at an endpoint,
describe the load pattern in a form, and watch requests-per-second, latency and
error rate stream in live — no k6 scripts to hand-write, no CLI to remember.

Under the hood, every test run is executed as a disposable [k6](https://k6.io)
container. Cicada builds the k6 script for you, launches the container,
tails its metrics output, and streams the numbers to your browser over a
WebSocket.

## Quick start

**Prerequisites**

- Docker
- Docker Compose

**Run**

```
git clone https://github.com/yourusername/cicada
cd cicada
./scripts/setup-env.sh   # writes .env with the correct HOST_PROJECT_DIR
docker compose up -d
```

Open **http://localhost:3000** and create your first test.

That's it — Postgres, Redis, the API, the UI, and the k6 runner all start
together. Nothing else needs to be installed on your machine.

## How it works

```
┌────────────┐      REST + WS       ┌─────────────┐
│  Frontend  │ ───────────────────► │   Backend   │
│  (nginx)   │ ◄─────────────────── │  (FastAPI)  │
└────────────┘                      └──────┬──────┘
                                            │ docker.sock
                                            ▼
                                     ┌─────────────┐
                                     │  k6 runner  │  (spawned per test run)
                                     │ (container) │
                                     └──────┬──────┘
                                            │ writes NDJSON metrics
                                            ▼
                                     ./data/results/*.json
                                            │
                                     backend tails file,
                                     aggregates, broadcasts
                                     over WebSocket
```

1. You describe a test in the UI (target URL, method, headers, body,
   virtual users, load stages, thresholds).
2. The backend renders that into a real k6 script
   (`app/k6_script_generator.py`) and writes it to `./data/scripts/`.
3. The backend talks to the **host** Docker daemon via the mounted
   `docker.sock` (the same "Docker-outside-of-Docker" pattern Jenkins agents
   use) and launches `grafana/k6` with the script mounted in, on the same
   compose network as the rest of the stack — so it can hit other services
   in the project by their compose service name, or any external URL.
4. k6 is told to write its metrics stream to `./data/results/<run_id>.json`
   as NDJSON. The backend tails that file as it grows, aggregates it into
   1-second buckets (vus, RPS, p95 latency, error rate) and pushes each
   bucket to any browser subscribed to `/ws/runs/{run_id}`.
5. When the container exits, the backend reads the k6 summary, stores it in
   Postgres against the run, and closes the socket.

## Project layout

```
cicada/
├── backend/            FastAPI app, k6 script generator, docker runner
├── frontend/            Static HTML/CSS/JS UI, served by nginx
├── data/                Shared bind mount: generated scripts + raw results
├── scripts/             Helper shell scripts
├── docker-compose.yml
└── .env.example
```

## Windows

If you're on Docker Desktop with the WSL2 backend, run `setup-env.sh` from
inside a WSL shell (not PowerShell) so `HOST_PROJECT_DIR` comes out as a
Linux-style path Docker Desktop can translate correctly.

## A note on the docker.sock mount

The backend container is given access to `/var/run/docker.sock` so it can
launch k6 containers on demand. This effectively gives the backend
root-equivalent control of the host's Docker daemon — fine for a self-hosted
tool you run on your own machine or a trusted internal server, but treat it
the same way you'd treat a Jenkins controller: don't expose the backend's
port to the open internet without authentication in front of it.

## Environment variables

See `.env.example`. The one that matters most locally is
`HOST_PROJECT_DIR` — it must be the **absolute host path** to this project
directory, because the backend asks the host Docker daemon to bind-mount
`./data` into the k6 containers it spawns, and the daemon only understands
host paths, not paths inside the backend container.

## Extending it

- Swap the JSON summary columns for a proper metrics table if you want
  cross-run comparison queries.
- Add an auth layer (even HTTP basic auth in nginx) before exposing this
  beyond localhost.
- Point k6 at `--out experimental-prometheus-rw` instead of the file tail
  if you already run Prometheus/Grafana and want richer dashboards.
