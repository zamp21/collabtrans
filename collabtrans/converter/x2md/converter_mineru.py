# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import time
import zipfile
import logging
from dataclasses import dataclass
from typing import Hashable, Literal

import httpx

logger = logging.getLogger(__name__)

from collabtrans.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from collabtrans.ir.attachment_manager import AttachMent
from collabtrans.ir.document import Document
from collabtrans.ir.markdown_document import MarkdownDocument
from collabtrans.utils.markdown_utils import embed_inline_image_from_zip

URL = 'https://mineru.net/api/v4/file-urls/batch'


@dataclass(kw_only=True)
class ConverterMineruConfig(X2MarkdownConverterConfig):
    mineru_token: str
    formula_ocr: bool = True
    ocr_enabled: bool = True
    model_version: Literal["pipeline", "vlm"] = "vlm"
    base_url: str = "https://mineru.net"

    def gethash(self) -> Hashable:
        return self.formula_ocr, self.ocr_enabled, self.model_version, self.base_url


timeout = httpx.Timeout(
    connect=10.0,   # Connection timeout
    read=600.0,    # Read timeout: 600 seconds for all API calls
    write=300.0,   # Write timeout
    pool=10.0
)
# if USE_PROXY:
#     client = httpx.Client(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
#     client_async = httpx.AsyncClient(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
# else:
#     client = httpx.Client(trust_env=False, timeout=timeout, proxy=None, verify=False)
#     client_async = httpx.AsyncClient(trust_env=False, timeout=timeout, proxy=None, verify=False)

limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
# trust_env=True lets corporate proxies/CA settings take effect if present
client = httpx.Client(limits=limits, trust_env=True, timeout=timeout, verify=False, follow_redirects=True)
client_async = httpx.AsyncClient(limits=limits, trust_env=True, timeout=timeout, verify=False, follow_redirects=True)


