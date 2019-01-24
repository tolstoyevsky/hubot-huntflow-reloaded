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

from tornado.escape import json_decode
from tornado.web import RequestHandler


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


class HuntflowWebhookHandler(RequestHandler):  # pylint: disable=abstract-method
    """Class implementing a Huntflow Webhook handler. """

    ADD_TYPE = 1
    REMOVED_TYPE = 2
    STATUS_TYPE = 3
    TYPES = {
        'ADD': ADD_TYPE,
        'REMOVED': REMOVED_TYPE,
        'STATUS': STATUS_TYPE,
    }

    def __init__(self, application, request, **kwargs):
        super(HuntflowWebhookHandler, self).__init__(application, request,
                                                     **kwargs)
        self._channel_name = self._channel_name or None
        self._decoded_body = {}
        self._handlers = {}
        self._logger = logging.getLogger('tornado.application')
        self._redis_conn = self._redis_conn or None
        self._req_type = None

        for i in dir(self):
            if i.endswith('_TYPE'):
                key = getattr(self, i)
                val = self._get_attr_or_stub('{}_handler'.format(i.lower()))
                self._handlers[key] = val

    def initialize(self, redis_conn, channel_name):  # pylint: disable=arguments-differ
        self._channel_name = channel_name
        self._redis_conn = redis_conn

    def _classify_request(self):
        try:
            req_type = self._decoded_body['event']['type']
        except KeyError:
            raise UndefinedType

        try:
            self._req_type = HuntflowWebhookHandler.TYPES[req_type]
        except KeyError:
            raise UnknownType

    def _get_attr_or_stub(self, attribute_name):
        try:
            return getattr(self, attribute_name)
        except AttributeError:
            return self.stub_handler

    def _process_request(self):
        pass

    def post(self):  # pylint: disable=arguments-differ
        body = self.request.body.decode('utf8')

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
            self._handlers[self._req_type]()
        except IncompleteRequest:
            self._logger.debug(body)
            self.write('Incomplete request')
            self.set_status(500)
            return

    #
    # Handlers
    #

    def add_type_handler(self):
        """Invokes when a request of the 'ADD' type is received. """
        self._logger.info("Handling 'add' request")

    def removed_type_handler(self):
        """Invokes when a request of the 'REMOVED' type is received. """
        self._logger.info("Handling 'removed' request")

    def status_type_handler(self):
        """Invokes when a request of the 'STATUS' type is received. """

        self._logger.info("Handling 'status' request")

        event = self._decoded_body['event']
        try:
            _id = event['applicant']['id']
            first_name = event['applicant']['first_name']
            last_name = event['applicant']['last_name']
            start = event['calendar_event']['start']
            _end = event['calendar_event']['end']
        except KeyError:
            raise IncompleteRequest

        message = {
            'type': 'interview',
            'first_name': first_name,
            'last_name': last_name,
            'start': start,
        }

        self._redis_conn.publish(self._channel_name, json.dumps(message))

    def stub_handler(self):
        """Invokes when a type is registered but there is no handler defined
        which is responsible for dealing with the requests of the type.
        """
        self._logger.info('Invoking the stub handler to serve the request of '
                          'the type %s', self._req_type)
