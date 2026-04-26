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

# Sample shape mirroring BoE Interactive Database response (IUDBEDR daily).
BOE_IADB_HTML = """
<TABLE>
<tr><td width="75" align="right" nowrap>04 Aug 16</td><td align="right">0.25</td></tr>
<tr><td width="75" align="right" nowrap>05 Aug 16</td><td align="right">0.25</td></tr>
<tr><td width="75" align="right" nowrap>02 Nov 17</td><td align="right">0.50</td></tr>
<tr><td width="75" align="right" nowrap>03 Nov 17</td><td align="right">0.50</td></tr>
<tr><td width="75" align="right" nowrap>02 Aug 18</td><td align="right">0.75</td></tr>
</TABLE>
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


class TestBankRateScraper:
    def test_parse_iadb_html_extracts_rate_history(self):
        from lseg_toolkit.timeseries.boe.bank_rate_scraper import (
            parse_boe_bank_rate_html,
        )

        history = parse_boe_bank_rate_html(BOE_IADB_HTML)
        assert history == {
            date(2016, 8, 4): 0.25,
            date(2016, 8, 5): 0.25,
            date(2017, 11, 2): 0.50,
            date(2017, 11, 3): 0.50,
            date(2018, 8, 2): 0.75,
        }

    def test_derive_decision_dates_filters_to_changes(self):
        from lseg_toolkit.timeseries.boe.bank_rate_scraper import (
            derive_decision_dates,
            parse_boe_bank_rate_html,
        )

        dates = derive_decision_dates(parse_boe_bank_rate_html(BOE_IADB_HTML))
        # First observation is always a "change" (no prior); subsequent only on diff.
        assert dates == [
            date(2016, 8, 4),
            date(2017, 11, 2),
            date(2018, 8, 2),
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
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_boe_bank_rate_history")
    def test_falls_back_when_iadb_unreachable(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings

        mock_rate.side_effect = RuntimeError("BoE IADB unreachable")
        mock_future.return_value = [
            BoEMeeting(meeting_date=date(2026, 3, 20), source="boe_calendar")
        ]
        meetings = fetch_boe_meetings(allow_missing_rate_history=True)
        assert len(meetings) == 1
        assert meetings[0].rate_upper is None

    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_future_boe_meetings")
    @patch("lseg_toolkit.timeseries.boe.fetcher.fetch_boe_bank_rate_history")
    def test_uses_iadb_history_for_decisions(self, mock_rate, mock_future):
        from lseg_toolkit.timeseries.boe.fetcher import fetch_boe_meetings

        mock_rate.return_value = {
            date(2024, 8, 1): 5.00,
            date(2024, 9, 19): 5.00,
            date(2024, 11, 7): 4.75,
        }
        mock_future.return_value = []
        meetings = fetch_boe_meetings()
        # Only rate-change days become meetings (first + on diff).
        decision_dates = [m.meeting_date for m in meetings]
        assert decision_dates == [date(2024, 8, 1), date(2024, 11, 7)]
        assert meetings[1].decision == RateDecision.CUT
        assert meetings[1].rate_change_bps == -25
