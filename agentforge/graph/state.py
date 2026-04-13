from typing import TypedDict

class AgentForgeState(TypedDict):
    task: str               # Original plain English Task
    subtasks: list[str]     # [{agent, description, status}]
    results: list[dict]     # [{agent, output, success}]
    current_agent: str      # Which agent is running now
    iteration: int          # Loop Guard
    completed: bool         # All subtasks done?
    audit_log: list[str]    # Every action taken