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

import fakeredis
import testing.postgresql
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from huntflow_reloaded import handler
from test import stubs


ACCOUNT = """
    "account": {
        "id": 1,
        "name": "Noname"
    }
"""

CREATED_DATE = "1989-12-17T00:00:00+00:00"


def compose(req):
    return (req.replace('%ACCOUNT%', ACCOUNT)
               .replace('%CREATED_DATE%', CREATED_DATE))


class WebTestCase(AsyncHTTPTestCase):
    """Base class for web tests that also supports WSGI mode.

    Override get_handlers and get_app_kwargs instead of get_app.
    Append to wsgi_safe to have it run in wsgi_test as well.
    The code was borrowed from the original Tornado tests.
    """
    def get_app(self):
        self.app = Application(self.get_handlers(), **self.get_app_kwargs())
        return self.app

    def setUp(self):
        super(WebTestCase, self).setUp()
        self._mock_postgres = testing.postgresql.Postgresql(port=5432)

    def get_handlers(self):
        raise NotImplementedError()

    def get_app_kwargs(self):
        return {}

    def tearDown(self):
        super(WebTestCase, self).tearDown()
        self._mock_postgres.stop()

class HuntflowWebhookHandlerTest(WebTestCase):
    def get_handlers(self):
        conn = fakeredis.FakeStrictRedis()
        args = {
            'postgres': {
                'dbname': 'test',
                'hostname': 'localhost',
                'password': '',
                'port': '5432',
                'username': 'postgres',
            },
            'redis_conn': conn,
            'channel_name': 'stub',
        }
        return [
            ('/hf', handler.HuntflowWebhookHandler, args),
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
        response = self.fetch('/hf',
                              body=compose(stubs.INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'')

    def test_missing_calendar_event_item(self):
        response = self.fetch('/hf',
                              body=compose(stubs.MISSING_CALENDAR_INTERVIEW_REQUEST),
                              method='POST')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.body, b'Could not decode request body. There must be valid JSON')
