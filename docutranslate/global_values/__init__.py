import os

from .conditional_import import available_packages, conditional_import

USE_PROXY = True if (os.getenv("DOCUTRANSLATE_USE_PROXY") and os.getenv(
    "DOCUTRANSLATE_USE_PROXY").lower() == "true") else False
