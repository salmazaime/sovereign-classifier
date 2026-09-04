-- These belong on COMPANY, not on any individual ENTITY or
-- CANONICAL_SCHEMA row, because OIV status is a designation on the
-- ORGANIZATION (per Loi 05-20), not on any single asset it owns.
ALTER TABLE COMPANY
    ADD COLUMN is_oiv BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN oiv_sector TEXT,
    ADD COLUMN qualified_provider_required BOOLEAN NOT NULL DEFAULT false;

    