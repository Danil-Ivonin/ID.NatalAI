from __future__ import annotations

import anyio
import boto3

from app.core.config import Settings


class ChartImageStorage:
    def __init__(self, settings: Settings, client=None) -> None:
        self.bucket = settings.chart_image_s3_bucket
        self.expires_seconds = settings.chart_image_url_expires_seconds
        self.client = client or boto3.client(
            "s3",
            endpoint_url=settings.chart_image_s3_endpoint_url or None,
            region_name=settings.chart_image_s3_region,
            aws_access_key_id=settings.chart_image_s3_access_key_id or None,
            aws_secret_access_key=settings.chart_image_s3_secret_access_key or None,
        )

    async def upload(self, object_key: str, content: bytes, mime_type: str) -> None:
        await anyio.to_thread.run_sync(
            lambda: self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=content,
                ContentType=mime_type,
                CacheControl="private, max-age=86400",
            )
        )

    def presigned_url(self, object_key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=self.expires_seconds,
        )
