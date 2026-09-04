```markdown
# Sovereignty Compliance Platform

A multi-cloud data sovereignty enforcement platform for Moroccan data protection law (Loi 09-08, Loi 05-20), built as an end-to-end system: real-time cloud discovery, a rule-based legal decision engine, CI/CD-integrated policy enforcement, human review workflows, and compliance audit reporting.

Built on **Atlas Cloud** infrastructure.

---

## The problem

Moroccan data sovereignty law isn't one rule — it's two independent legal axes:

- **Loi 09-08** governs *what kind of data* is being processed and under what conditions it may leave the country (adequacy decisions, derogations, CNDP authorization).
- **Loi 05-20** governs *where sensitive infrastructure must physically reside*, with a stricter regime for entities designated as *Infrastructure d'Importance Vitale* (OIV).

Most compliance tooling treats "can this data leave the country" as a single yes/no flag. This platform treats it as what it actually is: a legal decision with citable statutory basis, a full audit trail, and a human-in-the-loop path for the cases automation legitimately cannot resolve on its own.

## What it does

1. **Discovers** infrastructure across AWS and Azure (S3, Blob Storage, EC2, VMs) and scans content for legally-defined sensitive categories (national ID, health, genetic, religious/political, union, criminal record, ordinary PII) — including graceful, fail-cautious handling of unscannable formats (video, executables, archives).
2. **Intercepts** infrastructure changes at the CI/CD layer — parsing real Terraform and Kubernetes manifests in a GitHub Actions pipeline, before deployment, and blocking non-compliant pushes with a real exit code.
3. **Decides** every transfer against a deterministic, fully-tested legal rule engine, citing the specific law article or decree behind each verdict.
4. **Escalates** ambiguous cases to a human reviewer, race-condition-safe, with a full "why this needs review" explanation reconstructed from the engine's own reasoning — not a black box.
5. **Audits** every decision with an append-only history (nothing is ever overwritten, only superseded), exportable as a detailed PDF evidence pack.
6. **Enforces tenant isolation** — every company's data, decisions, and infrastructure are structurally isolated from every other company on the platform.

---

## Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│   Client-side (portable)    │        │        Atlas Cloud Platform        │
│                              │  HTTPS │                                    │
│  ┌────────────────────────┐ │  only  │  ┌──────────────┐  ┌────────────┐ │
│  │ Discovery Connectors    │─┼───────▶│  │  FastAPI     │  │ PostgreSQL │ │
│  │ (AWS / Azure scanners)  │ │        │  │  REST API    │◀─┤ (system    │ │
│  └────────────────────────┘ │        │  │              │  │  of record)│ │
│                              │        │  └──────┬───────┘  └────────────┘ │
│  ┌────────────────────────┐ │        │         │                          │
│  │ CI/CD Interceptor       │─┼───────▶│  ┌──────▼───────┐  ┌────────────┐ │
│  │ (Terraform/K8s parser,  │ │        │  │ Rule-Based   │  │   Neo4j    │ │
│  │  GitHub Actions gate)   │ │        │  │ Decision     │  │ (knowledge │ │
│  └────────────────────────┘ │        │  │ Engine       │  │  graph)    │ │
│                              │        │  └──────────────┘  └────────────┘ │
└──────────────────────────────┘        │                                    │
                                         │  Dashboard (Jinja2 + vanilla JS)   │
                                         └────────────────────────────────────┘
```

- **Client-side components** (discovery connectors, CI/CD interceptor) run entirely outside Atlas Cloud, on the client's own infrastructure, communicating exclusively over authenticated HTTP. They never import a database driver directly — a client can run these on any machine with network access to the platform API.
- **PostgreSQL** is the single source of truth: companies, entities, canonical schema history, policy decisions, authorization requests, audit evidence — all append-only where legally required.
- **Neo4j** models infrastructure dependency relationships (which workload depends on which data asset), enabling impact-radius queries the relational model can't express efficiently.

---

## Key design decisions

| Decision | Why |
|---|---|
| Decision engine is a **pure, deterministic function** — no DB/network calls inside it | Fully unit-testable, and every past decision is exactly reproducible from its stored inputs — essential for an audit trail. |
| **Residency lock overrides adequacy** unconditionally | A "good" destination country can never bypass a hard data-localization requirement — this is enforced as a hard gate, not a weighted signal. |
| **Fail-cautious defaults everywhere** (assume public, assume unencrypted, assume review-required on missing data) | On uncertainty, the system errs toward flagging risk, never toward silently approving it. |
| **Human review resolutions are new rows, never overwrites** | The engine's original verdict and the human's final call both remain in the permanent record — nobody can retroactively edit what the system originally found. |
| **API keys (SHA-256) for machines, JWT (bcrypt-backed passwords) for humans** | Different threat models: a 256-bit random secret needs no slow hashing; a human password does. |
| **Every company-scoped endpoint independently verifies tenant ownership** | Authentication alone doesn't prevent cross-tenant data access (OWASP API1) — every route checks the resource actually belongs to the caller's company, not just that the caller is logged in. |
| **"Why review" is reconstructed from the engine's own reasoning, not a fabricated confidence score** | The decision engine is deterministic, not probabilistic — it has no real "80% sure" to report. What it does have is a specific, honest reason it stopped short of a verdict, surfaced in plain language to the reviewer. |

---

