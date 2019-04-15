""" Scheduler module """

import json
from datetime import timedelta

from fakeredis import FakeStrictRedis
from redis import StrictRedis
from apscheduler.schedulers.tornado import TornadoScheduler

from huntflow_reloaded import handler

class Scheduler:
    """Class encapsulating scheduling logic. """

    def __init__(self, redis_args, channel_name, postgres_url):
        self.redis_args = redis_args
        self.channel_name = channel_name
        self.scheduler = TornadoScheduler(
            {'apscheduler.jobstores.default': {'type': 'sqlalchemy',
                                               'url': postgres_url}
            })

    def add(self, date, func, args):
        """Shortcut for adding new events. """

        self.scheduler.add_job(
            func=func,
            trigger='date',
            next_run_time=date,
            args=args
        )

    def create_event(self, message):
        """Schedules the events:
        * remind an hour in advance;
        * remind in the morning of the event day;
        * remind in the evening before the event day.
        """

        date = handler.get_date_from_string(message['start'])

        args = (message, self.redis_args, self.channel_name)

        an_hour_in_advance = date - timedelta(hours=1)
        self.add(date=an_hour_in_advance, func=self.notify_interview, args=args)

        morning_of_event_day = date.replace(hour=7, minute=0, second=0)
        self.add(date=morning_of_event_day, func=self.notify_interview, args=args)

        evening_before_event_day = date.replace(
            day=date.day - 1,
            hour=18,
            minute=0,
            second=0
        )
        self.add(date=evening_before_event_day, func=self.notify_interview, args=args)

    def make(self):
        """Runs the scheduler workers. """

        self.scheduler.start()

    @staticmethod
    def notify_interview(message, redis_conn_args, channel_name):
        """Invoked when the event comes.

        Note that the method should be static since pickle can't serialize self param.
        """

        conn = FakeStrictRedis() if not redis_conn_args else StrictRedis(**redis_conn_args)
        conn.publish(channel_name, json.dumps(message))

    def publish_now(self, message):
        """Publishes message in Redis channel immediately. """

        self.notify_interview(message, self.redis_args, self.channel_name)
