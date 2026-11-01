import os
from pathlib import Path
from typing import Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings


class StorageService:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.has_aws_creds = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        self.local_dir = Path(settings.LOCAL_STORAGE_DIR)
        self.local_dir.mkdir(parents=True, exist_ok=True)

        if self.has_aws_creds:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region,
                endpoint_url=settings.S3_ENDPOINT_URL,
                config=Config(signature_version="s3v4")
            )
        else:
            self.s3_client = None

    def upload_file(
        self,
        file_bytes: bytes,
        s3_key: str,
        content_type: str = "application/pdf"
    ) -> str:
        """Upload file bytes to S3 or local development fallback."""
        if self.s3_client:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type
            )
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

        # Local storage fallback for dev/testing
        file_path = self.local_dir / s3_key.replace("/", os.sep)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_bytes)
        return f"/api/v1/resumes/download-local/{s3_key}"

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600
    ) -> str:
        """Generate a time-limited presigned GET URL."""
        if self.s3_client:
            try:
                return self.s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expires_in
                )
            except ClientError:
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

        # Local fallback simulation URL
        return f"/api/v1/resumes/download-local/{s3_key}"

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str = "application/pdf",
        expires_in: int = 3600
    ) -> dict[str, Any]:
        """Generate a presigned PUT URL for client-side direct uploads."""
        if self.s3_client:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": content_type
                },
                ExpiresIn=expires_in
            )
            return {
                "upload_url": url,
                "method": "PUT",
                "headers": {"Content-Type": content_type},
                "expires_in": expires_in
            }

        return {
            "upload_url": f"/api/v1/resumes/upload-direct-local/{s3_key}",
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "expires_in": expires_in
        }

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3 or local storage."""
        if self.s3_client:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                return True
            except ClientError:
                return False

        file_path = self.local_dir / s3_key.replace("/", os.sep)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def read_file_bytes(self, s3_key: str) -> Any:
        """Read file bytes from S3 or local storage."""
        if self.s3_client:
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return response["Body"].read()
            except ClientError:
                return None

        file_path = self.local_dir / s3_key.replace("/", os.sep)
        if file_path.exists():
            return file_path.read_bytes()
        return None


storage_service = StorageService()

