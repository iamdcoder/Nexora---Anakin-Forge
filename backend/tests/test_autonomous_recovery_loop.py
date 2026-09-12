from autonomous import procure as procure_module

from autonomous.procure import (
    AutonomousProcurementRequest,
    ProcurementSupplier,
)

from autonomous.reason import (
    ProcurementReasoning,
)

from autonomous.act import (
    ActResponse,
)

from autonomous.verify import (
    VerificationResult,
)


def buyer_policy():

    return {
        "price": {
            "target": 110000,
            "minimum": 100000,
            "maximum": 120000,
        },
        "delivery": {
            "target_days": 30,
            "minimum_days": 20,
            "maximum_days": 40,
        },
        "payment": {
            "preferred_days": 60,
            "minimum_days": 30,
            "maximum_days": 90,
        },
        "sla": {
            "minimum_uptime": 98,
            "maximum_uptime": 99.9,
            "minimum_penalty": 1,
            "maximum_penalty": 5,
        },
        "batna": "No-deal",
        "max_rounds": 8,
    }


def supplier(
    name,
    target,
):

    policy = buyer_policy()

    policy["price"]["target"] = target

    policy["price"]["minimum"] = (
        target - 10000
    )

    policy["price"]["maximum"] = (
        target + 10000
    )

    policy["batna"] = (
        "Alternative supplier"
    )

    return ProcurementSupplier(
        name=name,
        source_url=(
            "https://example.com/supplier"
        ),
        policy=policy,
        description="Test supplier",
    )


def reasoning():

    return ProcurementReasoning(
        reasoning_id="RSN-TEST",
        intake_id="INT-TEST",
        objective="Procure servo motors.",
        product_name="Servo Motors",
        quantity=1000,
        target_delivery_days=30,
        target_payment_days=60,
        target_sla_uptime=98,
        target_sla_penalty=2,
        currency="INR",
        priorities=[
            "delivery",
            "sla",
            "price",
        ],
        hard_constraints=[],
        soft_preferences=[],
        missing_information=[],
        risks=[],
        negotiation_brief="test",
        confidence=0.9,
        reasoning_source="deterministic",
    )


def request():

    return AutonomousProcurementRequest(
        text=(
            "Need 1000 servo motors "
            "within 30 days."
        ),
        suppliers=[
            supplier(
                "Supplier A",
                108000,
            ),
            supplier(
                "Supplier B",
                110000,
            ),
        ],
        buyer=buyer_policy(),
        max_attempts=2,
        execution_mode="simulation",
    )


def action():

    return ActResponse(
        action_id="ACT-TEST",
        decision="AGREED",
        reason="test",
        reasoning_id="RSN-TEST",
        negotiation_id="NEG-TEST",
        negotiation={
            "status": "AGREED"
        },
    )


def verification(
    passed,
    violations=None,
):

    return VerificationResult(
        verification_id="VER-TEST",
        action_id="ACT-TEST",
        negotiation_id="NEG-TEST",
        status=(
            "verified"
            if passed
            else "rejected"
        ),
        verified=passed,
        checks=[],
        violations=(
            violations
            or []
        ),
        verified_contract=(
            {
                "contract_hash": "test"
            }
            if passed
            else None
        ),
    )


def test_recovery_reasons_again_and_retries_next_supplier(
    monkeypatch,
):

    reason_calls = []

    def fake_reason(
        intake,
        **kwargs,
    ):

        reason_calls.append(
            kwargs.get(
                "failure_context"
            )
        )

        result = reasoning()

        if kwargs.get(
            "failure_context"
        ):

            result.risks.append(
                "Recovery context considered"
            )

        return result

    act_calls = []

    def fake_act(req):

        act_calls.append(
            req.supplier_name
        )

        return action()

    verify_calls = []

    def fake_verify(req):

        verify_calls.append(
            req.supplier
        )

        if len(verify_calls) == 1:

            return verification(
                False,
                [
                    (
                        "Final delivery exceeds "
                        "buyer maximum delivery period."
                    )
                ],
            )

        return verification(
            True
        )

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        fake_reason,
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        fake_act,
    )

    monkeypatch.setattr(
        procure_module,
        "verify_autonomous_action",
        fake_verify,
    )

    result = (
        procure_module.procure(
            request()
        )
    )

    assert result.verified is True

    assert result.status == "verified"

    assert len(
        act_calls
    ) == 2

    assert (
        act_calls[0]
        != act_calls[1]
    )

    assert len(
        reason_calls
    ) == 2

    assert (
        reason_calls[0]
        is None
    )

    failed_supplier = act_calls[0]
    recovered_supplier = act_calls[1]

    assert (
        failed_supplier
        != recovered_supplier
    )

    assert (
        failed_supplier
        in reason_calls[1]
    )

    assert (
        "delivery"
        in reason_calls[1].lower()
    )

    assert (
        result.stages["recovery"]
        == "complete"
    )

    assert (
        len(
            result.reasoning_history
        )
        == 2
    )

    assert (
        len(
            result.recovery_events
        )
        == 1
    )

    assert (
        result.recovery_events[0][
            "trigger"
        ]
        == "REASON_AGAIN"
    )

    assert result.failure_provenance[0].code == "VERIFY_FAIL"
    assert result.failure_provenance[0].stage == "VERIFY"
    assert result.failure_provenance[0].attempt == 1
    assert (
        result.failure_provenance[0].supplier
        == act_calls[0]
    )
    assert result.failure_provenance[0].recoverable is True

    assert (
        result.attempts[0]
        .recovery_triggered
        is True
    )

    assert (
        result.attempts[1]
        .verified
        is True
    )


