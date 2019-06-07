# Copyright 2019 Evgeny Golyshev. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module containing the huntflow-reloaded server tests. """

from datetime import date, timedelta
import json
import pickle
import time

import subprocess
# Tests are running synchronously so we have to use sqlalchemy instead of gino.
import sqlalchemy as sa
import testing.postgresql
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from huntflow_reloaded import handler, scheduler
from huntflow_reloaded.models import Candidate, Interview, User
from huntflow_reloaded.tokens import Token
from . import stubs


ACCOUNT = """
    "account": {
        "id": 1,
        "name": "Noname"
    }
"""

CREATED_DATE = "1989-12-17T00:00:00+00:00"

POSTGRES_URL = "postgresql://postgres:@localhost:5432/test"

def compose(req, count=2):
    """Fills the stubs with relevant data to be sent to the server. """

    current_date = date.today()
    interview_date = current_date + timedelta(days=count)
    start_date = "{year}-{month}-{day}T12:00:00+03:00".format(
        year=interview_date.year,
        month=interview_date.month,
        day=interview_date.day
    )
    employment_date = "{year}-{month}-{day}".format(year=current_date.year,
                                                    month=current_date.month,
                                                    day=current_date.day)
    return (req.replace('%ACCOUNT%', ACCOUNT)
            .replace('%CREATED_DATE%', CREATED_DATE)
            .replace('%START_DATE%', start_date)
            .replace('%EMPLOYMENT_DATE%', employment_date))


class WebTestCase(AsyncHTTPTestCase):
    """Base class for web tests that also supports WSGI mode.

    Override get_handlers and get_app_kwargs instead of get_app.
    Append to wsgi_safe to have it run in wsgi_test as well.
    Override get_new_ioloop to avoid creating a new loop for each test case.
    The code was borrowed from the original Tornado tests.
    """

    def get_app(self):
        self.app = Application(self.get_handlers(), **self.get_app_kwargs())
        return self.app

    def setUp(self):
        super(WebTestCase, self).setUp()
        self._mock_postgres = testing.postgresql.Postgresql(port=5432)

        command = 'server/alembic/migrate.sh ' + POSTGRES_URL
        subprocess.Popen(command, shell=True).wait()

        engine = sa.create_engine(POSTGRES_URL)
        self.conn = engine.connect()

        scheduler_args = {
            'postgres_url': POSTGRES_URL,
            'redis_args': '',
            'channel_name': 'stub',
        }

        self.test_scheduler = scheduler.Scheduler(**scheduler_args)
        self.test_scheduler.make()

    def get_handlers(self):
        """Redefines buildin method. """

        raise NotImplementedError()

    def get_app_kwargs(self):  # pylint: disable=no-self-use
        """Redefines buildin method. """

        return {}

    def get_new_ioloop(self):
        return IOLoop.current()

    def tearDown(self):
        super(WebTestCase, self).tearDown()

        for table in (Interview, Candidate, User):
            self.conn.execute(table.delete)
        text = sa.sql.text('DELETE FROM apscheduler_jobs')
        self.conn.execute(text)

        self.conn.close()
        self._mock_postgres.stop()

