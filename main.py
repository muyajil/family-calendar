import requests
from icalendar import Calendar
import datetime as dt
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from typing import Literal, Optional
from weasyprint import HTML
import time
import os


app = FastAPI()

# Apply Timezone from env TZ
time.tzset()

WEEKDAYS = {
    0: "MO",
    1: "TU",
    2: "WE",
    3: "TH",
    4: "FR",
    5: "SA",
    6: "SU",
}


# CALENDARS = {
#     "🧔🏾‍♂️ Papi": "https://calendar.google.com/calendar/ical/mohammed%40ajil.ch/private-84c41a849708e86f2bbec955313cd040/basic.ics",
#     "🙋🏼‍♀️ Mami": "https://calendar.google.com/calendar/ical/larissa%40ajil.ch/private-b0079af6089fb2c216e36a6725445b97/basic.ics",
#     "👧🏽 Liana": "https://calendar.google.com/calendar/ical/liana%40ajil.ch/private-25cc80f17abf95e2642a2a4fc8cd4d85/basic.ics",
#     "👦🏽 Louai": "https://calendar.google.com/calendar/ical/louai%40ajil.ch/private-0f37554ab3acea9d1a88e8dc29896298/basic.ics",
#     "👶🏽 Mounir": "https://calendar.google.com/calendar/ical/mounir%40ajil.ch/private-373c517aa5e11fd77fd6439c047941c7/basic.ics",
#     "🎂 Birthdays": "https://calendar.google.com/calendar/ical/c_39cc4940487b0ba5997916afe101d20b52948233ba4087eedc36e2ecc0b77fc7%40group.calendar.google.com/private-8533f7d9a2338266c019cfaf05469923/basic.ics",
#     "🌴 Schulferien": "https://calendar.google.com/calendar/ical/4r9ae1aug8db4ischbec7fodsu6ch644%40import.calendar.google.com/public/basic.ics",
# }

# COLORS = {
#     "🧔🏾‍♂️ Papi": "#af7dff",
#     "🙋🏼‍♀️ Mami": "#f4be40",
#     "👧🏽 Liana": "#D81B60",
#     "👦🏽 Louai": "#4285F4",
#     "👶🏽 Mounir": "#0B8043",
#     "🎂 Birthdays": "#bfcaff",
#     "🌴 Schulferien": "#D50000",
# }

MAX_EVENTS_PER_CELL = 0


def get_html_table(table):
    html = "<head>"
    html += '<meta charset="utf-8">'
    html += '<link rel="preconnect" href="https://fonts.googleapis.com">'
    html += '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    html += '<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">'
    html += "<style type='text/css' media='all'>"
    html += "@page {"
    html += "size: A4 landscape;"
    html += "margin: 0.2cm;"
    html += "}"
    html += "table {"
    html += "width: 100%;"
    html += "table-layout: fixed;"
    html += "border-collapse: collapse;"
    html += "}"
    html += "td {"
    html += "font-family: 'Roboto', sans-serif;"
    html += "vertical-align: top;"
    html += "font-size: 0.6rem;"
    html += "padding-top: 0.2rem;"
    html += f"height: {MAX_EVENTS_PER_CELL * 0.6 * 1.5 + 0.1}rem;"
    html += "line-height: 1.5;"
    html += "}"
    html += ".cell {"
    html += "vertical-align: top;"
    html += "white-space: nowrap;"
    html += "overflow: hidden;"
    html += "font-weight: bold;"
    html += "border-top: 1px solid gray;"
    html += "}"
    html += ".header {"
    html += "font-size: 1rem;"
    html += "vertical-align: center;"
    html += "font-weight: bold;"
    html += "}"
    html += "</style>"
    html += "</head>"
    html += "<body>"

    html += "<table>"
    for idx, row in enumerate(table):
        row_classes = "row"
        html += f'<tr class="{row_classes}">'
        for cell, name in zip(row, table[0]):
            cell_classes = "cell"
            if idx == 0:
                cell_classes += " header"
            bg_color = (
                os.environ[f"COLOR_{name}"]
                if cell != "" and f"COLOR_{name}" in os.environ
                else "#ffffff"
                if idx % 2 == 0
                else "#f0f0f0"
            )
            html += f'<td class="{cell_classes}" style="background-color:{bg_color};">{cell}</td>'
        html += "</tr>"
    html += "</table>"
    html += "</body>"
    return html


def write_table(table, filename, format: Literal["pdf", "html"]):
    html = get_html_table(table)
    if format == "pdf":
        HTML(string=html).write_pdf(f"{filename}.pdf")
        return f"{filename}.pdf"
    else:
        return html


