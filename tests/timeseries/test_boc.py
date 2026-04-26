"""Tests for the BoC module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.boc.models import BoCMeeting, RateDecision

BOC_HTML = """
<html><body>
<p>March 12, 2026</p>
<p>April 16, 2026</p>
<p>June 4, 2026</p>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.boc.calendar_scraper import (
            parse_future_boc_meetings,
        )

        meetings = parse_future_boc_meetings(BOC_HTML, today=date(2026, 4, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 4, 16),
            date(2026, 6, 4),
        ]


class TestFetcherBuilders:
    def test_build_assigns_decision(self):
        from lseg_toolkit.timeseries.boc.fetcher import build_boc_meetings_from_dates

        dates = [date(2026, 1, 22), date(2026, 3, 12)]
        rate_history = {date(2026, 1, 22): 4.0, date(2026, 3, 12): 3.75}
        meetings = build_boc_meetings_from_dates(dates, rate_history)
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25


class TestFetchBoCMeetings:
    @patch("lseg_toolkit.timeseries.boc.fetcher.fetch_future_boc_meetings")
    @patch("lseg_toolkit.timeseries.boc.fetcher.fetch_target_rate_history")
    def test_falls_back_when_valet_unreachable(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boc.fetcher import fetch_boc_meetings

        mock_rate.side_effect = RuntimeError("Valet 503")
        mock_future.return_value = [
            BoCMeeting(meeting_date=date(2026, 4, 16), source="boc_calendar")
        ]
        meetings = fetch_boc_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