def test_recovery_does_not_retry_same_supplier(
    monkeypatch,
):

    calls = []

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        lambda *args, **kwargs: (
            reasoning()
        ),
    )

    def fake_act(req):

        calls.append(
            req.supplier_name
        )

        raise RuntimeError(
            "supplier execution failed"
        )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        fake_act,
    )

    result = (
        procure_module.procure(
            request()
        )
    )

    assert result.verified is False

    assert len(calls) == 2

    assert calls[0] != calls[1]

    assert (
        result.status
        == "recovery_exhausted"
    )

def test_recovery_classifies_verification_failure(monkeypatch):

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        lambda intake, **kwargs: reasoning(),
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        lambda req: action(),
    )

    monkeypatch.setattr(
        procure_module,
        "verify_autonomous_action",
        lambda req: verification(
            False,
            [
                "Final terms violate buyer policy constraints."
            ],
        ),
    )

    result = procure_module.procure(
        request().model_copy(
            update={
                "max_attempts": 1,
            }
        )
    )

    assert result.verified is False

    assert result.failure_code == "POLICY_BLOCK"

    assert result.attempts[0].failure_code == "POLICY_BLOCK"


def test_recovery_exhaustion_is_bounded_and_classified(monkeypatch):

    reason_calls = []

    def fake_reason(intake, **kwargs):
        reason_calls.append(kwargs.get("failure_context"))
        return reasoning()

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        fake_reason,
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        lambda req: action(),
    )

    monkeypatch.setattr(
        procure_module,
        "verify_autonomous_action",
        lambda req: verification(
            False,
            [
                "Final delivery exceeds buyer maximum delivery period."
            ],
        ),
    )

    result = procure_module.procure(
        request().model_copy(
            update={
                "max_attempts": 2,
            }
        )
    )

    assert result.verified is False
    assert result.status == "recovery_exhausted"
    assert len(result.attempts) == 2
    assert all(
        item.failure_code == "VERIFY_FAIL"
        for item in result.attempts
    )
    assert result.failure_code == "VERIFY_FAIL"
    assert len(reason_calls) == 2


def test_failure_provenance_records_act_failure(monkeypatch):

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        lambda intake, **kwargs: reasoning(),
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        lambda req: (_ for _ in ()).throw(
            RuntimeError("Lyzr provider timeout")
        ),
    )

    result = procure_module.procure(
        request().model_copy(
            update={"max_attempts": 1}
        )
    )

    assert result.verified is False
    assert result.failure_code == "TIMEOUT"
    assert len(result.failure_provenance) == 1
    assert result.failure_provenance[0].stage == "ACT"
    assert result.failure_provenance[0].code == "TIMEOUT"
    assert result.failure_provenance[0].recoverable is False


def test_failure_provenance_records_recovery_failure(monkeypatch):

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        lambda intake, **kwargs: (
            (_ for _ in ()).throw(
                RuntimeError("Lyzr reasoning failed")
            )
            if kwargs.get("failure_context")
            else reasoning()
        ),
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        lambda req: (_ for _ in ()).throw(
            RuntimeError("initial Lyzr failure")
        ),
    )

    result = procure_module.procure(
        request().model_copy(
            update={"max_attempts": 2}
        )
    )

    assert result.verified is False
    assert any(
        item.stage == "RECOVERY"
        and item.code == "LYZR_ERROR"
        for item in result.failure_provenance
    )
    assert result.failure_code == "LYZR_ERROR"


def test_simulation_supplier_read_does_not_hit_live_network(
    monkeypatch,
):

    def fail_live_fetch(url):
        raise AssertionError(
            "Simulation mode must not call the live supplier URL."
        )

    monkeypatch.setattr(
        "autonomous.read._fetch_source",
        fail_live_fetch,
    )

    monkeypatch.setattr(
        procure_module,
        "reason_about_procurement",
        lambda intake, **kwargs: reasoning(),
    )

    monkeypatch.setattr(
        procure_module,
        "act_on_procurement",
        lambda req: action(),
    )

    monkeypatch.setattr(
        procure_module,
        "verify_autonomous_action",
        lambda req: verification(True),
    )

    result = procure_module.procure(
        request()
    )

    assert result.verified is True
