#!/usr/bin/env python3
"""通过 SkillSvc 的 GPT Image 与 Nano Banana API 进行上下文感知的图片生成和编辑。"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def load_environment(explicit_path: str | None) -> list[str]:
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


def normalize_model(value: str | None) -> str:
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


def api_key_for(model: str) -> tuple[str | None, str]:
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


def load_session(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取会话文件 {path}：{exc}") from exc
    if not isinstance(session, dict) or session.get("version") != 1:
        raise ValueError(f"会话文件无效或版本不受支持：{path}")
    return session


def last_output(session: dict[str, Any]) -> Path | None:
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


def decode_data_url(value: str) -> tuple[bytes, str] | None:
    if not value.startswith("data:") or ";base64," not in value:
        return None
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0]
    return base64.b64decode(encoded), mime


def extract_gpt_image(
    payload: dict[str, Any], key: str, timeout: int, expected_mime: str
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
            response = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
            if response.status_code < 200 or response.status_code >= 300:
                raise ImageAPIError(f"图片下载失败，HTTP {response.status_code}：{error_text(response)}")
            return response.content, response.headers.get("Content-Type", "image/png").split(";", 1)[0]
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
                mime = mimetypes.guess_type(source.name)[0] or "image/png"
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
        checked_json(response), key, timeout, f"image/{output_format}"
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
        mime = mimetypes.guess_type(source.name)[0] or "image/png"
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


def extension_for(mime: str, fallback: str) -> str:
    normalized = mime.split(";", 1)[0].lower()
    return {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}.get(normalized, fallback)


def unique_output_path(output_dir: Path, requested: str | None, extension: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if requested:
        candidate = Path(requested).expanduser()
        if not candidate.is_absolute():
            candidate = output_dir / candidate
        if candidate.suffix.lower().lstrip(".") not in {"png", "jpg", "jpeg", "webp"}:
            candidate = candidate.with_suffix(f".{extension}")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.exists():
            raise ValueError(f"拒绝覆盖已有输出文件：{candidate.resolve()}")
        return candidate.resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return (output_dir / f"image_{stamp}.{extension}").resolve()


def validate_requested_output(output_dir: Path, requested: str | None, extension: str) -> None:
    """在付费 API 调用前检查显式输出路径，避免调用完成后才发现冲突。"""
    if not requested:
        return
    candidate = Path(requested).expanduser()
    if not candidate.is_absolute():
        candidate = output_dir / candidate
    if candidate.suffix.lower().lstrip(".") not in {"png", "jpg", "jpeg", "webp"}:
        candidate = candidate.with_suffix(f".{extension}")
    if candidate.exists():
        raise ValueError(f"拒绝覆盖已有输出文件：{candidate.resolve()}")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", required=True, help="直接的生成或编辑指令")
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
    reference.add_argument("--image", action="append", required=True, help="参考图片；可重复传入")
    edit = subparsers.add_parser("edit", help="编辑图片并保留会话上下文")
    add_common_options(edit)
    edit.add_argument("--image", help="编辑源图；会话已有上次输出时可省略")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    loaded_env_files = load_environment(args.env_file)
    session_path = Path(args.session).expanduser().resolve() if args.session else None
    session = load_session(session_path)
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    elif session_path:
        output_dir = session_path.parent
    else:
        output_dir = (Path.cwd() / "generated_images").resolve()
    if args.command in {"generate", "reference"} and session:
        raise ValueError(f"{args.command} 不能继续已有会话；请改用 edit")

    previous_params = session.get("parameters", {}) if session else {}
    model = normalize_model(args.model or (session or {}).get("model"))
    aspect_ratio = args.aspect_ratio or previous_params.get("aspect_ratio") or "16:9"
    parse_ratio(aspect_ratio)
    image_size = args.image_size or previous_params.get("image_size") or "2K"
    quality = args.quality or previous_params.get("quality") or "auto"
    output_format = args.output_format or previous_params.get("output_format") or "png"
    compression = args.compression
    if compression is None:
        compression = previous_params.get("compression", 100)
    if not 0 <= compression <= 100:
        raise ValueError("压缩参数必须在 0 到 100 之间")
    if args.timeout <= 0:
        raise ValueError("超时时间必须是正数")

    if args.size:
        width, height = parse_exact_size(args.size)
        size = f"{width}x{height}"
    elif args.aspect_ratio or args.image_size or not previous_params.get("size"):
        size = size_for_ratio(aspect_ratio, image_size)
    else:
        size = previous_params["size"]
    if model == NANO_MODEL and args.size:
        raise ValueError("--size 仅适用于 GPT；Nano Banana 请使用 --aspect-ratio 和 --image-size")

    new_context = load_context(args.context, args.context_file)
    recorded_context = list((session or {}).get("context", []))
    combined_context = recorded_context + [item for item in new_context if item not in recorded_context]
    previous_turns = list((session or {}).get("turns", []))
    effective_prompt = compose_prompt(args.command, args.prompt, combined_context, previous_turns)

    source_images: list[Path] = []
    if args.command == "edit":
        source = Path(args.image).expanduser().resolve() if args.image else (last_output(session) if session else None)
        if not source or not source.is_file():
            raise ValueError("edit 需要 --image，或需要一个包含已有输出图片的会话")
        source_images = [source]
    elif args.command == "reference":
        source_images = [Path(item).expanduser().resolve() for item in args.image]
        missing = [str(path) for path in source_images if not path.is_file()]
        if missing:
            raise ValueError(f"参考图片不存在：{missing[0]}")
    for source in source_images:
        if source.stat().st_size > 4 * 1024 * 1024:
            raise ValueError(f"输入图片超过服务的 4 MB 限制：{source}")

    url = base_url()
    endpoint = (
        f"{url}/v1beta/models/{NANO_MODEL}:generateContent"
        if model == NANO_MODEL
        else f"{url}/v1/images/{'edits' if source_images else 'generations'}"
    )
    parameters = {
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "compression": compression,
    }
    validate_requested_output(output_dir, args.output, output_format)
    if args.dry_run:
        return {
            "dry_run": True,
            "command": args.command,
            "model": model,
            "endpoint": endpoint,
            "source_image": str(source_images[0]) if len(source_images) == 1 else None,
            "source_images": [str(source) for source in source_images],
            "env_files": loaded_env_files,
            "parameters": parameters,
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
    extension = extension_for(mime, output_format)
    output_path = unique_output_path(output_dir, args.output, extension)
    output_path.write_bytes(image_data)

    if session_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_path = (output_dir / f"session_{stamp}.json").resolve()
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
        "prompt": args.prompt.strip(),
        "effective_prompt": effective_prompt,
        "input_image": str(source_images[0]) if args.command == "edit" else None,
        "input_images": [str(source) for source in source_images],
        "output_image": str(output_path),
        "mime_type": mime,
        "parameters": parameters,
    })
    write_json_atomic(session_path, session)
    return {
        "image": str(output_path),
        "session": str(session_path),
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
