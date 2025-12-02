"""
Cloud Storage Service (S3 and Cloudinary)
Upload generated videos/images to cloud storage
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import os
from enum import Enum

logger = logging.getLogger(__name__)


class StorageProvider(str, Enum):
    S3 = "s3"
    R2 = "r2"  # Cloudflare R2 (S3-compatible)
    SUPABASE = "supabase"
    CLOUDINARY = "cloudinary"
    LOCAL = "local"


class CloudStorage:
    """
    Unified cloud storage interface supporting S3 and Cloudinary.
    """

    def __init__(self, provider: str = None):
        """
        Initialize cloud storage.

        Args:
            provider: 'r2', 's3', 'supabase', 'cloudinary', or 'local' (defaults to env var STORAGE_PROVIDER)
        """
        self.provider = StorageProvider(provider or os.getenv("STORAGE_PROVIDER", "local"))

        if self.provider == StorageProvider.R2:
            self._init_r2()
        elif self.provider == StorageProvider.S3:
            self._init_s3()
        elif self.provider == StorageProvider.SUPABASE:
            self._init_supabase()
        elif self.provider == StorageProvider.CLOUDINARY:
            self._init_cloudinary()
        else:
            self._init_local()

    def _init_r2(self):
        """Initialize Cloudflare R2 client (S3-compatible)."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            # R2 uses S3-compatible API with custom endpoint
            account_id = os.getenv("R2_ACCOUNT_ID")
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                region_name='auto'  # R2 uses 'auto' for region
            )
            self.s3_bucket = os.getenv("R2_BUCKET_NAME", "instaai-storage")
            # Custom domain or R2 public URL
            self.s3_base_url = os.getenv("R2_PUBLIC_URL", f"https://pub-{account_id}.r2.dev")

            logger.info("Cloudflare R2 storage initialized")
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize R2: {e}")
            raise

    def _init_s3(self):
        """Initialize AWS S3 client."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            self.s3_bucket = os.getenv("AWS_S3_BUCKET", "instaai-content")
            self.s3_base_url = f"https://{self.s3_bucket}.s3.amazonaws.com"

            logger.info("S3 storage initialized")
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3: {e}")
            raise

    def _init_supabase(self):
        """Initialize Supabase Storage client."""
        try:
            from supabase import create_client, Client

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin access

            self.supabase: Client = create_client(supabase_url, supabase_key)
            self.supabase_bucket = os.getenv("SUPABASE_BUCKET", "instaai-media")
            self.supabase_base_url = f"{supabase_url}/storage/v1/object/public/{self.supabase_bucket}"

            # Create bucket if it doesn't exist
            try:
                self.supabase.storage.get_bucket(self.supabase_bucket)
            except:
                self.supabase.storage.create_bucket(self.supabase_bucket, {"public": True})

            logger.info("Supabase storage initialized")
        except ImportError:
            logger.error("supabase not installed. Install with: pip install supabase")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            raise

    def _init_cloudinary(self):
        """Initialize Cloudinary client."""
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET")
            )
            self.cloudinary = cloudinary

            logger.info("Cloudinary storage initialized")
        except ImportError:
            logger.error("cloudinary not installed. Install with: pip install cloudinary")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Cloudinary: {e}")
            raise

    def _init_local(self):
        """Initialize local file storage."""
        self.local_storage_path = Path(os.getenv("LOCAL_STORAGE_PATH", "./storage"))
        self.local_storage_path.mkdir(parents=True, exist_ok=True)
        self.local_base_url = os.getenv("LOCAL_BASE_URL", "http://localhost:8000/media")

        logger.info(f"Local storage initialized at {self.local_storage_path}")

    def upload_video(
        self,
        file_path: Path,
        folder: str = "reels",
        public_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload video to cloud storage.

        Args:
            file_path: Path to video file
            folder: Storage folder/prefix
            public_id: Optional custom ID for the file

        Returns:
            {
                "url": "https://...",
                "secure_url": "https://...",
                "public_id": "...",
                "format": "mp4",
                "resource_type": "video"
            }
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.provider in [StorageProvider.R2, StorageProvider.S3]:
            return self._upload_to_s3(file_path, folder, public_id)
        elif self.provider == StorageProvider.SUPABASE:
            return self._upload_to_supabase(file_path, folder, public_id, "video")
        elif self.provider == StorageProvider.CLOUDINARY:
            return self._upload_to_cloudinary(file_path, folder, public_id, "video")
        else:
            return self._upload_local(file_path, folder, public_id)

    def upload_image(
        self,
        file_path: Path,
        folder: str = "images",
        public_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image to cloud storage.

        Args:
            file_path: Path to image file
            folder: Storage folder/prefix
            public_id: Optional custom ID

        Returns:
            Upload metadata with URL
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.provider in [StorageProvider.R2, StorageProvider.S3]:
            return self._upload_to_s3(file_path, folder, public_id)
        elif self.provider == StorageProvider.SUPABASE:
            return self._upload_to_supabase(file_path, folder, public_id, "image")
        elif self.provider == StorageProvider.CLOUDINARY:
            return self._upload_to_cloudinary(file_path, folder, public_id, "image")
        else:
            return self._upload_local(file_path, folder, public_id)

    def _upload_to_s3(
        self,
        file_path: Path,
        folder: str,
        public_id: Optional[str]
    ) -> Dict[str, Any]:
        """Upload file to AWS S3."""
        try:
            # Generate key
            if public_id:
                key = f"{folder}/{public_id}{file_path.suffix}"
            else:
                key = f"{folder}/{file_path.name}"

            # Determine content type
            content_type = "video/mp4" if file_path.suffix == ".mp4" else "image/jpeg"

            # Upload
            self.s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ACL": "public-read"
                }
            )

            url = f"{self.s3_base_url}/{key}"

            logger.info(f"✅ Uploaded to S3: {url}")

            return {
                "url": url,
                "secure_url": url,
                "public_id": key,
                "format": file_path.suffix.lstrip('.'),
                "resource_type": "video" if ".mp4" in file_path.suffix else "image"
            }

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def _upload_to_cloudinary(
        self,
        file_path: Path,
        folder: str,
        public_id: Optional[str],
        resource_type: str
    ) -> Dict[str, Any]:
        """Upload file to Cloudinary."""
        try:
            result = self.cloudinary.uploader.upload(
                str(file_path),
                folder=folder,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True
            )

            logger.info(f"✅ Uploaded to Cloudinary: {result['secure_url']}")

            return {
                "url": result["url"],
                "secure_url": result["secure_url"],
                "public_id": result["public_id"],
                "format": result["format"],
                "resource_type": result["resource_type"]
            }

        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise

    def _upload_to_supabase(
        self,
        file_path: Path,
        folder: str,
        public_id: Optional[str],
        resource_type: str
    ) -> Dict[str, Any]:
        """Upload file to Supabase Storage."""
        try:
            # Generate path
            if public_id:
                object_path = f"{folder}/{public_id}{file_path.suffix}"
            else:
                object_path = f"{folder}/{file_path.name}"

            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Determine content type
            if resource_type == "video":
                content_type = "video/mp4" if file_path.suffix == ".mp4" else "video/quicktime"
            else:
                content_type = "image/jpeg" if file_path.suffix in [".jpg", ".jpeg"] else f"image/{file_path.suffix.lstrip('.')}"

            # Upload to Supabase
            response = self.supabase.storage.from_(self.supabase_bucket).upload(
                object_path,
                file_data,
                {"content-type": content_type}
            )

            # Get public URL
            url = f"{self.supabase_base_url}/{object_path}"

            logger.info(f"✅ Uploaded to Supabase: {url}")

            return {
                "url": url,
                "secure_url": url,
                "public_id": object_path,
                "format": file_path.suffix.lstrip('.'),
                "resource_type": resource_type
            }

        except Exception as e:
            logger.error(f"Supabase upload failed: {e}")
            raise

    def _upload_local(
        self,
        file_path: Path,
        folder: str,
        public_id: Optional[str]
    ) -> Dict[str, Any]:
        """Save file to local storage."""
        try:
            # Create folder
            dest_folder = self.local_storage_path / folder
            dest_folder.mkdir(parents=True, exist_ok=True)

            # Generate filename
            if public_id:
                dest_filename = f"{public_id}{file_path.suffix}"
            else:
                dest_filename = file_path.name

            dest_path = dest_folder / dest_filename

            # Copy file
            import shutil
            shutil.copy2(file_path, dest_path)

            url = f"{self.local_base_url}/{folder}/{dest_filename}"

            logger.info(f"✅ Saved locally: {dest_path}")

            return {
                "url": url,
                "secure_url": url,
                "public_id": f"{folder}/{dest_filename}",
                "format": file_path.suffix.lstrip('.'),
                "resource_type": "video" if ".mp4" in file_path.suffix else "image",
                "local_path": str(dest_path)
            }

        except Exception as e:
            logger.error(f"Local storage failed: {e}")
            raise

    def delete_file(self, public_id: str) -> bool:
        """
        Delete file from cloud storage.

        Args:
            public_id: Public ID or key of the file

        Returns:
            True if successful
        """
        try:
            if self.provider in [StorageProvider.R2, StorageProvider.S3]:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=public_id)
            elif self.provider == StorageProvider.SUPABASE:
                self.supabase.storage.from_(self.supabase_bucket).remove([public_id])
            elif self.provider == StorageProvider.CLOUDINARY:
                self.cloudinary.uploader.destroy(public_id)
            else:
                # Local deletion
                file_path = self.local_storage_path / public_id
                if file_path.exists():
                    file_path.unlink()

            logger.info(f"✅ Deleted: {public_id}")
            return True

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    def get_url(self, public_id: str) -> str:
        """
        Get public URL for a file.

        Args:
            public_id: Public ID or key

        Returns:
            Public URL
        """
        if self.provider in [StorageProvider.R2, StorageProvider.S3]:
            return f"{self.s3_base_url}/{public_id}"
        elif self.provider == StorageProvider.SUPABASE:
            return f"{self.supabase_base_url}/{public_id}"
        elif self.provider == StorageProvider.CLOUDINARY:
            from cloudinary import CloudinaryImage
            return CloudinaryImage(public_id).build_url()
        else:
            return f"{self.local_base_url}/{public_id}"


# Singleton instance
_storage = None


def get_storage() -> CloudStorage:
    """Get singleton cloud storage instance."""
    global _storage
    if _storage is None:
        _storage = CloudStorage()
    return _storage
