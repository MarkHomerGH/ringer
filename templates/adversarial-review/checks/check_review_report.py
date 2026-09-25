#!/usr/bin/env python3
"""Validate an adversarial review report with structured findings."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


REQUIRED_LABELS = ["Finding", "Evidence", "Impact", "Fix", "Priority", "Confidence"]
LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:[-*+][ \t]*)?(?:\*\*)?"
    r"(Finding|Evidence|Impact|Fix|Priority|Confidence)(?:\*\*)?[ \t]*:[ \t]*(?:\*\*)?(.*)$"
)


def finding_blocks(region: str) -> list[str]:
    markers = [match for match in LABEL_RE.finditer(region) if match.group(1).lower() == "finding"]
    blocks: list[str] = []
    for index, match in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(region)
        blocks.append(region[match.start():end])
    return blocks


def label_values(block: str) -> dict[str, str]:
    matches = list(LABEL_RE.finditer(block))
    values: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        continuation = block[match.end():end]
        lines = [match.group(2).strip()]
        for line in continuation.splitlines():
            if line.startswith((" ", "\t")):
                lines.append(line.strip())
            elif line.strip():
                break
        values[label] = "\n".join(part for part in lines if part).strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="report.md")
    args = parser.parse_args()

    path = pathlib.Path(args.file)
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    fails: list[str] = []

    if not re.search(r"(?im)^#+\s*summary\b", text):
        fails.append("missing ## Summary section")

    # Parse Finding: blocks ONLY inside the '## Findings' section — scanning the
    # whole report once flunked an honest review when a Summary sentence
    # line-wrapped onto the word 'finding:' (homer-workspace v0.4.2 round 7,
    # 2026-09-02; fixed there as 3601665). No-heading reports fall back to
    # whole-text scanning.
    findings_region = text
    heading = re.search(r"(?im)^#+\s*findings\b.*$", text)
    if heading:
        tail = text[heading.end():]
        stop_at = len(tail)
        for stop in re.finditer(r"(?m)^#+\s*\S.*$", tail):
            if not LABEL_RE.match(stop.group(0)):
                stop_at = stop.start()
                break
        findings_region = tail[:stop_at]
    blocks = finding_blocks(findings_region)
    finding_count = len(blocks)
    no_findings = bool(re.search(r"(?i)\bNO FINDINGS\b", findings_region))
    no_findings = no_findings or bool(re.search(r"(?i)\bNo findings\.", findings_region))

    if finding_count == 0 and not no_findings:
        fails.append("report must contain NO FINDINGS or at least one Finding: block")

    for index, block_text in enumerate(blocks, start=1):
        labels = label_values(block_text)
        for label in REQUIRED_LABELS:
            if label not in labels:
                fails.append(f"finding {index}: missing {label}: label")
        if not re.match(r"P[0-3]\b", labels.get("Priority", "")):
            fails.append(f"finding {index}: Priority must be P0, P1, P2, or P3")
        if not re.match(r"(high|medium|low)\b", labels.get("Confidence", ""), re.IGNORECASE):
            fails.append(f"finding {index}: Confidence must be high, medium, or low")
        evidence = labels.get("Evidence")
        if evidence is not None and len(evidence.strip()) < 20:
            fails.append(f"finding {index}: Evidence is too thin; cite a file, route, log, or reproduction detail")

    if re.search(r"(?i)\b(i\s+(fixed|patched|committed|pushed|modified)|patched\s+the|committed\s+the|pushed\s+the)\b", text):
        fails.append("reviewer appears to claim it changed files; reviewers must not fix")

    if fails:
        print("FAIL:")
        for fail in fails:
            print(f" - {fail}")
        return 1
    if no_findings and finding_count == 0:
        print("PASS: explicit no-findings report with summary")
    else:
        print(f"PASS: {finding_count} structured finding block(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
