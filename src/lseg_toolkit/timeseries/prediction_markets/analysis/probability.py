"""Probability distribution reconstruction from prediction market data.

KXFED markets form a ladder of binary contracts ("rate > X%?") at 25bps
intervals. Prices are cumulative probabilities. The probability of the rate
landing in a specific bucket is the difference between adjacent strikes.
"""

import math

from lseg_toolkit.timeseries.prediction_markets.models import Market


def rate_distribution(markets: list[Market]) -> dict[str, float]:
    """
    CDF differencing across a KXFED strike ladder.

    Takes a list of KXFED markets (each with strike_value and last_price)
    and computes P(rate in bucket) = P(rate > lower) - P(rate > upper).

    Handles edge cases:
    - Non-monotonic CDF (stale prices): clips negative probabilities to zero
    - Renormalizes so total probability = 1.0

    Args:
        markets: List of Market models with strike_value and last_price set.
            Can use last_price (current) or price_close from candlesticks.

    Returns:
        Dict mapping rate bucket labels to probabilities.
        E.g. {"3.50-3.75": 0.96, "3.75-4.00": 0.03}
    """
    # Filter to markets with strike values and prices
    priced = [
        m for m in markets if m.strike_value is not None and m.last_price is not None
    ]
    if len(priced) < 2:
        return {}

    # Sort by strike ascending
    priced.sort(key=lambda m: m.strike_value or 0.0)

    # CDF differencing
    raw_probs: dict[str, float] = {}

    # Lower tail: P(rate <= lowest_strike) = 1 - P(rate > lowest_strike)
    lowest = priced[0]
    lower_tail = 1.0 - (lowest.last_price or 0.0)
    if lower_tail > 0.001:
        raw_probs[f"<{lowest.strike_value:.2f}"] = lower_tail

    # Interior buckets
    for i in range(len(priced) - 1):
        lower = priced[i]
        upper = priced[i + 1]
        prob = (lower.last_price or 0.0) - (upper.last_price or 0.0)
        label = f"{lower.strike_value:.2f}-{upper.strike_value:.2f}"
        raw_probs[label] = prob

    # Upper tail: P(rate > highest_strike)
    highest = priced[-1]
    upper_tail = highest.last_price or 0.0
    if upper_tail > 0.001:
        raw_probs[f">{highest.strike_value:.2f}"] = upper_tail

    # Clip negative probabilities (from non-monotonic CDF)
    clipped = {k: max(0.0, v) for k, v in raw_probs.items()}

    # Renormalize to sum to 1.0
    total = sum(clipped.values())
    if total == 0:
        return {}

    return {k: v / total for k, v in clipped.items()}


def implied_rate(markets: list[Market]) -> float | None:
    """
    Calculate expected rate from a KXFED strike ladder.

    Expected rate = sum(bucket_midpoint * probability).

    Args:
        markets: List of KXFED Market models.

    Returns:
        Expected rate as a float, or None if insufficient data.
    """
    dist = rate_distribution(markets)
    if not dist:
        return None

    expected = 0.0
    for label, prob in dist.items():
        if label.startswith("<"):
            # Lower tail: use strike - 0.125 as midpoint
            strike = float(label[1:])
            midpoint = strike - 0.125
        elif label.startswith(">"):
            # Upper tail: use strike + 0.125 as midpoint
            strike = float(label[1:])
            midpoint = strike + 0.125
        else:
            # Interior bucket: midpoint of range
            low, high = label.split("-")
            midpoint = (float(low) + float(high)) / 2

        expected += midpoint * prob

    return expected


def compare_distributions(
    pm_dist: dict[str, float],
    stir_dist: dict[str, float],
) -> dict | None:
    """
    Compare two probability distributions.

    Renamed from spec's `compare_to_stir` since the function is
    provider-agnostic and works with any two distributions.

    Args:
        pm_dist: Prediction market distribution.
        stir_dist: STIR futures distribution.

    Returns:
        Dict with comparison metrics, or None if inputs are empty.
        Keys: brier_score, kl_divergence, max_divergence, max_divergence_bucket
    """
    if not pm_dist or not stir_dist:
        return None

    # Align on common buckets
    all_buckets = sorted(set(pm_dist.keys()) | set(stir_dist.keys()))

    brier_sum = 0.0
    kl_sum = 0.0
    max_div = 0.0
    max_bucket = ""

    for bucket in all_buckets:
        p = pm_dist.get(bucket, 0.0)
        s = stir_dist.get(bucket, 0.0)
        diff = abs(p - s)

        brier_sum += (p - s) ** 2

        # KL divergence: sum(p * log(p/s)) for p > 0 and s > 0
        if p > 0 and s > 0:
            kl_sum += p * math.log(p / s)

        if diff > max_div:
            max_div = diff
            max_bucket = bucket

    brier_score = brier_sum / len(all_buckets)

    return {
        "brier_score": brier_score,
        "kl_divergence": kl_sum,
        "max_divergence": max_div,
        "max_divergence_bucket": max_bucket,
    }
