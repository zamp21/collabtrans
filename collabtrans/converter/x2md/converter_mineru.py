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
    model_version: Literal["pipeline", "vlm"] = "vlm"

    def gethash(self) -> Hashable:
        return self.formula_ocr, self.model_version


timeout = httpx.Timeout(
    connect=5.0,  # Connection timeout (maximum time to establish connection)
    read=200.0,  # Read timeout (maximum time to wait for server response)
    write=200.0,  # Write timeout (maximum time to send data)
    pool=1.0  # Timeout to get connection from connection pool
)
# if USE_PROXY:
#     client = httpx.Client(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
#     client_async = httpx.AsyncClient(proxies=get_httpx_proxies(), timeout=timeout, verify=False)
# else:
#     client = httpx.Client(trust_env=False, timeout=timeout, proxy=None, verify=False)
#     client_async = httpx.AsyncClient(trust_env=False, timeout=timeout, proxy=None, verify=False)

limits = httpx.Limits(max_connections=500, max_keepalive_connections=20)
client = httpx.Client(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)
client_async = httpx.AsyncClient(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)


class ConverterMineru(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruConfig):
        super().__init__(config=config)
        self.mineru_token = (config.mineru_token or "").strip()
        self.formula = config.formula_ocr
        self.model_version = config.model_version
        self.attachments: list[AttachMent] = []
        

    def _get_header(self):
        headers = {
            'Content-Type': 'application/json'
        }
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
                {"name": f"{document.name}", "is_ocr": True}
            ]
        }

    def upload(self, document: Document):
        # Get upload URL
        response = client.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # Get
            res_upload = client.put(urls[0], content=document.content)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

    async def upload_async(self, document: Document):
        # Get upload URL
        response = await client_async.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # Get
            res_upload = await client_async.put(urls[0], content=document.content)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

    def get_file_url(self, batch_id: str) -> str:
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
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
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
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
        response = client.get(zip_url)  # Add timeout
        response.raise_for_status()
        print("ZIP file download completed.")
        return embed_inline_image_from_zip(response.content, filename_in_zip=filename_in_zip,
                                           encoding=encoding), response.content


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
        response = await client_async.get(zip_url)  # Add timeout
        response.raise_for_status()
        print("ZIP file download completed.")
        return await asyncio.to_thread(embed_inline_image_from_zip, response.content, filename_in_zip=filename_in_zip,
                                       encoding=encoding), response.content


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
