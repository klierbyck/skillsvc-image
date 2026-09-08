#!/usr/bin/env python3
"""通过 SkillSvc 的 GPT Image 与 Nano Banana API 进行上下文感知的图片生成和编辑。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from math import gcd
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

try:
    import requests
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit("Missing dependency: install requests with 'python3 -m pip install requests'") from exc


DEFAULT_BASE_URL = "https://www.skillsvc.cc"
DEFAULT_MODEL = "gpt-image-2"
NANO_MODEL = "nana-banana-2"
MODEL_ALIASES = {
    "gpt": DEFAULT_MODEL,
    "gpt-image": DEFAULT_MODEL,
    DEFAULT_MODEL: DEFAULT_MODEL,
    "banana": NANO_MODEL,
    "nano-banana": NANO_MODEL,
    "nanobanana": NANO_MODEL,
    NANO_MODEL: NANO_MODEL,
}
RATIO_RE = re.compile(r"^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$")
SIZE_RE = re.compile(r"^(\d+)[xX](\d+)$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SUPPORTED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MIME_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
}
MAX_REMOTE_IMAGE_BYTES = 32 * 1024 * 1024


class ImageAPIError(RuntimeError):
    """可由用户处理的 API 或响应错误。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: Path) -> None:
    """加载常规 .env 文件，但不覆盖进程中已有的环境变量。"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"无法读取环境配置文件 {path}：{exc}") from exc
    for line_number, original in enumerate(lines, 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{line_number} 不是有效的 .env 配置项")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not ENV_KEY_RE.fullmatch(key):
            raise ValueError(f"{path}:{line_number} 的环境变量名无效")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


def load_environment(explicit_path: Optional[str]) -> list[str]:
    configured = explicit_path or os.getenv("SKILLSVC_IMAGE_ENV_FILE")
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"环境配置文件不存在：{path}")
        load_env_file(path)
        return [str(path)]

    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    loaded: list[str] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved.is_file() and str(resolved) not in loaded:
            load_env_file(resolved)
            loaded.append(str(resolved))
    return loaded


def normalize_model(value: Optional[str]) -> str:
    raw = (value or os.getenv("IMAGE_MODEL") or DEFAULT_MODEL).strip().lower()
    try:
        return MODEL_ALIASES[raw]
    except KeyError as exc:
        valid = ", ".join(sorted({DEFAULT_MODEL, NANO_MODEL}))
        raise ValueError(f"不支持模型 '{raw}'；可选值：{valid}") from exc


def parse_ratio(value: str) -> tuple[float, float]:
    match = RATIO_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"宽高比 '{value}' 无效；应使用 W:H 格式，例如 16:9")
    width, height = (float(part) for part in match.groups())
    if not width or not height or max(width / height, height / width) > 3:
        raise ValueError("宽高比两边必须为正数，且比例不能超过 3:1")
    return width, height


def parse_exact_size(value: str) -> tuple[int, int]:
    match = SIZE_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"尺寸 '{value}' 无效；应使用 WIDTHxHEIGHT 格式")
    width, height = (int(part) for part in match.groups())
    if width < 256 or height < 256:
        raise ValueError("宽度和高度都不能小于 256 像素")
    if width % 16 or height % 16:
        raise ValueError("宽度和高度都必须是 16 的倍数")
    if max(width / height, height / width) > 3:
        raise ValueError("图片宽高比不能超过 3:1")
    return width, height


def ratio_for_size(width: int, height: int) -> str:
    divisor = gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def size_for_ratio(aspect_ratio: str, image_size: str) -> str:
    ratio_width, ratio_height = parse_ratio(aspect_ratio)
    long_edge = {"1K": 1024, "2K": 2048, "4K": 4096}[image_size]
    if ratio_width >= ratio_height:
        width = long_edge
        height = round((long_edge * ratio_height / ratio_width) / 16) * 16
    else:
        height = long_edge
        width = round((long_edge * ratio_width / ratio_height) / 16) * 16
    return f"{max(width, 256)}x{max(height, 256)}"


def api_key_for(model: str) -> tuple[Optional[str], str]:
    if model == NANO_MODEL:
        return (
            os.getenv("NANO_BANANA_API_KEY")
            or os.getenv("NANOBANANA_API_KEY")
            or os.getenv("NANA_API_KEY"),
            "NANO_BANANA_API_KEY",
        )
    return os.getenv("GPT_IMAGE_API_KEY") or os.getenv("GPT_API_KEY"), "GPT_IMAGE_API_KEY"


def base_url() -> str:
    return (os.getenv("IMAGE_API_BASE_URL") or os.getenv("BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def load_context(values: list[str], files: list[str]) -> list[str]:
    context = [value.strip() for value in values if value.strip()]
    for filename in files:
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"上下文文件不存在：{path}")
        text = path.read_text(encoding="utf-8").strip()
        if text:
            context.append(text)
    return context


def load_session(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None or not path.exists():
        return None
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取会话文件 {path}：{exc}") from exc
    if not isinstance(session, dict) or session.get("version") != 1:
        raise ValueError(f"会话文件无效或版本不受支持：{path}")
    return session


def load_manifest(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None:
        return None
    if not path.exists():
        return {"version": 1, "created_at": utc_now(), "assets": {}}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 manifest {path}：{exc}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("version") != 1
        or not isinstance(manifest.get("assets"), dict)
    ):
        raise ValueError(f"manifest 无效或版本不受支持：{path}")
    return manifest


def manifest_file_path(manifest_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def manifest_record_path(manifest_path: Path, value: Path) -> str:
    """优先在 manifest 中保存可移植的相对路径。"""
    resolved = value.expanduser().resolve()
    try:
        return resolved.relative_to(manifest_path.parent).as_posix()
    except ValueError:
        return str(resolved)


def validate_asset_id(value: str, label: str = "asset ID") -> str:
    if not ASSET_ID_RE.fullmatch(value):
        raise ValueError(
            f"{label} '{value}' 无效；仅允许字母、数字、点、下划线和连字符，最长 128 字符"
        )
    return value


def load_prompt(
    value: Optional[str], filename: Optional[str], manifest_path: Optional[Path]
) -> tuple[str, Optional[Path]]:
    if value and filename:
        raise ValueError("--prompt 与 --prompt-file 只能使用一个")
    if filename:
        path = (
            manifest_file_path(manifest_path, filename)
            if manifest_path
            else Path(filename).expanduser().resolve()
        )
        if not path.is_file():
            raise ValueError(f"提示词文件不存在：{path}")
        prompt = path.read_text(encoding="utf-8").strip()
        if not prompt:
            raise ValueError(f"提示词文件为空：{path}")
        return prompt, path
    if value and value.strip():
        return value.strip(), None
    raise ValueError("需要 --prompt 或 --prompt-file")


def last_output(session: dict[str, Any]) -> Optional[Path]:
    for turn in reversed(session.get("turns", [])):
        output = turn.get("output_image")
        if output:
            return Path(output).expanduser().resolve()
    return None


def compose_prompt(
    command: str,
    prompt: str,
    context: list[str],
    previous_turns: list[dict[str, Any]],
) -> str:
    labels = {
        "generate": "图片生成要求：",
        "reference": "结合视觉参考的新图片生成要求：",
        "edit": "图片编辑要求：",
    }
    sections = [labels[command], prompt.strip()]
    if context:
        sections.extend(["相关上下文：", "\n\n".join(context)])
    if command == "edit":
        if previous_turns:
            history = [turn.get("prompt", "").strip() for turn in previous_turns if turn.get("prompt")]
            if history:
                sections.extend(["此前的图片要求与编辑记录：", "\n".join(f"- {item}" for item in history)])
        sections.append("以提供的图片为编辑源图，并保持本轮未指定修改的元素不变。")
    elif command == "reference":
        sections.append(
            "提供的图片只作为指定特征的视觉参考。请生成一张采用全新构图的新图片，"
            "不要把任务当作对参考图本身的编辑。"
        )
    return "\n\n".join(sections)


def error_text(response: requests.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str):
            return error
    except (ValueError, TypeError):
        pass
    return response.text[:1000] or str(response.status_code)


def checked_json(response: requests.Response) -> dict[str, Any]:
    if response.status_code < 200 or response.status_code >= 300:
        raise ImageAPIError(f"HTTP {response.status_code}：{error_text(response)}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ImageAPIError(f"API 响应不是 JSON：{response.text[:500]}") from exc
    if not isinstance(payload, dict):
        raise ImageAPIError("API 响应的根节点不是对象")
    return payload


def decode_data_url(value: str) -> Optional[tuple[bytes, str]]:
    if not value.startswith("data:") or ";base64," not in value:
        return None
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0]
    return base64.b64decode(encoded), mime


def origin(value: str) -> tuple[str, str, Optional[int]]:
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    port = parsed.port or ({"http": 80, "https": 443}.get(scheme))
    return scheme, (parsed.hostname or "").lower(), port


def download_image(
    image_url: str,
    api_base_url: str,
    key: str,
    timeout: int,
) -> tuple[bytes, str]:
    parsed = urlsplit(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ImageAPIError("图片下载地址不是有效的 HTTP(S) URL")
    same_origin = origin(image_url) == origin(api_base_url)
    if parsed.scheme != "https" and not (
        same_origin and parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ImageAPIError("拒绝通过非 HTTPS 地址下载远程图片")
    headers = {"Authorization": f"Bearer {key}"} if same_origin else {}
    response = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
    try:
        if response.status_code < 200 or response.status_code >= 300:
            raise ImageAPIError(
                f"图片下载失败，HTTP {response.status_code}：{error_text(response)}"
            )
        final_url = getattr(response, "url", image_url)
        final_parsed = urlsplit(final_url)
        if final_parsed.scheme != "https" and not (
            origin(final_url) == origin(api_base_url)
            and final_parsed.hostname
            and final_parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ImageAPIError("拒绝通过非 HTTPS 重定向下载远程图片")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_REMOTE_IMAGE_BYTES:
                    raise ImageAPIError("远程图片超过 32 MB 限制")
            except ValueError:
                pass
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_REMOTE_IMAGE_BYTES:
                raise ImageAPIError("远程图片超过 32 MB 限制")
            chunks.append(chunk)
        mime = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0]
        return b"".join(chunks), mime
    finally:
        response.close()


def extract_gpt_image(
    payload: dict[str, Any], key: str, timeout: int, expected_mime: str, api_base_url: str
) -> tuple[bytes, str]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ImageAPIError("图片响应中没有 data 列表")
    for item in data:
        if not isinstance(item, dict):
            continue
        for field in ("b64_json", "base64", "image_b64"):
            encoded = item.get(field)
            if encoded:
                decoded = decode_data_url(encoded)
                if decoded:
                    return decoded
                try:
                    return base64.b64decode(encoded, validate=True), expected_mime
                except (ValueError, TypeError) as exc:
                    raise ImageAPIError(f"字段 '{field}' 中的 base64 图片无效") from exc
        url = item.get("url")
        if url:
            return download_image(str(url), api_base_url, key, timeout)
    raise ImageAPIError("API 响应中没有图片数据")


def call_gpt(
    prompt: str,
    sources: list[Path],
    size: str,
    quality: str,
    output_format: str,
    compression: int,
    key: str,
    url: str,
    timeout: int,
) -> tuple[bytes, str, str]:
    fields: dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "output_format": output_format,
    }
    if output_format in {"jpeg", "webp"}:
        fields["output_compression"] = compression
    headers = {"Authorization": f"Bearer {key}"}
    if sources:
        endpoint = f"{url}/v1/images/edits"
        with ExitStack() as stack:
            files = []
            for source in sources:
                mime = source_image_mime(source)
                image_file = stack.enter_context(source.open("rb"))
                files.append(("image", (source.name, image_file, mime)))
            response = requests.post(
                endpoint,
                headers=headers,
                data={name: str(value) for name, value in fields.items()},
                files=files,
                timeout=timeout,
            )
    else:
        endpoint = f"{url}/v1/images/generations"
        response = requests.post(
            endpoint,
            headers={**headers, "Content-Type": "application/json"},
            json=fields,
            timeout=timeout,
        )
    image, mime = extract_gpt_image(
        checked_json(response), key, timeout, f"image/{output_format}", url
    )
    return image, mime, endpoint


def call_nano(
    prompt: str,
    sources: list[Path],
    aspect_ratio: str,
    image_size: str,
    key: str,
    url: str,
    timeout: int,
) -> tuple[bytes, str, str]:
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for source in sources:
        mime = source_image_mime(source)
        parts.append({
            "inlineData": {
                "mimeType": mime,
                "data": base64.b64encode(source.read_bytes()).decode("ascii"),
            }
        })
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": aspect_ratio, "imageSize": image_size},
        },
    }
    endpoint = f"{url}/v1beta/models/{NANO_MODEL}:generateContent"
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    result = checked_json(response)
    for candidate in result.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                try:
                    return base64.b64decode(inline["data"]), mime, endpoint
                except (ValueError, TypeError) as exc:
                    raise ImageAPIError("Nano Banana 返回的 base64 图片数据无效") from exc
    raise ImageAPIError("Nano Banana 响应中没有图片数据")


def canonical_extension(value: str) -> str:
    normalized = value.lower().lstrip(".")
    return "jpeg" if normalized == "jpg" else normalized


def detected_image_extension(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return None


def source_image_mime(path: Path) -> str:
    with path.open("rb") as handle:
        extension = detected_image_extension(handle.read(12))
    if extension is None:
        raise ValueError(f"输入文件不是受支持的 PNG、JPEG 或 WebP 图片：{path}")
    return {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }[extension]


def validated_image_extension(data: bytes, mime: str) -> str:
    detected = detected_image_extension(data)
    if detected is None:
        raise ImageAPIError("API 返回的数据不是受支持的 PNG、JPEG 或 WebP 图片")
    declared = MIME_EXTENSIONS.get(mime.split(";", 1)[0].lower())
    if declared and canonical_extension(declared) != canonical_extension(detected):
        raise ImageAPIError(f"API 返回的图片格式与 Content-Type 不一致：{mime} / {detected}")
    return detected


def requested_output_path(output_dir: Path, requested: str, extension: str) -> Path:
    candidate = Path(requested).expanduser()
    if not candidate.is_absolute():
        candidate = output_dir / candidate
    suffix = candidate.suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_IMAGE_EXTENSIONS or canonical_extension(suffix) != canonical_extension(extension):
        candidate = candidate.with_suffix(f".{extension}")
    return candidate.resolve()


def unique_output_path(output_dir: Path, requested: Optional[str], extension: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if requested:
        candidate = requested_output_path(output_dir, requested, extension)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.exists():
            raise ValueError(f"拒绝覆盖已有输出文件：{candidate}")
        return candidate
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return (output_dir / f"image_{stamp}.{extension}").resolve()


def validate_requested_output(output_dir: Path, requested: Optional[str], extension: str) -> None:
    """在付费 API 调用前检查显式输出路径，避免调用完成后才发现冲突。"""
    if not requested:
        return
    candidate = requested_output_path(output_dir, requested, extension)
    if candidate.exists():
        raise ValueError(f"拒绝覆盖已有输出文件：{candidate}")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="直接的生成或编辑指令")
    parser.add_argument("--prompt-file", help="包含完整生成或编辑指令的 UTF-8 文件")
    parser.add_argument("--context", action="append", default=[], help="相关上下文；可重复传入")
    parser.add_argument("--context-file", action="append", default=[], help="UTF-8 上下文文件；可重复传入")
    parser.add_argument("--model", help="gpt-image-2（默认）或 nana-banana-2")
    parser.add_argument("--aspect-ratio", help="目标宽高比，例如 16:9（默认）")
    parser.add_argument("--image-size", choices=("1K", "2K", "4K"), help="图片尺寸档位（默认：2K）")
    parser.add_argument("--size", help="GPT 精确像素尺寸，例如 2048x1152")
    parser.add_argument("--quality", choices=("auto", "low", "medium", "high"), help="GPT 渲染质量（默认：auto）")
    parser.add_argument("--output-format", choices=("png", "jpeg", "webp"), help="GPT 输出格式")
    parser.add_argument("--compression", type=int, help="JPEG/WebP 压缩参数 0-100（默认：100）")
    parser.add_argument("--output-dir", help="输出图片和默认会话文件所在目录")
    parser.add_argument("--output", help="输出文件名或路径；不会覆盖已有文件")
    parser.add_argument("--session", help="要创建或继续使用的会话 JSON 路径")
    parser.add_argument("--manifest", help="generation-manifest.json 路径；需与 --asset-id 同时使用")
    parser.add_argument("--asset-id", help="manifest 中稳定且唯一的资产 ID")
    parser.add_argument("--asset-role", help="资产用途，例如 cover 或 content-card")
    parser.add_argument("--env-file", help="指定 .env 文件（默认读取当前目录或技能目录）")
    parser.add_argument("--timeout", type=int, default=600, help="HTTP 超时秒数")
    parser.add_argument("--dry-run", action="store_true", help="不访问 API，仅校验并输出请求计划")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="根据文本和上下文生成图片")
    add_common_options(generate)
    reference = subparsers.add_parser("reference", help="结合视觉参考生成一张新图片")
    add_common_options(reference)
    reference.add_argument("--image", action="append", default=[], help="参考图片；可重复传入")
    reference.add_argument("--reference-asset-id", help="从 manifest 读取作为视觉锚点的资产 ID")
    edit = subparsers.add_parser("edit", help="编辑图片并保留会话上下文")
    add_common_options(edit)
    edit.add_argument("--image", help="编辑源图；会话已有上次输出时可省略")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    loaded_env_files = load_environment(args.env_file)

    if bool(args.manifest) != bool(args.asset_id):
        raise ValueError("--manifest 与 --asset-id 必须同时使用")
    if args.asset_role and not args.asset_id:
        raise ValueError("--asset-role 仅能与 --manifest 和 --asset-id 一起使用")

    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else None
    manifest = load_manifest(manifest_path)
    asset_id = validate_asset_id(args.asset_id) if args.asset_id else None
    reference_asset_id = getattr(args, "reference_asset_id", None)
    if reference_asset_id:
        validate_asset_id(reference_asset_id, "reference asset ID")
        if not manifest_path or manifest is None:
            raise ValueError("--reference-asset-id 需要同时使用 --manifest 和 --asset-id")
        if reference_asset_id == asset_id:
            raise ValueError("资产不能把自身作为 reference_asset_id")

    assets = manifest["assets"] if manifest is not None else {}
    existing_asset = assets.get(asset_id) if asset_id else None
    if existing_asset is not None and not isinstance(existing_asset, dict):
        raise ValueError(f"manifest 资产记录无效：{asset_id}")
    if args.command == "edit" and manifest is not None and existing_asset is None:
        raise ValueError(f"manifest 中不存在可编辑资产：{asset_id}")
    if args.command in {"generate", "reference"} and existing_asset is not None:
        raise ValueError(f"manifest 中的 asset_id 已存在：{asset_id}")
    if (
        existing_asset
        and args.asset_role
        and existing_asset.get("role")
        and existing_asset["role"] != args.asset_role
    ):
        raise ValueError(
            f"资产 {asset_id} 的 role 已是 {existing_asset['role']}，不能改为 {args.asset_role}"
        )

    explicit_session_path = Path(args.session).expanduser().resolve() if args.session else None
    if args.command == "edit" and existing_asset is not None:
        stored_session = existing_asset.get("session")
        if not isinstance(stored_session, str) or not stored_session:
            raise ValueError(f"manifest 资产 {asset_id} 没有可用的 session")
        assert manifest_path is not None
        manifest_session_path = manifest_file_path(manifest_path, stored_session)
        if explicit_session_path and explicit_session_path != manifest_session_path:
            raise ValueError("--session 与 manifest 中该资产的 session 不一致")
        session_path = manifest_session_path
    else:
        session_path = explicit_session_path

    session = load_session(session_path)
    if args.command == "edit" and existing_asset is not None and session is None:
        raise ValueError(f"manifest 资产 {asset_id} 的 session 文件不存在：{session_path}")

    prompt, prompt_file = load_prompt(args.prompt, args.prompt_file, manifest_path)
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    elif session_path:
        output_dir = session_path.parent
    elif manifest_path:
        output_dir = manifest_path.parent
    else:
        output_dir = (Path.cwd() / "generated_images").resolve()
    if args.command in {"generate", "reference"} and session:
        raise ValueError(f"{args.command} 不能继续已有会话；请改用 edit")

    previous_params = session.get("parameters", {}) if session else {}
    model = normalize_model(args.model or (session or {}).get("model"))
    if args.size and (args.aspect_ratio or args.image_size):
        raise ValueError("--size 不能与 --aspect-ratio 或 --image-size 同时使用")
    if model == NANO_MODEL:
        if args.size:
            raise ValueError("--size 仅适用于 GPT；Nano Banana 请使用 --aspect-ratio 和 --image-size")
        if args.quality is not None:
            raise ValueError("--quality 仅适用于 GPT，Nano Banana 不支持")
        if args.compression is not None:
            raise ValueError("--compression 仅适用于 GPT，Nano Banana 不支持")
        if args.output_format and args.output_format != "png":
            raise ValueError("Nano Banana 当前只输出 PNG，不支持其他 --output-format")

    previous_size = previous_params.get("size")
    if args.size:
        width, height = parse_exact_size(args.size)
        size = f"{width}x{height}"
        aspect_ratio = ratio_for_size(width, height)
        image_size: Optional[str] = None
    elif args.aspect_ratio or args.image_size or not previous_size:
        aspect_ratio = (
            args.aspect_ratio or previous_params.get("aspect_ratio") or "16:9"
        )
        parse_ratio(aspect_ratio)
        image_size = args.image_size or previous_params.get("image_size") or "2K"
        size = size_for_ratio(aspect_ratio, image_size)
    else:
        size = str(previous_size)
        width, height = parse_exact_size(size)
        aspect_ratio = previous_params.get("aspect_ratio") or ratio_for_size(width, height)
        parse_ratio(aspect_ratio)
        image_size = previous_params.get("image_size")
    if model == NANO_MODEL and image_size is None:
        image_size = args.image_size or "2K"

    quality = args.quality or previous_params.get("quality") or "auto"
    output_format = (
        "png"
        if model == NANO_MODEL
        else (args.output_format or previous_params.get("output_format") or "png")
    )
    compression = args.compression
    if compression is None:
        compression = previous_params.get("compression", 100)
    if not 0 <= compression <= 100:
        raise ValueError("压缩参数必须在 0 到 100 之间")
    if args.timeout <= 0:
        raise ValueError("超时时间必须是正数")

    new_context = load_context(args.context, args.context_file)
    recorded_context = list((session or {}).get("context", []))
    combined_context = recorded_context + [item for item in new_context if item not in recorded_context]
    previous_turns = list((session or {}).get("turns", []))
    effective_prompt = compose_prompt(args.command, prompt, combined_context, previous_turns)

    source_images: list[Path] = []
    direct_reference_images: list[Path] = []
    reference_asset_image: Optional[Path] = None
    if args.command == "edit":
        source = Path(args.image).expanduser().resolve() if args.image else (last_output(session) if session else None)
        if not source or not source.is_file():
            raise ValueError("edit 需要 --image，或需要一个包含已有输出图片的会话")
        source_images = [source]
    elif args.command == "reference":
        direct_reference_images = [Path(item).expanduser().resolve() for item in args.image]
        missing = [str(path) for path in direct_reference_images if not path.is_file()]
        if missing:
            raise ValueError(f"参考图片不存在：{missing[0]}")
        source_images = list(direct_reference_images)
        if reference_asset_id:
            reference_asset = assets.get(reference_asset_id)
            if not isinstance(reference_asset, dict):
                raise ValueError(f"manifest 中不存在参考资产：{reference_asset_id}")
            if reference_asset.get("status") not in {None, "complete"}:
                raise ValueError(f"参考资产尚未完成：{reference_asset_id}")
            stored_image = reference_asset.get("image")
            if not isinstance(stored_image, str) or not stored_image:
                raise ValueError(f"参考资产没有可用图片：{reference_asset_id}")
            assert manifest_path is not None
            reference_asset_image = manifest_file_path(manifest_path, stored_image)
            if not reference_asset_image.is_file():
                raise ValueError(f"参考资产图片不存在：{reference_asset_image}")
            if reference_asset_image not in source_images:
                source_images.append(reference_asset_image)
        if not source_images:
            raise ValueError("reference 需要 --image 或 --reference-asset-id")
    for source in source_images:
        if source.stat().st_size > 4 * 1024 * 1024:
            raise ValueError(f"输入图片超过服务的 4 MB 限制：{source}")
        source_image_mime(source)

    url = base_url()
    endpoint = (
        f"{url}/v1beta/models/{NANO_MODEL}:generateContent"
        if model == NANO_MODEL
        else f"{url}/v1/images/{'edits' if source_images else 'generations'}"
    )
    if model == NANO_MODEL:
        parameters = {
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "output_format": "png",
        }
    else:
        parameters = {
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "compression": compression,
        }
    expected_extension = "png" if model == NANO_MODEL else output_format
    validate_requested_output(output_dir, args.output, expected_extension)
    if session_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_path = (output_dir / f"session_{stamp}.json").resolve()
    if args.dry_run:
        return {
            "dry_run": True,
            "command": args.command,
            "model": model,
            "endpoint": endpoint,
            "source_image": str(source_images[0]) if len(source_images) == 1 else None,
            "source_images": [str(source) for source in source_images],
            "session": str(session_path),
            "manifest": str(manifest_path) if manifest_path else None,
            "asset_id": asset_id,
            "asset_role": args.asset_role or (existing_asset or {}).get("role"),
            "reference_asset_id": reference_asset_id,
            "reference_asset_image": (
                str(reference_asset_image) if reference_asset_image else None
            ),
            "prompt_file": str(prompt_file) if prompt_file else None,
            "env_files": loaded_env_files,
            "parameters": parameters,
            "planned_output": (
                str(requested_output_path(output_dir, args.output, expected_extension))
                if args.output
                else None
            ),
            "effective_prompt": effective_prompt,
        }

    key, key_name = api_key_for(model)
    if not key:
        raise ValueError(f"缺少 API Key：请在环境变量中设置 {key_name}")

    started = time.monotonic()
    if model == NANO_MODEL:
        image_data, mime, endpoint = call_nano(
            effective_prompt, source_images, aspect_ratio, image_size, key, url, args.timeout
        )
    else:
        image_data, mime, endpoint = call_gpt(
            effective_prompt,
            source_images,
            size,
            quality,
            output_format,
            compression,
            key,
            url,
            args.timeout,
        )
    elapsed = round(time.monotonic() - started, 3)
    extension = validated_image_extension(image_data, mime)
    output_path = unique_output_path(output_dir, args.output, extension)
    output_path.write_bytes(image_data)

    if session is None:
        session = {
            "version": 1,
            "id": str(uuid.uuid4()),
            "created_at": utc_now(),
            "context": combined_context,
            "turns": [],
        }
    session.update({
        "updated_at": utc_now(),
        "model": model,
        "base_url": url,
        "context": combined_context,
        "parameters": parameters,
    })
    session["turns"].append({
        "type": args.command,
        "created_at": utc_now(),
        "prompt": prompt,
        "effective_prompt": effective_prompt,
        "input_image": str(source_images[0]) if args.command == "edit" else None,
        "input_images": [str(source) for source in source_images],
        "output_image": str(output_path),
        "mime_type": mime,
        "parameters": parameters,
    })
    write_json_atomic(session_path, session)

    if manifest is not None:
        assert manifest_path is not None and asset_id is not None
        record = dict(existing_asset or {})
        record.setdefault("created_at", utc_now())
        role = args.asset_role or record.get("role")
        if role:
            record["role"] = role
        if prompt_file:
            record["prompt_file"] = manifest_record_path(manifest_path, prompt_file)
            record.pop("prompt", None)
        else:
            record["prompt"] = prompt
            record.pop("prompt_file", None)
        record.update({
            "action": args.command,
            "image": manifest_record_path(manifest_path, output_path),
            "session": manifest_record_path(manifest_path, session_path),
            "model": model,
            "parameters": parameters,
            "status": "complete",
            "updated_at": utc_now(),
        })
        if args.command == "reference":
            record["reference_images"] = [
                manifest_record_path(manifest_path, path) for path in direct_reference_images
            ]
            if reference_asset_id:
                record["reference_asset_id"] = reference_asset_id
            else:
                record.pop("reference_asset_id", None)
        assets[asset_id] = record
        manifest["updated_at"] = utc_now()
        write_json_atomic(manifest_path, manifest)

    return {
        "image": str(output_path),
        "requested_output": args.output,
        "session": str(session_path),
        "manifest": str(manifest_path) if manifest_path else None,
        "asset_id": asset_id,
        "model": model,
        "endpoint": endpoint,
        "env_files": loaded_env_files,
        "parameters": parameters,
        "mime_type": mime,
        "bytes": len(image_data),
        "elapsed_seconds": elapsed,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, requests.RequestException, ImageAPIError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
