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

"""Module containing the Huntflow webhook handler. """


import json
import logging
import re
from datetime import datetime

from tornado.escape import json_decode
from tornado.web import RequestHandler, MissingArgumentError

from huntflow_reloaded import models
from .tokens import RefreshToken, AccessToken, ExpiredTokenException, InvalidTokenException

class IncompleteRequest(Exception):
    """Exception raised when receiving a request of a specific type but not
    containing the necessary fields for this type.
    """


class UndefinedType(Exception):
    """Exception raised when receiving a request which doesn't contain the type
    field in its body.
    """


class UnknownType(Exception):
    """Exception raised when receiving a request which has the type field in
    its body, but the value is unknown.
    """


class HuntflowWebhookHandler(RequestHandler):  # pylint: disable=abstract-method,too-many-instance-attributes
    """Class implementing a Huntflow Webhook handler. """

    ADD_TYPE = 1
    REMOVED_TYPE = 2
    STATUS_TYPE = 3
    TYPES = {
        'ADD': ADD_TYPE,
        'REMOVED': REMOVED_TYPE,
        'STATUS': STATUS_TYPE,
    }
    GINO_CONNECTED = False

    def __init__(self, application, request, **kwargs):
        super(HuntflowWebhookHandler, self).__init__(application, request,
                                                     **kwargs)
        self._decoded_body = {}
        self._handlers = {}
        self._logger = logging.getLogger('tornado.application')
        self._req_type = None
        self.basic_attrs = {}
        self.event = {}
        self.event_type = ''
        self.context = {}
        self.message = {}

        for i in dir(self):
            if i.endswith('_TYPE'):
                key = getattr(self, i)
                val = self._get_attr_or_stub('{}_handler'.format(i.lower()))
                self._handlers[key] = val

    def initialize(self, postgres_url, scheduler):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url
        self._scheduler = scheduler

    def _classify_request(self):
        try:
            req_type = self._decoded_body['event']['type']
        except KeyError:
            raise UndefinedType

        try:
            self._req_type = HuntflowWebhookHandler.TYPES[req_type]
        except KeyError:
            raise UnknownType

    async def _connect_to_database(self):
        """ Connecting to ORM if not connected already """
        if not HuntflowWebhookHandler.GINO_CONNECTED:
            try:
                await models.gino_run(self._postgres_url)
            except:
                raise ConnectionError('Could not connect to Postgresql')
            else:
                HuntflowWebhookHandler.GINO_CONNECTED = True

    def _get_attr_or_stub(self, attribute_name):
        try:
            return getattr(self, attribute_name)
        except AttributeError:
            return self.stub_handler

    def _process_request(self):
        pass

    def _form_valid_basic_attrs(self):
        applicant = self.event['applicant']

        try:
            self.basic_attrs['_id'] = applicant['id']
            self.basic_attrs['first_name'] = applicant['first_name']
            self.basic_attrs['last_name'] = applicant['last_name']
        except KeyError:
            raise IncompleteRequest

    async def post(self):  # pylint: disable=arguments-differ
        body = self.request.body.decode('utf8')

        await self._connect_to_database()

        try:
            self._decoded_body = json_decode(body)
        except json.decoder.JSONDecodeError:
            self.write('Could not decode request body. '
                       'There must be valid JSON')
            self.set_status(500)
            return

        try:
            self._classify_request()
        except UndefinedType:
            self._logger.debug(body)
            self.write('Undefined type')
            self.set_status(500)
            return
        except UnknownType:
            self._logger.debug(body)
            self.write('Unknown type')
            self.set_status(500)
            return

        self._logger.debug(self._decoded_body)

        try:
            await self._handlers[self._req_type]()
        except IncompleteRequest:
            self._logger.debug(body)
            self.write('Incomplete request')
            self.set_status(500)
            return

        self._logger.debug(body)

    #
    # Handlers
    #

    async def add_type_handler(self):
        """Invokes when a request of the 'ADD' type is received. """
        self._logger.info("Handling 'add' request")

    async def removed_type_handler(self):
        """Invokes when a request of the 'REMOVED' type is received. """
        self._logger.info("Handling 'removed' request")

    async def status_type_handler(self):
        """Invokes when a request of the 'STATUS' type is received:
        * setting interview;
        * resetting interview;
        * setting the first working day.
        """

        self._logger.info("Handling 'status' request")

        self.event = self._decoded_body['event']

        self._form_valid_basic_attrs()

        if self.event.get('calendar_event'):
            await self.handle_calendar_event()
        elif self.event.get('employment_date'):
            await self.handle_employment_date()
        else:
            raise IncompleteRequest

        self._scheduler.publish_now(self.message)
        await self._scheduler.create_event(self.event_type,
                                           context=self.context)

    async def handle_calendar_event(self):  # pylint: disable=too-many-locals
        """Handles the setting and rescheduling of the interview. """

        calendar_event = self.event['calendar_event']

        try:
            start = calendar_event['start']
            _end = calendar_event['end']
        except KeyError:
            raise IncompleteRequest

        message_type = 'interview'
        _id = self.basic_attrs['_id']

        candidate = await models.Candidate.query.where(models.Candidate.id == _id).gino.all()

        if not candidate:
            await models.Candidate.create(
                id=self.basic_attrs['_id'],
                first_name=self.basic_attrs['first_name'],
                last_name=self.basic_attrs['last_name']
            )

        interview = await models.Interview.query \
            .where(models.Interview.candidate == _id) \
            .where(models.Interview.type == self.event.get('type')) \
            .gino.first()

        if interview:
            message_type = 'rescheduled-interview'

            if interview.jobs:
                jobs_to_be_deleted = json_decode(interview.jobs)

                for job_id in jobs_to_be_deleted:
                    self._scheduler.remove_job(job_id)

            await models.Interview.delete.where(models.Interview.candidate == _id).gino.status()

        interview_start = get_date_from_string(start)
        interview_end = get_date_from_string(_end)

        today = datetime.now()

        options = {
            "created": today,
            "type": self.event.get('type'),
            "candidate": _id,
            "start": interview_start,
            "end": interview_end
        }

        interview = await models.Interview.create(**options)

        self.event_type = 'schedule_interview'

        self.message = {
            "type": message_type,
            "first_name": self.basic_attrs['first_name'],
            "last_name": self.basic_attrs['last_name'],
            "start": start,
        }

        message_to_be_scheduled = self.message.copy()
        message_to_be_scheduled["type"] = "interview"

        self.context = {"message": message_to_be_scheduled,
                        "interview": interview}

    async def handle_employment_date(self):
        """Handles the setting of the first working day. """

        try:
            employment_date = self.event['employment_date']
        except KeyError:
            raise IncompleteRequest

        _id = self.basic_attrs['_id']

        candidate = await models.Candidate.query.where(
            models.Candidate.id == _id).gino.first()

        date_from_string = datetime.strptime(employment_date, "%Y-%m-%d").date()

        await candidate.update(first_working_day=date_from_string).apply()

        self.event_type = 'remove_candidate'

        self.message = {
            'type': 'fwd',
            'first_name': self.basic_attrs['first_name'],
            'last_name': self.basic_attrs['last_name'],
            'employment_date': employment_date,
        }

        self.context = {'employment_date': employment_date,
                        'candidate_id': _id}

    async def stub_handler(self):
        """Invokes when a type is registered but there is no handler defined
        which is responsible for dealing with the requests of the type.
        """
        self._logger.info('Invoking the stub handler to serve the request of '
                          'the type %s', self._req_type)


