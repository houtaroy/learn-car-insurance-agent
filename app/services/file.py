from datetime import date
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote
from uuid import uuid4

import alibabacloud_oss_v2 as oss

from app.config import Settings
from app.schemas import FileUploadResponse


def upload_file(
    file: BinaryIO,
    filename: str,
    content_type: str | None,
    settings: Settings,
    client: oss.Client,
) -> FileUploadResponse:
    suffix = Path(filename).suffix
    date_prefix = date.today().strftime("%Y/%m/%d")
    object_key = f"{date_prefix}/{uuid4().hex}{suffix}"

    client.put_object(
        oss.PutObjectRequest(
            bucket=settings.oss_bucket,
            key=object_key,
            body=file,
            content_type=content_type,
        )
    )

    encoded_key = quote(object_key, safe="/")
    url = (
        f"https://{settings.oss_bucket}."
        f"oss-{settings.oss_region}.aliyuncs.com/{encoded_key}"
    )
    return FileUploadResponse(
        url=url,
    )
