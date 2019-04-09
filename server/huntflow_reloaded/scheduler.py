""" Scheduler module """

import re
import json
from datetime import timedelta, datetime

from apscheduler.schedulers.tornado import TornadoScheduler

class Scheduler:
    """Class encapsulating scheduling logic. """

    def __init__(self, redis_conn, channel_name):
        self.redis_conn = redis_conn
        self.scheduler = TornadoScheduler()
        self.channel_name = channel_name

    def add(self, date, func, msg):
        """Shortcut for adding new events. """

        self.scheduler.add_job(
            func=func,
            trigger='date',
            next_run_time=date,
            args=msg
        )

    def create_event(self, message):
        """Schedules the events:
        * remind an hour in advance;
        * remind in the morning of the event day;
        * remind in the evening before the event day.
        """

        time_string = re.sub(r"(\+\d{1,2})(:)(\d{1,2})", r"\1\3", message['start'])
        date = datetime \
            .strptime(time_string, '%Y-%m-%dT%H:%M:%S%z') \
            .replace()

        msg = (message,)

        an_hour_in_advance = date - timedelta(hours=1)
        self.add(date=an_hour_in_advance, func=self.notify_interview, msg=msg)

        morning_of_event_day = date.replace(hour=7, minute=0, second=0)
        self.add(date=morning_of_event_day, func=self.notify_interview, msg=msg)

        evening_before_event_day = date.replace(
            day=date.day - 1,
            hour=18,
            minute=0,
            second=0
        )
        self.add(date=evening_before_event_day, func=self.notify_interview, msg=msg)

    def make(self):
        """Runs the scheduler workers. """

        self.scheduler.start()

    def notify_interview(self, message):
        """Invoked when the event comes. """

        self.redis_conn.publish(self.channel_name, json.dumps(message))
