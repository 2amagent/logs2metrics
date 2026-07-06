import boto3

from logtriage.ports.object_store import ObjectStore


class S3ObjectStore(ObjectStore):
    """boto3-backed adapter. Works against AWS S3 or any S3-compatible endpoint (e.g. MinIO) via endpoint_url."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ):
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def put_object(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
