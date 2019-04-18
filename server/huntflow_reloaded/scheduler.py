""" Scheduler module """

import json
from datetime import timedelta, datetime

from fakeredis import FakeStrictRedis
from redis import StrictRedis
from apscheduler.schedulers.tornado import TornadoScheduler

from huntflow_reloaded import handler
from .models import Candidate, Interview

class Scheduler:
    """Class encapsulating scheduling logic. """

    def __init__(self, redis_args, channel_name, postgres_url):
        self.redis_args = redis_args
        self.channel_name = channel_name
        self.scheduler = TornadoScheduler(
            {'apscheduler.jobstores.default': {'type': 'sqlalchemy',
                                               'url': postgres_url}
            })
    #
    # The main entry-point
    #

    async def create_event(self, event_type, context):
        """Runs the schedule method by name. """
        func = getattr(self, event_type)
        await func(context)

    #
    # Shortcuts for scheduler methods
    #

    def add(self, date, func, args):
        """Shortcut for adding new events. """

        job = self.scheduler.add_job(
            func=func,
            trigger='date',
            next_run_time=date,
            args=args
        )
        return job

    def make(self):
        """Shortcut for running the scheduler workers. """

        self.scheduler.start()

    def remove_job(self, job_id):
        """Shortcut for removing scheduler job by id. """

        job = self.scheduler.get_job(job_id)
        if job:
            job.remove()

    def publish_now(self, message):
        """Shortcut for publishing message in Redis channel immediately. """

        self._notify_interview(message, self.redis_args, self.channel_name)

    #
    # Setting scheduler tasks
    #

    async def schedule_interview(self, context):
        """Schedules the events:
        * remind an hour in advance;
        * remind in the morning of the event day;
        * remind in the evening before the event day.
        """

        message = context['message']
        interview = context['interview']
        interview_date = handler.get_date_from_string(message['start'])

        args = (message, self.redis_args, self.channel_name)

        scheduled_dates = self.get_scheduled_dates(interview_date)

        jobs = []

        for scheduled_date in scheduled_dates:
            job = self.add(date=scheduled_date, func=self._notify_interview, args=args)
            jobs.append(job.id)

        await interview.update(jobs=json.dumps(jobs)).apply()

    async def remove_candidate(self, context):
        """Removes the candidate in a day after first working day at midnight. """

        day_after_fwd = self.get_day_after_fwd(context['employment_date'])

        self.add(
            date=day_after_fwd,
            func=self._remove_candidate,
            args=(context['candidate_id'], )
        )

    #
    # Functions to be invoked when the date comes
    # Note that the method should be static since pickle can't serialize self param.
    #

    @staticmethod
    def _notify_interview(message, redis_conn_args, channel_name):
        conn = FakeStrictRedis() if not redis_conn_args else StrictRedis(**redis_conn_args)
        conn.publish(channel_name, json.dumps(message))

    @staticmethod
    async def _remove_candidate(candidate_id):
        await Interview.delete.where(
            Interview.candidate == candidate_id).gino.status()

        candidate = await Candidate.get(candidate_id)
        await candidate.delete()

    #
    # Calculates dates to be used as triggers for scheduler jobs
    #

    @staticmethod
    def get_scheduled_dates(interview_date):
        """Calculates the dates for notification about incoming interview. """

        an_hour_in_advance = interview_date - timedelta(hours=1)
        morning_of_event_day = interview_date.replace(hour=7, minute=0, second=0)
        evening_before_event_day = interview_date.replace(
            hour=18,
            minute=0,
            second=0
        ) - timedelta(days=1)
        return an_hour_in_advance, morning_of_event_day, evening_before_event_day

    @staticmethod
    def get_day_after_fwd(fwd_date_string):
        """Calculates the day after first working day from string. """

        fwd_date = list(map(int, fwd_date_string.split('-')))
        day_after_fwd = datetime(
            year=fwd_date[0],
            month=fwd_date[1],
            day=fwd_date[2]
        ) + timedelta(days=1)
        return day_after_fwd
