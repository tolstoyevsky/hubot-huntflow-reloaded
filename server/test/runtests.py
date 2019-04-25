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

from datetime import date, timedelta, datetime
import json
import pickle
import time

import subprocess
import sqlalchemy as sa  # Tests are running synchronously so we have to use sqlalchemy instead of gino.
import testing.postgresql
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from huntflow_reloaded import handler, scheduler, models
from huntflow_reloaded.models import Candidate, Interview, User
from huntflow_reloaded.tokens import Token
from test import stubs


ACCOUNT = """
    "account": {
        "id": 1,
        "name": "Noname"
    }
"""

CREATED_DATE = "1989-12-17T00:00:00+00:00"

POSTGRES_URL = "postgresql://postgres:@localhost:5432/test"

def compose(req, count=2):
    current_date = date.today()
    interview_date = current_date + timedelta(days=count)
    START_DATE = "{year}-{month}-{day}T12:00:00+03:00".format(
        year=interview_date.year,
        month=interview_date.month,
        day=interview_date.day
    )
    EMPLOYMENT_DATE = "{year}-{month}-{day}".format(year=current_date.year,
                                                    month=current_date.month,
                                                    day=current_date.day)
    return (req.replace('%ACCOUNT%', ACCOUNT)
               .replace('%CREATED_DATE%', CREATED_DATE)
               .replace('%START_DATE%', START_DATE)
               .replace('%EMPLOYMENT_DATE%', EMPLOYMENT_DATE))


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

    def get_handlers(self):
        raise NotImplementedError()

    def get_app_kwargs(self):
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
    def get_handlers(self):
        scheduler_args = {
            'postgres_url': POSTGRES_URL,
            'redis_args': '',
            'channel_name': 'stub',
        }
        self.test_scheduler = scheduler.Scheduler(**scheduler_args)
        self.test_scheduler.make()

        app_args = {
            'scheduler': self.test_scheduler,
            'postgres_url': POSTGRES_URL,
        }
        return [
            ('/hf', handler.HuntflowWebhookHandler, app_args),
        ]

    def test_broken_request(self):
        response = self.fetch('/hf', body='hello', method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Could not decode request body. '
                                        b'There must be valid JSON')

    def test_request_with_undefined_type(self):
        response = self.fetch('/hf',
                              body=compose(stubs.REQUEST_WITH_UNDEFINED_TYPE),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Undefined type')

    def test_request_with_unknown_type(self):
        response = self.fetch('/hf',
                              body=compose(stubs.REQUEST_WITH_UNKNOWN_TYPE),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Unknown type')

    def test_handling_incomplete_interview_request(self):
        response = self.fetch('/hf',
                              body=compose(stubs.INCOMPLETE_INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Incomplete request')

    def test_handling_interview_request(self):
        body = compose(stubs.INTERVIEW_REQUEST)

        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        s = sa.sql.select([Candidate]).where(Candidate.id == 1)
        result = self.conn.execute(s)
        row = result.fetchone()
        result.close()

        event = json.loads(body)['event']
        exp_candidate = event['applicant']
        exp_row = (exp_candidate['id'], exp_candidate['first_name'], exp_candidate['last_name'])
        self.assertEqual(row, exp_row)

        calendar_event = event['calendar_event']

        s = sa.sql.select([Interview]).where(Interview.candidate == exp_candidate['id'])
        result = self.conn.execute(s)
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

        s = sa.sql.select([Interview]).where(Interview.candidate == exp_candidate['id'])
        result = self.conn.execute(s).fetchall()
        self.assertEqual(len(result), 1)

        row = result[0]

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

    def test_missing_calendar_event_item(self):
        response = self.fetch('/hf',
                              body=compose(stubs.MISSING_CALENDAR_INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Could not decode request body. There must be valid JSON')

    def test_employment_date(self):
        body = compose(stubs.INTERVIEW_REQUEST)
        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        candidate_id = json.loads(body)['event']['applicant']['id']
        s = sa.sql.select([Interview]).where(
            Interview.candidate == candidate_id)
        interview = self.conn.execute(s).fetchall()
        self.assertEqual(len(interview), 1)

        jobs_id = json.loads(interview[0].jobs)

        # Mocking of expired jobs
        for job_id in jobs_id:
            self.test_scheduler.remove_job(job_id)

        body = compose(stubs.FWD_REQUEST)
        response = self.fetch('/hf', body=body, method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        text = sa.sql.text('SELECT job_state FROM apscheduler_jobs')
        result = self.conn.execute(text).fetchall()
        self.assertEqual(len(result), 1)

        for row in result:
            job_state = pickle.loads(row[0])

        fwd_date = json.loads(body)['event']['employment_date']
        exp_datetime = self.test_scheduler.get_day_after_fwd(fwd_date)

        self.assertEqual(
            job_state.get('next_run_time').replace(tzinfo=None), exp_datetime)


class ManageHandlerTest(WebTestCase):
    def get_handlers(self):
        scheduler_args = {
            'postgres_url': POSTGRES_URL,
            'redis_args': '',
            'channel_name': 'stub',
        }

        self.test_scheduler = scheduler.Scheduler(**scheduler_args)
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
        ]

    def get_tokens(self):
        return self.fetch('/token', body=stubs.AUTH_REQUEST, method='POST')

    def send_status_request(self, body=None):
        if not body:
            body = compose(stubs.INTERVIEW_REQUEST)

        response = self.fetch('/hf', body=body, method='POST')

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

    def get_users_list(self, access_token=None):
        if not access_token:
            access_token = self.access_token

        body = 'access=' + access_token
        url = '/manage/list/?' + body

        return self.fetch(url, method='GET')

    def test_auth_of_non_existing_user(self):
        response = self.get_tokens()
        exp_error_message = {
            "detail": "No active account found with the given credentials",
            "code": "invalid_auth_creds"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_error_message)

    def test_token_handling(self):
        # create user to login
        text = User.insert().values(email='admin@mail.com', password='pass')
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
        exp_res = {"detail": "Token is invalid" }

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
        body = stubs.DELETE_REQUEST
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

        s = sa.sql.select([User]).where(User.id == user_id)
        row = self.conn.execute(s).fetchone()

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
        response = self.fetch('/hf', body=compose(stubs.INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

        # create user to login
        text = User.insert().values(email='admin@mail.com', password='pass')
        self.conn.execute(text)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        self.access_token = json.loads((response.body)).get('access')

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

        body = stubs.DELETE_REQUEST
        url = '/manage/delete/?access=' + self.access_token

        response = self.fetch(url, body=body, method='POST')
        self.assertEqual(response.code, 200)

        text = sa.sql.text(
            'SELECT job_state FROM apscheduler_jobs ORDER BY next_run_time')
        result = self.conn.execute(text).fetchall()

        self.assertFalse(result)

        s = sa.sql.select([Interview]).where(Interview.candidate == 1)
        interview = self.conn.execute(s).fetchall()

        self.assertFalse(interview)

    def test_invalid_deleting_of_interview(self):
        body = compose(stubs.INTERVIEW_REQUEST, count=-2)
        self.send_status_request(body=body)

        text = User.insert().values(email='admin@mail.com', password='pass')
        self.conn.execute(text)

        # get pair of tokens
        response = self.get_tokens()
        self.assertEqual(response.code, 200)
        self.assertIn('access', json.loads(response.body))
        self.assertIn('refresh', json.loads(response.body))

        access_token = json.loads((response.body)).get('access')

        body = stubs.INVALID_DELETE_REQUEST
        url = '/manage/delete/?access=' + access_token
        response = self.fetch(url, body=body, method='POST')

        exp_res = {
            "detail": "Candidate with the given credentials was not found",
            "code": "no_candidate"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)

        url = '/manage/delete/?access=' + access_token
        response = self.fetch(url, body=stubs.DELETE_REQUEST, method='POST')

        exp_res = {
            "detail": "Candidate does not have non-expired interviews",
            "code": "no_interview"
        }

        self.assertEqual(response.code, 400)
        self.assertEqual(json.loads(response.body), exp_res)

    def test_missing_token(self):
        exp_res = {"detail": "Token is not provided"}

        response = self.fetch('/manage/list/', method='GET')
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), exp_res)

        response = self.fetch(
            '/manage/delete/', body=stubs.DELETE_REQUEST, method='POST')
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body), exp_res)
