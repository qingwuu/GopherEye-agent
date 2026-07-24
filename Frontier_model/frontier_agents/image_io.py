from __future__ import annotations

import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote, urlparse


def file_uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Not a file URI: {uri}")
    path_text = unquote(parsed.path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:/", path_text):
        path_text = path_text[1:]
    return Path(path_text)


def resolve_image_path(image_ref: str) -> Path:
    if image_ref.startswith("file://"):
        return file_uri_to_path(image_ref)
    return Path(image_ref).expanduser()


def image_ref_to_data_url(image_ref: str) -> str:
    if image_ref.startswith(("http://", "https://", "data:")):
        return image_ref

    path = resolve_image_path(image_ref)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Cannot encode missing image: {image_ref}")

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def image_ref_to_anthropic_block(image_ref: str) -> Dict[str, Any]:
    if image_ref.startswith(("http://", "https://")):
        return {
            "type": "image",
            "source": {"type": "url", "url": image_ref},
        }

    data_url = image_ref_to_data_url(image_ref)
    match = re.match(r"^data:([^;]+);base64,(.*)$", data_url, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Unsupported image reference for Anthropic: {image_ref}")
    media_type, data = match.groups()
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }
