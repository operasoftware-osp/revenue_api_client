# Copyright 2020 Opera Software International AS
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

import logging
import os
from enum import Enum
from json import JSONDecodeError
from time import sleep

import requests
import timeout_decorator
from requests.auth import HTTPBasicAuth


__all__ = [
    "OperaRevenueApiClient",
    "OperaRevenueApiError",
    "OperaRevenueApiTimeExceeded",
    "OperaRevenueApiUploadError",
    "OperaRevenueApiValidationError",
]


class OperaRevenueApiError(Exception):
    pass


class OperaRevenueApiTimeExceeded(OperaRevenueApiError, timeout_decorator.TimeoutError):
    pass


class OperaRevenueApiUploadError(OperaRevenueApiError):
    pass


class OperaRevenueApiValidationError(OperaRevenueApiError):
    pass


class OperaRevenueApiClient:
    """
    Opera Revenue API client.
    Can be used to upload revenue data in CSV format and ensures that upload was completed.
    """

    MAX_FILE_SIZE = 30 * 1024**2

    class JobStatus(Enum):
        SUCCESS = "success"
        FAILED = "failed"
        RUNNING = "running"
        UNDEFINED = "undefined"

    def __init__(
        self,
        user,
        api_token,
        api_version="v1",
        api_url="https://revenueapi.osp.opera.software",
    ):
        self.user = user
        self.api_token = api_token
        self.api_url = api_url.rstrip("/")
        self.version = api_version.strip("/")
        self.log = logging.getLogger()

    def upload_and_wait_for_success(self, csv_path=None, csv_content=None):
        """
        Starts upload and waits until remote job is completed.
        """
        upload_response = self.upload_daily_data(csv_path, csv_content)
        job_id = upload_response.get("job_id")
        if not job_id:
            raise OperaRevenueApiUploadError("Upload was not started. Error: {}".format(upload_response))
        self.log.info("Upload started with id {}".format(job_id))
        return self._wait_for_job_to_end(job_id)

    def check_job_status(self, job_id: str) -> dict:
        """
        Checks status of previously started upload.
        """
        if job_id is None:
            raise OperaRevenueApiValidationError('"job_id" must be provided to check job status')
        response = requests.get(
            self._get_endpoint(method="check_job_status"),
            params={"job_id": job_id},
            auth=HTTPBasicAuth(self.user, self.api_token),
        )
        self._check_status_code(response)
        try:
            return response.json()
        except JSONDecodeError:
            return {"error": response.content}

    def upload_daily_data(self, csv_path=None, csv_content=None) -> dict:
        """
        Starts upload without waiting for remote job to complete.
        Remote job should still be monitored in your integration.
        """
        csv_content = self._get_csv(csv_path, csv_content)
        response = requests.post(
            self._get_endpoint(method="upload_daily_data"),
            json={"csv": csv_content},
            auth=HTTPBasicAuth(self.user, self.api_token),
        )
        self._check_status_code(response)
        try:
            return response.json()
        except JSONDecodeError:
            return {"error": response.content}

    def fetch_data(self, start_date, end_date, source, csv_path=None):
        response = requests.get(
            self._get_endpoint("fetch_partner_data"),
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "source": source,
            },
            auth=HTTPBasicAuth(self.user, self.api_token),
        )
        self._check_status_code(response)
        fetched_data = response.json()
        logging.info(f"Fetched data for days: {fetched_data['available_days']}")
        if csv_path is not None:
            if not csv_path.endswith(".csv"):
                csv_path += ".csv"
            if os.path.exists(csv_path):
                raise FileExistsError(f"File {csv_path} already exists, provide another path.")
            with open(csv_path, "w") as f:
                f.write(fetched_data["data"])
        else:
            print(fetched_data["data"])

    @classmethod
    def _check_status_code(cls, response):
        if 500 <= response.status_code < 600:
            raise requests.HTTPError(
                "API is currently unavailable. Please try again later. Response: {}".format(response.content)
            )
        elif response.status_code != 200:
            raise requests.HTTPError(
                "Client error. Status: {}. API response: {}".format(response.status_code, response.text)
            )

    def _get_endpoint(self, method):
        return "{}/{}/{}".format(self.api_url, self.version, method)

    def _get_csv(self, csv_path, csv_content):
        if (csv_content is None) == (csv_path is None):
            raise OperaRevenueApiError('One of "csv_content" or "csv_path" must be defined')
        if csv_content is not None:
            return csv_content
        if not os.path.isfile(csv_path):
            raise OperaRevenueApiValidationError("Could not find csv file: {}".format(csv_path))
        file_size = os.stat(csv_path).st_size
        if file_size > self.MAX_FILE_SIZE:
            raise OperaRevenueApiValidationError(
                "Selected file is too big (>{}MiB): {}".format(self.MAX_FILE_SIZE / 1024**2, csv_path)
            )
        with open(csv_path) as f:
            return f.read()

    @timeout_decorator.timeout(seconds=15 * 60, timeout_exception=OperaRevenueApiTimeExceeded)
    def _wait_for_job_to_end(self, job_id):
        job_status = OperaRevenueApiClient.JobStatus.RUNNING.value
        response = self.check_job_status(job_id)
        while job_status == OperaRevenueApiClient.JobStatus.RUNNING.value:
            sleep(5)
            response = self.check_job_status(job_id)
            job_status = response.get("status")
        if job_status == OperaRevenueApiClient.JobStatus.SUCCESS.value:
            return response
        raise OperaRevenueApiUploadError("Data upload failed. API response: {}".format(response))
