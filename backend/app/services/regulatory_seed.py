"""Baseline regulatory mapping seed data.

ACCURACY RULE: reference these instruments by their official-style names
only. Do NOT invent circular numbers, dates, or clause numbers anywhere in
this file. If precise citations are needed later they will be added
deliberately; fabricated specifics are worse than none in front of a CCO.
See tests/test_regulatory.py's no-fabricated-citation guard test, which
enforces this over every seeded row.
"""

from sqlalchemy.orm import Session

from app.models import GuidanceType, RegulatoryMapping

SEED_MAPPINGS: list[dict[str, str | GuidanceType | None]] = [
    {
        "control_key": "independent_validation",
        "regulation_name": "RBI Scale Based Regulation (SBR) Framework",
        "reference_text": (
            "Enhanced governance expectations for NBFC-ML and NBFC-UL, including "
            "model validation independence for material models."
        ),
        "guidance_type": GuidanceType.BINDING,
        "effective_note": "Scale Based Regulation framework for NBFCs",
    },
    {
        "control_key": "human_override",
        "regulation_name": "RBI Guidelines on Digital Lending",
        "reference_text": (
            "Credit decisioning accountability cannot be fully delegated to "
            "automated systems; a human accountable owner is expected."
        ),
        "guidance_type": GuidanceType.BINDING,
        "effective_note": "Digital Lending Guidelines",
    },
    {
        "control_key": "audit_logging",
        "regulation_name": (
            "RBI Master Direction on IT Governance, Risk, Controls and Assurance "
            "Practices"
        ),
        "reference_text": (
            "Regulated entities must maintain audit logging and traceability for "
            "critical systems and decisioning processes."
        ),
        "guidance_type": GuidanceType.BINDING,
        "effective_note": "IT Governance Master Direction",
    },
    {
        "control_key": "documentation",
        "regulation_name": (
            "RBI Master Direction on IT Governance, Risk, Controls and Assurance "
            "Practices"
        ),
        "reference_text": (
            "Adequate documentation of systems, controls, and decisioning logic is "
            "expected for supervisory review."
        ),
        "guidance_type": GuidanceType.BINDING,
        "effective_note": "IT Governance Master Direction",
    },
    {
        "control_key": "vendor_risk",
        "regulation_name": (
            "RBI Guidelines on Managing Risks and Code of Conduct in Outsourcing of "
            "Financial Services"
        ),
        "reference_text": (
            "Material outsourcing and third-party dependencies require risk "
            "assessment, due diligence, and ongoing oversight."
        ),
        "guidance_type": GuidanceType.BINDING,
        "effective_note": "Outsourcing Guidelines (incl. IT outsourcing)",
    },
    {
        "control_key": "explainability",
        "regulation_name": (
            "RBI FREE-AI Committee — Framework for Responsible and Ethical "
            "Enablement of AI"
        ),
        "reference_text": (
            "Responsible AI adoption in the financial sector emphasises "
            "explainability and transparency of AI-driven decisions."
        ),
        "guidance_type": GuidanceType.EMERGING,
        "effective_note": "Committee framework — emerging guidance, not a binding direction",
    },
    {
        "control_key": "drift_monitoring",
        "regulation_name": (
            "RBI FREE-AI Committee — Framework for Responsible and Ethical "
            "Enablement of AI"
        ),
        "reference_text": (
            "Ongoing monitoring of AI model behaviour and drift is expected as part "
            "of responsible AI lifecycle management."
        ),
        "guidance_type": GuidanceType.EMERGING,
        "effective_note": "Committee framework — emerging guidance, not a binding direction",
    },
]


def seed_regulatory_mappings(db: Session) -> None:
    """Inserts the baseline mappings only if the table is empty. Idempotent —
    safe to call on every startup."""
    if db.query(RegulatoryMapping).first() is not None:
        return
    for row in SEED_MAPPINGS:
        db.add(RegulatoryMapping(**row))
    db.commit()
