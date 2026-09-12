import pytest

from models.policy import PricePolicy

def test_valid_price_policy():
    policy = PricePolicy(
        target=100,
        minimum=90,
        maximum=110,
    )

    assert policy.target == 100
    assert policy.minimum == 90
    assert policy.maximum == 110

def test_negative_price_is_rejected():
    with pytest.raises(ValueError):
        PricePolicy(
            target=-100,
            minimum=90,
            maximum=110,
        )