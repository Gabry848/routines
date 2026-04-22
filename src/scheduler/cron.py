from datetime import datetime, timedelta


class CronExpression:
    """Simple 5-field cron parser (minute hour day month weekday)."""

    def __init__(self, expression: str) -> None:
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        self.minutes = self._parse_field(parts[0], 0, 59)
        self.hours = self._parse_field(parts[1], 0, 23)
        self.days = self._parse_field(parts[2], 1, 31)
        self.months = self._parse_field(parts[3], 1, 12)
        self.weekdays = self._parse_weekday_field(parts[4])

    @staticmethod
    def _parse_field(field: str, min_value: int, max_value: int) -> set[int]:
        values: set[int] = set()

        for part in field.split(","):
            values.update(CronExpression._parse_field_part(part.strip(), min_value, max_value))

        if not values:
            raise ValueError(f"Invalid cron field: {field}")

        return values

    @staticmethod
    def _parse_field_part(part: str, min_value: int, max_value: int) -> set[int]:
        if part == "*":
            return set(range(min_value, max_value + 1))

        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            if step <= 0:
                raise ValueError(f"Invalid step value: {part}")

            if base == "*":
                start = min_value
                end = max_value
            elif "-" in base:
                start, end = CronExpression._parse_range(base, min_value, max_value)
            else:
                start = CronExpression._parse_number(base, min_value, max_value)
                end = max_value

            return set(range(start, end + 1, step))

        if "-" in part:
            start, end = CronExpression._parse_range(part, min_value, max_value)
            return set(range(start, end + 1))

        return {CronExpression._parse_number(part, min_value, max_value)}

    @staticmethod
    def _parse_number(value: str, min_value: int, max_value: int) -> int:
        number = int(value)
        if number < min_value or number > max_value:
            raise ValueError(f"Value out of range: {value}")
        return number

    @staticmethod
    def _parse_range(value: str, min_value: int, max_value: int) -> tuple[int, int]:
        start_str, end_str = value.split("-", 1)
        start = CronExpression._parse_number(start_str, min_value, max_value)
        end = CronExpression._parse_number(end_str, min_value, max_value)
        if start > end:
            raise ValueError(f"Invalid range: {value}")
        return start, end

    @staticmethod
    def _parse_weekday_field(field: str) -> set[int]:
        raw_values = CronExpression._parse_field(field, 0, 7)
        normalized_values: set[int] = set()

        for raw_day in raw_values:
            # In cron, 0 and 7 are Sunday. We map to Python weekday() values.
            if raw_day in (0, 7):
                normalized_values.add(6)
            else:
                normalized_values.add(raw_day - 1)

        return normalized_values

    def matches(self, dt: datetime) -> bool:
        return (
            dt.minute in self.minutes
            and dt.hour in self.hours
            and dt.day in self.days
            and dt.month in self.months
            and dt.weekday() in self.weekdays
        )

    def next_run_after(self, after: datetime) -> datetime:
        candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Search up to five years ahead to avoid infinite loops with malformed schedules.
        max_checks = 5 * 366 * 24 * 60
        for _ in range(max_checks):
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)

        raise RuntimeError("Could not find next run time for cron expression")
