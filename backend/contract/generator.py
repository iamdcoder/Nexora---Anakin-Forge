import hashlib
import json
import uuid
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from models.contract import (
    B2BContract,
    SLAContract,
)
from models.proposal import NegotiationProposal

def generate_contract_pdf(
    contract: B2BContract,
    output_path: str,
) -> None:

    pdf = canvas.Canvas(
        output_path,
        pagesize=A4,
    )

    _, height = A4

    y = height - 60

    pdf.setFont(
        "Helvetica-Bold",
        18,
    )

    pdf.drawString(
        60,
        y,
        "B2B SUPPLY AGREEMENT",
    )

    y -= 40

    fields = [
        (
            "Contract ID",
            contract.contract_id,
        ),
        (
            "Buyer",
            contract.buyer_name,
        ),
        (
            "Supplier",
            contract.supplier_name,
        ),
        (
            "Product",
            contract.product_name,
        ),
        (
            "Quantity",
            str(contract.quantity),
        ),
        (
            "Unit Price",
            (
                f"{contract.currency} "
                f"{contract.unit_price:,.2f}"
            ),
        ),
        (
            "Delivery",
            f"{contract.delivery_days} days",
        ),
        (
            "Payment",
            f"Net {contract.payment_days}",
        ),
        (
            "Minimum SLA Uptime",
            f"{contract.sla.minimum_uptime}%",
        ),
        (
            "SLA Penalty",
            f"{contract.sla.penalty_percent}%",
        ),
    ]

    for label, value in fields:

        pdf.setFont(
            "Helvetica-Bold",
            11,
        )

        pdf.drawString(
            60,
            y,
            f"{label}:",
        )

        pdf.setFont(
            "Helvetica",
            11,
        )

        pdf.drawString(
            190,
            y,
            value,
        )

        y -= 24

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        12,
    )

    pdf.drawString(
        60,
        y,
        "Negotiation Record",
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawString(
        60,
        y,
        (
            "Negotiation ID: "
            f"{contract.negotiation_id}"
        ),
    )

    y -= 18

    pdf.drawString(
        60,
        y,
        (
            "Negotiation rounds: "
            f"{contract.negotiation_rounds}"
        ),
    )

    y -= 18

    pdf.drawString(
        60,
        y,
        f"Status: {contract.status}",
    )

    y -= 50

    pdf.setFont(
        "Helvetica",
        9,
    )

    pdf.drawString(
        60,
        y,
        (
            "This document represents the terms "
            "agreed during the"
        ),
    )

    y -= 14

    pdf.drawString(
        60,
        y,
        (
            "automated B2B negotiation process."
        ),
    )

    pdf.save()

def contract_payload_hash(contract: B2BContract) -> str:
    payload = contract.model_dump(mode="json")
    payload.pop("contract_hash", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def contract_to_json(
    contract: B2BContract,
) -> str:

    return json.dumps(
        contract.model_dump(
            mode="json"
        ),
        indent=2,
    )

def create_contract(
    final_proposal: NegotiationProposal,
    buyer_name: str,
    supplier_name: str,
    product_name: str,
    quantity: int,
    negotiation_id: str,
    negotiation_rounds: int,
) -> B2BContract:

    return B2BContract(
        contract_id=(
            f"CTR-"
            f"{uuid.uuid4().hex[:8].upper()}"
        ),

        buyer_name=buyer_name,
        supplier_name=supplier_name,

        product_name=product_name,
        quantity=quantity,

        unit_price=final_proposal.price,
        currency="INR",

        delivery_days=(
            final_proposal.delivery_days
        ),

        payment_days=(
            final_proposal.payment_days
        ),

        sla=SLAContract(
            minimum_uptime=(
                final_proposal.sla_uptime
            ),
            penalty_percent=(
                final_proposal.sla_penalty
            ),
        ),

        negotiation_id=negotiation_id,

        negotiation_rounds=(
            negotiation_rounds
        ),

        status="AGREED",
        version=1,
        contract_hash=None,

        created_at=datetime.now(
            timezone.utc
        ),
    )