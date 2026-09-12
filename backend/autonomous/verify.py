from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from autonomous.act import ActResponse
from autonomous.reason import ProcurementReasoning
from models.policy import PartyPolicy


router = APIRouter(
    prefix="/api/autonomous",
    tags=["Autonomous Procurement"],
)


class VerifyRequest(BaseModel):
    action: ActResponse

    reasoning: ProcurementReasoning

    buyer: PartyPolicy

    supplier: PartyPolicy


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class VerificationResult(BaseModel):
    verification_id: str

    action_id: str

    negotiation_id: str | None = None

    status: str

    verified: bool

    checks: list[VerificationCheck] = Field(
        default_factory=list
    )

    violations: list[str] = Field(
        default_factory=list
    )

    verified_contract: dict[str, Any] | None = None


def _check_price(
    price: float,
    buyer: PartyPolicy,
    supplier: PartyPolicy,
) -> list[str]:

    violations: list[str] = []

    buyer_min = buyer.price.minimum

    buyer_max = buyer.price.maximum

    supplier_min = supplier.price.minimum

    supplier_max = supplier.price.maximum

    if (
        buyer_min is not None
        and price < buyer_min
    ):

        violations.append(
            f"Final price {price} is below buyer minimum {buyer_min}."
        )

    if (
        buyer_max is not None
        and price > buyer_max
    ):

        violations.append(
            f"Final price {price} exceeds buyer maximum {buyer_max}."
        )

    if (
        supplier_min is not None
        and price < supplier_min
    ):

        violations.append(
            f"Final price {price} is below supplier minimum {supplier_min}."
        )

    if (
        supplier_max is not None
        and price > supplier_max
    ):

        violations.append(
            f"Final price {price} exceeds supplier maximum {supplier_max}."
        )

    return violations


def _check_delivery(
    delivery_days: int,
    buyer: PartyPolicy,
    supplier: PartyPolicy,
) -> list[str]:

    violations: list[str] = []

    if (
        delivery_days
        > buyer.delivery.maximum_days
    ):

        violations.append(
            "Final delivery exceeds buyer maximum delivery period."
        )

    if (
        delivery_days
        > supplier.delivery.maximum_days
    ):

        violations.append(
            "Final delivery exceeds supplier maximum delivery period."
        )

    return violations


def _check_payment(
    payment_days: int,
    buyer: PartyPolicy,
    supplier: PartyPolicy,
) -> list[str]:

    violations: list[str] = []

    if (
        payment_days
        < buyer.payment.minimum_days
    ):

        violations.append(
            "Final payment terms are below buyer minimum payment days."
        )

    if (
        payment_days
        < supplier.payment.minimum_days
    ):

        violations.append(
            "Final payment terms are below supplier minimum payment days."
        )

    return violations


def _check_sla(
    uptime: float,
    penalty: float,
    buyer: PartyPolicy,
    supplier: PartyPolicy,
) -> list[str]:

    violations: list[str] = []

    if (
        uptime
        < buyer.sla.minimum_uptime
    ):

        violations.append(
            "Final SLA uptime is below buyer minimum uptime."
        )

    if (
        uptime
        < supplier.sla.minimum_uptime
    ):

        violations.append(
            "Final SLA uptime is below supplier minimum uptime."
        )

    if (
        penalty
        < buyer.sla.minimum_penalty
    ):

        violations.append(
            "Final SLA penalty is below buyer minimum penalty."
        )

    if (
        penalty
        > buyer.sla.maximum_penalty
    ):

        violations.append(
            "Final SLA penalty exceeds buyer maximum penalty."
        )

    if (
        penalty
        < supplier.sla.minimum_penalty
    ):

        violations.append(
            "Final SLA penalty is below supplier minimum penalty."
        )

    if (
        penalty
        > supplier.sla.maximum_penalty
    ):

        violations.append(
            "Final SLA penalty exceeds supplier maximum penalty."
        )

    return violations


def _calculate_contract_hash(
    contract: dict[str, Any],
) -> str:

    payload = dict(contract)

    payload.pop(
        "contract_hash",
        None,
    )

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _check_contract_hash(
    contract: dict[str, Any],
) -> tuple[bool, str]:

    stored_hash = contract.get(
        "contract_hash"
    )

    if not stored_hash:

        return (
            False,
            "Contract does not contain a payload hash.",
        )

    calculated_hash = _calculate_contract_hash(
        contract
    )

    if calculated_hash != stored_hash:

        return (
            False,
            "Contract payload hash does not match.",
        )

    return (
        True,
        "Contract payload hash matches.",
    )


