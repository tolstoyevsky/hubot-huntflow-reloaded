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
- [Authors](#authors)
- [Licensing](#licensing)

## Prerequisites

* The bot must be in the channel specified via the `HUNTFLOW_REMINDER_CHANNEL` environment variable.
* There must be specified the `POSTGRES_PASSWORD` environment variable (see the [configuration section](#configuration-1) for details).

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

| Environment variables | Command line options   | Description                                                                    | Default                                   |
|-----------------------|------------------------|--------------------------------------------------------------------------------|-------------------------------------------|
|`LOGLEVEL`             | `--logging`            | Logs level.                                                                    | `info`                                    |
|`LOG_FILE`             | `--log-file-prefix`    | File where log information will be stored.                                     | `/var/log/huntflow-reloaded-server.log`   |
|`POSTGRES_DBNAME`      | `--postgres-dbname`    | Database name.                                                                 | `huntflow-reloaded`                       |
|`POSTGRES_HOST`        | `--postgres-host`      | PostgreSQL host.                                                               | 127.0.0.1                                 |
|`POSTGRES_PORT`        | `--postgres-port`      | Port PostgreSQL listens on.                                                    | `5432`                                    |
|`POSTGRES_USER`        | `--postgres-user`      | PostgreSQL user name.                                                          | postgres                                  |
|`POSTGRES_PASSWORD`    | `--postgres-pass`      | Password of the above-mentioned PostgreSQL user.                               |                                           |
|`REDIS_HOST`           | `--redis-host`         | Redis host.                                                                    | 127.0.0.1                                 |
|`REDIS_PORT`           | `--redis-port`         | Port Redis listens on.                                                         | `6379` or `16379` (in a Docker container) |
|`REDIS_PASSWORD`       | `--redis-password`     | Redis password.                                                                |                                           |
|`CHANNEL_NAME`         | `--channel-name`       | Redis channel name to be used for communication between the server and client. | `hubot-huntflow-reloaded`                 |
|`TZ`                   |                        | Timezone for for scheduler **(for Docker container only)**.                    | Europe/Moscow                             |

## Authors

See [AUTHORS](AUTHORS.md).

## Licensing

hubot-huntflow-reloaded is available under the [Apache License, Version 2.0](LICENSE).
