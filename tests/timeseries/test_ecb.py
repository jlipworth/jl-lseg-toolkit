"""Tests for the ECB module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.ecb.models import ECBMeeting, RateDecision

ECB_HTML = """
<html><body>
<dt><time datetime="2026-03-11">Wednesday, 11 March 2026</time></dt>
<dt><time datetime="2026-04-29">Wednesday, 29 April 2026</time></dt>
<dt><time datetime="2026-06-10">Wednesday, 10 June 2026</time></dt>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.ecb.calendar_scraper import (
            parse_future_ecb_meetings,
        )

        meetings = parse_future_ecb_meetings(ECB_HTML, today=date(2026, 4, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 4, 29),
            date(2026, 6, 10),
        ]

    def test_parse_dedupes_repeats(self):
        from lseg_toolkit.timeseries.ecb.calendar_scraper import (
            parse_future_ecb_meetings,
        )

        repeated = ECB_HTML + ECB_HTML
        meetings = parse_future_ecb_meetings(repeated, today=date(2026, 1, 1))
        dates = [m.meeting_date for m in meetings]
        assert len(dates) == len(set(dates))


class TestFetcherBuilders:
    def test_build_assigns_decision_from_rate_change(self):
        from lseg_toolkit.timeseries.ecb.fetcher import (
            build_ecb_meetings_from_dates,
        )

        dates = [date(2026, 1, 30), date(2026, 3, 13), date(2026, 4, 24)]
        rate_history = {
            date(2026, 1, 30): 4.0,
            date(2026, 3, 13): 3.75,
            date(2026, 4, 24): 3.75,
        }
        meetings = build_ecb_meetings_from_dates(dates, rate_history)

        assert meetings[0].decision is None
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25
        assert meetings[2].decision == RateDecision.HOLD


class TestFetchECBMeetings:
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_future_ecb_meetings")
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_dfr_history")
    def test_merges_future_with_historical(self, mock_dfr, mock_future):
        from lseg_toolkit.timeseries.ecb.fetcher import fetch_ecb_meetings

        mock_dfr.return_value = {date(2025, 12, 1): 3.25}
        mock_future.return_value = [
            ECBMeeting(meeting_date=date(2026, 3, 11), source="ecb_calendar")
        ]

        meetings = fetch_ecb_meetings()
        dates = [m.meeting_date for m in meetings]
        assert date(2025, 12, 1) in dates
        assert date(2026, 3, 11) in dates

    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_future_ecb_meetings")
    @patch("lseg_toolkit.timeseries.ecb.fetcher.fetch_dfr_history")
    def test_falls_back_when_fred_missing(self, mock_dfr, mock_future):
        from lseg_toolkit.timeseries.ecb.fetcher import fetch_ecb_meetings

        mock_dfr.side_effect = ValueError("FRED_API_KEY environment variable not set")
        mock_future.return_value = [
            ECBMeeting(meeting_date=date(2026, 3, 11), source="ecb_calendar")
        ]

        meetings = fetch_ecb_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
