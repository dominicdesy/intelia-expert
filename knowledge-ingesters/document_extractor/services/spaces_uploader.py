"""
Digital Ocean Spaces Uploader
Version: 1.0.0
Last modified: 2025-10-31

Uploads images to Digital Ocean Spaces (S3-compatible object storage)
"""

import os
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SpacesUploader:
    """
    Upload files to Digital Ocean Spaces (S3-compatible storage).

    Environment variables required:
        DO_SPACES_KEY: Digital Ocean Spaces access key
        DO_SPACES_SECRET: Digital Ocean Spaces secret key
        DO_SPACES_REGION: Digital Ocean Spaces region (e.g., nyc3, sfo3, ams3)
        DO_SPACES_ENDPOINT: Digital Ocean Spaces endpoint (e.g., https://nyc3.digitaloceanspaces.com)
    """

    def __init__(
        self,
        bucket: str = "intelia-knowledge",
        region: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """
        Initialize Spaces uploader.

        Args:
            bucket: Spaces bucket name
            region: Optional region override
            endpoint: Optional endpoint override
        """
        self.bucket = bucket
        self.region = region or os.getenv("DO_SPACES_REGION", "nyc3")
        self.endpoint = endpoint or os.getenv(
            "DO_SPACES_ENDPOINT",
            f"https://{self.region}.digitaloceanspaces.com"
        )

        # Get credentials from environment
        self.access_key = os.getenv("DO_SPACES_KEY")
        self.secret_key = os.getenv("DO_SPACES_SECRET")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "Digital Ocean Spaces credentials not found. "
                "Set DO_SPACES_KEY and DO_SPACES_SECRET environment variables."
            )

        # Initialize S3 client (Spaces is S3-compatible)
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

        logger.info(f"Spaces uploader initialized: {self.endpoint}/{self.bucket}")

    def upload_image(
        self,
        image_data: bytes,
        filename: str,
        folder: str = "documents",
        content_type: str = "image/png",
        make_public: bool = True
    ) -> str:
        """
        Upload an image to Digital Ocean Spaces.

        Args:
            image_data: Image binary data
            filename: Filename to save as
            folder: Folder path within bucket (default: "documents")
            content_type: MIME type (default: "image/png")
            make_public: Make file publicly accessible (default: True)

        Returns:
            Public URL of uploaded image

        Raises:
            ClientError: If upload fails
        """
        # Build S3 key (path within bucket)
        s3_key = f"{folder}/{filename}"

        try:
            # Prepare upload parameters
            upload_params = {
                'Body': image_data,
                'Bucket': self.bucket,
                'Key': s3_key,
                'ContentType': content_type
            }

            # Make public if requested
            if make_public:
                upload_params['ACL'] = 'public-read'

            # Upload to Spaces
            self.s3_client.put_object(**upload_params)

            # Generate public URL (origin endpoint - CDN is disabled)
            # Format: https://bucket.region.digitaloceanspaces.com/folder/filename
            public_url = f"https://{self.bucket}.{self.region}.digitaloceanspaces.com/{s3_key}"

            logger.info(f"Uploaded: {filename} → {public_url}")

            return public_url

        except ClientError as e:
            logger.error(f"Failed to upload {filename}: {e}")
            raise

    def upload_file(
        self,
        file_path: str,
        folder: str = "documents",
        filename: Optional[str] = None,
        make_public: bool = True
    ) -> str:
        """
        Upload a file from disk to Digital Ocean Spaces.

        Args:
            file_path: Local file path
            folder: Folder path within bucket
            filename: Optional custom filename (default: use original filename)
            make_public: Make file publicly accessible

        Returns:
            Public URL of uploaded file
        """
        import mimetypes
        from pathlib import Path

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use original filename if not specified
        if not filename:
            filename = file_path.name

        # Detect MIME type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"

        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Upload
        return self.upload_image(
            image_data=file_data,
            filename=filename,
            folder=folder,
            content_type=content_type,
            make_public=make_public
        )

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from Spaces.

        Args:
            s3_key: Full S3 key (path) of file to delete

        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {s3_key}: {e}")
            return False

    def list_files(self, prefix: str = "") -> list:
        """
        List files in Spaces bucket.

        Args:
            prefix: Filter by prefix (folder)

        Returns:
            List of file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )

            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            else:
                return []

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in Spaces.

        Args:
            s3_key: Full S3 key (path) of file

        Returns:
            True if file exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False


# Example usage
if __name__ == "__main__":
    """
    Test Spaces uploader.

    Before running:
    1. Set environment variables in .env file:
       DO_SPACES_KEY=your_access_key
       DO_SPACES_SECRET=your_secret_key
       DO_SPACES_REGION=nyc3
       DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

    2. Create a bucket named "intelia-knowledge" in Digital Ocean Spaces
    """

    # Initialize uploader
    uploader = SpacesUploader(bucket="intelia-knowledge")

    # Test upload (dummy image)
    from PIL import Image
    import io

    # Create a test image
    test_image = Image.new('RGB', (800, 600), color='blue')
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()

    # Upload
    url = uploader.upload_image(
        image_data=img_bytes,
        filename="test_image.png",
        folder="test",
        content_type="image/png"
    )

    print(f"Uploaded test image: {url}")

    # List files
    files = uploader.list_files(prefix="test/")
    print(f"Files in test/: {files}")
