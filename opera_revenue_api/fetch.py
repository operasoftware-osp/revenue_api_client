import argparse
from datetime import datetime

from opera_revenue_api.client import OperaRevenueApiClient


def opera_revenue_api_fetch():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--api-version", default="v1")
    parser.add_argument("--api-url", default="https://revenueapi.osp.opera.software")

    parser.add_argument(
        "--start-date",
        required=True,
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help="End date in YYYY-MM-DD format",
    )
    parser.add_argument("--source", required=True, help="Data source name provided by Opera")
    parser.add_argument(
        "--csv-output-file", default=None, help="Path to save csv file, will be printed to stdout if None"
    )

    args = parser.parse_args()
    client = OperaRevenueApiClient(
        user=args.user,
        api_token=args.token,
        api_version=args.api_version,
        api_url=args.api_url,
    )

    client.fetch_data(
        start_date=args.start_date, end_date=args.end_date, source=args.source, csv_path=args.csv_output_file
    )


if __name__ == "__main__":
    opera_revenue_api_fetch()
