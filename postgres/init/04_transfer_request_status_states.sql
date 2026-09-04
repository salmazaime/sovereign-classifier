-- Explicit state machine for TRANSFER_REQUEST.status:
--   PENDING          -> initial state, decision engine hasn't run yet (rare in
--                       practice since /transfer-request runs the engine
--                       synchronously, but kept for completeness / future
--                       async flows)
--   ALLOWED          -> engine said ALLOW, or a human review resolved to ALLOW
--   DENIED           -> engine said DENY, or a human review resolved to DENY,
--                       or a review EXPIRED (fail-closed)
--   REVIEW_PENDING   -> engine said REVIEW, waiting on AUTHORIZATION_REQUEST
--   COMPLETED        -> interceptor reported it actually executed the transfer
--   ABORTED          -> interceptor reported it did NOT execute (e.g. caller
--                       cancelled, or execution failed on their end)
ALTER TABLE TRANSFER_REQUEST
    ADD CONSTRAINT chk_transfer_request_status
    CHECK (status IN ('PENDING', 'ALLOWED', 'DENIED', 'REVIEW_PENDING', 'COMPLETED', 'ABORTED'));