def _check_final_proposal_matches_contract(
    final_proposal: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:

    violations: list[str] = []

    fields = (
        (
            "price",
            "unit_price",
        ),
        (
            "delivery_days",
            "delivery_days",
        ),
        (
            "payment_days",
            "payment_days",
        ),
        (
            "sla_uptime",
            "sla",
        ),
    )

    final_price = final_proposal.get(
        "price"
    )

    contract_price = contract.get(
        "unit_price"
    )

    if (
        final_price is not None
        and contract_price is not None
        and float(final_price)
        != float(contract_price)
    ):

        violations.append(
            "Contract unit price does not match final proposal."
        )

    if (
        final_proposal.get(
            "delivery_days"
        )
        != contract.get(
            "delivery_days"
        )
    ):

        violations.append(
            "Contract delivery does not match final proposal."
        )

    if (
        final_proposal.get(
            "payment_days"
        )
        != contract.get(
            "payment_days"
        )
    ):

        violations.append(
            "Contract payment terms do not match final proposal."
        )

    contract_sla = contract.get(
        "sla"
    ) or {}

    if (
        final_proposal.get(
            "sla_uptime"
        ) is not None
        and contract_sla.get(
            "minimum_uptime"
        ) is not None
        and float(
            final_proposal["sla_uptime"]
        )
        != float(
            contract_sla[
                "minimum_uptime"
            ]
        )
    ):

        violations.append(
            "Contract SLA uptime does not match final proposal."
        )

    if (
        final_proposal.get(
            "sla_penalty"
        ) is not None
        and contract_sla.get(
            "penalty_percent"
        ) is not None
        and float(
            final_proposal[
                "sla_penalty"
            ]
        )
        != float(
            contract_sla[
                "penalty_percent"
            ]
        )
    ):

        violations.append(
            "Contract SLA penalty does not match final proposal."
        )

    return violations


def _run_verification(
    request: VerifyRequest,
) -> VerificationResult:

    from main import _store

    verification_id = (
        f"VER-{uuid4().hex[:10].upper()}"
    )

    action = request.action

    negotiation_id = (
        action.negotiation_id
    )

    checks: list[VerificationCheck] = []

    violations: list[str] = []

    if action.decision == "executed":

        checks.append(
            VerificationCheck(
                name="action_executed",
                passed=True,
                detail=(
                    "The ACT layer reported an executed action."
                ),
            )
        )

    else:

        checks.append(
            VerificationCheck(
                name="action_executed",
                passed=False,
                detail=(
                    "The ACT layer did not report an executed action."
                ),
            )
        )

        violations.append(
            "ACT result was not executed."
        )

    if not negotiation_id:

        checks.append(
            VerificationCheck(
                name="negotiation_id",
                passed=False,
                detail=(
                    "No negotiation ID was returned."
                ),
            )
        )

        violations.append(
            "No negotiation ID was returned."
        )

        return VerificationResult(
            verification_id=verification_id,
            action_id=action.action_id,
            status="rejected",
            verified=False,
            checks=checks,
            violations=violations,
        )

    entry = _store.get(
        negotiation_id
    )

    if entry is None:

        checks.append(
            VerificationCheck(
                name="negotiation_exists",
                passed=False,
                detail=(
                    "Negotiation could not be found in Nexora's store."
                ),
            )
        )

        violations.append(
            "Negotiation record not found."
        )

        return VerificationResult(
            verification_id=verification_id,
            action_id=action.action_id,
            negotiation_id=negotiation_id,
            status="rejected",
            verified=False,
            checks=checks,
            violations=violations,
        )

    checks.append(
        VerificationCheck(
            name="negotiation_exists",
            passed=True,
            detail=(
                "Negotiation record exists."
            ),
        )
    )

    negotiation = (
        action.negotiation
        or {}
    )

    negotiation_status = (
        negotiation.get(
            "status"
        )
    )

    agreed = (
        negotiation_status
        == "agreed"
    )

    checks.append(
        VerificationCheck(
            name="agreement_reached",
            passed=agreed,
            detail=(
                "Negotiation reached agreement."
                if agreed
                else
                "Negotiation did not reach agreement."
            ),
        )
    )

    if not agreed:

        violations.append(
            "Negotiation status is not agreed."
        )

    contract = entry.get(
        "contract"
    )

    has_contract = (
        isinstance(
            contract,
            dict,
        )
        and bool(contract)
    )

    checks.append(
        VerificationCheck(
            name="contract_exists",
            passed=has_contract,
            detail=(
                "A generated contract is stored."
                if has_contract
                else
                "No generated contract is stored."
            ),
        )
    )

    if not has_contract:

        violations.append(
            "No generated contract exists."
        )

        return VerificationResult(
            verification_id=verification_id,
            action_id=action.action_id,
            negotiation_id=negotiation_id,
            status="rejected",
            verified=False,
            checks=checks,
            violations=violations,
        )

    final_proposal = (
        negotiation.get(
            "final_proposal"
        )
    )

    proposal_available = (
        isinstance(
            final_proposal,
            dict,
        )
        and bool(final_proposal)
    )

    checks.append(
        VerificationCheck(
            name="final_proposal_exists",
            passed=proposal_available,
            detail=(
                "Final negotiated proposal exists."
                if proposal_available
                else
                "Final negotiated proposal is missing."
            ),
        )
    )

    if not proposal_available:

        violations.append(
            "Final negotiated proposal is missing."
        )

        return VerificationResult(
            verification_id=verification_id,
            action_id=action.action_id,
            negotiation_id=negotiation_id,
            status="rejected",
            verified=False,
            checks=checks,
            violations=violations,
            verified_contract=contract,
        )

    integrity_ok, integrity_detail = (
        _check_contract_hash(
            contract
        )
    )

    checks.append(
        VerificationCheck(
            name="contract_integrity",
            passed=integrity_ok,
            detail=integrity_detail,
        )
    )

    if not integrity_ok:

        violations.append(
            integrity_detail
        )

    consistency_violations = (
        _check_final_proposal_matches_contract(
            final_proposal,
            contract,
        )
    )

    consistency_ok = not consistency_violations

    checks.append(
        VerificationCheck(
            name="proposal_contract_consistency",
            passed=consistency_ok,
            detail=(
                "Final proposal and contract are consistent."
                if consistency_ok
                else
                "Final proposal and contract differ."
            ),
        )
    )

    violations.extend(
        consistency_violations
    )

    price = float(
        final_proposal.get(
            "price",
            contract.get(
                "unit_price",
                0,
            ),
        )
    )

    delivery_days = int(
        final_proposal.get(
            "delivery_days",
            contract.get(
                "delivery_days",
                0,
            ),
        )
    )

    payment_days = int(
        final_proposal.get(
            "payment_days",
            contract.get(
                "payment_days",
                0,
            ),
        )
    )

    sla_uptime = float(
        final_proposal.get(
            "sla_uptime",
            contract.get(
                "sla",
                {},
            ).get(
                "minimum_uptime",
                0,
            ),
        )
    )

    sla_penalty = float(
        final_proposal.get(
            "sla_penalty",
            contract.get(
                "sla",
                {},
            ).get(
                "penalty_percent",
                0,
            ),
        )
    )

    policy_violations = []

    policy_violations.extend(
        _check_price(
            price,
            request.buyer,
            request.supplier,
        )
    )

    policy_violations.extend(
        _check_delivery(
            delivery_days,
            request.buyer,
            request.supplier,
        )
    )

    policy_violations.extend(
        _check_payment(
            payment_days,
            request.buyer,
            request.supplier,
        )
    )

    policy_violations.extend(
        _check_sla(
            sla_uptime,
            sla_penalty,
            request.buyer,
            request.supplier,
        )
    )

    policy_ok = not policy_violations

    checks.append(
        VerificationCheck(
            name="policy_compliance",
            passed=policy_ok,
            detail=(
                "Final terms satisfy both party policy bounds."
                if policy_ok
                else
                "Final terms violate one or more policy bounds."
            ),
        )
    )

    violations.extend(
        policy_violations
    )

    expected_product = (
        request.reasoning.product_name
    )

    if (
        expected_product
        and contract.get(
            "product_name"
        )
    ):

        product_ok = (
            expected_product.strip().lower()
            == str(
                contract[
                    "product_name"
                ]
            ).strip().lower()
        )

    else:

        product_ok = True

    checks.append(
        VerificationCheck(
            name="product_consistency",
            passed=product_ok,
            detail=(
                "Contract product matches procurement reasoning."
                if product_ok
                else
                "Contract product does not match procurement reasoning."
            ),
        )
    )

    if not product_ok:

        violations.append(
            "Contract product does not match procurement reasoning."
        )

    expected_quantity = (
        request.reasoning.quantity
    )

    if (
        expected_quantity is not None
        and contract.get(
            "quantity"
        ) is not None
    ):

        quantity_ok = (
            int(
                expected_quantity
            )
            == int(
                contract[
                    "quantity"
                ]
            )
        )

    else:

        quantity_ok = True

    checks.append(
        VerificationCheck(
            name="quantity_consistency",
            passed=quantity_ok,
            detail=(
                "Contract quantity matches procurement reasoning."
                if quantity_ok
                else
                "Contract quantity does not match procurement reasoning."
            ),
        )
    )

    if not quantity_ok:

        violations.append(
            "Contract quantity does not match procurement reasoning."
        )

    audit_path = entry.get(
        "audit_path"
    )

    audit_ok = False

    if audit_path:

        try:

            from audit.logger import AuditLogger

            audit_result = AuditLogger(
                path=str(audit_path)
            ).verify()

            audit_ok = bool(
                audit_result.get(
                    "valid"
                )
            )

        except Exception:

            audit_ok = False

    checks.append(
        VerificationCheck(
            name="audit_integrity",
            passed=audit_ok,
            detail=(
                "Audit chain verified successfully."
                if audit_ok
                else
                "Audit chain could not be verified."
            ),
        )
    )

    if not audit_ok:

        violations.append(
            "Audit chain verification failed."
        )

    verified = (
        len(violations)
        == 0
    )

    return VerificationResult(
        verification_id=verification_id,
        action_id=action.action_id,
        negotiation_id=negotiation_id,
        status=(
            "verified"
            if verified
            else "rejected"
        ),
        verified=verified,
        checks=checks,
        violations=violations,
        verified_contract=contract,
    )


@router.post(
    "/verify",
    response_model=VerificationResult,
)
def verify_autonomous_action(
    request: VerifyRequest,
) -> VerificationResult:

    return _run_verification(
        request
    )