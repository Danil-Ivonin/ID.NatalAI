from types import SimpleNamespace

from app.services.chart_image_storage import ChartImageStorage


class Client:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def generate_presigned_url(self, *_args, **_kwargs):
        return f"{self.endpoint}/natalai-charts/chart.svg?signature=secret"


def test_presigned_url_uses_public_endpoint() -> None:
    settings = SimpleNamespace(
        chart_image_s3_bucket="natalai-charts",
        chart_image_url_expires_seconds=3600,
        chart_image_s3_endpoint_url="http://minio:9000",
        chart_image_public_endpoint_url="http://localhost:9000",
        chart_image_s3_region="us-east-1",
        chart_image_s3_access_key_id="minioadmin",
        chart_image_s3_secret_access_key="minioadmin",
    )

    assert ChartImageStorage(
        settings,
        client=Client("http://minio:9000"),
        presign_client=Client("http://localhost:9000"),
    ).presigned_url("chart.svg") == (
        "http://localhost:9000/natalai-charts/chart.svg?signature=secret"
    )
