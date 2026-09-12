from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from models.validation import (
    ValidationResult,
    ValidationStatus,
)

from guardrails.legal_validator import LegalValidator
from guardrails.policy_validator import PolicyValidator

class AgreementValidator:

    @staticmethod
    def validate(
        proposal: NegotiationProposal,
        buyer_policy: PartyPolicy,
        supplier_policy: PartyPolicy,
    ) -> ValidationResult:

        violations = []

                         

        buyer_result = PolicyValidator.validate(
            proposal=proposal,
            policy=buyer_policy,
            role="buyer",
        )

        if (
            buyer_result.status
            == ValidationStatus.BLOCKED
        ):
            violations.extend(
                [
                    f"BUYER: {violation}"
                    for violation
                    in buyer_result.violations
                ]
            )

                            

        supplier_result = PolicyValidator.validate(
            proposal=proposal,
            policy=supplier_policy,
            role="supplier",
        )

        if (
            supplier_result.status
            == ValidationStatus.BLOCKED
        ):
            violations.extend(
                [
                    f"SUPPLIER: {violation}"
                    for violation
                    in supplier_result.violations
                ]
            )

                          

        legal_result = LegalValidator.validate(
            proposal
        )

        if (
            legal_result.status
            == ValidationStatus.BLOCKED
        ):
            violations.extend(
                [
                    f"LEGAL: {violation}"
                    for violation
                    in legal_result.violations
                ]
            )

                      

        if violations:

            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=(
                    "Final agreement failed "
                    "independent validation."
                ),
                violations=violations,
                validator="agreement_firewall",
                severity="critical",
            )

        return ValidationResult(
            status=ValidationStatus.ALLOWED,
            reason=(
                "Final agreement passed buyer, "
                "supplier, and legal validation."
            ),
            violations=[],
            validator="agreement_firewall",
            severity="none",
        )