import asyncio

from scheduler.app import run_scheduler


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()