def get_date_from_string(date_string):
    """Transforms the specified date string into a proper datetime object. """

    format_string = '%Y-%m-%dT%H:%M:%S%z'
    regexp = r"(\+\d{1,2})(:)(\d{1,2})"

    data = datetime \
        .strptime(re.sub(regexp, r"\1\3", date_string), format_string) \
        .replace(tzinfo=None)

    return data


class TokenObtainPairHandler(RequestHandler):  # pylint: disable=abstract-method,
    """Class implementing obtaining tokens pair. """

    def __init__(self, application, request, **kwargs):
        super(TokenObtainPairHandler, self).__init__(application, request,
                                                     **kwargs)
        self.user = None
        self.valid = False

    def initialize(self, postgres_url):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url

    async def post(self):  # pylint: disable=arguments-differ
        body = self.request.body.decode('utf8')

        try:
            _decoded_body = json_decode(body)
        except json.decoder.JSONDecodeError:
            self.write('Could not decode request body. '
                       'There must be valid JSON')
            self.set_status(500)
            return

        try:
            user = _decoded_body['user']
            email = user['email']
            password = user['password']
        except KeyError:
            self.write('Incomplete request')
            self.set_status(500)
            return

        await self.validate(email, password)

        if self.valid:
            refresh = RefreshToken.for_user(self.user.id)

            data = {
                'access': str(refresh.access_token()), 'refresh': str(refresh)}
        else:
            data = {
                'detail': 'No active account found with the given credentials',
                'code': 'invalid_auth_creds'
            }
            self.set_status(400)

        self.write(data)

    async def validate(self, email, password):
        """Checks if user with the given credentials exists. """

        await models.gino_run(self._postgres_url)

        user = await models.User.query.where(
            models.User.email == email).gino.first()

        if user and user.password == password:
            self.user = user
            self.valid = True


