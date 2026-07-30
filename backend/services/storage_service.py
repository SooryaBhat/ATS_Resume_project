"""
storage_service.py — Supabase Storage upload/download helpers.

Handles:
  - Uploading resume files to the 'resumes' bucket
  - Uploading generated PDF reports to the 'pdf_reports' bucket
  - Generating signed URLs for secure file downloads
"""

import logging
from typing import Optional
import httpx

from backend.core.config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger('ats_resume_scorer')


def _storage_base() -> str:
    return f"{SUPABASE_URL.rstrip('/')}/storage/v1"


def _auth_headers() -> dict:
    return {
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }


async def upload_resume_file(
    user_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str = 'application/pdf',
) -> Optional[str]:
    """
    Upload a resume file to the 'resumes' storage bucket.
    Returns the storage path (e.g. '{user_id}/{filename}') or None on failure.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning('Supabase credentials not configured — skipping storage upload.')
        return None

    storage_path = f'{user_id}/{filename}'
    url = f"{_storage_base()}/object/resumes/{storage_path}"

    headers = {
        **_auth_headers(),
        'Content-Type': content_type,
        'x-upsert': 'true',   # overwrite if same filename exists
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, content=file_bytes, headers=headers)
            if resp.status_code in (200, 201):
                logger.info(f'Uploaded resume to storage: {storage_path}')
                return storage_path
            logger.error(f'Storage upload failed ({resp.status_code}): {resp.text}')
            return None
    except Exception as exc:
        logger.error(f'upload_resume_file exception: {exc}')
        return None


async def upload_pdf_report(
    user_id: str,
    pdf_bytes: bytes,
    filename: str,
) -> Optional[str]:
    """
    Upload a generated PDF report to the 'pdf_reports' storage bucket.
    Returns the storage path or None on failure.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    storage_path = f'{user_id}/{filename}'
    url = f"{_storage_base()}/object/pdf_reports/{storage_path}"

    headers = {
        **_auth_headers(),
        'Content-Type': 'application/pdf',
        'x-upsert': 'true',
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, content=pdf_bytes, headers=headers)
            if resp.status_code in (200, 201):
                logger.info(f'Uploaded PDF report to storage: {storage_path}')
                return storage_path
            logger.error(f'PDF storage upload failed ({resp.status_code}): {resp.text}')
            return None
    except Exception as exc:
        logger.error(f'upload_pdf_report exception: {exc}')
        return None


async def get_signed_url(bucket: str, storage_path: str, expires_in: int = 3600) -> Optional[str]:
    """
    Generate a time-limited signed URL for private file access.
    Returns the signed URL string or None on failure.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = f"{_storage_base()}/object/sign/{bucket}/{storage_path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={'expiresIn': expires_in},
                headers={**_auth_headers(), 'Content-Type': 'application/json'},
            )
            if resp.status_code == 200:
                data = resp.json()
                signed_path = data.get('signedURL', '')
                return f"{SUPABASE_URL.rstrip('/')}/storage/v1{signed_path}"
            logger.error(f'Signed URL generation failed ({resp.status_code}): {resp.text}')
            return None
    except Exception as exc:
        logger.error(f'get_signed_url exception: {exc}')
        return None


async def download_file(bucket: str, storage_path: str) -> Optional[bytes]:
    """
    Download a file from Supabase Storage by path.
    Used for serving stored PDFs.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = f"{_storage_base()}/object/{bucket}/{storage_path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=_auth_headers())
            if resp.status_code == 200:
                return resp.content
            logger.error(f'Storage download failed ({resp.status_code}): {resp.text}')
            return None
    except Exception as exc:
        logger.error(f'download_file exception: {exc}')
        return None
