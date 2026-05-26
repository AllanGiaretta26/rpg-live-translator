from __future__ import annotations

from dataclasses import dataclass

from live_translator.application.capture_loop_service import CaptureLoopService
from live_translator.domain.models import GameProfile, TextRegion


@dataclass
class FakeClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ControlledWorker:
    def __init__(self, target):
        self._target = target
        self.started = False
        self.finished = False

    def start(self) -> None:
        self.started = True

    def run(self) -> None:
        self._target()
        self.finished = True


class ControlledThreadFactory:
    def __init__(self):
        self.workers: list[ControlledWorker] = []

    def __call__(self, target):
        worker = ControlledWorker(target)
        self.workers.append(worker)
        return worker


class FakeScreenCapture:
    def __init__(self, *, failures: int = 0):
        self.calls: list[TextRegion] = []
        self._failures_remaining = failures

    def capture_region(self, region: TextRegion):
        self.calls.append(region)
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            raise RuntimeError("capture failed")
        return {"region": region, "frame": len(self.calls)}


class FakePipeline:
    def __init__(self):
        self.frames: list[object] = []

    def process_frame(self, image: object) -> None:
        self.frames.append(image)


class FakeProfileRepository:
    def __init__(self, active_profile: GameProfile | None):
        self.active_profile = active_profile
        self.calls = 0

    def get_active_profile(self):
        self.calls += 1
        return self.active_profile


def build_service(
    *,
    clock: FakeClock | None = None,
    capture: FakeScreenCapture | None = None,
    pipeline: FakePipeline | None = None,
    profile_repository: FakeProfileRepository | None = None,
    thread_factory: ControlledThreadFactory | None = None,
    paused: bool = True,
    capture_interval_ms: int = 1000,
    error_handler=None,
):
    clock = clock or FakeClock()
    capture = capture or FakeScreenCapture()
    pipeline = pipeline or FakePipeline()
    profile_repository = profile_repository or FakeProfileRepository(
        GameProfile(
            name="game",
            window_title="RPG Maker",
            text_region=TextRegion(x=10, y=20, width=300, height=120),
        )
    )
    thread_factory = thread_factory or ControlledThreadFactory()

    service = CaptureLoopService(
        screen_capture=capture,
        pipeline=pipeline,
        profile_repository=profile_repository,
        capture_interval_ms=capture_interval_ms,
        clock=clock,
        thread_factory=thread_factory,
        error_handler=error_handler,
        paused=paused,
    )

    return service, clock, capture, pipeline, profile_repository, thread_factory


def test_capture_loop_pauses_and_resumes():
    service, clock, capture, pipeline, profiles, threads = build_service()

    assert service.tick() is False
    assert profiles.calls == 0

    service.resume()
    assert service.is_paused is False
    assert service.last_error_message is None
    assert service.tick() is True
    assert len(threads.workers) == 1
    assert service.is_busy is True

    threads.workers[0].run()

    assert profiles.calls == 1
    assert capture.calls == [profiles.active_profile.text_region]
    assert len(pipeline.frames) == 1
    assert service.is_busy is False

    assert service.tick() is False

    clock.advance(1.0)
    assert service.tick() is True
    assert len(threads.workers) == 2


def test_capture_loop_blocks_parallel_frames_while_worker_is_running():
    service, clock, capture, pipeline, profiles, threads = build_service()
    service.resume()

    assert service.tick() is True
    assert service.is_busy is True

    clock.advance(10.0)
    assert service.tick() is False
    assert len(threads.workers) == 1
    assert capture.calls == []
    assert pipeline.frames == []

    threads.workers[0].run()

    assert capture.calls == [profiles.active_profile.text_region]
    assert len(pipeline.frames) == 1
    assert service.is_busy is False


def test_capture_loop_handles_capture_errors_without_stopping():
    errors: list[Exception] = []
    capture = FakeScreenCapture(failures=1)
    service, clock, _, pipeline, profiles, threads = build_service(
        capture=capture,
        error_handler=errors.append,
    )
    service.resume()

    assert service.tick() is True
    threads.workers[0].run()

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert service.last_error_message == "capture failed"
    assert pipeline.frames == []
    assert service.is_busy is False

    service.resume()
    assert service.last_error_message is None

    clock.advance(1.0)
    assert service.tick() is True
    threads.workers[1].run()

    assert profiles.calls == 2
    assert len(capture.calls) == 2
    assert len(pipeline.frames) == 1
