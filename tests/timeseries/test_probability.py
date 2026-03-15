"""Tests for probability distribution reconstruction from prediction markets."""

from lseg_toolkit.timeseries.prediction_markets.analysis.probability import (
    compare_distributions,
    implied_rate,
    rate_distribution,
)
from lseg_toolkit.timeseries.prediction_markets.models import Market


def _make_kxfed_markets(prices: dict[float, float]) -> list[Market]:
    """Helper: create KXFED markets with given strike→last_price mapping."""
    return [
        Market(
            platform_id=1,
            market_ticker=f"KXFED-26JAN-T{strike:.2f}",
            platform_market_id=f"m-{strike}",
            title=f"Rate above {strike}%",
            strike_value=strike,
            last_price=price,
            status="settled",
        )
        for strike, price in sorted(prices.items())
    ]


class TestRateDistribution:
    """Tests for CDF differencing on KXFED strike ladder."""

    def test_basic_distribution(self):
        """Simple 3-strike ladder should produce valid distribution."""
        markets = _make_kxfed_markets(
            {
                3.50: 0.99,  # P(rate > 3.50) = 99%
                3.75: 0.96,  # P(rate > 3.75) = 96%
                4.00: 0.03,  # P(rate > 4.00) = 3%
            }
        )
        dist = rate_distribution(markets)

        # P(rate in [3.50, 3.75]) = 0.99 - 0.96 = 0.03
        assert abs(dist["3.50-3.75"] - 0.03) < 1e-6
        # P(rate in [3.75, 4.00]) = 0.96 - 0.03 = 0.93
        assert abs(dist["3.75-4.00"] - 0.93) < 1e-6

    def test_distribution_sums_to_one(self):
        """After including tails, probabilities should sum to ~1.0."""
        markets = _make_kxfed_markets(
            {
                3.50: 0.99,
                3.75: 0.96,
                4.00: 0.03,
                4.25: 0.01,
            }
        )
        dist = rate_distribution(markets)

        total = sum(dist.values())
        assert abs(total - 1.0) < 0.02  # Allow small tolerance

    def test_verified_kxfed_26jan_data(self):
        """Reproduce the verified KXFED-26JAN result from API exploration.

        Day before meeting: 96% probability in 3.50-3.75% bucket.
        """
        markets = _make_kxfed_markets(
            {
                3.00: 0.99,
                3.25: 0.99,
                3.50: 0.99,
                3.75: 0.03,
                4.00: 0.02,
                4.25: 0.01,
            }
        )
        dist = rate_distribution(markets)

        # Main bucket: 3.50-3.75 should be 0.99 - 0.03 = 0.96
        assert abs(dist["3.50-3.75"] - 0.96) < 1e-6

    def test_handles_non_monotonic_cdf(self):
        """Should clip negative probabilities to zero and renormalize."""
        markets = _make_kxfed_markets(
            {
                3.50: 0.95,
                3.75: 0.97,  # Non-monotonic: higher than previous
                4.00: 0.03,
            }
        )
        dist = rate_distribution(markets)

        # All probabilities should be >= 0
        assert all(p >= 0 for p in dist.values())
        # Should still sum to ~1.0 after renormalization
        total = sum(dist.values())
        assert abs(total - 1.0) < 0.02

    def test_empty_markets_returns_empty(self):
        dist = rate_distribution([])
        assert dist == {}

    def test_single_market_returns_empty(self):
        """Need at least 2 strikes for CDF differencing."""
        markets = _make_kxfed_markets({3.50: 0.99})
        dist = rate_distribution(markets)
        assert dist == {}


class TestImpliedRate:
    """Tests for expected rate calculation."""

    def test_implied_rate_basic(self):
        """Expected rate = sum(midpoint * probability)."""
        markets = _make_kxfed_markets(
            {
                3.50: 0.99,
                3.75: 0.96,
                4.00: 0.03,
                4.25: 0.01,
            }
        )
        rate = implied_rate(markets)

        # Most probability in 3.75-4.00 bucket (midpoint 3.875)
        # Some in 3.50-3.75 bucket (midpoint 3.625)
        assert 3.5 < rate < 4.25

    def test_implied_rate_verified_data(self):
        """Verified: expected rate from KXFED-26JAN was ~3.63%."""
        markets = _make_kxfed_markets(
            {
                3.00: 0.99,
                3.25: 0.99,
                3.50: 0.99,
                3.75: 0.03,
                4.00: 0.02,
                4.25: 0.01,
            }
        )
        rate = implied_rate(markets)

        # Verified: expected rate was 3.63% (actual outcome: 3.75% upper bound)
        assert abs(rate - 3.63) < 0.1

    def test_empty_returns_none(self):
        assert implied_rate([]) is None


class TestCompareDistributions:
    """Tests for distribution comparison metrics."""

    def test_identical_distributions(self):
        d = {"3.50-3.75": 0.5, "3.75-4.00": 0.5}
        result = compare_distributions(d, d)

        assert result["max_divergence"] == 0.0
        assert result["brier_score"] == 0.0

    def test_different_distributions(self):
        pm = {"3.50-3.75": 0.9, "3.75-4.00": 0.1}
        stir = {"3.50-3.75": 0.6, "3.75-4.00": 0.4}
        result = compare_distributions(pm, stir)

        assert abs(result["max_divergence"] - 0.3) < 1e-9
        assert result["brier_score"] > 0
        assert result["kl_divergence"] > 0  # Distributions differ → positive KL

    def test_identical_has_zero_kl(self):
        d = {"3.50-3.75": 0.5, "3.75-4.00": 0.5}
        result = compare_distributions(d, d)
        assert abs(result["kl_divergence"]) < 1e-9

    def test_empty_returns_none(self):
        assert compare_distributions({}, {"a": 1.0}) is None
        assert compare_distributions({"a": 1.0}, {}) is None
