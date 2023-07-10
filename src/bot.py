import json
import time
import os
import requests
import datetime
import pygsheets
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

format_str = '%m/%d/%Y'

auth_token = os.getenv('API_CALLBACK_AUTH_TOKEN')
bot_id = os.getenv('BOT_ID')
sheet_id = os.getenv('GOOGLE_SHEET_ID')
calendar_id = os.getenv('GOOGLE_CALENDAR_ID')

help_text = """Encounter Bot Version 2.0.0

Usage:
!encounter <command>
!e <command>

Commands:
    birthday - View or add birthdays
    event - View events
"""

birthday_help_text = """Birthday command usage:
!encounter birthday <command> <options>
!e birthday <command> <options>

Commands:
    add - Add a birthday
        Syntax:
            !e birthday add M/D/YYYY <Full Name>
        Example: !e birthday add 11/30/1991 Bob Barker
    list - List birthdays
        Options:
            year - List all upcoming birthdays for the year
            month - List all upcoming birthdays for the current month
            week - List all upcoming birthdays for the current week
            day - List all birthdays for the current day
        Syntax:
            !e birthday list <option>
        Example:
            !e birthday list week
"""

event_help_text = """Event command usage:
!encounter event <command> <options>
!e event <command> <options>

Commands:
    list - List events
        Options:
            year - List all upcoming events for the year
            month - List all upcoming events for the current month
            week - List all upcoming events for the current week
            day - List all upcoming events for the current day
        Syntax:
            !e event list <option>
        Example:
            !e event list week
"""


def unauthorized():
    return {
        'statusCode': '401',
        'body': 'Unauthorized',
        'headers': {
            'Content-Type': 'text/plain',
        }
    }


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def callback_handler(event, context):
    if 'queryStringParameters' not in event or 'auth_token' not in event['queryStringParameters'] or \
            event['queryStringParameters']['auth_token'] != auth_token:
        print("Received UNAUTHORIZED event : " + json.dumps(event, indent=2))
        return unauthorized()

    if "body" in event:
        return process_request(json.loads(event['body']))


def daily_handler(event, context):
    print("Received request: " + json.dumps(event, indent=2))
    return list_birthdays("day", True)


def echo(message):
    # Sanitization is for safety to prevent recursive loop attacks
    sanitized = message
    if message.startswith('!encounter'):
        sanitized = message.replace("!encounter", '$', 1)

    limit = 450
    if len(sanitized) > limit:
        lines = sanitized.split('\n')
        buffer = ""
        length = 0
        for line in lines:
            if length + len(line) < limit:  # One under for the new line character
                buffer = buffer + "\n" + line
                length = length + len(line)
            else:
                flush_message(buffer)
                buffer = ""
                length = 0
                time.sleep(1)
        if len(buffer) > 0:
            flush_message(buffer)
    else:
        flush_message(message)


def flush_message(message):
    if message is not None and len(message) > 0 and message[0] == "\n" and len(message) > 1 and message[1] != " ":
        message = message.replace("\n", "", 1)
    print(message)
    requests.post('https://api.groupme.com/v3/bots/post', json={
        "text": message,
        "bot_id": bot_id
    })


def process_request(request):
    print("Received request: " + json.dumps(request, indent=2))

    text = request['text']
    name = request['name']

    if text.startswith("!e ") or text == "!e":
        text = text.replace("!e", "!encounter", 1)

    if text.startswith('!encounter'):
        execute(text.replace("!encounter", "", 1), name)

    return respond(None, {})


def take_space(command):
    if command.startswith(" ") and len(command) > 1:
        return take_space(command.replace(" ", "", 1))
    return command


def execute(command, sender):
    command = take_space(command)

    if command.startswith("birthday"):
        return birthday(command.replace("birthday", "", 1), sender)

    if command.startswith("event"):
        return event(command.replace("event", "", 1), sender)

    return echo(help_text)


def event(command, sender):
    command = take_space(command)

    if command.startswith("list"):
        return list_events(command.replace("list", "", 1))

    return echo(event_help_text)


def list_events(command, silent=False):
    command = take_space(command)

    if command.startswith("year"):
        return echo_events(get_events(), silent)
    # elif command.startswith("month"):
    #     return echo_birthdays(get_birthdays_for_month(), silent)
    # elif command.startswith("week"):
    #     return echo_birthdays(get_birthdays_for_week(), silent)
    # elif command.startswith("day"):
    #     return echo_birthdays(get_birthdays_for_day(), silent)
    else:
        return echo(event_help_text)

def birthday(command, sender):
    command = take_space(command)

    if command.startswith("add"):
        return add_birthday(command.replace("add", "", 1), sender)

    if command.startswith("list"):
        return list_birthdays(command.replace("list", "", 1))

    return echo(birthday_help_text)