## Tech stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2
- **Databases**: PostgreSQL 16 (system of record), Neo4j 5 (dependency graph)
- **Auth**: PyJWT, passlib/bcrypt, SHA-256 API keys
- **Cloud SDKs**: boto3 (AWS), azure-mgmt-* (Azure)
- **IaC parsing**: python-hcl2 (Terraform), PyYAML (Kubernetes)
- **Content analysis**: regex + keyword detection, pypdf, pytesseract (OCR)
- **Frontend**: Jinja2 server-side templates, vanilla JS, Chart.js, jsVectorMap, Flatpickr, Font Awesome — no build toolchain
- **PDF generation**: fpdf2
- **Observability**: structured JSON logging with request correlation, Prometheus metrics
- **Containerization**: multi-stage Docker build, Docker Compose

---

## Project structure

```
sovereign-classifier/
├── app/
│   ├── api/                # Core REST routes
│   ├── auth/                # JWT + API key authentication, RBAC
│   ├── connectors/          # AWS/Azure discovery, content detection
│   ├── db/                  # PostgreSQL repository layer
│   ├── graph/                # Neo4j repository layer
│   ├── ingestion/            # Discovery-finding ingestion pipeline
│   ├── interceptor/           # CI/CD gate (IaC parsers, orchestration)
│   ├── observability/         # Logging, metrics, request context
│   ├── policy/                # Decision engine, lookup tables, explainability
│   ├── compliance/            # PDF audit report generation
│   ├── static/                # CSS, JS, images
│   ├── templates/             # Jinja2 dashboard pages
│   └── schemas.py             # Pydantic models (validation boundary)
├── config/                    # Legal lookup tables (adequacy list, qualified providers)
├── postgres/init/             # Database schema migrations
├── scripts/                   # Discovery runner, CI interceptor entry point, seed scripts
├── tests/                     # Unit + integration tests
├── .github/workflows/         # Sovereignty compliance CI gate
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Quickstart

```bash
git clone https://github.com/salmazaime/sovereign-classifier
cd sovereign-classifier
cp .env.example .env    # fill in real secrets — never commit .env
docker compose up --build
```

This brings up PostgreSQL, Neo4j, and the API/dashboard with one command. Verify:

```bash
curl http://localhost:8000/health
```

Seed a reviewer account and the legal knowledge base:

```bash
docker compose exec app python -m scripts.seed_admin_user
docker compose exec app python -m scripts.seed_law_knowledge_base
```

Dashboard: **http://localhost:8000/dashboard/**

> ⚠️ **Never commit `.env`.** Generate a real `JWT_SECRET_KEY` with `openssl rand -hex 32` and unique database passwords before any deployment beyond local development.

---

## Core API surface

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` / `POST /auth/login` | Company + admin account creation, session issuance |
| `POST /ingest` | Discovery/interceptor findings enter the system (API key auth) |
| `POST /transfer-request` | The decision engine evaluates a specific transfer |
| `GET /transfer-request/{id}/status` | Poll a pending review's resolved status |
| `POST /deployment-actions` | Server-side re-validated proof that a deployment was actually cleared |
| `GET /companies/{id}/reviews` / `POST /reviews/{id}/resolve` | Human review queue and race-safe resolution |
| `GET /policy-decisions/{id}/audit` | Full reconstructed justification for one decision |
| `GET /policy-decisions/{id}/review-reasoning` | Plain-language explanation of why automation couldn't resolve a case |
| `GET /policy-decisions/{id}/infrastructure` | Full infrastructure and provenance detail (cloud, account, who pushed it, when) |
| `GET /companies/{id}/geo-distribution` | Aggregated destination-country data powering the dashboard map |
| `POST /compliance/evidence-packs` + `.../document` | Compliance report generation and PDF export |

Full interactive docs at `/docs` once running.

---

## Testing

```bash
pytest tests/ -v -m "not integration"      # fast unit suite, no live services needed
pytest tests/ -v -m integration            # requires running Postgres/Neo4j
```

The decision engine, status resolution logic, and interceptor routing are all pure functions tested with zero I/O — the highest-value tests in the suite are the ones proving the residency-lock override and the fail-closed-on-expiry behavior hold under every input.

---

## Known limitations (by design, not oversight)

- **Video/executable/archive content is flagged for manual review, not deep-scanned.** Real content analysis of these formats (frame-level OCR, binary disassembly) is a materially different engineering discipline from document/text scanning and was deliberately out of scope — the system fails toward caution here rather than pretending to a capability it doesn't have.
- **AWS account ID resolution in the CI/CD interceptor requires live credentials in the pipeline environment.** Static Terraform files don't encode account identity; when credentials are available (e.g., via OIDC-federated GitHub Actions), it's resolved via a live STS call — when not, it's explicitly marked `unknown`, never guessed.
- **The interceptor's loose-file content scan is informational, not a transfer-blocking gate.** It answers "is there sensitive content sitting in this repo," a secrets-in-git concern better served by dedicated tools (gitleaks, trufflehog) — not "can this data legally leave the country," which requires a declared destination the file scan doesn't have.
- **Prometheus metrics are in-process and reset on container restart.** Postgres remains the durable source of truth for all decision history; metrics are a live operational snapshot, not a permanent record.
- **The `qualified_providers.json` and `cndp_adequacy_countries.json` lookup tables ship with placeholder entries** and must be populated with the actual, currently-published CNDP/decree lists before any production use.

---

## Legal basis

- **Loi 09-08** — Protection of individuals with regard to the processing of personal data
- **Loi 05-20** — Cybersecurity of vital infrastructure and sensitive information systems
- **Decree 2.24.921** — Qualified cloud/hosting provider requirements for sensitive and OIV data

---

## Author

Built as a PFE (Projet de Fin d'Études) internship project — Atlas Cloud.
```