class TokenRefreshHandler(RequestHandler):  # pylint: disable=abstract-method
    """Class implementing handler for refreshing tokens pair request."""

    async def post(self):  # pylint: disable=arguments-differ
        try:
            refresh = RefreshToken(self.get_argument('refresh'))
            data = {'access': str(refresh.access_token())}
        except ExpiredTokenException:
            self.set_status(403)
            data = {'detail': 'Refresh token is expired'}
        except InvalidTokenException:
            self.set_status(401)
            data = {'detail': 'Refresh token is invalid'}
        except MissingArgumentError:
            self.set_status(401)
            self.write({'detail': 'Refresh token is not provided'})

        self.write(data)


class ManageHandler(RequestHandler):  # pylint: disable=abstract-method,
    """Class implementing common methods for handling /manage endpoint. """

    async def _connect_to_database(self):
        """Connecting to ORM. """

        await models.gino_run(self._postgres_url)  # pylint: disable=no-member

    def get_current_user(self):
        try:
            access_token = self.get_argument('access')

        except MissingArgumentError:
            self.write({'detail': 'Token is not provided'})
            self.set_status(401)
            return None

        try:
            user_id = AccessToken(access_token).payload['user_id']
            return user_id
        except (InvalidTokenException, KeyError):
            self.write({'detail': 'Token is invalid'})
            self.set_status(401)
            return None

        except ExpiredTokenException:
            self.write({'detail': 'Token is expired'})
            self.set_status(403)
            return None


class DeleteInterviewHandler(ManageHandler):  # pylint: disable=abstract-method
    """
    Class implementing handler for request from authorized user to delete
    interview for specified candidate.
    """

    def __init__(self, application, request, **kwargs):
        super(DeleteInterviewHandler, self).__init__(application, request,
                                                     **kwargs)
        self.token = None
        self._decoded_body = {}

    def initialize(self, postgres_url, scheduler):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url
        self._scheduler = scheduler

    async def post(self):  # pylint: disable=arguments-differ
        if not self.current_user:
            return
        body = self.request.body.decode('utf8')

        try:
            _decoded_body = json_decode(body)
        except json.decoder.JSONDecodeError:
            self.write('Could not decode request body. '
                       'There must be valid JSON')
            self.set_status(500)
            return
        try:
            candidate = _decoded_body['candidate']
            first_name = candidate['first_name']
            last_name = candidate['last_name']
        except KeyError:
            self.write('Incomplete request')
            self.set_status(500)
            return

        await self._connect_to_database()

        candidate = await models.Candidate.query.where(
            models.Candidate.first_name == first_name).where(
                models.Candidate.last_name == last_name).gino.first()

        if candidate:
            interview = await models.Interview.query.where(
                models.Interview.candidate == candidate.id).gino.first()
        else:
            data = {
                'detail': 'Candidate with the given credentials was not found',
                'code': 'no_candidate'}
            self.set_status(400)
            self.write(data)
            return

        if interview and interview.start > datetime.now():
            if interview.jobs:
                jobs_to_be_deleted = json_decode(interview.jobs)

                for job_id in jobs_to_be_deleted:
                    self._scheduler.remove_job(job_id)

            await models.Interview.delete.where(
                models.Interview.candidate == candidate.id).gino.status()
        else:
            message = {
                'detail': 'Candidate does not have non-expired interviews',
                'code': 'no_interview'
            }
            self.set_status(400)
            self.write(message)
            return


