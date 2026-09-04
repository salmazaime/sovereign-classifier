-- A natural key for ENTITY: within one company, an entity is uniquely
-- identified by its type + name (e.g. one company can't have two
-- DATA_ASSETs both named "payroll_2026_07.csv"). This is what lets us
-- upsert instead of blindly inserting duplicates on every scan.
ALTER TABLE ENTITY
    ADD CONSTRAINT uq_entity_company_type_name
    UNIQUE (company_id, entity_type, name);
    

ALTER TABLE COMPANY
    ADD CONSTRAINT uq_company_name UNIQUE (name);
