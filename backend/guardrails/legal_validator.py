from models.proposal import NegotiationProposal
from models.validation import ValidationResult, ValidationStatus

class LegalValidator:
    """Deterministic legal/commercial sanity firewall.

    This intentionally checks only rules encoded by the application; it is not legal advice.
    """

    @staticmethod
    def validate(proposal: NegotiationProposal) -> ValidationResult:
        violations: list[str] = []
        rule_ids: list[str] = []

        checks = [
            ("LEGAL-PRICE-001", proposal.price > 0, "Unit price must be greater than zero."),
            ("LEGAL-DELIVERY-001", 0 < proposal.delivery_days <= 3650, "Delivery period must be between 1 and 3650 days."),
            ("LEGAL-PAYMENT-001", 0 < proposal.payment_days <= 365, "Payment period must be between 1 and 365 days."),
            ("LEGAL-SLA-001", 95 <= proposal.sla_uptime <= 100, "SLA uptime must be between 95% and 100%."),
            ("LEGAL-SLA-002", proposal.sla_penalty >= 0, "SLA penalty cannot be negative."),
        ]
        for rule_id, ok, message in checks:
            if not ok:
                rule_ids.append(rule_id)
                violations.append(f"{rule_id}: {message}")

        if violations:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason="Proposal violates mandatory legal/commercial rules.",
                violations=violations,
                validator="legal",
                severity="critical",
            )

        return ValidationResult(
            status=ValidationStatus.ALLOWED,
            reason="Proposal passed legal validation.",
            violations=[],
            validator="legal",
            severity="none",
        )
