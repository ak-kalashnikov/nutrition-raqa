"""Debounced upload of local FAISS index to Hugging Face Hub."""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger("nutrition-raqa.hub_upload")

_timer: threading.Timer | None = None
_timer_lock = threading.Lock()


def schedule_hub_index_upload(
    debounce_seconds: float,
    upload_fn: Callable[[], None],
) -> None:
    """Debounce many append operations into a single Hub upload."""

    def _run():
        global _timer
        try:
            upload_fn()
        except Exception as e:
            logger.exception("Hub index upload failed: %s", e)
        finally:
            with _timer_lock:
                _timer = None

    global _timer
    with _timer_lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(debounce_seconds, _run)
        _timer.daemon = True
        _timer.start()
