"""CLI tests for generate_smoke_report_v2 (offline only)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_smoke_report_v2.py"

LEGACY = [
    ROOT / "results/evaluation/smoke_pl_basic_v1.json",
    ROOT / "results/evaluation/smoke_comparison.md",
    ROOT / "results/evaluation/smoke_error_taxonomy.md",
    ROOT / "results/evaluation/smoke_alignment_pl_basic_v1.json",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.skipif(not SCRIPT.is_file(), reason="CLI script missing")
def test_cli_writes_v2_and_preserves_legacy(tmp_path: Path) -> None:
    # Use real smoke inputs but write to temp — must still be under repo v2
    # So we run against the real v2 dir after hashing legacy, then restore isn't
    # needed if CLI refuses non-v2 paths. Instead: hash legacy, run CLI to
    # results/evaluation/v2, re-hash legacy.
    before = {p: _sha(p) for p in LEGACY if p.is_file()}

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after = {p: _sha(p) for p in LEGACY if p.is_file()}
    assert after == before

    metrics = ROOT / "results/evaluation/v2/smoke_metrics.json"
    assert metrics.is_file()
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    assert payload["api_used"] is False
    assert payload["asr_inference_performed"] is False
    assert "ELEVENLABS" not in metrics.read_text(encoding="utf-8")
    assert str(Path.home()) not in metrics.read_text(encoding="utf-8")

    md = (ROOT / "results/evaluation/v2/smoke_comparison_v2.md").read_text(
        encoding="utf-8"
    )
    for mid in payload["model_ids"]:
        wer = payload["models"][mid]["profiles"]["pl_wer_normalized_v1"]["wer"]
        assert f"{100.0 * wer:.1f}%" in md


@pytest.mark.skipif(not SCRIPT.is_file(), reason="CLI script missing")
def test_cli_refuses_outside_v2(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path / "elsewhere")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "refusing" in (proc.stdout + proc.stderr).lower()
