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
        return "https://storage.test/generated.svg?signature=test"


class FakeSettings:
    chart_image_s3_bucket = "charts"
    chart_image_url_expires_seconds = 3600


@pytest.mark.asyncio
async def test_chart_image_storage_uploads_svg_with_cache_and_content_type() -> None:
    from app.services.chart_image_storage import ChartImageStorage

    client = FakeS3Client()
    storage = ChartImageStorage(settings=FakeSettings(), client=client)

    await storage.upload(
        "generations/id/natal-chart.svg",
        b"<svg>chart</svg>",
        "image/svg+xml",
    )

    assert client.uploads == [
        {
            "Bucket": "charts",
            "Key": "generations/id/natal-chart.svg",
            "Body": b"<svg>chart</svg>",
            "ContentType": "image/svg+xml",
            "CacheControl": "private, max-age=86400",
        }
    ]


def test_chart_image_storage_generates_presigned_get_url() -> None:
    from app.services.chart_image_storage import ChartImageStorage

    client = FakeS3Client()
    storage = ChartImageStorage(settings=FakeSettings(), client=client)

    url = storage.presigned_url("generations/id/natal-chart.svg")

    assert url == "https://storage.test/generated.svg?signature=test"
    assert client.presigned_requests == [
        {
            "ClientMethod": "get_object",
            "Params": {
                "Bucket": "charts",
                "Key": "generations/id/natal-chart.svg",
            },
            "ExpiresIn": 3600,
        }
    ]
