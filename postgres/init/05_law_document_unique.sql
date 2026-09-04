ALTER TABLE LAW_DOCUMENT ADD CONSTRAINT uq_law_document_name_version UNIQUE (name, version);

ALTER TABLE LAW_CLAUSE ADD COLUMN policy_reference_code TEXT UNIQUE;
