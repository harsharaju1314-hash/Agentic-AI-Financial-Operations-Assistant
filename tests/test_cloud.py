import os
from unittest.mock import MagicMock, patch
from cloud.s3_storage import S3StorageManager


def test_s3_storage_local_fallback(tmp_path):
    test_file = tmp_path / "sample.csv"
    test_file.write_text("col1,col2\n1,2")

    manager = S3StorageManager(bucket_name="test-bucket")
    res = manager.upload_file(str(test_file), "sample.csv")
    assert res["status"] in ("local_fallback", "uploaded")
    assert "local_path" in res or "s3_url" in res


def test_s3_storage_with_mock_client(tmp_path):
    test_file = tmp_path / "report.json"
    test_file.write_text('{"report": "ok"}')

    manager = S3StorageManager(bucket_name="finops-bucket")
    manager.is_configured = True
    manager.client = MagicMock()

    res = manager.upload_file(str(test_file), "archive/report.json")
    assert res["status"] == "uploaded"
    assert "s3_url" in res
    manager.client.upload_file.assert_called_once()
