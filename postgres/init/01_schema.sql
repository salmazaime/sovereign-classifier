-- Extension needed to generate UUIDs with gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- IDENTITY & ACCESS

CREATE TABLE COMPANY (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    sector      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ROLE (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE USER_ACCOUNT (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE USER_ROLE (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES USER_ACCOUNT(id) ON DELETE CASCADE,
    role_id      UUID NOT NULL REFERENCES ROLE(id) ON DELETE CASCADE,
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, role_id)
);

-- REGIONS

CREATE TABLE REGION (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT NOT NULL,
    country           TEXT NOT NULL,
    provider          TEXT NOT NULL,
    is_sovereign_zone BOOLEAN NOT NULL DEFAULT false
);

-- ENTITY  (merged DATA_ASSET + WORKLOAD_INFO)
-- NOTE: latest_canonical_schema_id FK added later (circular ref)

CREATE TABLE ENTITY (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id               UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    entity_type              TEXT NOT NULL CHECK (entity_type IN ('DATA_ASSET', 'WORKLOAD')),
    name                     TEXT NOT NULL,
    business_owner           TEXT,
    environment              TEXT,
    current_region_id        UUID REFERENCES REGION(id),
    latest_canonical_schema_id UUID,  -- FK added below, after CANONICAL_SCHEMA exists
    first_seen_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TRANSFER_REQUEST & INGESTION_RUN
-- (both must exist before CANONICAL_SCHEMA, which references them)

CREATE TABLE TRANSFER_REQUEST (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                  UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    entity_id                   UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE,
    operation                   TEXT NOT NULL,
    source_country               TEXT,
    source_deployment_type      TEXT,
    destination_country          TEXT,
    destination_deployment_type TEXT,
    initiated_by                TEXT,
    initiating_application       TEXT,
    status                      TEXT NOT NULL DEFAULT 'PENDING',
    requested_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE INGESTION_RUN (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    run_type      TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    items_pulled  INT DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'RUNNING'
);

-- CANONICAL_SCHEMA — the actual JSON payload 

CREATE TABLE CANONICAL_SCHEMA (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                  UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    entity_id                   UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE,
    transfer_request_id         UUID REFERENCES TRANSFER_REQUEST(id) ON DELETE SET NULL,
    ingestion_run_id            UUID REFERENCES INGESTION_RUN(id) ON DELETE SET NULL,
    phase                       TEXT NOT NULL CHECK (phase IN ('INITIAL_DISCOVERY', 'RUNTIME_TRANSFER')),
    discovery_connector_id      TEXT,   -- logical ref to client-side connector, NOT a DB-enforced FK
    interceptor_id              TEXT,   -- same — logical ref only
    plugin_used                 TEXT,
    payload                     JSONB NOT NULL,
    plugin_confidence            REAL,
    graph_enrichment_confidence  REAL,
    overall_confidence           REAL,
    is_latest                   BOOLEAN NOT NULL DEFAULT true,
    generated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE ENTITY
    ADD CONSTRAINT fk_entity_latest_canonical_schema
    FOREIGN KEY (latest_canonical_schema_id)
    REFERENCES CANONICAL_SCHEMA(id)
    ON DELETE SET NULL;

-- POLICY DECISIONS

CREATE TABLE POLICY_DECISION (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id            UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    entity_id             UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE,
    canonical_schema_id   UUID NOT NULL REFERENCES CANONICAL_SCHEMA(id) ON DELETE CASCADE,
    transfer_request_id   UUID REFERENCES TRANSFER_REQUEST(id) ON DELETE SET NULL,
    ingestion_run_id      UUID REFERENCES INGESTION_RUN(id) ON DELETE SET NULL,
    model_name            TEXT,
    model_version         TEXT,
    confidence_score      REAL,
    decision_features     JSONB,
    decision              TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'REVIEW')),
    is_current            BOOLEAN NOT NULL DEFAULT true,
    decided_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by             UUID REFERENCES USER_ACCOUNT(id)
);

CREATE TABLE AUTHORIZATION_REQUEST (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id         UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    policy_decision_id UUID NOT NULL REFERENCES POLICY_DECISION(id) ON DELETE CASCADE,
    reason             TEXT,
    status             TEXT NOT NULL DEFAULT 'PENDING',
    reviewed_by        UUID REFERENCES USER_ACCOUNT(id),
    decision_at         TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    cndp_reference      TEXT
);

CREATE TABLE HOMOLOGATION_RECORD (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    entity_id       UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE,
    confidence      REAL,
    submitted_at     TIMESTAMPTZ,
    certified_at     TIMESTAMPTZ,
    certificate_ref TEXT
);

CREATE TABLE DEPLOYMENT_ACTION (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id         UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    policy_decision_id UUID NOT NULL REFERENCES POLICY_DECISION(id) ON DELETE CASCADE,
    target_region_id   UUID REFERENCES REGION(id),
    mode               TEXT,
    status             TEXT NOT NULL DEFAULT 'PENDING',
    executed_at         TIMESTAMPTZ,
    executed_by         UUID REFERENCES USER_ACCOUNT(id),
    log_ref             TEXT
);

-- COMPLIANCE REPORTING

CREATE TABLE COMPLIANCE_EVIDENCE_PACK (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    generated_by  UUID REFERENCES USER_ACCOUNT(id),
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    period_start   DATE,
    period_end     DATE,
    report_path   TEXT
);

CREATE TABLE COMPLIANCE_EVIDENCE_ITEM (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pack_id            UUID NOT NULL REFERENCES COMPLIANCE_EVIDENCE_PACK(id) ON DELETE CASCADE,
    policy_decision_id UUID NOT NULL REFERENCES POLICY_DECISION(id) ON DELETE CASCADE,
    entity_type        TEXT,
    entity_id          UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE
);

-- LEGAL KNOWLEDGE BASE

CREATE TABLE LAW_DOCUMENT (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    version          TEXT,
    country          TEXT,
    issuing_authority TEXT,
    content_path     TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE LAW_CLAUSE (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    law_document_id UUID NOT NULL REFERENCES LAW_DOCUMENT(id) ON DELETE CASCADE,
    article_number  TEXT,
    content         TEXT,
    embedding_ref   TEXT
);

CREATE TABLE CLASSIFICATION_EVIDENCE (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_decision_id UUID NOT NULL REFERENCES POLICY_DECISION(id) ON DELETE CASCADE,
    law_clause_id      UUID NOT NULL REFERENCES LAW_CLAUSE(id) ON DELETE CASCADE,
    triggered_by       TEXT,
    status             TEXT
);

CREATE TABLE SECURITY_AUDIT_OBLIGATION (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_decision_id UUID NOT NULL REFERENCES POLICY_DECISION(id) ON DELETE CASCADE,
    entity_type        TEXT,
    entity_id          UUID NOT NULL REFERENCES ENTITY(id) ON DELETE CASCADE,
    triggers           TEXT,
    deadline           DATE,
    status             TEXT NOT NULL DEFAULT 'OPEN'
);

-- CHAT / ASSISTANT

CREATE TABLE CHAT_SESSION (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES USER_ACCOUNT(id) ON DELETE CASCADE,
    company_id  UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    topic       TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE CHAT_MESSAGE (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES CHAT_SESSION(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE INDEX idx_entity_company           ON ENTITY(company_id);
CREATE INDEX idx_canonical_schema_entity   ON CANONICAL_SCHEMA(entity_id);
CREATE INDEX idx_canonical_schema_latest   ON CANONICAL_SCHEMA(entity_id, is_latest);
CREATE INDEX idx_policy_decision_entity    ON POLICY_DECISION(entity_id);
CREATE INDEX idx_policy_decision_schema    ON POLICY_DECISION(canonical_schema_id);
CREATE INDEX idx_transfer_request_entity   ON TRANSFER_REQUEST(entity_id);
CREATE INDEX idx_law_clause_document       ON LAW_CLAUSE(law_document_id);

