"""findings-protocol — fail-greedy helper for architecture validation.

抽象自 harness phase-1-bootstrap 实战。让架构验证测试套撞 bug 不停继续记 finding。

Usage:
    from findings_protocol import record_and_continue

    async def test_k0_adapter_called(phase_run):
        rows = phase_run.ledger_rows
        llm_rows = [r for r in rows if r.operation == Operation.LLM_CALL]
        if not llm_rows:
            record_and_continue(
                phase=1,
                finding_id="001",
                severity="serious",
                error=AssertionError("ledger has 0 LLM_CALL rows for trace"),
                root_cause_tag="k0-adapter-no-ledger",
                suspect_layer="K0",
                repro_snippet=...,
                observed_extra=f"trace_id={phase_run.trace_id}",
            )
            raise AssertionError("unreachable")  # noqa: TRY003
        assert llm_rows[0].versions.harness_v
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


SEVERITY = ["blocker", "serious", "minor", "nit"]


def utc_now() -> datetime:
    """Return tz-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _findings_dir(project_root: Path | None = None) -> Path:
    """Locate tests/arch-validation/findings/ relative to project root."""
    project_root = project_root or Path.cwd()
    findings = project_root / "tests" / "arch-validation" / "findings"
    findings.mkdir(parents=True, exist_ok=True)
    return findings


def record_and_continue(
    *,
    phase: int,
    finding_id: str,
    severity: str,
    error: Exception,
    root_cause_tag: str,
    suspect_layer: str,
    repro_snippet: str = "",
    observed_extra: str = "",
    linked_spec: str = "",
    project_root: Path | None = None,
) -> None:
    """Record finding to _LEDGER.md + per-finding .md + xfail the test.

    Args:
        phase: Phase number (1, 2, 3, 4, 5)
        finding_id: Per-phase finding ID (001, 002, ..., or arbitrary token)
        severity: One of "blocker" / "serious" / "minor" / "nit"
        error: The exception raised by the assertion
        root_cause_tag: Short kebab-case tag (e.g. "k0-adapter-no-ledger")
        suspect_layer: Architecture layer suspected (e.g. "K0", "K1", "横切 ledger")
        repro_snippet: pytest selector + expected vs actual
        observed_extra: Extra context (trace_id, etc.)
        linked_spec: Optional SPEC §X.Y reference
        project_root: Override project root (default: cwd)

    Raises:
        Calls pytest.xfail() — test will be marked xfail not failed.
    """
    if severity not in SEVERITY:
        raise ValueError(f"severity must be one of {SEVERITY}, got {severity!r}")

    findings = _findings_dir(project_root)
    full_id = f"PHASE-{phase}-{finding_id}"
    ts = utc_now().isoformat()

    # 1. Append _LEDGER.md row
    ledger = findings / "_LEDGER.md"
    if not ledger.exists():
        ledger.write_text(
            "# Findings ledger\n\n"
            "| id | severity | root_cause_tag | suspect_layer | recorded_at |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    with ledger.open("a", encoding="utf-8") as f:
        f.write(
            f"| {full_id} | {severity} | {root_cause_tag} | {suspect_layer} | {ts} |\n"
        )

    # 2. Write per-finding .md (only if doesn't exist — dedup)
    finding_md = findings / f"{full_id}.md"
    if not finding_md.exists():
        body = f"""# Finding {full_id} — {error}

> Auto-recorded by record_and_continue at phase acceptance time.
> Architect: when triaging, refine `suspect-layer` if needed and
> fill the `## Resolution Attempts` section.

---

id: {full_id}
title: {error}
severity: {severity}
observed: {observed_extra}
suspect-layer: {suspect_layer}
repro: {repro_snippet}
status: open

# 可选
root-cause-tag: {root_cause_tag}
linked-spec: {linked_spec}

---

## Resolution Attempts

(open,等 architect 立修复 SPEC 后追加 Round 1。)
"""
        finding_md.write_text(body, encoding="utf-8")

    # 3. xfail this test (don't raise — let phase continue)
    pytest.xfail(reason=f"recorded as {full_id}")


def aggregate_findings(project_root: Path | None = None) -> dict:
    """Aggregate _LEDGER.md into severity counts.

    Returns:
        {"blocker": N, "serious": N, "minor": N, "nit": N, "total": N}
    """
    findings = _findings_dir(project_root)
    ledger = findings / "_LEDGER.md"
    if not ledger.exists():
        return {s: 0 for s in SEVERITY} | {"total": 0}

    counts = {s: 0 for s in SEVERITY}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        if "severity" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 2 and parts[1] in SEVERITY:
            counts[parts[1]] += 1
    counts["total"] = sum(counts.values())
    return counts


def phase_can_pass(project_root: Path | None = None) -> bool:
    """SKILL §6.6 phase 收敛标准:0 blocker + 0 serious 才 pass."""
    counts = aggregate_findings(project_root)
    return counts["blocker"] == 0 and counts["serious"] == 0
