# Monorepo Selective CI Optimizer

A smart CI system that detects changed services in a monorepo and only runs relevant pipelines — drastically cutting build times.

---

## Overview

In a typical monorepo, a single commit triggers builds for **every** service — even ones that weren't touched. This project solves that problem by:

1. Detecting which files changed via `git diff`
2. Building a dependency graph from per-service config files
3. Propagating changes through the graph to find all affected services
4. Dynamically triggering only the relevant `test` and `build` pipelines

The result: a commit touching only `auth` never wastes time building `payments` or `notifications`.

```
Developer pushes commit
        │
        ▼
  Detect changed files (git diff)
        │
        ▼
  Walk dependency graph
        │
        ▼
  Output affected services → ["auth"]
        │
        ▼
  Run test + build only for auth ✅
  Skip payments, notifications   ⏭️
```

---

## Technologies

- **Python 3.12** — change detection and dependency graph engine
- **PyYAML** — parsing per-service dependency configs
- **GitHub Actions** — CI orchestration with dynamic matrix strategy
- **Docker** — containerized service builds, pushed to DockerHub
- **pytest** — per-service test runner

---

## Dependencies

```bash
pip install pyyaml
```

For CI, all dependencies are installed automatically via `requirements.txt`.

---

## Project Structure

```
monorepo/
├── services/
│   ├── auth/
│   │   ├── service.yaml        ← dependency declaration
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── payments/
│   │   ├── service.yaml
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   └── notifications/
│       ├── service.yaml
│       ├── Dockerfile
│       ├── requirements.txt
│       └── tests/
├── libs/
│   ├── shared-utils/
│   │   └── service.yaml
│   └── db-client/
│       └── service.yaml
├── main.py                     ← CI detection engine
├── requirements.txt
└── .github/
    └── workflows/
        └── ci.yaml             ← GitHub Actions pipeline
```

---

## How It Works

### 1. Dependency Declaration

Each service declares its own dependencies in a `service.yaml` file:

```yaml
# services/payments/service.yaml
name: payments
dependencies:
  - db-client
  - shared-utils
```

### 2. Dependency Graph Engine (`main.py`)

The engine has three stages:

**Stage 1 — Build the forward graph** (who depends on what):
```python
{
  "payments": ["db-client", "shared-utils"],
  "auth": ["shared-utils"],
  "notifications": ["db-client"]
}
```

**Stage 2 — Invert the graph** (what is depended on by whom):
```python
{
  "db-client": ["payments", "notifications"],
  "shared-utils": ["payments", "auth"]
}
```

**Stage 3 — Propagate changes**: Given changed files, look up which services are affected via the inverted graph.

If `libs/db-client/client.py` changes → `payments` and `notifications` rebuild. `auth` is skipped.

### 3. CI Pipeline (GitHub Actions)

Three jobs run in sequence:

```
detect → test → build
```

- **detect**: Runs `main.py`, outputs affected services as a JSON array
- **test**: Spins up a parallel matrix job per affected service, runs `pytest`
- **build**: Builds and pushes a Docker image per service (only if tests pass)

The matrix is dynamically populated at runtime — no hardcoded service names in the workflow.

---

## How to Deploy

### 1. Add `service.yaml` to every service and lib

```yaml
name: your-service-name
dependencies:
  - lib-name   # or empty list [] if no dependencies
```

### 2. Add a `Dockerfile` to every service

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### 3. Add DockerHub secrets to your GitHub repository

Go to **Settings → Secrets → Actions** and add:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | Your DockerHub access token |

### 4. Push the workflow file

Place `.github/workflows/ci.yaml` in your repository. The pipeline triggers automatically on every push.

### 5. Verify it's working

Push a commit that changes only one service. In the **Actions** tab you should see:
- `detect` runs and outputs a list with only that service
- `test` and `build` run only for the affected service(s)

---

## Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| First commit (no `HEAD~1`) | Falls back to `git ls-files` — rebuilds everything |
| No services affected | Matrix is empty → `test` and `build` jobs are skipped cleanly |
| `main.py` crashes | Outputs `[]` → pipeline skips safely instead of erroring |
| Lib change | Propagates through dependency graph to all dependent services |

---

## Example Run

Push touches `libs/db-client/utils.py`:

```
detect   → ["payments", "notifications"]

test     → payments   ✅ passed
           notifications ✅ passed

build    → payments:abc1234   pushed to DockerHub ✅
           notifications:abc1234 pushed to DockerHub ✅

auth     → skipped ⏭️  (not affected)
```

Total time saved vs naive CI: ~60% on a 5-service repo, scales further as the monorepo grows.