class HuntflowWebhookHandlerTest(WebTestCase):
    """Class for testing Huntflow webhooks handling. """

    def get_handlers(self):
        scheduler_args = {
            'postgres_url': POSTGRES_URL,
            'redis_args': '',
            'channel_name': 'stub',
        }
        self.test_scheduler = scheduler.Scheduler(**scheduler_args)  # pylint: disable=attribute-defined-outside-init
        self.test_scheduler.make()

        app_args = {
            'scheduler': self.test_scheduler,
            'postgres_url': POSTGRES_URL,
        }
        return [
            ('/hf', handler.HuntflowWebhookHandler, app_args),
        ]

    def test_broken_request(self):
        """Check if it is not possible to send the request with invalid body. """

        response = self.fetch('/hf', body='hello', method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Could not decode request body. '
                                        b'There must be valid JSON')

    def test_request_with_undefined_type(self):
        """Check if it is not possible to send the request with underfined body type. """

        response = self.fetch('/hf',
                              body=compose(stubs.REQUEST_WITH_UNDEFINED_TYPE),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Undefined type')

    def test_request_with_unknown_type(self):
        """Check if it is not possible to send the request with unknown body type. """

        response = self.fetch('/hf',
                              body=compose(stubs.REQUEST_WITH_UNKNOWN_TYPE),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Unknown type')

    def test_handling_incomplete_interview_request(self):
        """Check the error code and message in case of incomplete webhook. """

        response = self.fetch('/hf',
                              body=compose(stubs.INCOMPLETE_INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Incomplete request')

    def test_handling_interview_request(self):  # pylint: disable=too-many-locals
        """Check if it is possible to handle correctly interview request:
         * saving candidate instance if it doesn't exist
         * saving interview instance
         * saving relevant schedulers to be triggered
            - at 6:00 p.m before event
            - at 7:00 a.m in the day of event
            - in one hour before event
         """

        body = compose(stubs.INTERVIEW_REQUEST)

        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        to_be_executed = sa.sql.select([Candidate]).where(Candidate.id == 1)
        result = self.conn.execute(to_be_executed)
        row = result.fetchone()
        result.close()

        event = json.loads(body)['event']
        exp_candidate = event['applicant']
        exp_row = (
            exp_candidate['id'], exp_candidate['first_name'], exp_candidate['last_name'], None)
        self.assertEqual(row, exp_row)

        calendar_event = event['calendar_event']

        to_be_executed = sa.sql.select([Interview]).where(
            Interview.candidate == exp_candidate['id'])
        result = self.conn.execute(to_be_executed)
        row = result.fetchone()
        result.close()

        interview_start = handler.get_date_from_string(calendar_event['start'])
        interview_end = handler.get_date_from_string(calendar_event['end'])

        self.assertEqual(row[Interview.start], interview_start)
        self.assertEqual(row[Interview.end], interview_end)
        self.assertEqual(row[Interview.type], event['type'])

        text = sa.sql.text('SELECT job_state FROM apscheduler_jobs ORDER BY next_run_time')
        result = self.conn.execute(text).fetchall()

        date_tuple = self.test_scheduler.get_scheduled_dates(interview_start)

        for row, exp_datetime in zip(result, sorted(date_tuple)):
            job_state = pickle.loads(row[0])
            self.assertEqual(job_state.get('next_run_time').replace(tzinfo=None), exp_datetime)

    def test_reschedule_interview(self):
        """Check if server reset interview in case of repeating interview webhook:
        - updating interview of the relevant candidate
        - rescheduling reminders
        """
        response = self.fetch('/hf', body=compose(stubs.INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        rescheduled_interview = compose(stubs.INTERVIEW_REQUEST, count=5)
        response = self.fetch('/hf', body=rescheduled_interview, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        event = json.loads(rescheduled_interview)['event']
        exp_candidate = event['applicant']
        calendar_event = event['calendar_event']

        to_be_executed = sa.sql.select([Interview]).where(
            Interview.candidate == exp_candidate['id'])
        result = self.conn.execute(to_be_executed).fetchall()
        self.assertEqual(len(result), 1)

        row = result[0]

        interview_start = handler.get_date_from_string(calendar_event['start'])
        interview_end = handler.get_date_from_string(calendar_event['end'])

        self.assertEqual(row[Interview.start], interview_start)
        self.assertEqual(row[Interview.end], interview_end)
        self.assertEqual(row[Interview.type], event['type'])

        to_be_executed = sa.sql.text(
            'SELECT job_state FROM apscheduler_jobs ORDER BY next_run_time')
        result = self.conn.execute(to_be_executed).fetchall()

        date_tuple = self.test_scheduler.get_scheduled_dates(interview_start)

        for row, exp_datetime in zip(result, sorted(date_tuple)):
            job_state = pickle.loads(row[0])
            self.assertEqual(job_state.get('next_run_time').replace(tzinfo=None), exp_datetime)

    def test_missing_calendar_event_item(self):
        """Check if it is not possible to send the request with missing calendar_event item. """

        response = self.fetch('/hf',
                              body=compose(stubs.MISSING_CALENDAR_INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Could not decode request body. There must be valid JSON')

    def test_handling_employment_date_request(self):
        """Check if it is possible to handle correctly request with employment_date item:
        - setting scheduler for removing candidate and relevant interview
          in a day after his/her wirst working day
        """

        body = compose(stubs.INTERVIEW_REQUEST)
        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        candidate_id = json.loads(body)['event']['applicant']['id']
        to_be_executed = sa.sql.select([Interview]).where(
            Interview.candidate == candidate_id)
        interview = self.conn.execute(to_be_executed).fetchall()
        self.assertEqual(len(interview), 1)

        jobs_id = json.loads(interview[0].jobs)

        # Mocking of expired jobs
        for job_id in jobs_id:
            self.test_scheduler.remove_job(job_id)

        body = compose(stubs.FWD_REQUEST)
        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        to_be_executed = sa.sql.text('SELECT job_state FROM apscheduler_jobs')
        result = self.conn.execute(to_be_executed).fetchall()
        self.assertEqual(len(result), 1)

        for row in result:
            job_state = pickle.loads(row[0])

        fwd_date = json.loads(body)['event']['employment_date']
        exp_datetime = self.test_scheduler.get_day_after_fwd(fwd_date)

        self.assertEqual(
            job_state.get('next_run_time').replace(tzinfo=None), exp_datetime)


class ManageEndpointHandlerTest(WebTestCase):
    """Class for testing API of the /manage endpoint. """

    def get_handlers(self):
        scheduler_args = {
            'postgres_url': POSTGRES_URL,
            'redis_args': '',
            'channel_name': 'stub',
        }

        self.test_scheduler = scheduler.Scheduler(**scheduler_args)  # pylint: disable=attribute-defined-outside-init
        self.test_scheduler.make()

        app_args = {
            'postgres_url': POSTGRES_URL,
            'scheduler': self.test_scheduler,
        }

        db_args = {'postgres_url': POSTGRES_URL}

        return [
            ('/hf', handler.HuntflowWebhookHandler, app_args),
            (r'/token', handler.TokenObtainPairHandler, db_args),
            (r'/token/refresh', handler.TokenRefreshHandler),
            (r'/manage/list/', handler.ListCandidatesHandler, db_args),
            (r'/manage/delete/', handler.DeleteInterviewHandler, app_args),
            (r'/manage/fwd_list/', handler.ListCandidatesWithFwdHandler, db_args),
            (r'/manage/fwd/', handler.ShowFwdHandler, db_args),
        ]

    def get_tokens(self):
        """Shortcut for requesting token pair. """

        return self.fetch('/token', body=stubs.AUTH_REQUEST, method='POST')

    def send_status_request(self, body=None):
        """Shortcut for requesting token pair. """

        if not body:
            body = compose(stubs.INTERVIEW_REQUEST)

        response = self.fetch('/hf', body=body, method='POST')

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

    def get_users_list(self, access_token=None):
        """Shortcut for requesting users list with non-expired interviews. """

        if not access_token:
            access_token = self.access_token

        body = 'access=' + access_token
        url = '/manage/list/?' + body

        return self.fetch(url, method='GET')

    def test_auth_of_non_existing_user(self):
        """Check if it not possible to get token pair for non-existing user. """

        response = self.get_tokens()
        exp_error_message = {
            "detail": "No active account found with the given credentials",
            "code": "invalid_auth_creds"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_error_message)

    def test_token_handling(self):
        """Test the tokens' handling:
        - possibility to obtain valid token pair for existing user
        - expiring of access and refresh tokens
        - possibility to refresh access token
        - correct handling of invalid token
        """

        # create user to login
        text = User.insert().values(email='admin@mail.com', password='pass')  # pylint: disable=no-member
        self.conn.execute(text)

        # check if it is possible to obtain token pair
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        refresh_token = json.loads((response.body)).get('refresh')
        access_token = json.loads((response.body)).get('access')

        # check the response in case of invalid access token
        response = self.get_users_list(access_token=access_token + 'u')
        exp_res = {"detail": "Token is invalid"}

        self.assertEqual(response.code, 401)
        self.assertEqual(exp_res, json.loads(response.body))

        # wait until access token become expired
        time.sleep(50)

        # check if it is impossible to get data with expired token
        response = self.get_users_list(access_token=access_token)
        exp_res = {"detail": "Token is expired"}

        self.assertEqual(response.code, 403)
        self.assertEqual(exp_res, json.loads(response.body))

        # check if it is impossible to delete interview with expired token
        body = stubs.CANDIDATE_REQUEST
        url = '/manage/delete/?access=' + access_token
        response = self.fetch(url, body=body, method='POST')

        self.assertEqual(response.code, 403)
        self.assertEqual(exp_res, json.loads(response.body))

        # refresh token and check its payload
        body = 'refresh=' + refresh_token
        response = self.fetch('/token/refresh', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))

        access_token = json.loads((response.body)).get('access')
        token = Token(access_token)
        self.assertIn('user_id', token.payload)

        user_id = token.payload['user_id']

        to_be_executed = sa.sql.select([User]).where(User.id == user_id)
        row = self.conn.execute(to_be_executed).fetchone()

        self.assertEqual(row['email'], 'admin@mail.com')
        self.assertEqual(row['password'], 'pass')

        # wait until refresh token become expired
        time.sleep(30)

        # check if it is impossible to use for refreshing the expired refresh token
        exp_res = {"detail": "Refresh token is expired"}

        response = self.fetch('/token/refresh', body=body, method='POST')
        self.assertEqual(response.code, 403)
        self.assertEqual(exp_res, json.loads(response.body))

    def test_manage_entrypoint(self):
        """Test the success workflow on /manage entrypoint:
        - obtaining the token pair
        - retrieving the list of candidates who have non-expired interviews
        - deleting interview of the specified candidate
        - removing relevant scheduled reminders
        """
        response = self.fetch('/hf', body=compose(stubs.INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        # create user to login
        to_be_executed = User.insert().values(email='admin@mail.com', password='pass') # pylint: disable=no-member
        self.conn.execute(to_be_executed)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        self.access_token = json.loads((response.body)).get('access')  # pylint: disable=attribute-defined-outside-init

        exp_list = {
            "users": [
                {
                    "first_name": "Matt",
                    "last_name": "Groening",
                }
            ],
            "total": 1,
            "success": True
        }

        response = self.get_users_list()
        self.assertEqual(response.code, 200)
        self.assertEqual(exp_list, json.loads(response.body))

        body = stubs.CANDIDATE_REQUEST
        url = '/manage/delete/?access=' + self.access_token

        response = self.fetch(url, body=body, method='POST')
        self.assertEqual(response.code, 200)

        to_be_executed = sa.sql.text(
            'SELECT job_state FROM apscheduler_jobs ORDER BY next_run_time')
        result = self.conn.execute(to_be_executed).fetchall()

        self.assertFalse(result)

        to_be_executed = sa.sql.select([Interview]).where(Interview.candidate == 1)
        interview = self.conn.execute(to_be_executed).fetchall()

        self.assertFalse(interview)

    def test_invalid_deleting_of_interview(self):
        """Check error messages and codes in case of:
        - attempt to delete the interview of non-existed candidate
        - attempt to delete the interview of candidate who does not have the non-expired one.
        """

        body = compose(stubs.INTERVIEW_REQUEST, count=-2)
        self.send_status_request(body=body)

        to_be_executed = User.insert().values(email='admin@mail.com', password='pass')  # pylint: disable=no-member
        self.conn.execute(to_be_executed)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        access_token = json.loads((response.body)).get('access')

        body = stubs.INVALID_CANDIDATE_REQUEST
        url = '/manage/delete/?access=' + access_token
        response = self.fetch(url, body=body, method='POST')

        exp_res = {
            "detail": "Candidate with the given credentials was not found",
            "code": "no_candidate"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)

        url = '/manage/delete/?access=' + access_token
        response = self.fetch(url, body=stubs.CANDIDATE_REQUEST, method='POST')

        exp_res = {
            "detail": "Candidate does not have non-expired interviews",
            "code": "no_interview"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)

    def test_missing_token(self):
        """Check if it not possible to get the candidates list and to delete interview
        without providing token.
        """

        exp_res = {"detail": "Token is not provided"}

        response = self.fetch('/manage/list/', method='GET')
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), exp_res)

        response = self.fetch(
            '/manage/delete/', body=stubs.CANDIDATE_REQUEST, method='POST')
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), exp_res)

    def test_fwd_calls(self):
        """Test success workflow of retriving first working day of candidate:
         - getting the list of candidates with defined first working day
         - getting first working day of the specified candidate
         """
        self.send_status_request()

        body = compose(stubs.FWD_REQUEST)
        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        # create user to login
        text = User.insert().values(email='admin@mail.com', password='pass')  # pylint: disable=no-member
        self.conn.execute(text)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        self.access_token = json.loads((response.body)).get('access')  # pylint: disable=attribute-defined-outside-init

        # get list of candidates with fwd
        exp_list = {
            "users": [
                {
                    "first_name": "Matt",
                    "last_name": "Groening"
                }
            ],
            "total": 1,
            "success": True
        }
        body = 'access=' + self.access_token
        url = '/manage/fwd_list/?' + body

        response = self.fetch(url, method='GET')
        self.assertEqual(response.code, 200)
        self.assertEqual(exp_list, json.loads(response.body))

        # get fwd of the specified candidate
        body = json.loads(stubs.CANDIDATE_REQUEST)['candidate']
        url = ('/manage/fwd/?first_name={}&last_name={}&access={}'
               .format(body['first_name'], body['last_name'], self.access_token))

        exp_res = {
            "candidate" : {
                "first_name": "Matt",
                "last_name": "Groening",
                "fwd": date.today().isoformat()
            }
        }

        response = self.fetch(url, method='GET', allow_nonstandard_methods=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body), exp_res)

    def test_invalid_fwd_calls(self):
        """Test error messages and codes in case of:
        - attempt to get fwd of non-existed candidate
        - attempt to get fwd of candidate who does not have the attribute defined
        """
        # create user to login
        text = User.insert().values(email='admin@mail.com', password='pass')  # pylint: disable=no-member
        self.conn.execute(text)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        self.access_token = json.loads((response.body)).get('access')  # pylint: disable=attribute-defined-outside-init

        # try to get fwd for invalid candidate
        body = json.loads(stubs.INVALID_CANDIDATE_REQUEST)['candidate']
        url = ('/manage/fwd/?first_name={}&last_name={}&access={}'
               .format(body['first_name'], body['last_name'], self.access_token))

        response = self.fetch(url, method='GET',
                              allow_nonstandard_methods=True)
        exp_res = {
            'detail': 'Candidate with the given credentials was not found',
            'code': 'no_candidate'}

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)

        # try to get fwd for candidate without relevant attribute
        self.send_status_request()

        body = json.loads(stubs.CANDIDATE_REQUEST)['candidate']
        url = ('/manage/fwd/?first_name={}&last_name={}&access={}'
               .format(body['first_name'], body['last_name'], self.access_token))
        response = self.fetch(url, method='GET',
                              allow_nonstandard_methods=True)
        exp_res = {
            'detail': 'First working day of specified candidate was not found',
            'code': 'no_fwd'}

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)
