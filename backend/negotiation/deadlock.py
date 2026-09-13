def price_is_feasible(
    buyer_policy,
    supplier_policy,
) -> bool:

    buyer_max = buyer_policy.price.maximum
    supplier_min = supplier_policy.price.minimum

    if (
        buyer_max is None
        or supplier_min is None
    ):
        return True

    return buyer_max >= supplier_min

def detect_stagnation(
    gaps: list[float],
    repeated_rounds: int,
    threshold: int = 3,
) -> bool:

    if repeated_rounds >= threshold:
        return True

    if len(gaps) < 3:
        return False

    first = gaps[-3]
    second = gaps[-2]
    third = gaps[-1]

    tolerance = 0.0005

    return (
        second >= first - tolerance
        and third >= second - tolerance
    )