class ConverterMineru(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruConfig):
        super().__init__(config=config)
        self.mineru_token = (config.mineru_token or "").strip()
        self.formula = config.formula_ocr
        self.ocr_enabled = config.ocr_enabled
        self.model_version = config.model_version
        self.base_url = config.base_url.rstrip("/")
        self.attachments: list[AttachMent] = []
        

    def _get_header(self):
        headers = {}
        if self.mineru_token:
            headers["Authorization"] = f"Bearer {self.mineru_token}"
        return headers

    def _get_upload_data(self, document: Document):
        return {
            "enable_formula": self.formula,
            "language": "auto",
            "enable_table": True,
            "model_version": self.model_version,
            "files": [
                {"name": f"{document.name}", "is_ocr": self.ocr_enabled}
            ]
        }

    def _is_local_deployment(self) -> bool:
        """Check if this is a local MinerU deployment"""
        local_indicators = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        for indicator in local_indicators:
            if indicator in self.base_url.lower():
                return True
        # Also check for common internal network patterns (192.168.x.x, 10.x.x.x)
        import re
        if re.match(r'https?://(192\.168\.|10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[01]\.)', self.base_url):
            return True
        return False

    def upload(self, document: Document):
        # Detect local deployment first to avoid unnecessary API calls
        if self._is_local_deployment():
            self.logger.info(f"Detected local deployment: {self.base_url}, using local API paths")
            return self._upload_local(document)

        # Try public platform first for non-local deployments
        if self.base_url.endswith("/api/v4"):
            online_path = f"{self.base_url}/file-urls/batch"
        else:
            online_path = f"{self.base_url}/api/v4/file-urls/batch"

        try:
            response = client.post(online_path, headers=self._get_header(), json=self._get_upload_data(document))
            response.raise_for_status()
            result = response.json()
            if result.get("code") == 0:
                batch_id = result["data"]["batch_id"]
                urls = result["data"]["file_urls"]
                res_upload = client.put(urls[0], content=document.content)
                res_upload.raise_for_status()
                return batch_id
        except Exception as e:
            self.logger.warning(f"Public platform API failed: {e}, trying local deployment")
            return self._upload_local(document)

        raise Exception('Failed to upload document to MinerU')

    def _upload_local(self, document: Document):
        """Upload to local MinerU deployment"""
        local_paths = [
            f"{self.base_url}/file_parse",
            f"{self.base_url}/file_parse/",
            f"{self.base_url}/file/parse",
            f"{self.base_url}/file/parse/",
            f"{self.base_url}/api/file/parse",
            f"{self.base_url}/api/file/parse/",
        ]
        
        for upload_url in local_paths:
            try:
                # For local deployment, we need to upload the file directly
                # Create multipart form data
                import io
                
                # Create a file-like object from the document content
                file_content = io.BytesIO(document.content)
                file_content.name = document.name
                
                # Create multipart form data
                data = {
                    "backend": "hybrid-auto-engine",
                    "parse_method": "auto",
                    "formula_enable": self.formula,
                    "table_enable": True,
                    "return_md": True,
                    "return_content_list": True,  # Request structured content for better table handling
                    "is_ocr": self.ocr_enabled
                }
                
                # Send request with file upload
                response = client.post(
                    upload_url,
                    headers=self._get_header(),
                    data=data,
                    files={"files": (document.name, file_content, "application/pdf")}
                )
                response.raise_for_status()
                result = response.json()
                
                # Check if response format is from local deployment
                if result.get("status") == "completed" and result.get("results"):
                    # Local deployment returns results directly
                    # Store the result for later use
                    self.local_result = result
                    return "local_deployment"
                elif result.get("success"):
                    # Legacy local deployment format
                    # Store the result for later use
                    self.local_result = result
                    return "local_deployment"
            except Exception as e:
                # Log the error for debugging
                self.logger.error(f"Failed to upload to {upload_url}: {e}")
                # Try next path
                continue
        
        raise Exception('Failed to upload document to MinerU: all local API paths failed')

    async def upload_async(self, document: Document):
        # Detect local deployment first to avoid unnecessary API calls
        if self._is_local_deployment():
            self.logger.info(f"Detected local deployment: {self.base_url}, using local API paths")
            return await self._upload_local_async(document)

        # Try public platform first for non-local deployments
        if self.base_url.endswith("/api/v4"):
            online_path = f"{self.base_url}/file-urls/batch"
        else:
            online_path = f"{self.base_url}/api/v4/file-urls/batch"

        try:
            response = await client_async.post(online_path, headers=self._get_header(), json=self._get_upload_data(document))
            response.raise_for_status()
            result = response.json()
            if result.get("code") == 0:
                batch_id = result["data"]["batch_id"]
                urls = result["data"]["file_urls"]
                res_upload = await client_async.put(urls[0], content=document.content)
                res_upload.raise_for_status()
                return batch_id
        except Exception as e:
            self.logger.warning(f"Public platform API failed: {e}, trying local deployment")
            return await self._upload_local_async(document)

        raise Exception('Failed to upload document to MinerU')

    async def _upload_local_async(self, document: Document):
        """Upload to local MinerU deployment (async version)"""
        local_paths = [
            f"{self.base_url}/file_parse",
            f"{self.base_url}/file_parse/",
            f"{self.base_url}/file/parse",
            f"{self.base_url}/file/parse/",
            f"{self.base_url}/api/file/parse",
            f"{self.base_url}/api/file/parse/",
        ]

        for upload_url in local_paths:
            try:
                import io

                file_content = io.BytesIO(document.content)
                file_content.name = document.name

                data = {
                    "backend": "hybrid-auto-engine",
                    "parse_method": "auto",
                    "formula_enable": self.formula,
                    "table_enable": True,
                    "return_md": True,
                    "return_content_list": True,  # Request structured content for better table handling
                    "is_ocr": self.ocr_enabled
                }

                response = await client_async.post(
                    upload_url,
                    headers=self._get_header(),
                    data=data,
                    files={"files": (document.name, file_content, "application/pdf")}
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "completed" and result.get("results"):
                    self.local_result = result
                    return "local_deployment"
                elif result.get("success"):
                    self.local_result = result
                    return "local_deployment"
            except Exception as e:
                self.logger.error(f"Failed to upload to {upload_url}: {e}")
                continue

        raise Exception('Failed to upload document to MinerU: all local API paths failed')

    def get_file_url(self, batch_id: str) -> str:
        # For local deployment, the result is already available
        if batch_id == "local_deployment":
            # Local deployment returns results directly
            # We'll return a dummy URL and handle the actual content in the convert method
            return "local_deployment"
        
        # For online service
        while True:
            # Check if base_url already contains /api/v4
            if self.base_url.endswith("/api/v4"):
                url = f'{self.base_url}/extract-results/batch/{batch_id}'
            else:
                url = f'{self.base_url}/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = client.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                file_url = fileinfo["full_zip_url"]
                return file_url
            else:
                time.sleep(3)

    async def get_file_url_async(self, batch_id: str) -> str:
        # For local deployment, the result is already available
        if batch_id == "local_deployment":
            # Local deployment returns results directly
            # We'll return a dummy URL and handle the actual content in the convert method
            return "local_deployment"
        
        # For online service
        while True:
            # Check if base_url already contains /api/v4
            if self.base_url.endswith("/api/v4"):
                url = f'{self.base_url}/extract-results/batch/{batch_id}'
            else:
                url = f'{self.base_url}/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = await client_async.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                file_url = fileinfo["full_zip_url"]
                return file_url
            else:
                await asyncio.sleep(3)

    def convert(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"Converting document to markdown, model_version: {self.model_version}")
        time1 = time.time()
        batch_id = self.upload(document)
        
        # Handle local deployment
        if batch_id == "local_deployment":
            # Local deployment returns results directly
            if hasattr(self, 'local_result') and self.local_result:
                result = self.local_result
                # Check if result is in new format (with results field)
                if result.get('results'):
                    # New format: results are in results field
                    for filename, file_result in result['results'].items():
                        if file_result.get('md_content'):
                            content = file_result['md_content']
                            self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
                            md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
                            return md_document
                # Check if result is in legacy format (with data.markdown field)
                elif result.get('data') and result['data'].get('markdown'):
                    # Legacy format: results are in data.markdown field
                    content = result['data']['markdown']
                    self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
                    md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
                    return md_document
                else:
                    raise Exception('Local deployment returned invalid result format')
            else:
                raise Exception('Local deployment result not found')
        
        # For online service
        file_url = self.get_file_url(batch_id)
        content, mineru_parsed = get_md_from_zip_url_with_inline_images(zip_url=file_url)
        if mineru_parsed:
            self.attachments.append(AttachMent("mineru",Document.from_bytes(content=mineru_parsed, suffix=".zip", stem="mineru")))
        self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
        md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
        return md_document

    async def convert_async(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"Converting document to markdown, model_version: {self.model_version}")
        time1 = time.time()
        batch_id = await self.upload_async(document)
        
        # Handle local deployment
        if batch_id == "local_deployment":
            # Local deployment returns results directly
            if hasattr(self, 'local_result') and self.local_result:
                result = self.local_result
                # Check if result is in new format (with results field)
                if result.get('results'):
                    # New format: results are in results field
                    for filename, file_result in result['results'].items():
                        if file_result.get('md_content'):
                            content = file_result['md_content']
                            self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
                            md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
                            return md_document
                # Check if result is in legacy format (with data.markdown field)
                elif result.get('data') and result['data'].get('markdown'):
                    # Legacy format: results are in data.markdown field
                    content = result['data']['markdown']
                    self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
                    md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
                    return md_document
                else:
                    raise Exception('Local deployment returned invalid result format')
            else:
                raise Exception('Local deployment result not found')
        
        # For online service
        file_url = await self.get_file_url_async(batch_id)
        content, mineru_parsed = await get_md_from_zip_url_with_inline_images_async(zip_url=file_url)
        if mineru_parsed:
            self.attachments.append(AttachMent("mineru",Document.from_bytes(content=mineru_parsed, suffix=".zip", stem="mineru")))
        self.logger.info(f"Document converted to markdown, time taken: {time.time() - time1} seconds")
        md_document = MarkdownDocument.from_bytes(content=content.encode("utf-8"), suffix=".md", stem=document.stem)
        return md_document

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]


