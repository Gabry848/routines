## ADDED Requirements

### Requirement: Execution tracking in engine
RoutineScheduler SHALL maintain a dict of currently running executions keyed by execution_id, populated when a routine starts and cleared when it finishes.

#### Scenario: Track execution start and end
- **WHEN** `Routine.start()` begins execution
- **THEN** engine registers entry with execution_id, routine_name, task_id, started_at timestamp
- **WHEN** `Routine.start()` finishes (success or exception)
- **THEN** engine removes entry from running dict

### Requirement: Heartbeat and last sync timestamp
RoutineScheduler SHALL expose a heartbeat timestamp updated on every `sync_jobs()` call, and a `started_at` timestamp set on scheduler startup.

#### Scenario: Heartbeat reflects sync activity
- **WHEN** `sync_jobs()` completes
- **THEN** `last_sync_at` is set to current datetime
- **WHEN** scheduler starts
- **THEN** `started_at` is set to current datetime

### Requirement: task.enabled filter in loader
`load_jobs()` SHALL skip tasks where `task.enabled` is explicitly `false`. Tasks without an `enabled` field default to enabled.

#### Scenario: Skip disabled task
- **WHEN** task dict contains `"enabled": false`
- **THEN** loader skips that task, does not create a Routine instance for it

#### Scenario: Task without enabled field
- **WHEN** task dict has no `enabled` key
- **THEN** loader treats it as enabled, creates Routine instance

### Requirement: Execution log file registry
The system SHALL maintain an in-memory list of recent execution records with execution_id, routine_name, task_id, status (running/success/failed), started_at, finished_at.

#### Scenario: Record execution outcome
- **WHEN** a routine execution completes
- **THEN** system records outcome (success/failed) and finished_at timestamp in history list
