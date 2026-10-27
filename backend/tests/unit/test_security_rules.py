"""Scraped job data is untrusted: it can't run formulas in Excel or send auto-apply somewhere it shouldn't go."""

import csv

from openpyxl import load_workbook

from job_search.models import Job
from job_search.services.auto_apply.platforms import on_board
from job_search.services.reporting.excel_csv import as_text, write_reports
from job_search.services.scraping.apply_links import external_apply_url, public_host


def test_spreadsheet_cells_never_become_formulas(tmp_path):
    job = Job("naukri", "1", '=HYPERLINK("http://evil.example","Click")', "+Acme", "@Pune", "file:///C:/Windows/calc.exe",
              match_reason="-2+3", score=80)
    xlsx, csv_path = write_reports([job], tmp_path, "jobs")
    row = list(load_workbook(xlsx).active.iter_rows(min_row=2, values_only=True))[0]
    assert row[1:4] == ("'=HYPERLINK(\"http://evil.example\",\"Click\")", "'+Acme", "'@Pune")
    link = load_workbook(xlsx).active.cell(row=2, column=11)
    assert link.hyperlink is None  # only http(s) links are clickable
    with csv_path.open(encoding="utf-8-sig") as handle:
        assert list(csv.reader(handle))[1][1].startswith("'=")
    assert as_text("AI Engineer") == "AI Engineer" and as_text(85) == 85


def test_apply_links_never_point_inside_your_network():
    for host in ("localhost", "127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.9", "169.254.169.254", "[::1]",
                 "router.local", "nas.lan", "0.0.0.0", "intranet"):
        assert not public_host(host), host
    assert public_host("boards.greenhouse.io") and public_host("8.8.8.8")
    assert external_apply_url("http://192.168.1.1/admin") == ""
    assert external_apply_url("https://www.linkedin.com/x?url=http%3A%2F%2F127.0.0.1%3A8000%2Fapi", board_hosts=("linkedin.com",)) == ""
    assert external_apply_url("https://jobs.lever.co/acme/1") == "https://jobs.lever.co/acme/1"


def test_easy_apply_links_must_be_on_their_board():
    assert on_board("https://www.linkedin.com/jobs/view/1/", "linkedin")
    assert on_board("https://in.indeed.com/viewjob?jk=1", "indeed") and on_board("https://www.naukri.com/job-1", "naukri")
    assert not on_board("https://evil.example/linkedin.com", "linkedin")
    assert not on_board("https://linkedin.com.evil.example/", "linkedin")
    assert not on_board("javascript:alert(1)", "naukri") and not on_board("https://www.naukri.com/1", "indeed")
