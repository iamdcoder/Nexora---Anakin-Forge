from models.policy import PartyPolicy
from models.proposal import NegotiationProposal
from models.validation import (
    ValidationResult,
    ValidationStatus,
)

class PolicyValidator:

    @staticmethod
    def validate(
        proposal: NegotiationProposal,
        policy: PartyPolicy,
        role: str,
    ) -> ValidationResult:

        violations = []

                

        if proposal.action.value not in {
            "offer",
            "counter",
            "accept",
            "walk_away",
        }:
            violations.append(
                f"Unsupported proposal action: "
                f"{proposal.action.value}"
            )

               

        if role == "buyer":

            if policy.price.maximum is not None:
                if proposal.price > policy.price.maximum:
                    violations.append(
                        f"Price {proposal.price} exceeds "
                        f"buyer maximum "
                        f"{policy.price.maximum}"
                    )

        elif role == "supplier":

            if policy.price.minimum is not None:
                if proposal.price < policy.price.minimum:
                    violations.append(
                        f"Price {proposal.price} is below "
                        f"supplier minimum "
                        f"{policy.price.minimum}"
                    )

        else:

            violations.append(
                f"Unknown negotiation role: {role}"
            )

                  

        if (
            proposal.delivery_days
            > policy.delivery.maximum_days
        ):

            violations.append(
                f"Delivery {proposal.delivery_days} days "
                f"exceeds maximum "
                f"{policy.delivery.maximum_days} days"
            )

                 

        if (
            proposal.payment_days
            < policy.payment.minimum_days
        ):

            violations.append(
                f"Payment term Net "
                f"{proposal.payment_days} "
                f"is below minimum Net "
                f"{policy.payment.minimum_days}"
            )

                     

        if (
            proposal.sla_penalty
            < policy.sla.minimum_penalty
        ):

            violations.append(
                f"SLA penalty "
                f"{proposal.sla_penalty}% "
                f"is below minimum "
                f"{policy.sla.minimum_penalty}%"
            )

        if (
            proposal.sla_penalty
            > policy.sla.maximum_penalty
        ):

            violations.append(
                f"SLA penalty "
                f"{proposal.sla_penalty}% "
                f"exceeds maximum "
                f"{policy.sla.maximum_penalty}%"
            )

                    

        if (
            proposal.sla_uptime
            < policy.sla.minimum_uptime
        ):

            violations.append(
                f"SLA uptime "
                f"{proposal.sla_uptime}% "
                f"is below minimum "
                f"{policy.sla.minimum_uptime}%"
            )

                

        if violations:

            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=(
                    "Proposal violates party policy."
                ),
                violations=violations,
            )

        return ValidationResult(
            status=ValidationStatus.ALLOWED,
            reason=(
                "Proposal satisfies party policy."
            ),
            violations=[],
        )