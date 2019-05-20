## CLI Docs

Command line utility for managing users. 

### Table of Contents
- [Configuration](#configuration)
- [Interface for registering users](#interface-for-registering-users)
- [Interface for resending password](#interface-for-resending-password)
- [Interface for listing users](#interface-for-listing-users)
- [Interface for deleting users](#interface-for-deleting-users)

### Configuration

| Environment variables | Command line options   | Description                                         | Default             |
|-----------------------|------------------------|-----------------------------------------------------|---------------------|
|`POSTGRES_DBNAME`      | `--postgres-dbname`    | Database name.                                      | `huntflow-reloaded` |
|`POSTGRES_HOST`        | `--postgres-host`      | PostgreSQL host.                                    | 127.0.0.1           |
|`POSTGRES_PORT`        | `--postgres-port`      | Port PostgreSQL listens on.                         | `5432`              |
|`POSTGRES_USER`        | `--postgres-user`      | PostgreSQL user name.                               | postgres            |
|`POSTGRES_PASSWORD`    | `--postgres-pass`      | Password of the above-mentioned PostgreSQL user.    |                     |
|`SMTP_SERVER`          |                        | SMTP server address.                                |                     | 
|`SMTP_PORT`            |                        | SMTP port server listens on.                        |                     |
|`SENDER_EMAIL`         |                        | Sender email address.                               |                     |
|`SENDER_PASSWORD`      |                        | Sender email password.                              |                     |

Note, that these params should match the PostgreSQL params you will run server with.

### Interface for registering users
Registering a new user with the unique email. The password will be generated and credentials will be send to the user's email.

| Command line options   | Description                                                                   | Default  |
|------------------------|-------------------------------------------------------------------------------|----------|
| `-e`, `--email`        | Unique email address to register new user with. It is the required parameter. |          |
| `-l`, `--pass-len`     | The length of the password which will be automatically generated.             | 8        |
| `-s`, `--send-email`   | If specified the credentials will be sent to the user's email.                |          |
| `-c`, `--count-resend` | Number of attempts to send the credentials to the user's email.               | 5        |

Sample Call:

```bash
env PYTHONPATH=$(pwd) python cli/manager.py create -e user_email@domain.com -s
```

Success Response:

```bash
User created successfully!
Message was sent successfully!
```

### Interface for resending password

Resending the credentials to the user's email.

Sample Call:

```bash
env PYTHONPATH=$(pwd) python cli/manager.py resend -e user_email@domain.com
```
Success Response:

```bash
Message was sent successfully!
```

### Interface for listing users
Listing all users' emails.

Sample Call:

```bash
env PYTHONPATH=$(pwd) python cli/manager.py list
```

### Interface for deleting users

Sample Call:

```bash
env PYTHONPATH=$(pwd) python cli/manager.py delete -e user_email@domain.com
```
Success Response:

```bash
User deleted successfully!
```