class ListCandidatesHandler(ManageHandler):  # pylint: disable=abstract-method
    """
    Class implementing handler for request from authorized user to list the candidates
    which have non-expired interview.
    """

    def initialize(self, postgres_url):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url


    async def get(self):  # pylint: disable=arguments-differ
        if not self.current_user:
            return

        await self._connect_to_database()

        all_candidates = await models.Candidate.query.gino.all()

        all_candidates_names = []

        for candidate in all_candidates:
            interview = await models.Interview.query.where(
                models.Interview.candidate == candidate.id).gino.first()
            if interview and interview.start > datetime.now():
                all_candidates_names.append(
                    {'first_name': candidate.first_name,
                     'last_name': candidate.last_name})

        message = {
            'users': all_candidates_names,
            'total': len(all_candidates_names),
            'success': True
        }

        self.write(message)


class ListCandidatesWithFwdHandler(ManageHandler):  # pylint: disable=abstract-method
    """
    Class implementing handler for request from authorized user to list the candidates
    which have first working day attribute.
    """

    def initialize(self, postgres_url):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url

    async def get(self):  # pylint: disable=arguments-differ
        if not self.current_user:
            return

        await self._connect_to_database()

        all_candidates = await models.Candidate.query.gino.all()

        candidates_with_fwd = []

        for candidate in all_candidates:
            if candidate.first_working_day:
                candidates_with_fwd.append(
                    {'first_name': candidate.first_name,
                     'last_name': candidate.last_name}
                )

        message = {
            'users': candidates_with_fwd,
            'total': len(candidates_with_fwd),
            'success': True
        }

        self.write(message)


class ShowFwdHandler(ManageHandler):  # pylint: disable=abstract-method
    """
    Class implementing handler for request from authorized user to get the
    first working day for the specified candidate.
    """

    def initialize(self, postgres_url):  # pylint: disable=arguments-differ
        self._postgres_url = postgres_url

    async def get(self):  # pylint: disable=arguments-differ
        if not self.current_user:
            return

        try:
            first_name = self.get_argument('first_name')
            last_name = self.get_argument('last_name')
        except MissingArgumentError as err:
            data = {
                'detail': 'Missing parameter "{}"'.format(err.arg_name),
                'code': 'missing_parameter'
            }
            self.set_status(400)
            self.write(data)
            return

        await self._connect_to_database()

        candidate = await models.Candidate.query.where(
            models.Candidate.first_name == first_name).where(
                models.Candidate.last_name == last_name).gino.first()

        if candidate:
            if candidate.first_working_day:
                message = {
                    'candidate': {'first_name': candidate.first_name,
                                  'last_name': candidate.last_name,
                                  'fwd': candidate.first_working_day.isoformat()}
                }
                self.write(message)
            else:
                data = {
                    'detail': 'First working day of specified candidate was not found',
                    'code': 'no_fwd'}
                self.set_status(400)
                self.write(data)
        else:
            data = {
                'detail': 'Candidate with the given credentials was not found',
                'code': 'no_candidate'}
            self.set_status(400)
            self.write(data)
