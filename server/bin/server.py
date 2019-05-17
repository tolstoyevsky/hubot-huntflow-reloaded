#!/usr/bin/python3
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

"""Server intended for handling the POST requests from Huntflow. """

import logging
import sys

import redis
import tornado.ioloop
from tornado.options import define, options
from dotenv import load_dotenv
from aiologger import Logger as async_logger

from huntflow_reloaded.scheduler import Scheduler
from huntflow_reloaded import handler

load_dotenv()

LOGGER = logging.getLogger('tornado.application')


define('channel-name',
       help='specify the channel name which is used for communicating with '
            'the bot',
       default='hubot-huntflow-reloaded')
define('port', help='listen on a specific port', default=8888)
define('postgres-dbname', help='specify Postgres database name',
       default='huntflow-reloaded')
define('postgres-host', help='specify Postgres hostname and port', default='localhost')
define('postgres-pass', help='specify Postgres password', default='')
define('postgres-port', help='specify Postgres port', default='5432')
define('postgres-user', help='specify Postgres username', default='postgres')
define('redis-host', help='specify Redis host', default='localhost')
define('redis-password', help='specify Redis password', default='')
define('redis-port', help='specify Redis port', default=6379)


def main():
    """The main entry point. """

    options.parse_command_line()

    conn = redis.StrictRedis(host=options.redis_host,
                             password=options.redis_password,
                             port=options.redis_port)

    try:
        conn.ping()
    except redis.exceptions.RedisError:
        sys.stderr.write('Could not connect to Redis\n')
        sys.exit(1)

    postgres_url = 'postgresql://{user}:{password}@{host}:{port}/{dbname}'.format(
        user=options.postgres_user,
        password=options.postgres_pass,
        host=options.postgres_host,
        port=options.postgres_port,
        dbname=options.postgres_dbname
    )

    scheduler_args = {
        'postgres_url': postgres_url,
        'redis_args': {
            'host': options.redis_host,
            'password': options.redis_password,
            'port': options.redis_port,
        }
    }
    args = {
        'logger' : logger,
        'postgres': {
            'dbname': options.postgres_dbname,
            'hostname': options.postgres_host,
            'password': options.postgres_pass,
            'port': options.postgres_port,
            'username': options.postgres_user,
            'channel_name': options.channel_name,
        },
    }

    scheduler = Scheduler(**scheduler_args)
    scheduler.make()

    app_args = {
        'scheduler' : scheduler,
        'postgres_url': postgres_url,
    }

    application = tornado.web.Application([
        (r'/hf/?', handler.HuntflowWebhookHandler, app_args),
        (r'/token', handler.TokenObtainPairHandler, {'postgres_url': postgres_url}),
        (r'/token/refresh', handler.TokenRefreshHandler),
        (r'/manage/list', handler.ListCandidatesHandler, {'postgres_url': postgres_url}),
        (r'/manage/delete', handler.DeleteInterviewHandler, app_args),
        (r'/manage/fwd_list', handler.ListCandidatesWithFwdHandler, {'postgres_url': postgres_url}),
        (r'/manage/fwd', handler.ShowFwdHandler, {'postgres_url': postgres_url})
    ])
    application.listen(options.port)

    LOGGER.info('server is listening on %s', options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logger.close()
        sys.stderr.write('Shutting down the server since the signal was '
                         'generated by Ctrl-C\n')
        sys.exit(130)


if __name__ == '__main__':
    main()
