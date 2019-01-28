#!/bin/bash
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

set -x

LOGLEVEL=${LOGLEVEL:="info"}

LOG_FILE=${LOG_FILE:="/var/log/huntflow-reloaded-server.log"}

REDIS_HOST=${REDIS_HOST:="127.0.0.1"}

REDIS_PASSWORD=${REDIS_PASSWORD:=""}

REDIS_PORT=${REDIS_PORT:="16379"}

set +x

>&2 echo "Waiting for Redis"

./bin/wait-for-it.sh -h "${REDIS_HOST}" -p "${REDIS_PORT}" -t 90 -- >&2 echo "Redis is ready"

args=()

args+=( --logging="${LOGLEVEL}" )

args+=( --redis-host="${REDIS_HOST}" )

args+=( --redis-password="${REDIS_PASSWORD}" )

args+=( --redis-port="${REDIS_PORT}" )

args+=( --log-file-prefix="${LOG_FILE}" )

>&2 echo "huntflow-reloaded-server is starting..."

env PYTHONPATH="$(pwd)" python3 bin/server.py "${args[@]}" $*
