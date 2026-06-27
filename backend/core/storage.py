"""
StorageService — upload de fichiers vers S3, MinIO ou stockage local.
Utilisé pour les images produits et les reçus PDF.
"""

import uuid
from pathlib import Path
from typing import Optional

from core.config import get_settings

settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class StorageError(Exception):
    pass


def build_receipt_storage_key(company_id: uuid.UUID, receipt_id: uuid.UUID) -> str:
    return f"receipts/{company_id}/{receipt_id}.pdf"


def build_receipt_download_url(object_key: str) -> str:
    return f"{settings.API_URL}/api/v1/receipts/download/{object_key}"


def build_product_image_url(object_key: str) -> str:
    return f"{settings.API_URL}/api/v1/catalog/products/image/{object_key}"


def _ext_for_content_type(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type, ".bin")


def _storage_buckets() -> list[str]:
    if settings.STORAGE_BACKEND == "minio":
        return [settings.MINIO_BUCKET_PRODUCTS, settings.MINIO_BUCKET_RECEIPTS]
    if settings.STORAGE_BACKEND == "s3":
        return [settings.AWS_S3_BUCKET]
    return []


def _s3_client_kwargs() -> dict:
    if settings.STORAGE_BACKEND == "minio":
        return {
            "endpoint_url": f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}",
            "aws_access_key_id": settings.MINIO_ACCESS_KEY,
            "aws_secret_access_key": settings.MINIO_SECRET_KEY,
        }
    return {
        "region_name": settings.AWS_S3_REGION,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
    }


async def _create_bucket(client, bucket: str) -> None:
    if settings.STORAGE_BACKEND == "s3" and settings.AWS_S3_REGION and settings.AWS_S3_REGION != "us-east-1":
        await client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": settings.AWS_S3_REGION},
        )
    else:
        await client.create_bucket(Bucket=bucket)


class StorageService:
    """Upload asynchrone vers S3/MinIO/local selon STORAGE_BACKEND."""

    @staticmethod
    async def upload_product_image(
        company_id: uuid.UUID,
        product_id: uuid.UUID,
        content: bytes,
        content_type: str,
        filename: str,
    ) -> str:
        """
        Stocke l'image et retourne l'URL publique.
        Valide le type et la taille avant l'upload.
        """
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise StorageError(
                f"Type de fichier non autorisé : {content_type}. "
                f"Formats acceptés : jpeg, png, webp."
            )
        if len(content) > MAX_IMAGE_SIZE_BYTES:
            raise StorageError("L'image dépasse 5 Mo.")

        ext = _ext_for_content_type(content_type)
        object_key = f"companies/{company_id}/products/{product_id}/{uuid.uuid4().hex}{ext}"

        backend = settings.STORAGE_BACKEND
        if backend == "minio":
            return await _upload_minio(object_key, content, content_type, bucket=settings.MINIO_BUCKET_PRODUCTS, public=True)
        if backend == "s3":
            return await _upload_s3(object_key, content, content_type, bucket=settings.AWS_S3_BUCKET, public=True)
        return await _upload_local(object_key, content)

    @staticmethod
    async def upload_receipt_pdf(
        company_id: uuid.UUID,
        receipt_id: uuid.UUID,
        content: bytes,
    ) -> str:
        """Stocke un reçu PDF et retourne son URL publique via l'API."""
        object_key = build_receipt_storage_key(company_id, receipt_id)
        backend = settings.STORAGE_BACKEND
        if backend == "minio":
            await _upload_minio(
                object_key,
                content,
                "application/pdf",
                bucket=settings.MINIO_BUCKET_RECEIPTS,
                public=False,
            )
        elif backend == "s3":
            await _upload_s3(
                object_key,
                content,
                "application/pdf",
                bucket=settings.AWS_S3_BUCKET,
                public=False,
            )
        else:
            await _upload_local(object_key, content)
        return build_receipt_download_url(object_key)

    @staticmethod
    async def get_object(
        object_key: str,
        *,
        bucket_type: str,
    ) -> tuple[bytes, str]:
        """Récupère un objet depuis le backend configuré."""
        backend = settings.STORAGE_BACKEND
        if backend == "minio":
            bucket = settings.MINIO_BUCKET_PRODUCTS if bucket_type == "product" else settings.MINIO_BUCKET_RECEIPTS
            return await _download_minio(object_key, bucket)
        if backend == "s3":
            return await _download_s3(object_key, settings.AWS_S3_BUCKET)
        return await _download_local(object_key)

    @staticmethod
    async def ensure_ready(create_missing: bool = False) -> dict:
        """Vérifie le stockage et crée les buckets si demandé."""
        backend = settings.STORAGE_BACKEND
        if backend == "local":
            base_dir = Path("media")
            (base_dir / "companies").mkdir(parents=True, exist_ok=True)
            (base_dir / "receipts").mkdir(parents=True, exist_ok=True)
            return {"backend": "local", "status": "ok"}

        try:
            import aioboto3
        except ImportError as exc:
            raise StorageError("aioboto3 n'est pas installé.") from exc

        session = aioboto3.Session()
        async with session.client("s3", **_s3_client_kwargs()) as client:
            checked: dict[str, str] = {}
            for bucket in _storage_buckets():
                try:
                    await client.head_bucket(Bucket=bucket)
                    checked[bucket] = "ok"
                except Exception:
                    if not create_missing:
                        raise
                    await _create_bucket(client, bucket)
                    checked[bucket] = "created"
            return {"backend": backend, "status": "ok", "buckets": checked}

    @staticmethod
    async def delete_object(object_key: str) -> None:
        """Supprime un objet du stockage (best-effort, ne lève pas si introuvable)."""
        backend = settings.STORAGE_BACKEND
        try:
            if backend == "minio":
                await _delete_minio(object_key)
            elif backend == "s3":
                await _delete_s3(object_key)
            else:
                await _delete_local(object_key)
        except Exception:
            pass


