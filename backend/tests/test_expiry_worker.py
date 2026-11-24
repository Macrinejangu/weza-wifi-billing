import signal

import pytest

from app.workers import expire_sessions as worker


class FakeStopEvent:
    def __init__(self, stop_after=2):
        self.stopped = False
        self.wait_calls = []
        self.stop_after = stop_after

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.wait_calls.append(seconds)
        if len(self.wait_calls) >= self.stop_after:
            self.stopped = True


def configure_worker(monkeypatch, stop_after=2):
    event = FakeStopEvent(stop_after=stop_after)
    handlers = {}

    monkeypatch.setattr(worker, "Event", lambda: event)
    monkeypatch.setattr(
        worker.signal,
        "signal",
        lambda sig, handler: handlers.update({sig: handler}),
    )

    return event, handlers


def test_worker_runs_immediately_and_repeats(monkeypatch):
    event, _ = configure_worker(monkeypatch, stop_after=2)
    calls = []

    monkeypatch.setattr(
        worker,
        "run_expiry_cycle",
        lambda limit: calls.append(limit) or {
            "processed": 0,
            "expired": 0,
            "failed": 0,
        },
    )

    worker.run_worker(interval_seconds=5, batch_limit=20)

    assert calls == [20, 20]
    assert event.wait_calls == [5, 5]


def test_worker_retries_after_cycle_failure(monkeypatch):
    event, _ = configure_worker(monkeypatch, stop_after=2)
    calls = []

    def fake_cycle(limit):
        calls.append(limit)

        if len(calls) == 1:
            raise RuntimeError("Simulated database failure")

        return {
            "processed": 1,
            "expired": 1,
            "failed": 0,
        }

    monkeypatch.setattr(worker, "run_expiry_cycle", fake_cycle)

    worker.run_worker(interval_seconds=3, batch_limit=10)

    assert calls == [10, 10]
    assert event.wait_calls == [3, 3]


@pytest.mark.parametrize("shutdown_signal", [signal.SIGINT, signal.SIGTERM])
def test_worker_stops_when_shutdown_signal_is_received(
    monkeypatch, shutdown_signal
):
    event, handlers = configure_worker(monkeypatch, stop_after=5)
    calls = []

    def fake_cycle(limit):
        calls.append(limit)
        handlers[shutdown_signal](shutdown_signal, None)

        return {
            "processed": 0,
            "expired": 0,
            "failed": 0,
        }

    monkeypatch.setattr(worker, "run_expiry_cycle", fake_cycle)

    worker.run_worker(interval_seconds=5, batch_limit=10)

    assert len(calls) == 1
    assert event.is_set()


@pytest.mark.parametrize(
    "interval,batch",
    [
        (0, 10),
        (-1, 10),
        (5, 0),
        (5, -1),
    ],
)
def test_worker_rejects_invalid_configuration(interval, batch):
    with pytest.raises(ValueError):
        worker.run_worker(
            interval_seconds=interval,
            batch_limit=batch,
        )
