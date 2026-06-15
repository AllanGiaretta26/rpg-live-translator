from __future__ import annotations

import logging
from threading import Lock, Thread
from time import monotonic
from typing import Callable, Protocol

from live_translator.domain.interfaces import GameProfileRepository, ScreenCapture

logger = logging.getLogger(__name__)


class FrameProcessor(Protocol):
    def process_frame(self, image: object) -> None:
        """Process a captured image frame."""


class WorkerThread(Protocol):
    def start(self) -> None:
        """Start the worker."""


ThreadFactory = Callable[[Callable[[], None]], WorkerThread]
Clock = Callable[[], float]
ErrorHandler = Callable[[Exception], None]


def _default_thread_factory(target: Callable[[], None]) -> WorkerThread:
    return Thread(target=target, daemon=True)


def _default_error_handler(error: Exception) -> None:
    logger.exception("capture loop error: %s", error)


class CaptureLoopService:
    def __init__(
        self,
        screen_capture: ScreenCapture,
        pipeline: FrameProcessor,
        profile_repository: GameProfileRepository,
        capture_interval_ms: int = 500,
        *,
        clock: Clock = monotonic,
        thread_factory: ThreadFactory = _default_thread_factory,
        error_handler: ErrorHandler | None = None,
        paused: bool = True,
    ) -> None:
        if capture_interval_ms <= 0:
            raise ValueError("capture_interval_ms must be greater than zero")

        self._screen_capture = screen_capture
        self._pipeline = pipeline
        self._profile_repository = profile_repository
        self._capture_interval_seconds = capture_interval_ms / 1000.0
        self._clock = clock
        self._thread_factory = thread_factory
        self._error_handler = error_handler or _default_error_handler
        self._paused = paused
        self._in_flight = False
        self._last_error_message: str | None = None
        self._next_capture_at = 0.0
        self._state_lock = Lock()

    @property
    def is_paused(self) -> bool:
        with self._state_lock:
            return self._paused

    @property
    def is_busy(self) -> bool:
        with self._state_lock:
            return self._in_flight

    @property
    def last_error_message(self) -> str | None:
        with self._state_lock:
            return self._last_error_message

    def clear_last_error(self) -> None:
        with self._state_lock:
            self._last_error_message = None

    def pause(self) -> None:
        with self._state_lock:
            self._paused = True

    def resume(self) -> None:
        with self._state_lock:
            self._paused = False
            self._last_error_message = None

    def tick(self) -> bool:
        with self._state_lock:
            if self._paused or self._in_flight:
                return False

            now = self._clock()
            if now < self._next_capture_at:
                return False

            self._in_flight = True
            previous_next_capture_at = self._next_capture_at
            self._next_capture_at = now + self._capture_interval_seconds

        try:
            worker = self._thread_factory(self._run_cycle)
        except Exception as error:  # pragma: no cover - segurança defensiva.
            with self._state_lock:
                self._in_flight = False
                self._next_capture_at = previous_next_capture_at
            self._report_error(error)
            return False

        try:
            worker.start()
        except Exception as error:  # pragma: no cover - segurança defensiva.
            with self._state_lock:
                self._in_flight = False
                self._next_capture_at = previous_next_capture_at
            self._report_error(error)
            return False

        return True

    def _run_cycle(self) -> None:
        try:
            profile = self._profile_repository.get_active_profile()
            if profile is None:
                return

            image = self._screen_capture.capture_region(profile.text_region)
            self._pipeline.process_frame(image)
        except Exception as error:
            self._report_error(error)
        finally:
            with self._state_lock:
                self._in_flight = False

    def _report_error(self, error: Exception) -> None:
        with self._state_lock:
            self._last_error_message = str(error) or error.__class__.__name__

        try:
            self._error_handler(error)
        except Exception:  # pragma: no cover - segurança defensiva.
            logger.exception("capture loop error handler failed")
