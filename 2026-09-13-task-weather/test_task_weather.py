import json
from datetime import date, timedelta

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
