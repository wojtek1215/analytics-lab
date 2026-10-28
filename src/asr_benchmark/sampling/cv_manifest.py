"""Deterministic speaker-disjoint sampling from Common Voice test.tsv."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SAMPLING_PROTOCOL_ID = "cv_test_speaker_disjoint_v1"
MANIFEST_VERSION = "1.0.0"
SEED = 20261026
SAMPLE_COUNTS: dict[str, int] = {"qa": 10, "pilot": 40, "holdout": 200}
SPLIT_ORDER: tuple[str, ...] = ("qa", "pilot", "holdout")


@dataclass(frozen=True, slots=True)
class ClipRow:
    """One eligible Common Voice clip after filters."""

    path: str
    client_id: str
    sentence_id: str
    sentence: str
    up_votes: int
    down_votes: int
    duration_ms: int | None
    audio_relative: str


@dataclass(frozen=True, slots=True)
class FilterStats:
    """Counts of rows removed by each filter stage."""

    source_rows: int
    missing_required_fields: int
    duplicate_path: int
    audio_missing: int
    nonpositive_duration: int
    eligible: int
    unique_clients_in_eligible: int
    clips_dropped_for_one_per_client: int
    speaker_pool: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_split_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"client_id", "path", "sentence_id", "sentence"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{path} missing required columns {sorted(required)}; "
                f"got {reader.fieldnames!r}"
            )
        return list(reader)


def load_clip_durations(path: Path | None) -> dict[str, int]:
    if path is None or not path.is_file():
        return {}
    out: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        clip_key = "clip"
        duration_key = "duration[ms]"
        if reader.fieldnames is None or clip_key not in reader.fieldnames:
            raise ValueError(f"{path} missing 'clip' column; got {reader.fieldnames!r}")
        if duration_key not in reader.fieldnames:
            # tolerate alternate header
            candidates = [c for c in reader.fieldnames if c.startswith("duration")]
            if not candidates:
                raise ValueError(f"{path} missing duration column")
            duration_key = candidates[0]
        for row in reader:
            clip = (row.get(clip_key) or "").strip()
            raw = (row.get(duration_key) or "").strip()
            if not clip or not raw:
                continue
            out[clip] = int(float(raw))
    return out


def _parse_votes(raw: str | None) -> int:
    if raw is None or raw.strip() == "":
        return 0
    return int(raw)


def build_eligible_pool(
    rows: Sequence[Mapping[str, str]],
    *,
    clips_dir: Path,
    durations: Mapping[str, int] | None = None,
    require_audio: bool = True,
    require_positive_duration: bool = False,
) -> tuple[list[ClipRow], FilterStats]:
    """Apply documented filters and return path-sorted eligible clips."""
    durations = durations or {}
    missing_required = 0
    duplicate_path = 0
    audio_missing = 0
    nonpositive_duration = 0
    seen_paths: set[str] = set()
    eligible: list[ClipRow] = []

    for row in rows:
        client_id = (row.get("client_id") or "").strip()
        path = (row.get("path") or "").strip()
        sentence_id = (row.get("sentence_id") or "").strip()
        sentence = (row.get("sentence") or "").strip()
        if not client_id or not path or not sentence_id or not sentence:
            missing_required += 1
            continue
        if path in seen_paths:
            duplicate_path += 1
            continue
        seen_paths.add(path)

        duration_ms = durations.get(path)
        if require_positive_duration:
            if duration_ms is None or duration_ms <= 0:
                nonpositive_duration += 1
                continue

        audio_path = clips_dir / path
        if require_audio and not audio_path.is_file():
            audio_missing += 1
            continue

        eligible.append(
            ClipRow(
                path=path,
                client_id=client_id,
                sentence_id=sentence_id,
                sentence=sentence,
                up_votes=_parse_votes(row.get("up_votes")),
                down_votes=_parse_votes(row.get("down_votes")),
                duration_ms=duration_ms,
                audio_relative=f"clips/{path}",
            )
        )

    eligible.sort(key=lambda c: c.path)
    unique_clients = {c.client_id for c in eligible}
    stats = FilterStats(
        source_rows=len(rows),
        missing_required_fields=missing_required,
        duplicate_path=duplicate_path,
        audio_missing=audio_missing,
        nonpositive_duration=nonpositive_duration,
        eligible=len(eligible),
        unique_clients_in_eligible=len(unique_clients),
        clips_dropped_for_one_per_client=0,
        speaker_pool=0,
    )
    return eligible, stats


def one_clip_per_client(eligible: Sequence[ClipRow]) -> tuple[list[ClipRow], int]:
    """Keep the lexicographically first path per client_id (eligible already path-sorted)."""
    chosen: list[ClipRow] = []
    seen_clients: set[str] = set()
    for clip in eligible:
        if clip.client_id in seen_clients:
            continue
        seen_clients.add(clip.client_id)
        chosen.append(clip)
    dropped = len(eligible) - len(chosen)
    return chosen, dropped


def select_speaker_disjoint_splits(
    speaker_pool: Sequence[ClipRow],
    *,
    seed: int = SEED,
    counts: Mapping[str, int] | None = None,
) -> dict[str, list[ClipRow]]:
    """Shuffle the speaker pool with a fixed seed and slice qa / pilot / holdout."""
    counts = dict(counts or SAMPLE_COUNTS)
    needed = sum(counts[name] for name in SPLIT_ORDER)
    if len(speaker_pool) < needed:
        raise ValueError(
            f"speaker pool has {len(speaker_pool)} clips; need {needed} "
            f"for counts {counts}"
        )

    pool = list(speaker_pool)
    # Stable pre-order before shuffle so identical inputs always shuffle the same way.
    pool.sort(key=lambda c: c.path)
    rng = random.Random(seed)
    rng.shuffle(pool)

    out: dict[str, list[ClipRow]] = {}
    offset = 0
    for name in SPLIT_ORDER:
        n = counts[name]
        out[name] = pool[offset : offset + n]
        offset += n
    return out


def _clip_record(clip: ClipRow, split: str, index: int) -> dict[str, Any]:
    return {
        "split": split,
        "index_in_split": index,
        "clip_id": clip.path.removesuffix(".mp3"),
        "path": clip.path,
        "audio_relative": clip.audio_relative,
        "client_id": clip.client_id,
        "sentence_id": clip.sentence_id,
        "sentence": clip.sentence,
        "up_votes": clip.up_votes,
        "down_votes": clip.down_votes,
        "duration_ms": clip.duration_ms,
        "sentence_sha256": sha256_text(clip.sentence),
    }


def build_manifest(
    *,
    corpus_dir: Path,
    split_tsv_name: str = "test.tsv",
    seed: int = SEED,
    counts: Mapping[str, int] | None = None,
    require_audio: bool = True,
    require_positive_duration: bool = True,
    dataset_id: str = "cv-corpus-27.0-2026-09-11",
    locale: str = "pl",
) -> dict[str, Any]:
    """Build a full reproducible sampling manifest from a local CV corpus directory."""
    counts = dict(counts or SAMPLE_COUNTS)
    corpus_dir = corpus_dir.resolve()
    split_tsv = corpus_dir / split_tsv_name
    durations_path = corpus_dir / "clip_durations.tsv"
    clips_dir = corpus_dir / "clips"

    rows = load_split_tsv(split_tsv)
    durations = load_clip_durations(durations_path)
    eligible, filter_stats = build_eligible_pool(
        rows,
        clips_dir=clips_dir,
        durations=durations,
        require_audio=require_audio,
        require_positive_duration=require_positive_duration,
    )
    speaker_pool, dropped = one_clip_per_client(eligible)
    filter_stats = FilterStats(
        source_rows=filter_stats.source_rows,
        missing_required_fields=filter_stats.missing_required_fields,
        duplicate_path=filter_stats.duplicate_path,
        audio_missing=filter_stats.audio_missing,
        nonpositive_duration=filter_stats.nonpositive_duration,
        eligible=filter_stats.eligible,
        unique_clients_in_eligible=filter_stats.unique_clients_in_eligible,
        clips_dropped_for_one_per_client=dropped,
        speaker_pool=len(speaker_pool),
    )
    splits = select_speaker_disjoint_splits(speaker_pool, seed=seed, counts=counts)

    clip_records: list[dict[str, Any]] = []
    for split_name in SPLIT_ORDER:
        for index, clip in enumerate(splits[split_name]):
            clip_records.append(_clip_record(clip, split_name, index))

    # Overlap checks (must be empty for this protocol).
    client_sets = {
        name: {c.client_id for c in splits[name]} for name in SPLIT_ORDER
    }
    path_sets = {name: {c.path for c in splits[name]} for name in SPLIT_ORDER}
    overlaps = {
        "qa_pilot_clients": sorted(client_sets["qa"] & client_sets["pilot"]),
        "qa_holdout_clients": sorted(client_sets["qa"] & client_sets["holdout"]),
        "pilot_holdout_clients": sorted(
            client_sets["pilot"] & client_sets["holdout"]
        ),
        "qa_pilot_paths": sorted(path_sets["qa"] & path_sets["pilot"]),
        "qa_holdout_paths": sorted(path_sets["qa"] & path_sets["holdout"]),
        "pilot_holdout_paths": sorted(path_sets["pilot"] & path_sets["holdout"]),
    }
    if any(overlaps.values()):
        raise RuntimeError(f"sampling produced overlaps: {overlaps}")

    selected = [clip for name in SPLIT_ORDER for clip in splits[name]]
    duration_values = [
        clip.duration_ms for clip in selected if clip.duration_ms is not None
    ]
    total_duration_ms = sum(duration_values) if duration_values else None

    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "sampling_protocol": SAMPLING_PROTOCOL_ID,
        "seed": seed,
        "rng": "python.random.Random.shuffle",
        "python_random_note": (
            "Uses the stdlib MT19937 via random.Random(seed).shuffle on a "
            "path-sorted one-clip-per-client pool."
        ),
        "source": {
            "dataset_id": dataset_id,
            "locale": locale,
            "split_file": split_tsv_name,
            "split_tsv_sha256": sha256_file(split_tsv),
            "clip_durations_sha256": (
                sha256_file(durations_path) if durations_path.is_file() else None
            ),
            "corpus_dir_name": corpus_dir.name,
            "parent_archive_hint": corpus_dir.parent.name,
        },
        "selection_rules": {
            "source_split": split_tsv_name,
            "sort_key_before_client_collapse": "path ascending",
            "client_collapse": "first path per client_id after path sort",
            "shuffle": f"random.Random({seed}).shuffle(speaker_pool)",
            "assignment": (
                "qa = pool[0:10]; pilot = pool[10:50]; holdout = pool[50:250] "
                "(or counts override)"
            ),
            "speaker_disjoint_across_splits": True,
            "path_disjoint_across_splits": True,
            "require_audio": require_audio,
            "require_positive_duration": require_positive_duration,
        },
        "requested_counts": dict(counts),
        "filter_stats": asdict(filter_stats),
        "overlap_check": overlaps,
        "duration_summary_ms": {
            "n_with_duration": len(duration_values),
            "total_ms": total_duration_ms,
            "total_minutes": (
                round(total_duration_ms / 60000.0, 3)
                if total_duration_ms is not None
                else None
            ),
        },
        "clips": clip_records,
    }
    return manifest


def write_manifest_artifacts(
    manifest: Mapping[str, Any],
    output_dir: Path,
    *,
    basename: str = "cv27_pl_test_speaker_disjoint_v1",
) -> dict[str, Path]:
    """Write JSON manifest, per-split CSV lists, and a short Markdown report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    report_path = output_dir / f"{basename}_report.md"
    csv_paths: dict[str, Path] = {}

    json_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False)
    json_path.write_text(json_text + "\n", encoding="utf-8")

    fieldnames = [
        "split",
        "index_in_split",
        "clip_id",
        "path",
        "audio_relative",
        "client_id",
        "sentence_id",
        "sentence",
        "up_votes",
        "down_votes",
        "duration_ms",
        "sentence_sha256",
    ]
    by_split: dict[str, list[dict[str, Any]]] = {name: [] for name in SPLIT_ORDER}
    for row in manifest["clips"]:
        by_split[row["split"]].append(row)

    for split_name in SPLIT_ORDER:
        csv_path = output_dir / f"{basename}_{split_name}.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in by_split[split_name]:
                writer.writerow(row)
        csv_paths[split_name] = csv_path

    all_csv = output_dir / f"{basename}_all.csv"
    with all_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for split_name in SPLIT_ORDER:
            for row in by_split[split_name]:
                writer.writerow(row)

    report_path.write_text(_render_report(manifest, json_path.name), encoding="utf-8")

    return {
        "json": json_path,
        "report": report_path,
        "all_csv": all_csv,
        **{f"csv_{k}": v for k, v in csv_paths.items()},
    }