def get_md_from_zip_url_with_inline_images(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> tuple[str, bytes]:
    """
    Download and extract content from the specified file in the given ZIP file URL,
    and convert relative path images in the Markdown file to inline Base64 images.

    Args:
        zip_url (str): Download link for the ZIP file.
        filename_in_zip (str): Name of the target Markdown file in the ZIP archive (including path).
                               Defaults to "full.md".
        encoding (str): Expected encoding of the target file. Defaults to "utf-8".
    """
    try:
        print(f"Downloading ZIP file from {zip_url} (using httpx.get)...")
        last_exc = None
        for attempt in range(1, 4):  # retry 3 times with backoff
            try:
                response = client.get(zip_url)
                response.raise_for_status()
                print("ZIP file download completed.")
                return embed_inline_image_from_zip(response.content, filename_in_zip=filename_in_zip,
                                                   encoding=encoding), response.content
            except httpx.RequestError as e:
                last_exc = e
                wait_s = 2 ** attempt
                print(f"Download failed (attempt {attempt}), retrying in {wait_s}s: {e}")
                time.sleep(wait_s)
        raise httpx.RequestError(f"Repeated download failures after retries: {last_exc}")


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP error (httpx): {e.response.status_code} - {e.request.url}\nResponse content: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"Error occurred while downloading ZIP file (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("Error: Downloaded file is not a valid ZIP archive or is corrupted.")
    except UnicodeDecodeError:
        raise Exception(f"Error: Unable to decode file '{filename_in_zip}' content using '{encoding}' encoding.")
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print complete stack trace for debugging
        raise Exception(f"Unknown error occurred: {e}")


async def get_md_from_zip_url_with_inline_images_async(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> tuple[str, bytes]:
    """
    Download and extract content from the specified file in the given ZIP file URL,
    and convert relative path images in the Markdown file to inline Base64 images.

    Args:
        zip_url (str): Download link for the ZIP file.
        filename_in_zip (str): Name of the target Markdown file in the ZIP archive (including path).
                               Defaults to "full.md".
        encoding (str): Expected encoding of the target file. Defaults to "utf-8".

    Returns:
        str : If successful, returns the processed Markdown text content.
    """
    try:
        print(f"Downloading ZIP file from {zip_url} (using httpx.get)...")
        last_exc = None
        for attempt in range(1, 4):
            try:
                response = await client_async.get(zip_url)
                response.raise_for_status()
                print("ZIP file download completed.")
                return await asyncio.to_thread(embed_inline_image_from_zip, response.content, filename_in_zip=filename_in_zip,
                                               encoding=encoding), response.content
            except httpx.RequestError as e:
                last_exc = e
                wait_s = 2 ** attempt
                print(f"Download failed (attempt {attempt}), retrying in {wait_s}s: {e}")
                await asyncio.sleep(wait_s)
        raise httpx.RequestError(f"Repeated download failures after retries: {last_exc}")


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP error (httpx): {e.response.status_code} - {e.request.url}\nResponse content: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"Error occurred while downloading ZIP file (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("Error: Downloaded file is not a valid ZIP archive or is corrupted.")
    except UnicodeDecodeError:
        raise Exception(f"Error: Unable to decode file '{filename_in_zip}' content using '{encoding}' encoding.")
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print complete stack trace for debugging
        raise Exception(f"Unknown error occurred: {e}")


if __name__ == '__main__':
    pass
