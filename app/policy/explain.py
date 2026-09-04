# app/policy/explain.py -- NEW FILE
"""
Translates the engine's discrete decision path into a human-readable
explanation. Deliberately does NOT invent a confidence percentage --
decide_transfer() (Step 9) is a deterministic rule engine, not a
probabilistic model, so it has no real "80% sure" to report. What it
DOES have is a specific reason it stopped short of ALLOW/DENY, and
the specific facts that were and weren't satisfied. This reconstructs
that honestly rather than fabricating a number that would look
scientific but mean nothing.
"""


def explain_review_reasoning(context: dict) -> dict:
    features = context.get("decision_features") or {}
    classification = context.get("classification") or {}
    findings = context.get("content_findings") or []
    destination_country = context.get("destination_country")

    known_facts = []
    unresolved_questions = []

    # What the engine DID establish with certainty
    sensitivity = classification.get("aggregate_sensitivity", "unknown")
    known_facts.append(f"Aggregate sensitivity classified as '{sensitivity}'.")

    categories = classification.get("sensitivity_category", [])
    if categories and categories != ["none"]:
        known_facts.append(f"Content scan detected: {', '.join(categories)}.")
    else:
        known_facts.append("No specific sensitive-data categories detected in sampled content.")

    residency_lock = classification.get("residency_lock", "none")
    if residency_lock == "none":
        known_facts.append("No mandatory residency lock applies to this asset (Axis 3 check passed).")

    if not context.get("qualified_provider_required"):
        known_facts.append("Company is not flagged as requiring qualified-provider-only hosting.")

    # What the engine could NOT resolve on its own
    reason_code = features.get("reason_code", "")
    if reason_code == "destination_not_on_adequacy_list":
        unresolved_questions.append(
            f"Destination country '{destination_country}' is not on the CNDP-published adequacy list. "
            "This does not mean the transfer is illegal -- Loi 09-08 Art. 43-44 allows several derogations "
            "(explicit consent, contract necessity, vital interest, legal claims) that the system cannot "
            "verify automatically, since they depend on facts outside the technical transfer itself."
        )
        unresolved_questions.append(
            "No CNDP ad-hoc authorization is on file for this specific transfer."
        )

    if not reason_code:
        unresolved_questions.append("No specific blocking reason was recorded for this decision.")

    return {
        "engine_type": "deterministic_rule_engine",
        "known_facts": known_facts,
        "unresolved_questions": unresolved_questions,
        "raw_reason_code": reason_code,
    }
    