def _render_report(manifest: Mapping[str, Any], json_name: str) -> str:
    stats = manifest["filter_stats"]
    source = manifest["source"]
    counts = manifest["requested_counts"]
    duration = manifest["duration_summary_ms"]
    lines = [
        f"# Sampling report — `{manifest['sampling_protocol']}`",
        "",
        f"- **Manifest file:** `{json_name}`",
        f"- **Manifest version:** `{manifest['manifest_version']}`",
        f"- **Seed:** `{manifest['seed']}`",
        f"- **RNG:** `{manifest['rng']}`",
        f"- **Dataset:** `{source['dataset_id']}` / locale `{source['locale']}`",
        f"- **Source split:** `{source['split_file']}` "
        f"(sha256 `{source['split_tsv_sha256']}`)",
        "",
        "## Requested sample sizes",
        "",
        "| Split | N | Purpose |",
        "|---|---:|---|",
        f"| qa | {counts['qa']} | Pipeline / data QA |",
        f"| pilot | {counts['pilot']} | Development scoring |",
        f"| holdout | {counts['holdout']} | Frozen final evaluation (do not peek while tuning) |",
        "",
        "## Filter and pool statistics",
        "",
        "| Stage | Count |",
        "|---|---:|",
        f"| Source rows | {stats['source_rows']} |",
        f"| Missing required fields | {stats['missing_required_fields']} |",
        f"| Duplicate path | {stats['duplicate_path']} |",
        f"| Audio missing | {stats['audio_missing']} |",
        f"| Non-positive duration | {stats['nonpositive_duration']} |",
        f"| Eligible clips | {stats['eligible']} |",
        f"| Unique clients (eligible) | {stats['unique_clients_in_eligible']} |",
        f"| Dropped for one-clip-per-client | {stats['clips_dropped_for_one_per_client']} |",
        f"| Speaker pool (shuffled) | {stats['speaker_pool']} |",
        "",
        "## Duration (selected clips)",
        "",
        f"- Clips with duration: {duration['n_with_duration']}",
        f"- Total duration: {duration['total_ms']} ms "
        f"({duration['total_minutes']} minutes)",
        "",
        "## Overlap check",
        "",
        "All client and path overlap lists must be empty.",
        "",
        "```json",
        json.dumps(manifest["overlap_check"], indent=2),
        "```",
        "",
        "## Reproducibility",
        "",
        "```bash",
        "uv run python scripts/build_cv_manifest.py \\",
        "  --corpus-dir data/raw/cv-corpus-27.0-2026-09-11/pl \\",
        "  --output-dir data/manifests",
        "```",
        "",
        "Identical inputs + seed must reproduce byte-identical clip path lists.",
        "Do not retune selection after inspecting holdout ASR errors.",
        "",
    ]
    return "\n".join(lines)


def assert_deterministic_paths(
    manifests: Iterable[Mapping[str, Any]],
) -> list[str]:
    """Return ordered clip paths; raises if manifests disagree."""
    sequences = [
        [c["path"] for c in m["clips"]] for m in manifests
    ]
    first = sequences[0]
    for seq in sequences[1:]:
        if seq != first:
            raise AssertionError("manifest clip paths are not identical across runs")
    return first
