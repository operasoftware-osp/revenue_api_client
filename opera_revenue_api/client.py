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

import argparse
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
    "OperaRevenueApiUploadTimeExceeded",
    "OperaRevenueApiUploadError",
    "OperaRevenueApiValidationError",
]


class OperaRevenueApiError(ValueError):
    pass


class OperaRevenueApiUploadTimeExceeded(OperaRevenueApiError):
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

    MAX_FILE_SIZE = 30 * 1024 ** 2

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
                "Selected file is too big (>{}MiB): {}".format(self.MAX_FILE_SIZE / 1024 ** 2, csv_path)
            )
        with open(csv_path) as f:
            return f.read()

    @timeout_decorator.timeout(seconds=15 * 60, timeout_exception=OperaRevenueApiUploadTimeExceeded)
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


def opera_revenue_api_upload():
    usage_description = (
        "To upload data without checking job status (job status should be checked by separate command): "
        "opera_revenue_api_upload --upload-only --user your_username "
        "--token your_api_token --csv-path path/to/revenue.csv\n"
        "To check job status: opera_revenue_api_upload "
        "--job-status --user your_username --token your_api_token --job-id job_id_from_previous_step\n"
        "To execute upload synchronously and wait for job to finish: "
        "opera_revenue_api_upload --user your_username --token your_api_token --csv-path path/to/revenue.csv\n"
    )
    parser = argparse.ArgumentParser(description=usage_description)
    parser.add_argument("--user", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--api-version", default="v1")
    parser.add_argument("--api-url", default="https://revenueapi.osp.opera.software")

    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Upload data without checking job status (job status should be checked by separate command)",
    )
    parser.add_argument(
        "--job-status",
        action="store_true",
        help="Check status of previously started upload. --job-id must also be provided.",
    )

    parser.add_argument(
        "--csv-path", required=False, help="Full path to CSV file. When used, --csv-content cannot be used."
    )
    parser.add_argument("--csv-content", required=False, help="CSV file content. When used, --csv-path cannot be used.")
    parser.add_argument(
        "--job-id", required=False, help="Id of previously started upload. Use only with --job-status flag."
    )

    args = parser.parse_args()
    client = OperaRevenueApiClient(
        user=args.user,
        api_token=args.token,
        api_version=args.api_version,
        api_url=args.api_url,
    )

    if args.upload_only:
        print(client.upload_daily_data(args.csv_path, args.csv_content))
    elif args.job_status:
        print(client.check_job_status(args.job_id))
    else:
        print(client.upload_and_wait_for_success(args.csv_path, args.csv_content))


if __name__ == "__main__":
    opera_revenue_api_upload()
