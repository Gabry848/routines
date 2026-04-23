## ADDED Requirements

### Requirement: list_routines tool
The system SHALL provide an MCP tool `list_routines` returning all routines with: name, enabled, path, tasks (each with task_id, cron, timezone, enabled, next_run).

#### Scenario: List returns all routines
- **WHEN** Claude calls `list_routines`
- **THEN** system returns array of routine summary objects from both filesystem discovery and scheduler state

#### Scenario: Include disabled routines
- **WHEN** some routines have `enabled: false`
- **THEN** they appear in the list with `enabled: false`

### Requirement: get_routine tool
The system SHALL provide an MCP tool `get_routine` returning full routine detail: config.json content, prompt text, task list, filesystem path. Optional `task_id` parameter filters to specific task.

#### Scenario: Get routine by name
- **WHEN** Claude calls `get_routine(name="example")`
- **THEN** system returns full routine object with config, prompt_text, tasks, path

#### Scenario: Routine not found
- **WHEN** Claude calls `get_routine(name="nonexistent")`
- **THEN** system returns error message "routine not found"

#### Scenario: Get specific task
- **WHEN** Claude calls `get_routine(name="example", task_id="task-0")`
- **THEN** system returns only that task's detail

### Requirement: reload_routines tool
The system SHALL provide an MCP tool `reload_routines` that triggers immediate `sync_jobs()`.

#### Scenario: Force reload
- **WHEN** Claude calls `reload_routines`
- **THEN** system calls `sync_jobs()`, returns added/updated/removed counts

### Requirement: add_routine tool
The system SHALL provide an MCP tool `add_routine` that creates a new routine directory with config.json and prompt file.

#### Scenario: Create routine
- **WHEN** Claude calls `add_routine(name="my-routine", config={...}, prompt="...")`
- **THEN** system creates `routines/my-routine/`, writes config.json, writes PROMPT.md, creates env/ dir

#### Scenario: Duplicate name
- **WHEN** Claude calls `add_routine` with name that already exists
- **THEN** system returns error "routine already exists"

### Requirement: update_routine_config tool
The system SHALL provide an MCP tool `update_routine_config` that safely modifies config fields. Accepts partial updates merged into existing config.

#### Scenario: Update timezone
- **WHEN** Claude calls `update_routine_config(name="example", updates={"scheduler": {"timezone": "America/New_York"}})`
- **THEN** system deep-merges updates into config.json, validates, saves

#### Scenario: Invalid cron in update
- **WHEN** Claude calls `update_routine_config` with invalid cron expression
- **THEN** system returns validation error, does not save

### Requirement: delete_routine tool
The system SHALL provide an MCP tool `delete_routine` that deletes or disables a routine.

#### Scenario: Soft delete
- **WHEN** Claude calls `delete_routine(name="example", mode="disable")`
- **THEN** system sets `enabled: false` in config.json

#### Scenario: Hard delete
- **WHEN** Claude calls `delete_routine(name="example", mode="delete")`
- **THEN** system removes entire routine directory

### Requirement: rename_routine tool
The system SHALL provide an MCP tool `rename_routine` that renames the directory and maintains coherence.

#### Scenario: Rename routine
- **WHEN** Claude calls `rename_routine(name="old-name", new_name="new-name")`
- **THEN** system renames directory, returns updated routine detail

### Requirement: clone_routine tool
The system SHALL provide an MCP tool `clone_routine` that duplicates a routine with new name and unique task IDs.

#### Scenario: Clone routine
- **WHEN** Claude calls `clone_routine(name="example", new_name="example-copy")`
- **THEN** system copies directory, regenerates task_ids, returns new routine detail

### Requirement: enable_routine tool
The system SHALL provide an MCP tool `enable_routine` that sets `enabled: true`.

#### Scenario: Enable routine
- **WHEN** Claude calls `enable_routine(name="example")`
- **THEN** system sets `scheduler.enabled: true`, saves config.json

### Requirement: disable_routine tool
The system SHALL provide an MCP tool `disable_routine` that sets `enabled: false`.

#### Scenario: Disable routine
- **WHEN** Claude calls `disable_routine(name="example")`
- **THEN** system sets `scheduler.enabled: false`, saves config.json

### Requirement: add_task_to_routine tool
The system SHALL provide an MCP tool `add_task_to_routine` that appends a task to a routine's task list.

#### Scenario: Add task
- **WHEN** Claude calls `add_task_to_routine(name="example", task={"schedule": {"type": "cron", "expression": "0 10 * * *"}})`
- **THEN** system appends task to config.json tasks array

#### Scenario: Duplicate task_id
- **WHEN** Claude calls `add_task_to_routine` with task_id already in routine
- **THEN** system returns error "task_id already exists"

### Requirement: update_task tool
The system SHALL provide an MCP tool `update_task` that modifies a task by task_id.

#### Scenario: Update task schedule
- **WHEN** Claude calls `update_task(name="example", task_id="task-0", updates={"schedule": {"type": "cron", "expression": "0 12 * * *"}})`
- **THEN** system updates task in config.json, returns updated task

#### Scenario: Task not found
- **WHEN** Claude calls `update_task` with non-existent task_id
- **THEN** system returns error "task not found"

### Requirement: delete_task tool
The system SHALL provide an MCP tool `delete_task` that removes a task by task_id.

#### Scenario: Delete task
- **WHEN** Claude calls `delete_task(name="example", task_id="task-0")`
- **THEN** system removes task from config.json tasks array

### Requirement: enable_task tool
The system SHALL provide an MCP tool `enable_task` that sets `task.enabled: true`.

#### Scenario: Enable task
- **WHEN** Claude calls `enable_task(name="example", task_id="task-0")`
- **THEN** system sets task `enabled: true` in config.json

