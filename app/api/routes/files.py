import alibabacloud_oss_v2 as oss
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_app_settings, get_oss_client
from app.config import Settings
from app.schemas import FileUploadResponse
from app.services import file as file_service


router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=FileUploadResponse)
def upload_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_app_settings),
    client: oss.Client = Depends(get_oss_client),
) -> FileUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    try:
        return file_service.upload_file(
            file=file.file,
            filename=file.filename,
            content_type=file.content_type,
            settings=settings,
            client=client,
        )
    except oss.exceptions.ServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OSS 上传失败：{exc.message}",
        ) from exc
