# Utility for managing of users

Commands:
* Create
* Delete
* list

Usage:

```
manager.py [-h] [--postgres-pass POSTGRES_PASS]
                [--postgres-user POSTGRES_USER]
                [--postgres-host POSTGRES_HOST]
                [--postgres-port POSTGRES_PORT]
                {create,delete,list} ...

positional arguments:
  {create,delete,list}  commands
    create              create the user instance
    delete              delete the user instance
    list                print the list of users

optional arguments:
  -h, --help            show this help message and exit
  --postgres-pass POSTGRES_PASS
                        PostgreSQL user password
  --postgres-user POSTGRES_USER
                        PostgreSQL user name
  --postgres-host POSTGRES_HOST
                        PostgreSQL host
  --postgres-port POSTGRES_PORT
                        PostgreSQL port
```

Example of usage:
```
>>> env PYTHONPATH=$(pwd) python CLI/manager.py create -e test@test.com -l 5 -s
User created successfully!
Message sent successfully!
>>> env PYTHONPATH=$(pwd) python CLI/manager.py list
login: test@test.com; password: RtOhb
>>>env PYTHONPATH=$(pwd) python CLI/manager.py delete -e test@test.com;
User deleted successfully!
>>> env PYTHONPATH=$(pwd) python CLI/manager.py list


```
