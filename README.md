# hubot-huntflow-reloaded

hubot-huntflow-reloaded is a project intended to move the [Huntflow](https://huntflow.ru) reminders to a team chat (based on [Rocket.Chat](https://rocket.chat/)).

The project is split into two parts: server and client. The server side is a [Huntflow](https://huntflow.ru/) webhook handler. When Huntflow sends a POST request to the server, the server, in turn, pulls the events from the requests, schedules and sends them to the client, a Hubot script, via a Redis broker (the client subscribes to the channel and the server publishes the message to the channel). 

## Table of Contents

- [Prerequisites](#prerequisites)
- [Client](#client)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Server](#server)
  - [Installation](#installation-1)
  - [Configuration](#configuration-1)
  - [How to run server for development](#how-to-run-server-for-development)
  - [How to use stubs](#how-to-use-stubs)
  - [Known issues](#known-issues)
- [Authors](#authors)
- [Licensing](#licensing)

## Prerequisites

* The bot must be in the channel specified via the `HUNTFLOW_REMINDER_CHANNEL` environment variable.
* There must be specified the `POSTGRES_PASSWORD` environment variable (see the [configuration section](#configuration-1) for details).
* There must be specified `SERVER_USER_EMAIL` and `SERVER_USER_PASSWORD`(see the [configuration section](#configuration) for details). 

## Client

The client is a Hubot script intended to receive the reminders from the Redis channel and pass them to the specified Rocket.Chat channel. 

### Installation

In hubot project repo, run:

`npm install git+https://github.com/tolstoyevsky/hubot-huntflow-reloaded --save`

Then add **hubot-huntflow-reloaded** to your `external-scripts.json`:

```json
[
  "hubot-huntflow-reloaded"
]
```

### Configuration

| Parameter         | Description                                                                                            | Default                   |
|----------------------------|-----------------------------------------------------------------------------------------------|---------------------------|
|`HUNTFLOW_REMINDER_CHANNEL` | Defines the name of Rocket.Chat channel to send reminders to. It must exist before script run.| `hr`                      |
|`REDIS_HOST`                | Specifies the Redis host.                                                                     | 127.0.0.1                 |
|`REDIS_PORT`                | Port Redis listens on.                                                                        | 16379                     |
|`REDIS_PASSWORD`            | Specifies the Redis password.                                                                 | null                      |
|`REDIS_CHANNEL`             | Defines the name of Redis channel to get messages from the server.                            | `hubot-huntflow-reloaded` |
|`BASE_SERVER_URL`           | Defines the server url to handle requests.                                                    | `http://127.0.0.1:8888/`  |
|`SERVER_USER_EMAIL`         | Defines the server user email to make authorized requests.                                    | null                      |
|`SERVER_USER_PASSWORD`      | Defines the server user password to make authorized requests.                                 | null                      |

## Server

The Tornado-based server is intended to handle
* [Huntflow](https://huntflow.ru/) webhooks and schedule relevant reminders to be send to the client via Redis broker;
* requests for listing candidates with non-expired interviews and removing non-expired interviews of the specified candidates.

### Installation

The simplest way to install and run the server is to use the Docker image.

To run the server in the Docker container, go to the directory which contains the sources of the Docker image

```
$ cd server/docker
```

and run

```
$ docker-compose up
```

The command above will run huntflow-reloaded-server, the Redis and the PostgreSQL servers. To run only huntflow-reloaded-server, run

```
$ docker-compose up huntflow-reloaded-server
```
Note that in this case Redis and PostgreSQL servers should be run manually before huntflow-reloaded-server.

To build the Docker image, run `make` from the same directory. In a while, the `huntflow-reloaded-server:latest` image will be created.

### Configuration

The server can be configured via the following command line options or environment variables if you run it in a Docker container.

| Environment variables   | Command line options   | Description                                                                    | Default                                   |
|-------------------------|------------------------|--------------------------------------------------------------------------------|-------------------------------------------|
|`LOGLEVEL`               | `--logging`            | Logs level.                                                                    | `info`                                    |
|`LOG_FILE`               | `--log-file-prefix`    | File where log information will be stored.                                     | `/var/log/huntflow-reloaded-server.log`   |
|`POSTGRES_DBNAME`        | `--postgres-dbname`    | Database name.                                                                 | `huntflow-reloaded`                       |
|`POSTGRES_HOST`          | `--postgres-host`      | PostgreSQL host.                                                               | 127.0.0.1                                 |
|`POSTGRES_PORT`          | `--postgres-port`      | Port PostgreSQL listens on.                                                    | `5432`                                    |
|`POSTGRES_USER`          | `--postgres-user`      | PostgreSQL user name.                                                          | postgres                                  |
|`POSTGRES_PASSWORD`      | `--postgres-pass`      | Password of the above-mentioned PostgreSQL user.                               |                                           |
|`REDIS_HOST`             | `--redis-host`         | Redis host.                                                                    | 127.0.0.1                                 |
|`REDIS_PORT`             | `--redis-port`         | Port Redis listens on.                                                         | `6379` or `16379` (in a Docker container) |
|`REDIS_PASSWORD`         | `--redis-password`     | Redis password.                                                                |                                           |
|`CHANNEL_NAME`           | `--channel-name`       | Redis channel name to be used for communication between the server and client. | `hubot-huntflow-reloaded`                 |
|`TZ`                     |                        | Timezone for for scheduler **(for Docker container only)**.                    | Europe/Moscow                             |
|`ACCESS_TOKEN_LIFETIME`  |                        | The lifetime in of the access JWT token in minutes (can be float).             | `1`                                       |
|`REFRESH_TOKEN_LIFETIME` |                        | The lifetime in of the refresh JWT token in minutes (can be float).            | `60`                                      |
|`SEKRET_KEY`             |                        | The string which will be used as secret for the tokens' encoding.              | secret                                    |

### How to run server for development purposes

1. Create a virtual environment and install the required packages in it.
    ```bash
    virtualenv -p python3 hubot-huntflow-reloaded-env
    source hubot-huntflow-reloaded-env/bin/activate
    cd hubot-huntflow-reloaded
    pip install -r server/requirements.txt
    ```

2. To start work with the huntflow-reloaded server you need to setup the PostgreSQL database and apply the migrations. 
    The easiest way to do it is to specify the required param `POSTGRES_PASSWORD`, run
    ```bash
    cd server/docker/
    docker-compose up
    ```
    and then stop it by pressing Ctrl-C. It automatically prepares the database to be used later.
    
    Notice, that `docker-compose` runs three containers and if something goes wrong you need to look at `huntflow-reloaded-server` logs first of all to get to the bottom of the problem.
    
3. Deploy the Rocket.Chat server locally and run Hubot. For the details see Rocket.Chat [README](https://github.com/tolstoyevsky/mmb/tree/master/rocketchat), Rocket.Chat Hubot adapter [README](https://github.com/tolstoyevsky/mmb/tree/master/hubot-rocketchat) and [client configuration](#configuration) section.
    The Hubot runs also the Redis server. If you don't need the client run the Redis server manually.
    
    ```bash
    docker-compose up redis
    ```
    Also to debug you can subscribe to the Redis channel to see the reminders as a client would receive. 
    Find the name of the Redis container in the output of the command,
    ```
    docker ps
    ```
    start the Bash session in the running container via
    ```
    docker exec -it container_name bash
    ```
     and subscribe to the Redis channel.
    ```bash
    redis-cli -h 127.0.0.1 -p 16379 
    SUBSCRIBE hubot-huntflow-reloaded
    ```
    Notice, that if you change the default settings you need to use them.

4. Run PostgreSQL server
    ```bash
    docker-compose up postgres-hf
    ```

5. Run huntflow-reloaded-server
    ```bash
    cd ..
    env PYTHONPATH=$(pwd) python3 bin/server.py --redis-port=16379
    ```
    Now server is ready to accept connections.

### How to use stubs

The json files in stubs directory mock the requests which huntflow-reloaded-server is able to handle. 
There are the Huntflow webhooks and client requests. You can send these files via `curl` command to the server to emulate the real requests.
You can emulate the following actions:
- setting the interview

    ```bash
    curl -vX POST http://127.0.0.1:8888/hf -d @stubs/interview.json --header "Content-Type: application/json" 
    ```
  
    Note that if you want to test the scheduler you need to change the `start_date` inside `interview.json` to be the valid date in the future.
    Server will send the reminder to the Redis channel immediately and schedule the sending of reminders at 6 p.m. 
    before the event day, at 7 a.m. in the event day and an hour in advance.

- resetting the interview

    Send the same request as above but change the `start_date`. The reminders will be rescheduled.

- setting the first working day

    ```bash
    curl -vX POST http://127.0.0.1:8888/hf -d @stubs/fwd.json --header "Content-Type: application/json"
    ```
  
    Note that you need to replace the `employment_date` to the valid date in the future. 
    The server will send the reminder to the Redis channel immediately and 
    schedule the removing of the candidate instance in a day after the first working day at midnight (00:00 a.m.).

- user's authorization
    
    ```bash
     curl -vX POST http://127.0.0.1:8888/token -d @stubs/auth.json --header "Content-Type: application/json"
    ```
    It returns the valid token pair if user is registered.
    For the details of registering a new user see the CLI [README](https://github.com/tolstoyevsky/hubot-huntflow-reloaded/tree/master/cli/README.md).
    
- deleting interview of the specified candidate

    Huntflow does not sent requests when interview is canceled, so we need an interface for deleting of the
    interviews from huntflow-reloaded-server database. To emulate it you need to 
    - register the user
    - get the valid token pair (take a look at the point above)
    - get the list of the candidates with non-expired interviews
    - sent request for deleting the interview of the specified candidate
    
    ```bash
    curl -vX POST http://127.0.0.1:8888/manage/delete -d "access=<access_token>" -d @delete_interview.json --header "Content-Type: application/json"
    ```
    
    For the details check the API 
    [README](https://github.com/tolstoyevsky/hubot-huntflow-reloaded/blob/jwt-auth/docs/API_README.md)
    and CLI [README](https://github.com/tolstoyevsky/hubot-huntflow-reloaded/tree/master/cli/README.md).

### Known issues

If you use macOS you need to modify the configuration specified in `docker-compose.yml`.

Remove `network_mode: "host"` and instead specify the ports PostgreSQL and Redis listen on the following way
```
ports:
    - "5432:5432"
```
Also, see the Rocket.Chat Hubot adapter [README](https://github.com/tolstoyevsky/mmb/tree/master/hubot-rocketchat#known-issues) for details how to run it on macOS.

## Authors

See [AUTHORS](AUTHORS.md).

## Licensing

hubot-huntflow-reloaded is available under the [Apache License, Version 2.0](LICENSE).
