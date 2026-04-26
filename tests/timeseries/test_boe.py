"""Tests for the BoE module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.boe.models import BoEMeeting, RateDecision

BOE_HTML = """
<html><body>
<ul>
  <li>6 February 2026</li>
  <li>20 March 2026</li>
  <li>8 May 2026</li>
</ul>
</body></html>
"""


class TestCalendarScraper:
    def test_parse_filters_past_dates(self):
        from lseg_toolkit.timeseries.boe.calendar_scraper import (
            parse_future_boe_meetings,
        )

        meetings = parse_future_boe_meetings(BOE_HTML, today=date(2026, 3, 1))
        assert [m.meeting_date for m in meetings] == [
            date(2026, 3, 20),
            date(2026, 5, 8),
        ]


class TestFetcherBuilders:
    def test_build_assigns_decision_from_rate_change(self):
        from lseg_toolkit.timeseries.boe.fetcher import build_boe_meetings_from_dates

        dates = [date(2026, 2, 6), date(2026, 3, 20)]
        rate_history = {date(2026, 2, 6): 4.5, date(2026, 3, 20): 4.25}
        meetings = build_boe_meetings_from_dates(dates, rate_history)
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25


class TestFetchBoEMeetings:
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_future_boe_meetings")
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_bank_rate_history")
    def test_falls_back_when_fred_missing(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings

        mock_rate.side_effect = ValueError("FRED_API_KEY environment variable not set")
        mock_future.return_value = [
            BoEMeeting(meeting_date=date(2026, 3, 20), source="boe_calendar")
        ]
        meetings = fetch_boe_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None
