"""Run a single routine immediately, skipping the cron scheduler.

Usage:
    python -m tests.test_routine <routine-dir-name>

Example:
    python -m tests.test_routine mytaskly-api-status
"""

import asyncio
import sys

from scheduler.routine import RoutineConfig


async def run_routine(routine_dir_name: str) -> None:
    config = RoutineConfig(routine_dir_name).load()

    if not config.config_data:
        print(f"ERRORE: config.json non trovato per '{routine_dir_name}'")
        sys.exit(1)

    if not config.prompt_text:
        print(f"ERRORE: nessun file prompt trovato per '{routine_dir_name}'")
        sys.exit(1)

    scheduler = config.config_data.get("scheduler", {})
    tasks = scheduler.get("tasks", [])

    if not tasks:
        print(f"ATTENZIONE: nessun task definito in config.json per '{routine_dir_name}'. Eseguo con parametri di default.")
        job_name = routine_dir_name
        cron_expression = "* * * * *"
    else:
        task = tasks[0]
        job_name = task.get("job_name", routine_dir_name)
        cron_expression = task.get("schedule", {}).get("expression", "* * * * *")

    print(f"--- Test routine: {routine_dir_name} ---")
    print(f"    job: {job_name}")
    print(f"    cron: {cron_expression}")
    print(f"    model: {config.model_config.get('model', 'sonnet')}")
    
    docker_config = config.config_data.get("docker", {})
    if docker_config.get("enabled"):
        print(f"    docker: ENABLED (image: {docker_config.get('image', 'node:20')}, network: {docker_config.get('network', 'bridge')})")
    else:
        print(f"    docker: DISABLED")
        
    print()

    startup_script = config.startup_script_for(job_name, cron_expression)
    routine_path = config.routine_path

    if startup_script:
        from scheduler.routine import Routine

        Routine._setup(
            Routine(
                routine_dir_name=routine_dir_name,
                routine_name=job_name,
                timezone=scheduler.get("timezone", "UTC"),
                cron_expression=cron_expression,
            ),
            startup_script,
        )

    agent_options = config.build_agent_options()
    
    # Aumentiamo esplicitamente il timeout di caricamento se Docker è abilitato
    if agent_options.sandbox:
        agent_options.load_timeout_ms = max(agent_options.load_timeout_ms, 300000) # 5 minuti
        
    prompt = config.prompt_text.strip()

    from scheduler.agent import ClaudeAgent

    agent = ClaudeAgent(options=agent_options)
    await agent.run(prompt=prompt)

    print(f"--- Routine '{routine_dir_name}' completata ---")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tests.test_routine <routine-dir-name>")
        print("\nRoutine disponibili:")
        from scheduler.loader import discover_routines

        for d in discover_routines():
            print(f"  - {d.name}")
        sys.exit(1)

    asyncio.run(run_routine(sys.argv[1]))


if __name__ == "__main__":
    main()
