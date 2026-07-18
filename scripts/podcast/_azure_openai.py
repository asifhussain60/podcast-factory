"""scripts/podcast/_azure_openai.py — Azure OpenAI DALL-E 3 image generation.

Extracted verbatim from _azure.py (R3 DR-005 split, 2026-07-18); behavior unchanged.
_azure.py re-exports every name here, so `import _azure` call sites keep working.
"""

from __future__ import annotations

import json

from _azure_creds import OpenAICreds
from _azure_http import _http

DALLE_API_VERSION = "2024-02-01"
# Standard quality is cheaper; HD costs 2× and is used only when a caller
# explicitly requests it (e.g. the book-illustrate step for cover images).
DALLE_DEFAULT_SIZE = "1792x1024"  # landscape — matches 16:9 video frame
DALLE_DEFAULT_QUALITY = "standard"


def generate_image_dalle(
    creds: OpenAICreds,
    prompt: str,
    *,
    size: str = DALLE_DEFAULT_SIZE,
    quality: str = DALLE_DEFAULT_QUALITY,
    response_format: str = "url",  # "url" or "b64_json"
    revised_prompt_out: list[str] | None = None,
) -> bytes:
    """Generate an image from `prompt` using Azure DALL-E 3. Returns image bytes.

    Azure DALL-E 3 may revise the prompt for safety. If `revised_prompt_out` is
    a list, the revised prompt string is appended to it (so callers can log it
    for the cost ledger without changing the return type).

    Pricing (2026): standard 1792×1024 = $0.080/image, standard 1024×1024 =
    $0.040/image. HD costs 2× per size. For scenic episode images, standard is
    sufficient.

    Note: DALL-E 3 supports `n=1` only (one image per request). For multiple
    images, call this function in a loop.
    """
    url = (
        f"{creds.endpoint}/openai/deployments/{creds.dalle_deployment}"
        f"/images/generations?api-version={DALLE_API_VERSION}"
    )
    payload = json.dumps(
        {
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
            "response_format": response_format,
        }
    ).encode("utf-8")
    status, _, resp_body = _http(
        "POST",
        url,
        headers={
            "api-key": creds.key,
            "Content-Type": "application/json; charset=UTF-8",
        },
        body=payload,
        timeout=120.0,  # DALL-E can take up to 60s
    )
    if status != 200:
        raise RuntimeError(
            f"DALL-E generation failed: HTTP {status}\n{resp_body.decode('utf-8', errors='replace')[:600]}"
        )
    data = json.loads(resp_body)
    item = data.get("data", [{}])[0]
    if revised_prompt_out is not None:
        rp = item.get("revised_prompt", "")
        if rp:
            revised_prompt_out.append(rp)

    if response_format == "b64_json":
        import base64

        b64 = item.get("b64_json", "")
        if not b64:
            raise RuntimeError("DALL-E returned empty b64_json")
        return base64.b64decode(b64)
    else:
        img_url = item.get("url", "")
        if not img_url:
            raise RuntimeError("DALL-E returned no image URL")
        status2, _, img_bytes = _http("GET", img_url, headers={}, timeout=60.0)
        if status2 != 200:
            raise RuntimeError(f"DALL-E image download failed: HTTP {status2}")
        return img_bytes
