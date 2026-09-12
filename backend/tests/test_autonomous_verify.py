from autonomous.verify import (
    _check_delivery,
    _check_payment,
    _check_price,
    _check_sla,
    _calculate_contract_hash,
)

from models.policy import (
    DeliveryPolicy,
    PartyPolicy,
    PaymentPolicy,
    PricePolicy,
    SLAPolicy,
)


def make_policy():

    return PartyPolicy(
        price=PricePolicy(
            target=110000,
            minimum=100000,
            maximum=120000,
        ),
        delivery=DeliveryPolicy(
            target_days=30,
            maximum_days=40,
        ),
        payment=PaymentPolicy(
            preferred_days=60,
            minimum_days=30,
        ),
        sla=SLAPolicy(
            minimum_uptime=98,
            minimum_penalty=1,
            maximum_penalty=5,
        ),
        batna="No-deal",
        max_rounds=8,
    )


def test_valid_price_passes():

    policy = make_policy()

    assert _check_price(
        110000,
        policy,
        policy,
    ) == []


def test_price_outside_policy_fails():

    policy = make_policy()

    violations = _check_price(
        130000,
        policy,
        policy,
    )

    assert len(violations) > 0


def test_delivery_outside_policy_fails():

    policy = make_policy()

    violations = _check_delivery(
        50,
        policy,
        policy,
    )

    assert len(violations) > 0


def test_payment_below_minimum_fails():

    policy = make_policy()

    violations = _check_payment(
        15,
        policy,
        policy,
    )

    assert len(violations) > 0


def test_sla_outside_policy_fails():

    policy = make_policy()

    violations = _check_sla(
        97,
        6,
        policy,
        policy,
    )

    assert len(violations) > 0


def test_contract_hash_is_deterministic():

    contract = {
        "contract_id": "CTR-TEST",
        "unit_price": 110000,
        "quantity": 1000,
        "currency": "INR",
        "contract_hash": "ignored",
    }

    first = _calculate_contract_hash(
        contract
    )

    contract["contract_hash"] = first

    second = _calculate_contract_hash(
        contract
    )

    assert first == second