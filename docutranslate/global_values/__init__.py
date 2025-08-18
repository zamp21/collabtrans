import os

from .conditional_import import available_packages, conditional_import

USE_PROXY = True if (os.getenv("DOCUTRANSLATE_PROXY_ENABLED") and os.getenv(
    "DOCUTRANSLATE_PROXY_ENABLED").lower() == "true") else False

print(f"USE_PROXY:{USE_PROXY}")
