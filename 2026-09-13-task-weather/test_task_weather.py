import json
from datetime import date

from task_weather import forecast, parse_tasks, render


def test_parse_tasks_extracts_status_priority_dates_and_tags():
    tasks = parse_tasks("""# Sprint
- [ ] Ship it!!! 2026-09-14 #launch
- [x] Write docs #docs
- ordinary note
""")
    assert len(tasks) == 2
    assert tasks[0].priority == 3
    assert tasks[0].due == "2026-09-14"
    assert tasks[0].tags == ["launch"]
    assert tasks[1].done is True


def test_forecast_clear_when_everything_is_done():
    report = forecast(parse_tasks("- [x] Finished\n"))
    assert report["condition"] == "clear skies"
    assert report["open"] == 0


def test_pressure_rises_for_urgent_open_tasks():
    text = f"- [ ] Fix outage!!! {date.today().isoformat()}\n- [ ] Deploy!!!"
    report = forecast(parse_tasks(text))
    assert report["condition"] == "thunderstorm"
    assert report["pressure"] >= 18


def test_render_contains_task_and_forecast():
    tasks = parse_tasks("- [ ] Read a book\n")
    output = render(tasks, forecast(tasks))
    assert "TASK WEATHER" in output
    assert "Read a book" in output
    assert output.startswith("┌") and output.endswith("┘")


def test_invalid_dates_are_not_reported_as_due_dates():
    task = parse_tasks("- [ ] Impossible date 2026-02-30")[0]
    assert task.due is None


def test_forecast_can_be_pinned_to_a_reference_date():
    tasks = parse_tasks("- [ ] Ship 2026-01-02")
    assert forecast(tasks, date(2026, 1, 1))["pressure"] == 5
    assert forecast(tasks, date(2026, 1, 10))["pressure"] == 7
