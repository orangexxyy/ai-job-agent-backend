"""从本地 resume_source 选择主简历并生成规范化纯文本。

脚本只读取用户指定的本地简历来源，写入 current_resume.txt 和抽取报告；
不调用 LLM、不写数据库，也不生成或更新 candidate_profile。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from xml.etree import ElementTree


DEFAULT_SOURCE_DIR = Path("docs/input/resume_source")
DEFAULT_OUTPUT = Path("docs/input/current_resume.txt")
DEFAULT_REPORT = Path("docs/input/resume_extract_report.md")
SUPPORTED_SUFFIXES = {".docx", ".md", ".txt"}
SAMPLE_NAME = "sample_resume.md"
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class ExtractionResult(NamedTuple):
    text: str
    file_type: str
    read_encoding: str | None = None


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n" if text.strip() else ""


def extract_docx(path: Path) -> ExtractionResult:
    try:
        with zipfile.ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("DOCX does not contain word/document.xml") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("DOCX is not a valid ZIP container") from exc

    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": WORD_NAMESPACE}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        fragments: list[str] = []
        for element in paragraph.iter():
            if element.tag == f"{{{WORD_NAMESPACE}}}t" and element.text:
                fragments.append(element.text)
            elif element.tag == f"{{{WORD_NAMESPACE}}}tab":
                fragments.append("\t")
            elif element.tag in {
                f"{{{WORD_NAMESPACE}}}br",
                f"{{{WORD_NAMESPACE}}}cr",
            }:
                fragments.append("\n")
        value = "".join(fragments).strip()
        if value:
            paragraphs.append(value)
    return ExtractionResult(text="\n".join(paragraphs), file_type="docx")


def extract_text_file(path: Path) -> ExtractionResult:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return ExtractionResult(
                text=path.read_text(encoding=encoding),
                file_type=path.suffix.lower().lstrip("."),
                read_encoding=encoding,
            )
        except UnicodeDecodeError:
            continue
    raise ValueError("text file cannot be decoded as UTF-8 or GBK")


def extract_source(path: Path) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in {".md", ".txt"}:
        return extract_text_file(path)
    if suffix == ".pdf":
        raise ValueError(
            "PDF extraction is not implemented in Step 27A. "
            "Text PDF support can be added later; OCR is out of scope."
        )
    raise ValueError(f"unsupported source type: {suffix or '(no suffix)'}")


def discover_sources(source_dir: Path) -> list[Path]:
    return sorted(
        (path for path in source_dir.iterdir() if path.is_file()),
        key=lambda item: item.name.lower(),
    )


def select_main_source(
    files: list[Path], *, include_sample: bool, explicit_source: Path | None
) -> tuple[Path | None, list[tuple[Path, str]], list[str]]:
    skipped: list[tuple[Path, str]] = []
    warnings: list[str] = []
    if explicit_source is not None:
        for path in files:
            if path.resolve() != explicit_source.resolve():
                skipped.append((path, "not selected because --source-file was provided"))
        if explicit_source.name.lower() == SAMPLE_NAME:
            warnings.append("sample_resume.md was explicitly selected for format testing")
        return explicit_source, skipped, warnings

    usable = [path for path in files if path.suffix.lower() in SUPPORTED_SUFFIXES]
    samples = [path for path in usable if path.name.lower() == SAMPLE_NAME]
    non_samples = [path for path in usable if path.name.lower() != SAMPLE_NAME]
    preferred_docx = [
        path
        for path in non_samples
        if path.suffix.lower() == ".docx"
        and ("程伟桔" in path.name or "新版简历" in path.name)
    ]
    other_docx = [path for path in non_samples if path.suffix.lower() == ".docx"]
    fallback_text = [
        path for path in non_samples if path.suffix.lower() in {".md", ".txt"}
    ]

    selected = next(iter(preferred_docx or other_docx or fallback_text), None)
    if selected is None and samples:
        if include_sample or len(usable) == len(samples):
            selected = samples[0]
            warnings.append(
                "only sample resume source found; not recommended for real candidate_profile"
            )
    for path in files:
        if selected is not None and path.resolve() == selected.resolve():
            continue
        if path.name.lower() == SAMPLE_NAME and not include_sample:
            reason = "sample_resume.md skipped by default"
        elif path.suffix.lower() == ".pdf":
            reason = (
                "PDF extraction is not implemented in Step 27A. "
                "Text PDF support can be added later; OCR is out of scope."
            )
        elif path.suffix.lower() not in SUPPORTED_SUFFIXES:
            reason = "unsupported source type"
        else:
            reason = "not selected as the main resume source"
        skipped.append((path, reason))
    return selected, skipped, warnings


def detect_key_information(text: str) -> dict[str, bool]:
    lowered = text.lower()
    return {
        "本科": "本科" in text,
        "大专": "大专" in text or "专科" in text,
        "硕士": "硕士" in text or "研究生" in text,
        "博士": "博士" in text,
        "专业": "专业" in text,
        "求职方向": "求职方向" in text,
        "RAG": "rag" in lowered,
        "AI Job Agent": "ai job agent" in lowered,
        "FastAPI": "fastapi" in lowered,
        "Agent": "agent" in lowered,
    }


def write_report(
    *,
    report_path: Path,
    source_dir: Path,
    files: list[Path],
    selected: Path | None,
    skipped: list[tuple[Path, str]],
    warnings: list[str],
    result: ExtractionResult | None,
    output_path: Path,
) -> None:
    skipped_by_path = {path.resolve(): reason for path, reason in skipped}
    lines = [
        "# Resume Extract Report",
        "",
        f"- 抽取时间：`{datetime.now(timezone.utc).isoformat()}`",
        f"- source_dir：`{source_dir}`",
        f"- 主简历文件：`{selected if selected else '未选择'}`",
        f"- 输出文件：`{output_path}`",
        f"- 文件类型：`{result.file_type if result else '不适用'}`",
        f"- 抽取字符数：`{len(result.text.strip()) if result else 0}`",
        "",
        "## 发现的源文件",
        "",
    ]
    if files:
        for path in files:
            note = skipped_by_path.get(path.resolve(), "selected main resume source")
            lines.append(f"- `{path}` (`{path.suffix.lower() or 'no suffix'}`)：{note}")
    else:
        lines.append("- 未发现源文件")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- 无")
    lines.extend(["", "## 检测到的关键信息", ""])
    for label, found in detect_key_information(result.text if result else "").items():
        lines.append(f"- {label}：{'是' if found else '否'}")
    lines.extend(
        [
            "",
            "## 数据边界",
            "",
            "`current_resume.txt` 是后续生成 `candidate_profile_draft` 的输入，",
            "不是正式 `candidate_profile`，本脚本不会写数据库或调用 `/profile`。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select and extract the main local resume source."
    )
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--include-sample", action="store_true")
    parser.add_argument("--source-file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_path = Path(args.output)
    report_path = Path(args.report)
    explicit_source = Path(args.source_file) if args.source_file else None

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Error: source directory does not exist: {source_dir}", file=sys.stderr)
        return 1
    if explicit_source is not None and not explicit_source.is_file():
        print(f"Error: source file does not exist: {explicit_source}", file=sys.stderr)
        return 1

    files = discover_sources(source_dir)
    if explicit_source is not None and all(
        path.resolve() != explicit_source.resolve() for path in files
    ):
        files.append(explicit_source)
        files.sort(key=lambda item: item.name.lower())
    selected, skipped, warnings = select_main_source(
        files,
        include_sample=args.include_sample,
        explicit_source=explicit_source,
    )
    if selected is None:
        warnings.append("no supported resume source was selected")
        write_report(
            report_path=report_path,
            source_dir=source_dir,
            files=files,
            selected=None,
            skipped=skipped,
            warnings=warnings,
            result=None,
            output_path=output_path,
        )
        print("Error: no supported resume source was selected", file=sys.stderr)
        return 1

    try:
        raw_result = extract_source(selected)
        result = raw_result._replace(text=normalize_text(raw_result.text))
    except (OSError, ValueError, ElementTree.ParseError) as exc:
        warnings.append(str(exc))
        write_report(
            report_path=report_path,
            source_dir=source_dir,
            files=files,
            selected=selected,
            skipped=skipped,
            warnings=warnings,
            result=None,
            output_path=output_path,
        )
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if not result.text.strip():
        warnings.append("selected resume produced empty text")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.text, encoding="utf-8")
    write_report(
        report_path=report_path,
        source_dir=source_dir,
        files=files,
        selected=selected,
        skipped=skipped,
        warnings=warnings,
        result=result,
        output_path=output_path,
    )
    print(f"Selected source: {selected}")
    print(f"Generated: {output_path}")
    print(f"Generated: {report_path}")
    print(f"Extracted characters: {len(result.text.strip())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
