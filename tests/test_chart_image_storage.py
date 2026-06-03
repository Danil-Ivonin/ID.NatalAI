import pytest


class FakeS3Client:
    def __init__(self) -> None:
        self.uploads = []
        self.presigned_requests = []

    def put_object(self, **kwargs):
        self.uploads.append(kwargs)

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        self.presigned_requests.append(
            {
                "ClientMethod": ClientMethod,
                "Params": Params,
                "ExpiresIn": ExpiresIn,
            }
        )
        return "https://storage.test/generated.png?signature=test"


class FakeSettings:
    chart_image_s3_bucket = "charts"
    chart_image_url_expires_seconds = 3600


@pytest.mark.asyncio
async def test_chart_image_storage_uploads_png_with_cache_and_content_type() -> None:
    from app.services.chart_image_storage import ChartImageStorage

    client = FakeS3Client()
    storage = ChartImageStorage(settings=FakeSettings(), client=client)

    await storage.upload(
        "generations/id/natal-chart.png",
        b"\x89PNG\r\n\x1a\nchart",
        "image/png",
    )

    assert client.uploads == [
        {
            "Bucket": "charts",
            "Key": "generations/id/natal-chart.png",
            "Body": b"\x89PNG\r\n\x1a\nchart",
            "ContentType": "image/png",
            "CacheControl": "private, max-age=86400",
        }
    ]


def test_chart_image_storage_generates_presigned_get_url() -> None:
    from app.services.chart_image_storage import ChartImageStorage

    client = FakeS3Client()
    storage = ChartImageStorage(settings=FakeSettings(), client=client)

    url = storage.presigned_url("generations/id/natal-chart.png")

    assert url == "https://storage.test/generated.png?signature=test"
    assert client.presigned_requests == [
        {
            "ClientMethod": "get_object",
            "Params": {
                "Bucket": "charts",
                "Key": "generations/id/natal-chart.png",
            },
            "ExpiresIn": 3600,
        }
    ]