def list_birthdays(command, silent=False):
    command = take_space(command)

    if command.startswith("year"):
        return echo_birthdays(get_birthdays_for_year(), silent)
    elif command.startswith("month"):
        return echo_birthdays(get_birthdays_for_month(), silent)
    elif command.startswith("week"):
        return echo_birthdays(get_birthdays_for_week(), silent)
    elif command.startswith("day"):
        return echo_birthdays(get_birthdays_for_day(), silent)
    else:
        return echo(birthday_help_text)

def open_worksheet():
    gc = pygsheets.authorize(service_account_env_var='GOOGLE_SERVICE_ACCOUNT_CREDS')
    sh = gc.open_by_key(sheet_id)
    return sh[0]


def add_birthday(command, sender):
    command = take_space(command)
    parts = command.split(" ", 1)
    date = datetime.datetime.strptime(parts[0], format_str)
    datestr = date.strftime(format_str)
    name = parts[1]

    worksheet = open_worksheet()

    worksheet.append_table([name, datestr], start='A2', end=None, dimension='ROWS', overwrite=False)
    return echo(sender + " added birthday for " + name + " with date " + datestr)


def get_events():
    cred = service_account.Credentials.from_service_account_info(json.load(os.getenv('GOOGLE_SERVICE_ACCOUNT_CREDS')))
    calendar = build('calendar', 'v3', credentials=cred)
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    echo('Getting the upcoming 10 events')
    events_result = calendar.events().list(calendarId=calendar_id, timeMin=now,
                                           maxResults=10, singleEvents=True,
                                           orderBy='startTime').execute()
    events = events_result.get('items', [])
    results = []
    for e in events:
        startEntry = e['start']
        start = datetime.datetime.fromisoformat(startEntry.get('dateTime', startEntry.get('date')))
        summary = e['summary'] + " - " + format_event_time_string(e)
        results.append({
            start: start,
            summary: summary
        })
    return results


def format_event_time_string(event):
    startEntry = event['start']
    # endEntry = event['end']
    start = datetime.datetime.fromisoformat(startEntry.get('dateTime', startEntry.get('date')))
    # end = datetime.datetime.fromisoformat(endEntry.get('dateTime', endEntry.get('date')))
    result = start.strftime('%a') + " " + start.strftime('%b') + " " + start.strftime('%d').lstrip("0")
    if "dateTime" in startEntry:
        result = result + " @ " + start.strftime("%I").lstrip("0") + ":" + start.strftime("%M%p")
    else:
        result = result + " (All day)"
    return result


def get_birthdays():
    worksheet = open_worksheet()
    values = worksheet.get_values('A2', 'B1000', include_tailing_empty=False, include_tailing_empty_rows=False)
    result = {}
    for row in values:
        date = datetime.datetime.strptime(row[1], format_str)
        if date not in result:
            result[date] = [row[0]]
        else:
            result[date].append(row[0])
    return sorted(result.items(), key=lambda d: d[0])


def get_birthdays_for_year():
    birthdays = get_birthdays()
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    return {k: v for k, v in birthdays if k.replace(year=today.year) >= today}


def get_birthdays_for_month():
    birthdays = get_birthdays()
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    return {k: v for k, v in birthdays if
            k.replace(year=today.year) >= today and k.replace(year=today.year).month == today.month}


def get_birthdays_for_week():
    birthdays = get_birthdays()
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    return {k: v for k, v in birthdays if
            k.replace(year=today.year) >= today and k.replace(year=today.year).month == today.month and k.replace(
                year=today.year).strftime("%U") == today.strftime("%U")}


def get_birthdays_for_day():
    birthdays = get_birthdays()
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    return {k: v for k, v in birthdays if k.replace(year=today.year) == today}


def echo_birthdays(birthdays, silent=False):
    message = "Birthdays:"
    today = datetime.datetime.fromordinal(datetime.date.today().toordinal())
    count = 0
    for k, v in sorted(birthdays.items(), key=lambda d: d[0].replace(year=today.year)):
        for name in v:
            date = k.replace(year=today.year)
            age = today.year - k.year - ((today.month, today.day) < (k.month, k.day))
            message = message + "\n\t" + name + " - " + date.strftime('%a') + " " + date.strftime(
                '%b') + " " + date.strftime('%d').lstrip("0") + " (" + str(age) + " years)"
            count = count + 1
    if count > 0:
        echo(message)
    if count == 0 and not silent:
        echo("There are no upcoming birthdays =(")


def echo_events(events, silent=False):
    message = "Events:"
    count = 0
    for e in events:
        message = message + "\n\t" + e['summary']
        count = count + 1
    if count > 0:
        echo(message)
    if count == 0 and not silent:
        echo("There are no upcoming events =(")





def main():
    return daily_handler(None, None)


if __name__ == "__main__":
    main()
