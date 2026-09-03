from datetime import datetime, time, timedelta

from .models import WorkingHours


SLOT_MINUTES = 30

MANUAL_PADDING_HOURS = 2
MANUAL_EARLIEST_TIME = time(8, 0)
MANUAL_CLOSED_DAY_END = time(19, 0)


def get_manual_window(date):
    working_hours = WorkingHours.objects.filter(
        weekday=date.weekday()
    ).first()

    if not working_hours or working_hours.is_closed:
        return MANUAL_EARLIEST_TIME, MANUAL_CLOSED_DAY_END

    start = datetime.combine(
        date,
        working_hours.opening_time,
    ) - timedelta(hours=MANUAL_PADDING_HOURS)

    earliest = datetime.combine(
        date,
        MANUAL_EARLIEST_TIME,
    )

    if start < earliest:
        start = earliest

    end = datetime.combine(
        date,
        working_hours.closing_time,
    ) + timedelta(hours=MANUAL_PADDING_HOURS)

    return start.time(), end.time()


def get_manual_time_choices(date):
    start_time, end_time = get_manual_window(date)

    current = datetime.combine(date, start_time)
    end = datetime.combine(date, end_time)

    choices = []

    while current <= end:
        value = current.strftime("%H:%M")
        choices.append((value, value))
        current += timedelta(minutes=SLOT_MINUTES)

    return choices


def get_schedule_time_choices(date):
    working_hours = WorkingHours.objects.filter(
        weekday=date.weekday()
    ).first()

    if not working_hours or working_hours.is_closed:
        return []

    current = datetime.combine(
        date,
        working_hours.opening_time,
    )

    end = datetime.combine(
        date,
        working_hours.closing_time,
    )

    choices = []

    while current <= end:
        value = current.strftime("%H:%M")
        choices.append((value, value))
        current += timedelta(minutes=SLOT_MINUTES)

    return choices