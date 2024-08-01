## Fetch endpoint

You can use following command:

`opera_revenue_api_fetch --user USER --token TOKEN [--api-version API_VERSION] [--api-url API_URL] --start-date YYYY-mm-dd --end-date YYYY-mm-dd --source SOURCE [--csv-output-file CSV_OUTPUT_FILE]`

Where:
* `USER`, `TOKEN` and `SOURCE` will be provided by Opera,
* `API_VERSION` defaults to v1, which is the only currently supported option,
* `API_URL` defaults to https://revenueapi.osp.opera.software/. For testing purposes, use the endpoint https://revenueapi-test.osp.opera.software/,
* `CSV_OUTPUT_FILE` specifies the path, where the fetched data will be saved. If not provided CSV data will be printed to standard output.

You can also use the provided Python class OperaRevenueApiClient with `fetch_data` method. To import: `from opera_revenue_api.client import OperaRevenueApiClient`.

## Upload endpoint
Client will take only a CSV file path, a date and your credentials as input. It’ll upload the data and will be monitoring upload job status. It can also be used to check the status of previous jobs.

Following commands are available:

* To execute upload synchronously and wait for the upload job to finish: `opera_revenue_api_upload --user your_username --token your_api_token --csv-path path/to/revenue.csv`
* To separately/asynchronously upload data and check the upload job status:
  * Upload without checking the upload job status: `opera_revenue_api_upload --upload-only --user your_username --token your_api_token --csv-path path/to/revenue.csv`
  * Check job status: `opera_revenue_api_upload --job-status --user your_username --token your_api_token --job-id job_id_from_previous_step`

You can also use the provided Python class `OperaRevenueApiClient`, defined in `client.py` with methods `upload_daily_data`, `check_job_status`, `upload_and_wait_for_success`.
pr