async def _upload_minio(
    key: str,
    data: bytes,
    content_type: str,
    *,
    bucket: str,
    public: bool,
) -> str:
    try:
        import aioboto3
    except ImportError as exc:
        raise StorageError("aioboto3 n'est pas installé.") from exc

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        await client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            **({"ACL": "public-read"} if public else {}),
        )
    return build_product_image_url(key) if public else build_receipt_download_url(key)


async def _upload_s3(
    key: str,
    data: bytes,
    content_type: str,
    *,
    bucket: str,
    public: bool,
) -> str:
    try:
        import aioboto3
    except ImportError as exc:
        raise StorageError("aioboto3 n'est pas installé.") from exc

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        await client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            **({"ACL": "public-read"} if public else {}),
        )
    return build_product_image_url(key) if public else build_receipt_download_url(key)


async def _download_minio(key: str, bucket: str) -> tuple[bytes, str]:
    try:
        import aioboto3
    except ImportError as exc:
        raise StorageError("aioboto3 n'est pas installé.") from exc

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        response = await client.get_object(Bucket=bucket, Key=key)
        body = await response["Body"].read()
        return body, response.get("ContentType", "application/octet-stream")


async def _download_s3(key: str, bucket: str) -> tuple[bytes, str]:
    try:
        import aioboto3
    except ImportError as exc:
        raise StorageError("aioboto3 n'est pas installé.") from exc

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        response = await client.get_object(Bucket=bucket, Key=key)
        body = await response["Body"].read()
        return body, response.get("ContentType", "application/octet-stream")


async def _delete_minio(key: str) -> None:
    try:
        import aioboto3
    except ImportError:
        return

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        await client.delete_object(Bucket=settings.MINIO_BUCKET_PRODUCTS, Key=key)


async def _delete_s3(key: str) -> None:
    try:
        import aioboto3
    except ImportError:
        return

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as client:
        await client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)


async def _upload_local(key: str, data: bytes) -> str:
    base_dir = Path("media")
    dest = base_dir / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    if key.startswith("companies/"):
        return build_product_image_url(key)
    if key.startswith("receipts/"):
        return build_receipt_download_url(key)
    return f"{settings.API_URL}/media/{key}"


async def _download_local(key: str) -> tuple[bytes, str]:
    path = Path("media") / key
    if not path.exists():
        raise StorageError(f"Objet introuvable: {key}")
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(path.suffix.lower(), "application/octet-stream")
    return path.read_bytes(), content_type


async def _delete_local(key: str) -> None:
    path = Path("media") / key
    if path.exists():
        path.unlink()
