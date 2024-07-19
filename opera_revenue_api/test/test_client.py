from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from requests import HTTPError

from opera_revenue_api.client import (
    OperaRevenueApiClient,
    OperaRevenueApiUploadError,
    OperaRevenueApiValidationError,
)


@pytest.fixture
def client():
    return OperaRevenueApiClient(user="test_user", api_token="test_token")


@pytest.fixture
def mock_get(mocker):
    return mocker.patch("requests.get")


@pytest.fixture
def mock_post(mocker):
    return mocker.patch("requests.post")


def test_should_wait_for_success_status_after_upload(mocker, client, mock_get, mock_post, tmp_path):
    mocker.patch("opera_revenue_api.client.sleep")
    test_csv = tmp_path / "testfile.csv"
    test_csv.write_text("data")
    mock_post.return_value.json.return_value = {"job_id": "12345"}
    mock_post.return_value.status_code = 200
    mock_get.return_value.json.side_effect = [{"status": "running"}, {"status": "success"}]
    mock_get.return_value.status_code = 200

    result = client.upload_and_wait_for_success(csv_path=str(test_csv))

    assert result["status"] == "success"
    assert mock_post.called
    assert mock_get.call_count == 2


def should_fail_if_status_is_undefined(mocker, client, mock_get, mock_post, tmp_path):
    mocker.patch("opera_revenue_api.client.sleep")
    test_csv = tmp_path / "testfile.csv"
    test_csv.write_text("data")
    mock_post.return_value.json.return_value = {"job_id": "12345"}
    mock_post.return_value.status_code = 200
    mock_get.return_value.json.side_effect = [{"status": "running"}, {"status": "undefined"}]
    mock_get.return_value.status_code = 200

    with pytest.raises(OperaRevenueApiUploadError) as exc_info:
        client.upload_and_wait_for_success(csv_path=str(test_csv))

    assert "Data upload failed" in str(exc_info.value)
    assert mock_post.called
    assert mock_get.call_count == 2


def test_should_raise_exception_when_file_not_found(mocker, client):
    mocker.patch("os.path.isfile", return_value=False)

    with pytest.raises(OperaRevenueApiValidationError):
        client.upload_daily_data(csv_path="nonexistent_file.csv")


def test_should_raise_exception_when_file_too_large(mocker, client):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.stat", return_value=mocker.MagicMock(st_size=31 * 1024**2))

    with pytest.raises(OperaRevenueApiValidationError):
        client.upload_daily_data(csv_path="too_large_file.csv")


def test_should_upload_daily_data_from_csv_file_path(mock_post, client, tmp_path):
    test_csv = tmp_path / "testfile.csv"
    test_csv.write_text("data")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"job_id": "123"}

    response = client.upload_daily_data(csv_path=str(test_csv))

    assert response == {"job_id": "123"}


def test_should_upload_daily_data_from_csv_file_content(mock_post, client):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"job_id": "123"}

    response = client.upload_daily_data(csv_content="data")

    assert response == {"job_id": "123"}


def test_should_return_response_when_job_status_is_checked(client, mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json = MagicMock(return_value={"status": "running"})

    response = client.check_job_status("123")

    assert response == {"status": "running"}


def test_should_raise_exception_on_http_error(mock_get, client):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Server error"

    with pytest.raises(HTTPError):
        client.check_job_status("123")


def test_should_save_csv_if_path_is_provided(mock_get, client, tmp_path):
    data = "date,revenue\n2021-01-01,1000\n2021-01-02,1500"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"data": data, "available_days": "2021-01-01,2021-01-02"}
    csv_file = tmp_path / "output.csv"

    client.fetch_data(datetime(2021, 1, 1), datetime(2021, 1, 2), "test_source", csv_path=str(csv_file))

    assert csv_file.read_text() == data


def test_should_sprint_csv_if_path_is_not_provided(mock_get, client, capsys):
    data = "date,revenue\n2021-01-01,1000"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"data": data, "available_days": "2021-01-01"}

    client.fetch_data(datetime(2021, 1, 1), datetime(2021, 1, 1), "test_source")

    captured = capsys.readouterr()
    assert captured.out == data + "\n"


def test_should_raise_exception_when_existing_file_path_is_provided(mock_get, client, tmp_path):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"data": "data", "available_days": ["2021-01-01"]}
    csv_file = tmp_path / "output.csv"
    csv_file.write_text("existing data")

    with pytest.raises(FileExistsError):
        client.fetch_data(datetime(2021, 1, 1), datetime(2021, 1, 2), "test_source", csv_path=str(csv_file))
