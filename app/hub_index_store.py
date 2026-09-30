"""Download / upload FAISS index + metadata to a Hugging Face Hub repo."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("nutrition-raqa.hub_index")

try:
    from huggingface_hub import HfApi, hf_hub_download
except ImportError:  # pragma: no cover
    HfApi = None  # type: ignore
    hf_hub_download = None  # type: ignore


def _repo_configured(repo_id: str | None, token: str | None) -> bool:
    return bool(repo_id and token and HfApi is not None)


def try_download_index(repo_id: str, path_in_repo: str, dest_dir: str, token: str) -> bool:
    """Pull faiss.index and meta.jsonl from Hub into dest_dir (flat names). Returns True if both exist."""
    if not _repo_configured(repo_id, token):
        return False
    os.makedirs(dest_dir, exist_ok=True)
    prefix = path_in_repo.strip("/").strip()
    try:
        p_idx = hf_hub_download(
            repo_id=repo_id,
            filename=f"{prefix}/faiss.index",
            local_dir=dest_dir,
            token=token,
        )
        p_meta = hf_hub_download(
            repo_id=repo_id,
            filename=f"{prefix}/meta.jsonl",
            local_dir=dest_dir,
            token=token,
        )
    except Exception as e:
        logger.info("Hub index download not available: %s", e)
        return False
    flat_idx = os.path.join(dest_dir, "faiss.index")
    flat_meta = os.path.join(dest_dir, "meta.jsonl")
    try:
        import shutil

        shutil.copy2(p_idx, flat_idx)
        shutil.copy2(p_meta, flat_meta)
    except Exception as e:
        logger.warning("Failed to flatten Hub index files: %s", e)
        return False
    return os.path.isfile(flat_idx) and os.path.isfile(flat_meta)


def upload_index_snapshot(
    repo_id: str,
    path_in_repo: str,
    index_path: str,
    meta_path: str,
    token: str,
    extra_manifest: dict[str, Any] | None = None,
) -> str | None:
    """Upload faiss.index, meta.jsonl, and manifest.json under path_in_repo. Returns snapshot version string."""
    if not _repo_configured(repo_id, token):
        logger.warning("Hub upload skipped: INDEX_HF_REPO_ID or HF_TOKEN not set")
        return None
    if not os.path.isfile(index_path) or not os.path.isfile(meta_path):
        logger.warning("Hub upload skipped: missing index files")
        return None

    api = HfApi(token=token)
    repo_type = os.getenv("INDEX_HF_REPO_TYPE", "model")
    prefix = path_in_repo.strip("/").strip()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    manifest: dict[str, Any] = {
        "version": ts,
        "vector_count": None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra_manifest:
        manifest.update(extra_manifest)

    try:
        import faiss

        idx = faiss.read_index(index_path)
        manifest["vector_count"] = int(idx.ntotal)
    except Exception:
        manifest["vector_count"] = None

    with tempfile.TemporaryDirectory() as tmp:
        man_path = os.path.join(tmp, "manifest.json")
        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        for local, name in (
            (index_path, f"{prefix}/faiss.index"),
            (meta_path, f"{prefix}/meta.jsonl"),
            (man_path, f"{prefix}/manifest.json"),
        ):
            api.upload_file(
                path_or_fileobj=local,
                path_in_repo=name,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"Index snapshot {ts}",
            )
    logger.info("Uploaded index snapshot to %s/%s", repo_id, prefix)
    return ts
