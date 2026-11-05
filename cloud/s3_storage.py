import os
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.settings import settings

logger = logging.getLogger("finops_cloud")


class S3StorageManager:
    """
    AWS S3 Client Manager:
    Handles cloud archival of transaction batches, model weights, and financial reports.
    Gracefully falls back to local storage if AWS credentials are not configured.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = settings.AWS_DEFAULT_REGION
        self.is_configured = False
        self.client = None

        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.client = boto3.client(
                    "s3",
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                self.is_configured = True
            except Exception as e:
                logger.warning(f"Could not initialize S3 client: {e}")

    def upload_file(self, local_path: str, s3_key: str) -> Dict[str, Any]:
        """Uploads a local file to the configured S3 bucket."""
        if not self.is_configured or not self.client:
            logger.info(f"S3 not configured. Local fallback saved at: {local_path}")
            return {
                "status": "local_fallback",
                "local_path": local_path,
                "message": "AWS S3 credentials not provided. Stored locally.",
            }

        try:
            self.client.upload_file(local_path, self.bucket_name, s3_key)
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            logger.info(f"Uploaded {local_path} to {s3_url}")
            return {
                "status": "uploaded",
                "bucket": self.bucket_name,
                "s3_key": s3_key,
                "s3_url": s3_url,
            }
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"S3 Upload failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "local_path": local_path,
            }

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Downloads an object from S3 to local disk."""
        if not self.is_configured or not self.client:
            logger.warning("S3 client not configured for download.")
            return False

        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            logger.error(f"S3 Download failed: {e}")
            return False