### Requirement: disable_task tool
The system SHALL provide an MCP tool `disable_task` that sets `task.enabled: false`.

#### Scenario: Disable task
- **WHEN** Claude calls `disable_task(name="example", task_id="task-0")`
- **THEN** system sets task `enabled: false` in config.json

### Requirement: validate_routine_config tool
The system SHALL provide an MCP tool `validate_routine_config` that validates a config object for schema, cron, timezone, and references.

#### Scenario: Valid config
- **WHEN** Claude calls `validate_routine_config(config={...})`
- **THEN** system returns `{"valid": true, "errors": []}`

#### Scenario: Invalid config
- **WHEN** Claude calls `validate_routine_config` with missing fields and bad cron
- **THEN** system returns `{"valid": false, "errors": [...]}`

### Requirement: preview_schedule tool
The system SHALL provide an MCP tool `preview_schedule` returning next N run times for a cron expression and timezone.

#### Scenario: Preview from routine
- **WHEN** Claude calls `preview_schedule(name="example", count=5)`
- **THEN** system returns array of 5 ISO datetime strings

#### Scenario: Preview from raw cron
- **WHEN** Claude calls `preview_schedule(cron="0 9 * * *", timezone="Europe/Rome", count=3)`
- **THEN** system returns next 3 run times

### Requirement: run_routine_now tool
The system SHALL provide an MCP tool `run_routine_now` that triggers immediate routine execution.

#### Scenario: Run routine immediately
- **WHEN** Claude calls `run_routine_now(name="example")`
- **THEN** system schedules immediate execution via APScheduler, returns execution_id

#### Scenario: Run specific task
- **WHEN** Claude calls `run_routine_now(name="example", task_id="task-0")`
- **THEN** system triggers only that task

### Requirement: get_scheduler_status tool
The system SHALL provide an MCP tool `get_scheduler_status` returning: status, started_at, last_sync_at, polling_interval_seconds, active_job_count, total_routines, enabled_routines.

#### Scenario: Get status
- **WHEN** Claude calls `get_scheduler_status`
- **THEN** system returns scheduler state from RoutineScheduler instance

### Requirement: list_running_executions tool
The system SHALL provide an MCP tool `list_running_executions` returning currently executing routines.

#### Scenario: List running
- **WHEN** Claude calls `list_running_executions`
- **THEN** system returns array from engine's execution tracking dict

### Requirement: get_execution_logs tool
The system SHALL provide an MCP tool `get_execution_logs` returning log content from disk.

#### Scenario: Get logs by routine
- **WHEN** Claude calls `get_execution_logs(name="example", limit=5)`
- **THEN** system reads last 5 log files from `routines/example/logs/`, returns content

### Requirement: list_execution_history tool
The system SHALL provide an MCP tool `list_execution_history` returning execution records with outcome and duration.

#### Scenario: History for routine
- **WHEN** Claude calls `list_execution_history(name="example", limit=10)`
- **THEN** system returns execution records from engine's history list

### Requirement: get_last_error tool
The system SHALL provide an MCP tool `get_last_error` returning the most recent error for a routine.

#### Scenario: Routine has errors
- **WHEN** Claude calls `get_last_error(name="example")`
- **THEN** system returns last recorded error with type, message, timestamp

#### Scenario: No errors
- **WHEN** Claude calls `get_last_error` and routine has no errors
- **THEN** system returns "no errors found"

### Requirement: check_filesystem_drift tool
The system SHALL provide an MCP tool `check_filesystem_drift` comparing on-disk state with in-memory scheduler state.

#### Scenario: Detect drift
- **WHEN** Claude calls `check_filesystem_drift`
- **THEN** system returns in_memory_only, on_disk_only, config_changed arrays

### Requirement: export_routine tool
The system SHALL provide an MCP tool `export_routine` returning routine as JSON (config + prompt + file list).

#### Scenario: Export routine
- **WHEN** Claude calls `export_routine(name="example")`
- **THEN** system returns JSON with config_data, prompt_text, file listing

### Requirement: import_routine tool
The system SHALL provide an MCP tool `import_routine` that creates a routine from JSON payload.

#### Scenario: Import routine
- **WHEN** Claude calls `import_routine(name="new-one", config={...}, prompt="...")`
- **THEN** system creates directory, writes files, returns routine detail

### Requirement: suggest_task_id tool
The system SHALL provide an MCP tool `suggest_task_id` generating a unique task_id.

#### Scenario: Generate task ID
- **WHEN** Claude calls `suggest_task_id(name="example")`
- **THEN** system returns a task_id not conflicting with existing tasks in that routine

### Requirement: test_startup_script tool
The system SHALL provide an MCP tool `test_startup_script` that runs a routine's startup_script in subprocess and returns output.

#### Scenario: Successful script
- **WHEN** Claude calls `test_startup_script(name="example")`
- **THEN** system runs script, returns stdout, stderr, exit_code, duration_ms

#### Scenario: No startup script
- **WHEN** Claude calls `test_startup_script` for routine without startup_script
- **THEN** system returns "no startup_script configured"

### Requirement: test_prompt tool
The system SHALL provide an MCP tool `test_prompt` that validates prompt file existence and content.

#### Scenario: Valid prompt
- **WHEN** Claude calls `test_prompt(name="example")`
- **THEN** system returns prompt length, word count, file name

#### Scenario: Missing prompt
- **WHEN** Claude calls `test_prompt` for routine without prompt file
- **THEN** system returns "no prompt file found"

### Requirement: list_available_models_tools_plugins tool
The system SHALL provide an MCP tool `list_available_models_tools_plugins` returning valid values for model_config fields.

#### Scenario: List options
- **WHEN** Claude calls `list_available_models_tools_plugins`
- **THEN** system returns models list, tools list, plugins list valid for model_config
