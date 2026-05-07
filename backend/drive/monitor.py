import io
import logging

from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)


def list_new_files(service, folder_id: str, processed_ids: set) -> list[dict]:
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType, modifiedTime)",
        orderBy="modifiedTime desc",
    ).execute()

    files = results.get("files", [])
    new = [f for f in files if f["id"] not in processed_ids]
    logger.info("Drive: %d arquivo(s) na pasta, %d novo(s)", len(files), len(new))
    return new


def download_file(service, file_id: str, mime_type: str = "") -> bytes:
    if "vnd.google-apps" in mime_type:
        export_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()
