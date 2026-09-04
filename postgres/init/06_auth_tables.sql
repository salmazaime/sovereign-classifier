-- Machine credentials, scoped per-company. NOT in the original ERD
-- -- a legitimate, necessary addition now that real auth exists.
-- key_hash stores a SHA-256 digest (see app/auth/api_keys.py for
-- why SHA-256, not bcrypt, is the correct choice here).
CREATE TABLE API_KEY (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL REFERENCES COMPANY(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    key_hash      TEXT NOT NULL UNIQUE,
    created_by    UUID REFERENCES USER_ACCOUNT(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked       BOOLEAN NOT NULL DEFAULT false,
    last_used_at  TIMESTAMPTZ
);

-- Partial index: only active keys are looked up on every authenticated
-- request, so indexing just the non-revoked rows keeps that lookup
-- fast without wasting index space on keys nobody will query by hash again.
CREATE INDEX idx_api_key_active_hash ON API_KEY(key_hash) WHERE revoked = false;

INSERT INTO ROLE (name, description) VALUES
    ('admin', 'Full administrative access within their company'),
    ('compliance_reviewer', 'Can resolve pending authorization requests'),
    ('compliance_officer', 'Can generate compliance evidence packs'),
    ('viewer', 'Read-only access to audit records')
ON CONFLICT (name) DO NOTHING;