def get_event_dates(component):
    ev_start = component.get("dtstart").dt
    ev_end = component.get("dtend").dt
    if not isinstance(ev_start, dt.datetime):
        ev_start = dt.datetime.combine(ev_start, dt.time(0, 0, 0))
    if not isinstance(ev_end, dt.datetime):
        ev_end = dt.datetime.combine(ev_end, dt.time(0, 0, 0))
    ev_start = ev_start.astimezone(ZoneInfo("Europe/Zurich"))
    ev_end = ev_end.astimezone(ZoneInfo("Europe/Zurich"))
    return ev_start, ev_end


def initialize_day(day, year, month, num_candidates):
    row = [None for _ in range(num_candidates)]
    day = dt.datetime(year, month, day + 1)
    row.insert(0, f"{WEEKDAYS[day.weekday()]} {day.strftime('%d/%m/%Y')}")
    return row


def initialize_table(candidates, num_days, year, month):
    header = [x for x in candidates.keys()]
    header.insert(0, "Date")
    table = [header]
    table.extend(
        [
            initialize_day(day, year, month, len(candidates.keys()))
            for day in range(num_days)
        ]
    )
    return table


def get_relevant_events(names, start_date, end_date):
    relevant_events = dict([(k, []) for k in names])
    for name in names:
        r = requests.get(os.environ[name])
        cal = Calendar.from_ical(r.content)
        components = cal.subcomponents
        for component in components:
            if component.name == "VEVENT":
                try:
                    ev_start, ev_end = get_event_dates(component)
                except Exception:
                    continue
                if (start_date <= ev_start < end_date) or (
                    start_date < ev_end <= end_date
                ):
                    relevant_events[name].append(
                        (ev_start, ev_end, str(component.get("summary")))
                    )
    return relevant_events


def remove_empty_calendars(relevant_events):
    for name in list(relevant_events.keys()):
        if len(relevant_events[name]) == 0:
            _ = relevant_events.pop(name)
        else:
            relevant_events[name].sort(key=lambda x: x[0])
    return relevant_events


def populate_table(relevant_events, start_date, end_date, year, month):
    global MAX_EVENTS_PER_CELL
    table = initialize_table(relevant_events, (end_date - start_date).days, year, month)
    for idx, name in enumerate(relevant_events.keys()):
        for event in relevant_events[name]:
            start, end, summary = event
            num_days = (end - start).days + 1
            if end.hour == 0 and end.minute == 0:
                # If an event ends at midnight on day one, no need to add it this month
                if end.day == 1:
                    continue
                # If an event ends at midnight in general, it ends at the end of the previous day
                num_days -= 1
            if start.month != month:
                # Since we want to start at the beginning of the month, we need to remove the days before
                new_start = dt.datetime(
                    year, month, 1, tzinfo=ZoneInfo("Europe/Zurich")
                )
                too_many_days = (new_start - start).days
                start = new_start
                num_days -= too_many_days
            # We iterate through the days of the event
            for day_offset in range(num_days):
                try:
                    # Initialize field if it is empty
                    if table[start.day + day_offset][idx + 1] is None:
                        table[start.day + day_offset][idx + 1] = []
                    # If the event starts at midnight, its usually a full day, omit start time
                    if start.hour == 0 and start.minute == 0:
                        table[start.day + day_offset][idx + 1].append(f"{summary}")
                    # Append the summary and the start time
                    else:
                        table[start.day + day_offset][idx + 1].append(
                            f"[{start.hour:02d}:{start.minute:02d}] {summary}"
                        )
                    # We use this later to determine the height of the cells
                    MAX_EVENTS_PER_CELL = max(
                        MAX_EVENTS_PER_CELL, len(table[start.day + day_offset][idx + 1])
                    )
                except IndexError:
                    # This is for events that range for a long time
                    continue
    return table


def stringify_table_content(table):
    for x in range(len(table)):
        for y in range(len(table[0])):
            if isinstance(table[x][y], list):
                table[x][y] = "<br>".join(table[x][y])
            if table[x][y] is None:
                table[x][y] = ""
    return table


@app.get("/")
def generate_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    format: Literal["pdf", "html"] = "pdf",
):
    names = os.environ["NAMES"].split(",")
    global MAX_EVENTS_PER_CELL
    if year is None:
        year = dt.datetime.now().year
    if month is None:
        month = dt.datetime.now().month

    start_date = dt.datetime(year, month, 1, tzinfo=ZoneInfo("Europe/Zurich"))
    end_date = dt.datetime(year, month + 1, 1, tzinfo=ZoneInfo("Europe/Zurich"))

    relevant_events = get_relevant_events(names, start_date, end_date)

    relevant_events = remove_empty_calendars(relevant_events)
    table = populate_table(relevant_events, start_date, end_date, year, month)
    table = stringify_table_content(table)
    result = write_table(table, f"calendar_{year}_{month}", format=format)
    print(f"Generated calendar for {year}/{month}")
    if format == "pdf":
        return FileResponse(result)
    else:
        return HTMLResponse(result)


if __name__ == "__main__":
    generate_calendar()