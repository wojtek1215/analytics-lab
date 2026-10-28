"""Unit tests for deterministic Common Voice sampling (offline fixtures)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from asr_benchmark.sampling.cv_manifest import (
    build_eligible_pool,
    build_manifest,
    one_clip_per_client,
    select_speaker_disjoint_splits,
    write_manifest_artifacts,
)


def _write_mini_corpus(root: Path, *, n_clients: int = 12, clips_per: int = 2) -> Path:
    corpus = root / "pl"
    clips = corpus / "clips"
    clips.mkdir(parents=True)
    rows: list[dict[str, str]] = []
    durations: list[tuple[str, int]] = []
    for client_i in range(n_clients):
        client_id = f"client_{client_i:03d}"
        for clip_j in range(clips_per):
            path = f"common_voice_pl_{client_i:04d}{clip_j}.mp3"
            (clips / path).write_bytes(b"ID3fake")
            rows.append(
                {
                    "client_id": client_id,
                    "path": path,
                    "sentence_id": f"sent_{client_i}_{clip_j}",
                    "sentence": f"Zdanie testowe {client_i} {clip_j}.",
                    "sentence_domain": "",
                    "up_votes": "2",
                    "down_votes": "0",
                    "age": "",
                    "gender": "",
                    "accents": "",
                    "variant": "",
                    "locale": "pl",
                    "segment": "",
                }
            )
            durations.append((path, 1000 + client_i * 10 + clip_j))

    fieldnames = list(rows[0].keys())
    with (corpus / "test.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    with (corpus / "clip_durations.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["clip", "duration[ms]"])
        writer.writerows(durations)

    return corpus


def test_one_clip_per_client_keeps_first_path(tmp_path: Path) -> None:
    corpus = _write_mini_corpus(tmp_path, n_clients=3, clips_per=2)
    rows = list(csv.DictReader((corpus / "test.tsv").open(encoding="utf-8"), delimiter="\t"))
    eligible, _ = build_eligible_pool(
        rows, clips_dir=corpus / "clips", require_audio=True
    )
    pool, dropped = one_clip_per_client(eligible)
    assert dropped == 3
    assert len(pool) == 3
    assert [c.path for c in pool] == sorted(c.path for c in pool)
    # First path per client after global path sort.
    assert pool[0].path.endswith("0000.mp3")


def test_select_splits_deterministic_and_disjoint() -> None:
    from asr_benchmark.sampling.cv_manifest import ClipRow

    pool = [
        ClipRow(
            path=f"p{i:03d}.mp3",
            client_id=f"c{i}",
            sentence_id=f"s{i}",
            sentence=f"t{i}",
            up_votes=1,
            down_votes=0,
            duration_ms=1000,
            audio_relative=f"clips/p{i:03d}.mp3",
        )
        for i in range(20)
    ]
    a = select_speaker_disjoint_splits(
        pool, seed=20261026, counts={"qa": 2, "pilot": 3, "holdout": 5}
    )
    b = select_speaker_disjoint_splits(
        pool, seed=20261026, counts={"qa": 2, "pilot": 3, "holdout": 5}
    )
    assert [c.path for c in a["qa"]] == [c.path for c in b["qa"]]
    assert [c.path for c in a["holdout"]] == [c.path for c in b["holdout"]]
    clients = (
        {c.client_id for c in a["qa"]}
        | {c.client_id for c in a["pilot"]}
        | {c.client_id for c in a["holdout"]}
    )
    assert len(clients) == 10


def test_build_manifest_roundtrip_and_determinism(tmp_path: Path) -> None:
    corpus = _write_mini_corpus(tmp_path, n_clients=15, clips_per=2)
    counts = {"qa": 2, "pilot": 3, "holdout": 5}
    m1 = build_manifest(
        corpus_dir=corpus,
        seed=20261026,
        counts=counts,
        require_audio=True,
        require_positive_duration=True,
    )
    m2 = build_manifest(
        corpus_dir=corpus,
        seed=20261026,
        counts=counts,
        require_audio=True,
        require_positive_duration=True,
    )
    assert [c["path"] for c in m1["clips"]] == [c["path"] for c in m2["clips"]]
    assert m1["filter_stats"]["speaker_pool"] == 15
    assert all(not v for v in m1["overlap_check"].values())

    out = tmp_path / "manifests"
    paths = write_manifest_artifacts(m1, out, basename="mini")
    assert paths["json"].is_file()
    assert paths["csv_qa"].is_file()
    qa_rows = list(csv.DictReader(paths["csv_qa"].open(encoding="utf-8")))
    assert len(qa_rows) == 2
    assert qa_rows[0]["split"] == "qa"


def test_insufficient_speakers_raises(tmp_path: Path) -> None:
    corpus = _write_mini_corpus(tmp_path, n_clients=5, clips_per=1)
    with pytest.raises(ValueError, match="speaker pool"):
        build_manifest(
            corpus_dir=corpus,
            counts={"qa": 2, "pilot": 3, "holdout": 5},
            require_audio=True,
            require_positive_duration=True,
        )
