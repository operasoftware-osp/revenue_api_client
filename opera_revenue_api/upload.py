import argparse

from opera_revenue_api.client import OperaRevenueApiClient


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
        "--csv-path",
        required=False,
        help="Full path to CSV file. When used, --csv-content cannot be used.",
    )
    parser.add_argument(
        "--csv-content",
        required=False,
        help="CSV file content. When used, --csv-path cannot be used.",
    )
    parser.add_argument(
        "--job-id",
        required=False,
        help="Id of previously started upload. Use only with --job-status flag.",
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
