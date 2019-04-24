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

        job = self.scheduler.add_job(
            func=func,
            trigger='date',
            next_run_time=date,
            args=args
        )
        return job

    async def create_event(self, message, interview):
        """Schedules the events:
        * remind an hour in advance;
        * remind in the morning of the event day;
        * remind in the evening before the event day.
        """

        interview_date = handler.get_date_from_string(message['start'])

        args = (message, self.redis_args, self.channel_name)

        scheduled_dates = self.get_scheduled_dates(interview_date)

        jobs = []

        for scheduled_date in scheduled_dates:
            job = self.add(date=scheduled_date, func=self.notify_interview, args=args)
            jobs.append(job.id)

        await interview.update(jobs=json.dumps(jobs)).apply()

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

    @staticmethod
    def get_scheduled_dates(interview_date):
        """Calculates the dates to be used as triggers for scheduler jobs. """

        an_hour_in_advance = interview_date - timedelta(hours=1)
        morning_of_event_day = interview_date.replace(hour=7, minute=0, second=0)
        evening_before_event_day = interview_date.replace(
            hour=18,
            minute=0,
            second=0
        ) - timedelta(days=1)
        return an_hour_in_advance, morning_of_event_day, evening_before_event_day

    def remove_job(self, job_id):
        """Shortcut for removing scheduler job by id. """

        job = self.scheduler.get_job(job_id)
        if job:
            job.remove()
