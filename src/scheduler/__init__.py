from .constants import ROUTINES_PATH


def run_scheduler() -> None:
    from .app import run_scheduler as _run_scheduler

    return _run_scheduler()


__all__ = ["run_scheduler", "ROUTINES_PATH"]
