""" Scheduler module """

import re
import json
from datetime import timedelta, datetime

from apscheduler.schedulers.tornado import TornadoScheduler

_SCHEDULER = TornadoScheduler()

def add(date, func, args=(), kwargs={}):  # pylint: disable=dangerous-default-value
    """ Shortcut for adding new events. """
    _SCHEDULER.add_job(
        func,
        'date',
        run_date=date,
        args=args,
        kwargs=kwargs
    )

def create_event(ctx, message):
    """
    Schedules the events:
    * remind an hour in advance;
    * remind in the morning of the event day;
    * remind in the evening of the event day.
    """
    time_string = re.sub(r"(\+\d{1,2})(:)(\d{1,2})", r"\1\3", message['start'])
    date = datetime \
        .strptime(time_string, '%Y-%m-%dT%H:%M:%S%z') \
        .replace(tzinfo=None)

    args = (message,)
    kwargs = {
        'ctx': ctx
    }

    an_hour_before = date - timedelta(hours=1)
    add(an_hour_before, notify_interview, args=args, kwargs=kwargs)

    morning_same_day = date.replace(hour=7, minute=0, second=0)
    add(morning_same_day, notify_interview, args=args, kwargs=kwargs)

    evening_of_yesterday = date.replace(
        day=date.day - 1,
        hour=18,
        minute=0,
        second=0
    )
    add(evening_of_yesterday, notify_interview, args=args, kwargs=kwargs)

def make():
    """ Runs the scheduler workers. """
    _SCHEDULER.start()

def notify_interview(message, ctx=None):
    """ Invoked when the event comes. """
    ctx._redis_conn.publish(ctx._channel_name, json.dumps(message))  # pylint: disable=W0212
