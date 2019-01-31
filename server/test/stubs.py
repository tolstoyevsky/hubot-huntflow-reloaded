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

"""Module containing stub requests. """


REQUEST_WITH_UNDEFINED_TYPE = """{
    %ACCOUNT%,
    "event": {
        "created": "%CREATED_DATE%"
    }
}
"""

REQUEST_WITH_UNKNOWN_TYPE = """{
    %ACCOUNT%,
    "event": {
        "created": "%CREATED_DATE%",
        "type": "wonder_type"
    }
}
"""

INCOMPLETE_INTERVIEW_REQUEST = """{
    %ACCOUNT%,
    "event": {
        "created": "%CREATED_DATE%",
        "type": "STATUS",
        "applicant": {
            "first_name": "Matt"
        }
    }
}
"""

MISSING_CALENDAR_INTERVIEW_REQUEST = """
    %ACCOUNT%,
    "event": {
        "created": "%CREATED_DATE%",
        "type": "STATUS",
        "applicant": {
            "id": 1,
            "first_name": "Matt",
            "last_name": "Groening"
        },
        "calendar_event": None
    }
}
"""

INTERVIEW_REQUEST = """{
    %ACCOUNT%,
    "event": {
        "created": "%CREATED_DATE%",
        "type": "STATUS",
        "applicant": {
            "id": 1,
            "first_name": "Matt",
            "last_name": "Groening"
        },
        "calendar_event": {
            "start": "1989-12-17T00:00:00+03:00",
            "end": "1989-12-17T01:00:00+03:00"
        }
    }
}
"""
