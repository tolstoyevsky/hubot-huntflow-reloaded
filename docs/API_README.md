## API Docs

The REST API allowing to retrieve and change data at huntflow-reloaded-server from the client side for the authorized users.

### Table of Contents

- [Interface to sign in](#interface-to-sign-in)
- [Interface for refreshing an access token](#interface-for-refreshing-an-access-token)
- [Interface for getting a list of candidates with non-expired interviews](#interface-for-getting-a-list-of-candidates-who-have-non-expired-interviews)
- [Interface for getting a list of candidates with fwd attribute](#interface-for-getting-a-list-of-candidates-with-first-working-day-attribute)
- [Interface for getting first working day for the specified candidate](#interface-for-getting-first-working-day-for-the-specified-candidate)
- [Interface for deleting an interview](#interface-for-deleting-a-non-expired-interview-for-the-specified-candidate)
- [Common Authorization Error Responses](#common-authorization-error-responses)

### Interface to sign in

| URI      | Method | Authorization |
|----------|--------|---------------|
|`/token`  | `POST` | not required  |


Param: json data.
```
{
    "user" : {
        "email": [string],
        "password": [string]
    }
}
```

Success Response:

* Code: 200
* Content: `{"refresh": "<refresh token>", "access": "<access token>"}`, where `<refresh token>` and `<access token>` are the valid JWT tokens.

Specific Error Responses:

* Code: 400
* Content: `{"detail": "No active account found with the given credentials", "code": "invalid_auth_creds"}`
* How to solve: register a user by yourself or ask your sysadmin to do it and provide valid credentials.

----------

* Code: 500
* Content:
    - `Could not decode request body. There must be valid JSON`
    - `Incomplete request`
* How to solve: provide the valid json.

Sample Call:

```bash
curl -X POST http://127.0.0.1:8888/token -d @auth.json --header "Content-Type: application/json"
```
   
### Interface for refreshing an access token

| URI               | Method | Authorization |
|-------------------|--------|---------------|
|`/token/refresh`   | `POST` | required      |


Param: `refresh=[string]` where refresh is the refresh token.

Success Response:
* Code: 200
* Content: `{"access": "<access>"}`, where <access> is a new access token which replaces the previous one.

Specific Error Responses:
* Code: 403
* Content: `{"detail": "Refresh token is expired"}`
* How to solve: get a new token pair sending a request to `/token` (see the [description of the endpoint](#interface-to-sign-in) for details).
----
* Code: 401
* Content: 
    - `{'detail': 'Refresh token is invalid'}`
    - `{'detail': 'Refresh token is not provided'}`

* How to solve: get a new token pair sending a request to `/token` (see the [description of the endpoint](#interface-to-sign-in) for details).

Sample Call:

```bash
$ curl -L -X POST http://127.0.0.1:8888/token/refresh -d "refresh=<refresh_token>"
```

#### Interface for getting a list of candidates who have non-expired interviews

| URI               | Method | Authorization |
|-------------------|--------|---------------|
|  `/manage/list`   | `GET`  | required      |

Param: `"access": [string]`, where access is users access token token.

Success Response:
* Code: 200
* Content: 
```
{
    "users": [
    {
        "first_name": [string],
        "last_name": [string]
    },
    {
    ...
    }
    ],
    "total": [number],
    "success": True
}
```

Sample Call:

```bash
$ curl -X GET http://127.0.0.1:8888/manage/list -d "access=<access_token>"
```

### Interface for getting a list of candidates with first working day attribute

| URI                   | Method | Authorization |
|-----------------------|--------|---------------|
|  `/manage/fwd_list`   | `GET`  | required      |

Param: `"access": [string]`, where access is users access token token.

Success Response:
* Code: 200
* Content:
```
{
    "users": [
    {
        "first_name": [string],
        "last_name": [string]
    },
    {
    ...
    }
    ],
    "total": [number],
    "success": True
}
```

Sample Call:

```bash
$ curl -X GET http://127.0.0.1:8888/manage/fwd_list -d "access=<access_token>"
```

### Interface for getting first working day for the specified candidate

| URI               | Method | Authorization |
|-------------------|--------|---------------|
| `/manage/fwd`     | `GET`  | required      |

Param: query data with: `"access": [string]` where `access` is the access token, `"first_name": [string]` where `first_name` is the first name of candidate, `"last_name": [string]` where `last_name` is the last name of candidate.

Success Response:
* Code: 200
* Content:
```
"candidate" : {
    "first_name": [string],
    "last_name": [string],
    "fwd": [string]
}
```

Specific Error Responses:

* Code: 400
* Content:
    - `{"detail": "Candidate with the given credentials was not found", "code": "no_candidate"}` 
    - `{"detail": "First working day of specified candidate was not found", "code"": "no_fwd"}` 
    - `{"detail": "Missing parameter paramName", "code": "missing_parameter"}`
----

* Code: 400
* Content:

    - `Could not decode request body. There must be valid JSON`
    - `Incomplete request`


Sample Call:

```bash
$ curl -X GET http://127.0.0.1:8888/manage/fwd -d "access=<access_token>" -d "first_name=<first_name>" -d "last_name=<last_name>"
```

### Interface for deleting a non-expired interview for the specified candidate

| URI               | Method | Authorization |
|-------------------|--------|---------------|
| `/manage/delete`  | `POST` | required      |

Param: json data and `"access": [string]` where `access` is the access token.
```
"candidate" : {
    "first_name": [string],
    "last_name": [string]
}
```

Success Response:
* Code: 200
* Content: None

Specific Error Responses:

* Code: 400
* Content: 
    - `{"detail": "Candidate with the given credentials was not found", "code": "no_candidate"}` 
    - `{"detail": "Candidate does not have non-expired interviews", "code"": "no_interview"}` 
----

* Code: 400
* Content: 

    - `Could not decode request body. There must be valid JSON`
    - `Incomplete request`
    

Sample Call:

```bash
$ curl -X POST http://127.0.0.1:8888/manage/delete -d "access=<access_token>" -d @candidate.json --header "Content-Type: application/json"
```

### Common Authorization Error Responses

Error Responses:

* Code: 401
* Content: `{"detail": "Token is invalid"}`
* How to solve: get a new token pair sending a request to `/token` (see the [description of the endpoint](#interface-to-sign-in) for details).
____

* Code: 403
* Content: `{"detail": "Token is expired"}`
* How to solve: refresh the access token sending a request to `/token/refresh` (see the [description of the endpoint](#interface-for-refreshing-an-access-token) for details).
____

* Code: 401
* Content: `{"detail": "Token is not provided"}`
* How to solve: add to the request a valid access token.
