from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from models.validation import (
    ValidationResult,
    ValidationStatus,
)

from guardrails.policy_validator import PolicyValidator
from guardrails.legal_validator import LegalValidator

class GuardrailEngine:

    @staticmethod
    def validate(
        proposal: NegotiationProposal,
        policy: PartyPolicy,
        role: str,
    ) -> ValidationResult:

                      

        policy_result = PolicyValidator.validate(
            proposal=proposal,
            policy=policy,
            role=role,
        )

        if (
            policy_result.status
            == ValidationStatus.BLOCKED
        ):

            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=policy_result.reason,
                violations=policy_result.violations,
                validator="policy",
                severity="error",
            )

                     

        legal_result = LegalValidator.validate(
            proposal
        )

        if (
            legal_result.status
            == ValidationStatus.BLOCKED
        ):

            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=legal_result.reason,
                violations=legal_result.violations,
                validator="legal",
                severity="critical",
            )

                 

        return ValidationResult(
            status=ValidationStatus.ALLOWED,
            reason=(
                "Proposal passed policy "
                "and legal validation."
            ),
            violations=[],
            validator="policy+legal",
            severity="none",
        )