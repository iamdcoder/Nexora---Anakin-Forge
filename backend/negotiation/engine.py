from dataclasses import dataclass
import inspect

from guardrails.agreement_validator import AgreementValidator
from guardrails.guardrail_engine import GuardrailEngine

from models.policy import PartyPolicy
from models.proposal import (
    NegotiationProposal,
    ProposalAction,
)
from models.validation import ValidationStatus

from negotiation.state import NegotiationState
from negotiation.convergence import calculate_gap
from negotiation.deadlock import (
    price_is_feasible,
    detect_stagnation,
)
from governance.lyzr_governance import LyzrGovernance

@dataclass
class NegotiationResult:
    status: str
    rounds: list[dict]
    final_proposal: NegotiationProposal | None = None
    reason: str | None = None

class NegotiationEngine:

    def __init__(
        self,
        buyer_policy: PartyPolicy,
        supplier_policy: PartyPolicy,
        buyer_agent,
        supplier_agent,
        audit_logger=None,
        negotiation_id: str = "NEG-001",
        buyer_name: str = "Buyer",
        supplier_name: str = "Supplier",
        max_revisions_per_round: int = 2,
        governance: LyzrGovernance | None = None,
    ):
        self.buyer_policy = buyer_policy
        self.supplier_policy = supplier_policy

        self.buyer_agent = buyer_agent
        self.supplier_agent = supplier_agent

        self.audit = audit_logger

        self.negotiation_id = negotiation_id

        self.buyer_name = buyer_name
        self.supplier_name = supplier_name

        self.max_revisions_per_round = (
            max_revisions_per_round
        )
        self.governance = governance or LyzrGovernance()

        self.state = NegotiationState()

               

    def run(self) -> NegotiationResult:

                           

        if not price_is_feasible(
            self.buyer_policy,
            self.supplier_policy,
        ):
            self.state.deadlock = True

            self._audit(
                event_type="deadlock",
                actor="negotiation_engine",
                status="deadlock",
                details={
                    "reason": (
                        "No feasible price overlap "
                        "exists."
                    )
                },
            )

            return NegotiationResult(
                status="deadlock",
                rounds=[],
                reason="No feasible price range exists.",
            )

        max_rounds = min(
            self.buyer_policy.max_rounds,
            self.supplier_policy.max_rounds,
        )

        supplier_offer = None
        previous_gap = None

        self._audit(
            event_type="negotiation_started",
            actor="negotiation_engine",
            status="started",
            details={
                "buyer": self.buyer_name,
                "supplier": self.supplier_name,
                "max_rounds": max_rounds,
            },
        )

                            

        for round_number in range(
            1,
            max_rounds + 1,
        ):

            context = (
                self.build_negotiation_context()
            )

                        

            buyer_offer = (
                self._generate_with_revisions(
                    agent=self.buyer_agent,
                    role="buyer",
                    round_number=round_number,
                    previous_offer=supplier_offer,
                    policy=self.buyer_policy,
                    context=context,
                    previous_offer_name="supplier_offer",
                )
            )

            if buyer_offer is None:
                return NegotiationResult(
                    status="blocked",
                    rounds=self.state_to_rounds(),
                    reason=(
                        "Buyer could not produce "
                        "a valid proposal."
                    ),
                )

            self._audit(
                event_type="proposal_generated",
                actor="buyer_agent",
                status="success",
                round_number=round_number,
                details={
                    "proposal": (
                        buyer_offer.model_dump()
                    ),
                },
            )

                             

            if (
                buyer_offer.action
                == ProposalAction.WALK_AWAY
            ):
                self.state.deadlock = True

                self._audit(
                    event_type="deadlock",
                    actor="buyer_agent",
                    status="walk_away",
                    round_number=round_number,
                    details={
                        "reason": (
                            "Buyer walked away."
                        )
                    },
                )

                return NegotiationResult(
                    status="walk_away",
                    rounds=self.state_to_rounds(),
                    reason="Buyer walked away.",
                )

                                    

            if (
                buyer_offer.action
                == ProposalAction.ACCEPT
            ):

                if supplier_offer is None:
                    return NegotiationResult(
                        status="deadlock",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Buyer attempted to "
                            "accept before a supplier "
                            "offer existed."
                        ),
                    )

                if (
                    buyer_offer.accepted_offer
                    not in (
                        None,
                        "supplier",
                    )
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Buyer provided an "
                            "invalid accepted_offer."
                        ),
                    )

                if not self.proposal_is_acceptable_to_buyer(
                    supplier_offer
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Buyer attempted to "
                            "accept terms outside "
                            "its authority."
                        ),
                    )

                final_validation = (
                    AgreementValidator.validate(
                        proposal=supplier_offer,
                        buyer_policy=self.buyer_policy,
                        supplier_policy=self.supplier_policy,
                    )
                )

                self._audit(
                    event_type="agreement_validation",
                    actor="agreement_firewall",
                    status=final_validation.status.value,
                    round_number=round_number,
                    details={
                        "validator": (
                            final_validation.validator
                        ),
                        "severity": (
                            final_validation.severity
                        ),
                        "reason": (
                            final_validation.reason
                        ),
                        "violations": (
                            final_validation.violations
                        ),
                    },
                )

                if (
                    final_validation.status
                    == ValidationStatus.BLOCKED
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Final agreement failed "
                            "independent validation."
                        ),
                    )

                                                             
                gap = calculate_gap(
                    supplier_offer,
                    supplier_offer,
                )

                self.state.record_round(
                    buyer_offer,
                    supplier_offer,
                    gap,
                    {
                        "actor": "buyer",
                        "action": "accept",
                        "gap": gap,
                        "convergence": (
                            None
                            if previous_gap is None
                            else previous_gap - gap
                        ),
                    },
                )

                self.state.agreement_reached = True

                self._audit(
                    event_type="agreement_reached",
                    actor="buyer_agent",
                    status="success",
                    round_number=round_number,
                    details={
                        "accepted_proposal": (
                            supplier_offer.model_dump()
                        )
                    },
                )

                return NegotiationResult(
                    status="agreed",
                    rounds=self.state_to_rounds(),
                    final_proposal=supplier_offer,
                    reason=(
                        "Buyer accepted the supplier's "
                        "latest offer."
                    ),
                )

                           

            supplier_offer = (
                self._generate_with_revisions(
                    agent=self.supplier_agent,
                    role="supplier",
                    round_number=round_number,
                    previous_offer=buyer_offer,
                    policy=self.supplier_policy,
                    context=(
                        self.build_negotiation_context()
                    ),
                    previous_offer_name="buyer_offer",
                )
            )

            if supplier_offer is None:
                return NegotiationResult(
                    status="blocked",
                    rounds=self.state_to_rounds(),
                    reason=(
                        "Supplier could not produce "
                        "a valid proposal."
                    ),
                )

            self._audit(
                event_type="proposal_generated",
                actor="supplier_agent",
                status="success",
                round_number=round_number,
                details={
                    "proposal": (
                        supplier_offer.model_dump()
                    ),
                },
            )

                                  

            if (
                round_number >= 2
                and self._is_jointly_feasible(supplier_offer)
            ):
                final_validation = AgreementValidator.validate(
                    proposal=supplier_offer,
                    buyer_policy=self.buyer_policy,
                    supplier_policy=self.supplier_policy,
                )

                self._audit(
                    event_type="agreement_validation",
                    actor="agreement_firewall",
                    status=final_validation.status.value,
                    round_number=round_number,
                    details={
                        "validator": final_validation.validator,
                        "severity": final_validation.severity,
                        "reason": final_validation.reason,
                        "violations": final_validation.violations,
                        "close_mode": "joint_feasibility",
                    },
                )

                if final_validation.status == ValidationStatus.ALLOWED:
                    gap = calculate_gap(supplier_offer, supplier_offer)
                    self.state.record_round(
                        buyer_offer,
                        supplier_offer,
                        gap,
                        {
                            "actor": "negotiation_arbiter",
                            "action": "joint_feasible_close",
                            "gap": gap,
                            "convergence": None if previous_gap is None else previous_gap - gap,
                        },
                    )
                    self.state.agreement_reached = True
                    self._audit(
                        event_type="agreement_reached",
                        actor="negotiation_arbiter",
                        status="success",
                        round_number=round_number,
                        details={
                            "final_proposal": supplier_offer.model_dump(),
                            "reason": "Supplier proposal lies inside the intersection of both private policy envelopes.",
                        },
                    )
                    return NegotiationResult(
                        status="agreed",
                        rounds=self.state_to_rounds(),
                        final_proposal=supplier_offer,
                        reason="A jointly feasible package was reached and independently validated.",
                    )

                                

            if (
                supplier_offer.action
                == ProposalAction.WALK_AWAY
            ):
                self.state.deadlock = True

                self._audit(
                    event_type="deadlock",
                    actor="supplier_agent",
                    status="walk_away",
                    round_number=round_number,
                    details={
                        "reason": (
                            "Supplier walked away."
                        )
                    },
                )

                return NegotiationResult(
                    status="walk_away",
                    rounds=self.state_to_rounds(),
                    reason="Supplier walked away.",
                )

                                    

            if (
                supplier_offer.action
                == ProposalAction.ACCEPT
            ):

                if (
                    supplier_offer.accepted_offer
                    not in (
                        None,
                        "buyer",
                    )
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Supplier provided an "
                            "invalid accepted_offer."
                        ),
                    )

                if not self.proposal_is_acceptable_to_supplier(
                    buyer_offer
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Supplier attempted to "
                            "accept terms outside "
                            "its authority."
                        ),
                    )

                final_validation = (
                    AgreementValidator.validate(
                        proposal=buyer_offer,
                        buyer_policy=self.buyer_policy,
                        supplier_policy=self.supplier_policy,
                    )
                )

                self._audit(
                    event_type="agreement_validation",
                    actor="agreement_firewall",
                    status=final_validation.status.value,
                    round_number=round_number,
                    details={
                        "validator": (
                            final_validation.validator
                        ),
                        "severity": (
                            final_validation.severity
                        ),
                        "reason": (
                            final_validation.reason
                        ),
                        "violations": (
                            final_validation.violations
                        ),
                    },
                )

                if (
                    final_validation.status
                    == ValidationStatus.BLOCKED
                ):
                    return NegotiationResult(
                        status="blocked",
                        rounds=self.state_to_rounds(),
                        reason=(
                            "Final agreement failed "
                            "independent validation."
                        ),
                    )

                gap = calculate_gap(
                    buyer_offer,
                    buyer_offer,
                )

                self.state.record_round(
                    buyer_offer,
                    supplier_offer,
                    gap,
                    {
                        "actor": "supplier",
                        "action": "accept",
                        "gap": gap,
                        "convergence": (
                            None
                            if previous_gap is None
                            else previous_gap - gap
                        ),
                    },
                )

                self.state.agreement_reached = True

                self._audit(
                    event_type="agreement_reached",
                    actor="supplier_agent",
                    status="success",
                    round_number=round_number,
                    details={
                        "accepted_proposal": (
                            buyer_offer.model_dump()
                        )
                    },
                )

                return NegotiationResult(
                    status="agreed",
                    rounds=self.state_to_rounds(),
                    final_proposal=buyer_offer,
                    reason=(
                        "Supplier accepted the buyer's "
                        "latest offer."
                    ),
                )

                                      

            gap = calculate_gap(
                buyer_offer,
                supplier_offer,
            )

            convergence_delta = None

            if previous_gap is not None:
                convergence_delta = (
                    previous_gap - gap
                )

            self.state.record_round(
                buyer_offer,
                supplier_offer,
                gap,
                {
                    "actor": "negotiation_engine",
                    "action": "counter",
                    "gap": gap,
                    "convergence": convergence_delta,
                },
            )

                       

            if previous_gap is not None:

                if gap >= previous_gap:
                    self.state.consecutive_non_concessions += 1
                else:
                    self.state.consecutive_non_concessions = 0

            previous_gap = gap

                             

            self._update_repeated_proposal_count()

                          

            if self.same_terms(
                buyer_offer,
                supplier_offer,
            ):

                final_validation = (
                    AgreementValidator.validate(
                        proposal=supplier_offer,
                        buyer_policy=self.buyer_policy,
                        supplier_policy=self.supplier_policy,
                    )
                )

                self._audit(
                    event_type="agreement_validation",
                    actor="agreement_firewall",
                    status=final_validation.status.value,
                    round_number=round_number,
                    details={
                        "validator": (
                            final_validation.validator
                        ),
                        "severity": (
                            final_validation.severity
                        ),
                        "reason": (
                            final_validation.reason
                        ),
                        "violations": (
                            final_validation.violations
                        ),
                    },
                )

                if (
                    final_validation.status
                    == ValidationStatus.ALLOWED
                ):

                    self.state.agreement_reached = True

                    self._audit(
                        event_type="agreement_reached",
                        actor="negotiation_engine",
                        status="success",
                        round_number=round_number,
                        details={
                            "final_proposal": (
                                supplier_offer.model_dump()
                            ),
                            "gap": gap,
                        },
                    )

                    return NegotiationResult(
                        status="agreed",
                        rounds=self.state_to_rounds(),
                        final_proposal=supplier_offer,
                        reason=(
                            "Both agents proposed the "
                            "same valid package."
                        ),
                    )

                      

            if detect_stagnation(
                self.state.gaps,
                self.state.consecutive_repeated_proposals,
            ):

                self.state.deadlock = True

                self._audit(
                    event_type="deadlock",
                    actor="negotiation_engine",
                    status="deadlock",
                    round_number=round_number,
                    details={
                        "reason": (
                            "Negotiation has stagnated."
                        ),
                        "gap": gap,
                    },
                )

                return NegotiationResult(
                    status="deadlock",
                    rounds=self.state_to_rounds(),
                    reason=(
                        "Negotiation has stagnated."
                    ),
                )

                    

        self.state.deadlock = True

        self._audit(
            event_type="deadlock",
            actor="negotiation_engine",
            status="deadlock",
            details={
                "reason": (
                    "Maximum negotiation rounds reached."
                )
            },
        )

        return NegotiationResult(
            status="deadlock",
            rounds=self.state_to_rounds(),
            reason=(
                "Maximum negotiation rounds reached."
            ),
        )

                                 

    def _generate_with_revisions(
        self,
        agent,
        role: str,
        round_number: int,
        previous_offer,
        policy: PartyPolicy,
        context: str,
        previous_offer_name: str,
    ):

        feedback = ""

        for attempt in range(
            self.max_revisions_per_round + 1
        ):

            attempt_number = attempt + 1

                                      

            self._audit(
                event_type="proposal_generation_attempt",
                actor=f"{role}_agent",
                status="attempt",
                round_number=round_number,
                details={
                    "attempt": attempt_number,
                    "max_attempts": (
                        self.max_revisions_per_round + 1
                    ),
                },
            )

                        

            try:

                proposal = self._call_agent(
                    agent=agent,
                    round_number=round_number,
                    previous_offer=previous_offer,
                    context=context,
                    feedback=feedback,
                    previous_offer_name=previous_offer_name,
                )

            except Exception as exc:

                self._audit(
                    event_type="proposal_parse_error",
                    actor=f"{role}_agent",
                    status="error",
                    round_number=round_number,
                    details={
                        "attempt": attempt_number,
                        "error": str(exc),
                    },
                )

                feedback = (
                    "Your previous response could not "
                    "be parsed as a valid proposal.\n"
                    f"Technical error: {exc}\n"
                    "Return ONLY the required JSON proposal."
                )

                if (
                    attempt
                    == self.max_revisions_per_round
                ):
                    return None

                continue

            if proposal is None:
                return None

                       

            if (
                proposal.action
                == ProposalAction.WALK_AWAY
            ):
                return proposal

                                    

            if (
                proposal.round_number
                != round_number
            ):

                validation_message = (
                    f"Proposal round number "
                    f"{proposal.round_number} does not "
                    f"match current round {round_number}."
                )

                self._audit(
                    event_type="policy_check",
                    actor="guardrail_engine",
                    status="blocked",
                    round_number=round_number,
                    details={
                        "role": role,
                        "attempt": attempt_number,
                        "validator": "protocol",
                        "violations": [
                            validation_message
                        ],
                    },
                )

                if (
                    attempt
                    == self.max_revisions_per_round
                ):
                    return None

                feedback = (
                    "Your proposal was blocked.\n"
                    f"Violation: {validation_message}\n"
                    "Return a proposal for the current "
                    f"round only: {round_number}."
                )

                continue

                                  

            governance_decision = self.governance.check(
                stage="agent_output",
                actor=f"{role}_agent",
                payload={
                    "round": round_number,
                    "proposal": proposal.model_dump(),
                },
            )
            self._audit(
                event_type="policy_check",
                actor="lyzr_responsible_ai",
                status="allowed" if governance_decision.allowed else "blocked",
                round_number=round_number,
                details={
                    "source": governance_decision.source,
                    "reason": governance_decision.reason,
                    "rule": governance_decision.rule,
                },
            )
            if not governance_decision.allowed:
                feedback = (
                    "Your proposal was blocked by the external governance gate. "
                    f"Reason: {governance_decision.reason}. Return a compliant proposal."
                )
                if attempt == self.max_revisions_per_round:
                    return None
                continue

                                       

            validation = GuardrailEngine.validate(
                proposal=proposal,
                policy=policy,
                role=role,
            )

            self._audit(
                event_type="policy_check",
                actor="guardrail_engine",
                status=validation.status.value,
                round_number=round_number,
                details={
                    "role": role,
                    "attempt": attempt_number,
                    "validator": validation.validator,
                    "severity": validation.severity,
                    "reason": validation.reason,
                    "violations": validation.violations,
                    "proposal": proposal.model_dump(),
                },
            )

                      

            if (
                validation.status
                == ValidationStatus.ALLOWED
            ):

                projected = self._project_to_joint_feasible_zone(
                    proposal=proposal,
                    role=role,
                )

                if projected != proposal:
                    self._audit(
                        event_type="feasibility_projection",
                        actor="negotiation_arbiter",
                        status="adjusted",
                        round_number=round_number,
                        details={
                            "role": role,
                            "original": proposal.model_dump(),
                            "projected": projected.model_dump(),
                            "reason": "LLM proposal was valid for its private policy but outside the counterparty's feasible boundary.",
                        },
                    )

                    projected_validation = GuardrailEngine.validate(
                        proposal=projected,
                        policy=policy,
                        role=role,
                    )
                    if projected_validation.status != ValidationStatus.ALLOWED:
                        return proposal
                    proposal = projected

                self._audit(
                    event_type="proposal_approved",
                    actor="guardrail_engine",
                    status="approved",
                    round_number=round_number,
                    details={
                        "role": role,
                        "attempt": attempt_number,
                        "proposal": proposal.model_dump(),
                    },
                )

                return proposal

                           

            if (
                attempt
                == self.max_revisions_per_round
            ):

                self._audit(
                    event_type="proposal_blocked",
                    actor="guardrail_engine",
                    status="blocked",
                    round_number=round_number,
                    details={
                        "role": role,
                        "attempts": attempt_number,
                        "violations": validation.violations,
                        "reason": validation.reason,
                    },
                )

                return None

                              

            feedback = self.build_revision_context(
                validation
            )

            self._audit(
                event_type="proposal_revised",
                actor="guardrail_engine",
                status="revision_requested",
                round_number=round_number,
                details={
                    "role": role,
                    "attempt": attempt_number,
                    "next_attempt": (
                        attempt_number + 1
                    ),
                    "violations": validation.violations,
                    "reason": validation.reason,
                },
            )

        return None

                

    @staticmethod
    def _call_agent(
        agent,
        round_number: int,
        previous_offer,
        context: str,
        feedback: str,
        previous_offer_name: str,
    ):

        params = inspect.signature(
            agent.generate_proposal
        ).parameters

        kwargs = {
            "round_number": round_number
        }

        if (
            previous_offer_name
            == "supplier_offer"
        ):
            kwargs["supplier_offer"] = previous_offer
        else:
            kwargs["buyer_offer"] = previous_offer

        if "negotiation_context" in params:
            kwargs["negotiation_context"] = context

        if "revision_feedback" in params:
            kwargs["revision_feedback"] = feedback

        return agent.generate_proposal(
            **kwargs
        )

    def _project_to_joint_feasible_zone(
        self,
        proposal: NegotiationProposal,
        role: str,
    ) -> NegotiationProposal:
        """Project an otherwise policy-valid LLM proposal toward the joint feasible zone.

        This is an arbiter step, not a policy concession: private policies remain
        authoritative, while values are minimally adjusted when the proposal is
        outside the counterparty's hard boundary but a feasible overlap exists.
        """
        values = proposal.model_copy(deep=True)

        buyer = self.buyer_policy
        supplier = self.supplier_policy

        buyer_max = buyer.price.maximum
        supplier_min = supplier.price.minimum
        if role == "buyer":
            if supplier_min is not None and values.price < supplier_min and (buyer_max is None or supplier_min <= buyer_max):
                values.price = supplier_min
        else:
            if buyer_max is not None and values.price > buyer_max and (supplier_min is None or buyer_max >= supplier_min):
                values.price = buyer_max

        shared_delivery_max = min(buyer.delivery.maximum_days, supplier.delivery.maximum_days)
        if values.delivery_days > shared_delivery_max:
            values.delivery_days = shared_delivery_max

        shared_payment_min = max(buyer.payment.minimum_days, supplier.payment.minimum_days)
        if values.payment_days < shared_payment_min:
            values.payment_days = shared_payment_min

        shared_penalty_min = max(buyer.sla.minimum_penalty, supplier.sla.minimum_penalty)
        shared_penalty_max = min(buyer.sla.maximum_penalty, supplier.sla.maximum_penalty)
        if shared_penalty_min <= shared_penalty_max:
            values.sla_penalty = min(max(values.sla_penalty, shared_penalty_min), shared_penalty_max)

        shared_uptime_min = max(buyer.sla.minimum_uptime, supplier.sla.minimum_uptime)
        if values.sla_uptime < shared_uptime_min:
            values.sla_uptime = shared_uptime_min

        return values

                      

    def proposal_is_acceptable_to_buyer(
        self,
        proposal,
    ) -> bool:

        if (
            self.buyer_policy.price.maximum
            is not None
        ):

            if (
                proposal.price
                > self.buyer_policy.price.maximum
            ):
                return False

        if (
            proposal.delivery_days
            > self.buyer_policy.delivery.maximum_days
        ):
            return False

        if (
            proposal.payment_days
            < self.buyer_policy.payment.minimum_days
        ):
            return False

        if (
            proposal.sla_penalty
            < self.buyer_policy.sla.minimum_penalty
        ):
            return False

        if (
            proposal.sla_penalty
            > self.buyer_policy.sla.maximum_penalty
        ):
            return False

        if (
            proposal.sla_uptime
            < self.buyer_policy.sla.minimum_uptime
        ):
            return False

        return True

    def proposal_is_acceptable_to_supplier(
        self,
        proposal,
    ) -> bool:

        if (
            self.supplier_policy.price.minimum
            is not None
        ):

            if (
                proposal.price
                < self.supplier_policy.price.minimum
            ):
                return False

        if (
            proposal.delivery_days
            > self.supplier_policy.delivery.maximum_days
        ):
            return False

        if (
            proposal.payment_days
            < self.supplier_policy.payment.minimum_days
        ):
            return False

        if (
            proposal.sla_penalty
            < self.supplier_policy.sla.minimum_penalty
        ):
            return False

        if (
            proposal.sla_penalty
            > self.supplier_policy.sla.maximum_penalty
        ):
            return False

        if (
            proposal.sla_uptime
            < self.supplier_policy.sla.minimum_uptime
        ):
            return False

        return True

    def _is_jointly_feasible(self, proposal: NegotiationProposal) -> bool:
        return (
            self.proposal_is_acceptable_to_buyer(proposal)
            and self.proposal_is_acceptable_to_supplier(proposal)
        )

             

    def build_negotiation_context(
        self,
    ) -> str:

        if not self.state.gaps:
            return "No previous rounds."

        latest_gap = self.state.gaps[-1]

        previous_gap = (
            self.state.gaps[-2]
            if len(self.state.gaps) >= 2
            else None
        )

        if previous_gap is None:

            trend = (
                "No convergence trend yet."
            )

        elif latest_gap < previous_gap:

            trend = (
                "The negotiation is converging."
            )

        elif latest_gap > previous_gap:

            trend = (
                "The negotiation is diverging."
            )

        else:

            trend = (
                "The negotiation has stalled."
            )

        return (
            f"Latest package gap: "
            f"{latest_gap:.4f}\n"
            f"Previous package gap: "
            f"{previous_gap}\n"
            f"Trend: {trend}\n"
            f"Rounds completed: "
            f"{self.state.current_round}"
        )

    @staticmethod
    def build_revision_context(
        validation,
    ) -> str:

        violations = "\n".join(
            f"- {item}"
            for item in validation.violations
        )

        return (
            "Your previous proposal was blocked.\n"
            f"Validator: {validation.validator}\n"
            f"Severity: {validation.severity}\n"
            f"Reason: {validation.reason}\n\n"
            "Violations:\n"
            f"{violations}\n\n"
            "Generate a revised proposal that "
            "fixes every violation.\n"
            "Stay within your private authority.\n"
            "Do not reveal or request private policy "
            "information.\n"
            "Return ONLY the corrected JSON proposal."
        )

             

    @staticmethod
    def same_terms(
        first,
        second,
    ) -> bool:

        return (
            first.price == second.price
            and first.delivery_days
            == second.delivery_days
            and first.payment_days
            == second.payment_days
            and first.sla_penalty
            == second.sla_penalty
            and first.sla_uptime
            == second.sla_uptime
        )

    def _update_repeated_proposal_count(
        self,
    ) -> None:

        if (
            len(self.state.buyer_proposals)
            < 2
        ):
            return

        if (
            len(self.state.supplier_proposals)
            < 2
        ):
            return

        buyer_repeated = self.same_terms(
            self.state.buyer_proposals[-2],
            self.state.buyer_proposals[-1],
        )

        supplier_repeated = self.same_terms(
            self.state.supplier_proposals[-2],
            self.state.supplier_proposals[-1],
        )

        if (
            buyer_repeated
            and supplier_repeated
        ):

            self.state.consecutive_repeated_proposals += 1

        else:

            self.state.consecutive_repeated_proposals = 0

                         

    def state_to_rounds(self) -> list[dict]:

        rounds = []

        for index in range(
            len(
                self.state.buyer_proposals
            )
        ):

            round_data = {
                "round": index + 1,
                "buyer": (
                    self.state.buyer_proposals[index]
                ),
                "supplier": (
                    self.state.supplier_proposals[index]
                ),
                "gap": self.state.gaps[index],
            }

            if (
                index
                < len(self.state.round_metrics)
            ):

                round_data["metrics"] = (
                    self.state.round_metrics[index]
                )

            rounds.append(
                round_data
            )

        return rounds

           

    def _audit(
        self,
        event_type: str,
        actor: str,
        status: str,
        details: dict,
        round_number: int | None = None,
    ) -> None:

        if self.audit is None:
            return

        try:

            from audit.models import AuditEventType

            event_mapping = {

                "negotiation_started":
                    AuditEventType.NEGOTIATION_STARTED,

                "proposal_generated":
                    AuditEventType.PROPOSAL_GENERATED,

                "policy_check":
                    AuditEventType.POLICY_CHECK,

                "proposal_blocked":
                    AuditEventType.PROPOSAL_BLOCKED,

                "proposal_revised":
                    AuditEventType.PROPOSAL_REVISED,

                "proposal_generation_attempt":
                    AuditEventType.PROPOSAL_GENERATION_ATTEMPT,

                "proposal_parse_error":
                    AuditEventType.PROPOSAL_PARSE_ERROR,

                "proposal_approved":
                    AuditEventType.PROPOSAL_APPROVED,

                "agreement_validation":
                    AuditEventType.AGREEMENT_VALIDATION,

                "agreement_reached":
                    AuditEventType.AGREEMENT_REACHED,

                "deadlock":
                    AuditEventType.DEADLOCK,
            }

            event = event_mapping.get(
                event_type
            )

            if event is None:
                return

            audit_event = self.audit.log(
                negotiation_id=self.negotiation_id,
                event_type=event,
                actor=actor,
                status=status,
                details=details,
                round_number=round_number,
            )

            self.governance.publish_event({
                "event_id": audit_event.event_id,
                "negotiation_id": self.negotiation_id,
                "timestamp": audit_event.timestamp.isoformat(),
                "round_number": round_number,
                "event_type": event.value,
                "actor": actor,
                "status": status,
                "details": details,
            })

        except (
            ImportError,
            AttributeError,
        ):
            pass