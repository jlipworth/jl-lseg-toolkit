"""Tests for the FOMC module."""

from datetime import date
from unittest.mock import patch

from lseg_toolkit.timeseries.fomc.models import FOMCMeeting

CALENDAR_HTML = """
<div class="panel panel-default"><div class="panel-heading"><h4><a id="2026">2026 FOMC Meetings</a></h4></div>
    <div class="row fomc-meeting" ">
        <div class="fomc-meeting__month col-xs-5 col-sm-3 col-md-2"><strong>January</strong></div>
        <div class="fomc-meeting__date col-xs-4 col-sm-9 col-md-10 col-lg-1">27-28</div>
    </div>
    <div class="fomc-meeting--shaded row fomc-meeting" ">
        <div class="fomc-meeting--shaded fomc-meeting__month col-xs-5 col-sm-3 col-md-2"><strong>March</strong></div>
        <div class="fomc-meeting__date col-xs-4 col-sm-9 col-md-10 col-lg-1">17-18*</div>
    </div>
</div>
<div class="panel panel-default"><div class="panel-heading"><h4><a id="2027">2027 FOMC Meetings</a></h4></div>
    <div class="row fomc-meeting" ">
        <div class="fomc-meeting__month col-xs-5 col-sm-3 col-md-2"><strong>Jan/Feb</strong></div>
        <div class="fomc-meeting__date col-xs-4 col-sm-9 col-md-10 col-lg-1">31-1</div>
    </div>
    <div class="fomc-meeting--shaded row fomc-meeting" ">
        <div class="fomc-meeting--shaded fomc-meeting__month col-xs-5 col-sm-3 col-md-2"><strong>March</strong></div>
        <div class="fomc-meeting__date col-xs-4 col-sm-9 col-md-10 col-lg-1">16-17*</div>
    </div>
</div>
</body>
"""


class TestCalendarScraper:
    def test_parse_future_fomc_meetings_filters_past_rows(self):
        from lseg_toolkit.timeseries.fomc.calendar_scraper import (
            parse_future_fomc_meetings,
        )

        meetings = parse_future_fomc_meetings(
            CALENDAR_HTML,
            today=date(2026, 2, 1),
        )

        assert [meeting.meeting_date for meeting in meetings] == [
            date(2026, 3, 18),
            date(2027, 2, 1),
            date(2027, 3, 17),
        ]

    def test_parse_future_fomc_meetings_handles_cross_month_rows(self):
        from lseg_toolkit.timeseries.fomc.calendar_scraper import (
            parse_future_fomc_meetings,
        )

        meetings = parse_future_fomc_meetings(
            CALENDAR_HTML,
            today=date(2027, 1, 1),
        )

        assert meetings[0].meeting_start_date == date(2027, 1, 31)
        assert meetings[0].meeting_date == date(2027, 2, 1)
        assert meetings[0].source == "fed_calendar"
        assert meetings[1].has_sep is True


class TestFetchFOMCMeetings:
    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_future_fomc_meetings")
    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_fomc_dates_from_fedtools")
    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_fed_funds_rate_history")
    def test_fetch_fomc_meetings_merges_future_schedule(
        self,
        mock_rate_history,
        mock_fedtools,
        mock_future,
    ):
        from lseg_toolkit.timeseries.fomc.fetcher import fetch_fomc_meetings

        mock_fedtools.return_value = [date(2026, 1, 28)]
        mock_rate_history.return_value = [
            {"date": date(2026, 1, 28), "upper": 4.50, "lower": 4.25}
        ]
        mock_future.return_value = [
            FOMCMeeting(
                meeting_date=date(2026, 3, 18),
                meeting_start_date=date(2026, 3, 17),
                source="fed_calendar",
                has_sep=True,
                has_presser=True,
            )
        ]

        meetings = fetch_fomc_meetings()

        assert [meeting.meeting_date for meeting in meetings] == [
            date(2026, 1, 28),
            date(2026, 3, 18),
        ]
        assert meetings[0].source == "fedtools"
        assert meetings[0].rate_upper == 4.50
        assert meetings[1].source == "fed_calendar"

    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_future_fomc_meetings")
    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_fomc_dates_from_fedtools")
    @patch("lseg_toolkit.timeseries.fomc.fetcher.fetch_fed_funds_rate_history")
    def test_fetch_fomc_meetings_can_fallback_when_fred_key_missing(
        self,
        mock_rate_history,
        mock_fedtools,
        mock_future,
    ):
        from lseg_toolkit.timeseries.fomc.fetcher import fetch_fomc_meetings

        mock_fedtools.return_value = [date(2025, 1, 29)]
        mock_rate_history.side_effect = ValueError(
            "FRED_API_KEY environment variable not set"
        )
        mock_future.return_value = []

        meetings = fetch_fomc_meetings(allow_missing_rate_history=True)

        assert len(meetings) == 1
        assert meetings[0].meeting_date == date(2025, 1, 29)
        assert meetings[0].rate_upper is None
        assert meetings[0].rate_lower is None
