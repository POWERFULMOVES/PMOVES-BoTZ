# A2A Protocol Skill

**Slice:** `slices/a2a/`
**Type:** Agent-to-Agent Communication

## Purpose

Agent-to-Agent protocol for delegating tasks to remote agents. Use this skill when:
- Work needs to be delegated to a specialized agent
- Multiple agents need to collaborate on a task
- Remote agent capabilities need to be discovered

## Quick Start

```python
from slices.a2a import A2AService

service = A2AService()

# Discover agent
agent = service.discover("http://code-runner:7000")
print(f"Agent: {agent.name}")
print(f"Capabilities: {agent.capabilities}")

# Delegate task
result = service.delegate(
    agent_url="http://code-runner:7000",
    skill_id="code_execution",
    message="Run pytest tests/ -v",
    timeout=120.0,
)
print(f"State: {result.state.value}")
print(f"Output: {result.artifacts[0].content}")
```

## API Reference

### A2AService

| Method | Description | Returns |
|--------|-------------|---------|
| `discover(url)` | Discover agent capabilities | `RemoteAgent` |
| `delegate(url, skill_id, message)` | Execute task on remote agent | `Task` |
| `list_registered_agents()` | List discovered agents | `List[RemoteAgent]` |
| `broadcast(skill_id, message)` | Send to multiple agents | `Dict[str, Task]` |

### Task States

| State | Description |
|-------|-------------|
| `submitted` | Task created, not started |
| `working` | Task in progress |
| `input-required` | Waiting for user input |
| `completed` | Task finished successfully |
| `failed` | Task failed with error |
| `cancelled` | Task was cancelled |

## A2A Protocol Overview

The A2A (Agent-to-Agent) protocol enables interoperability:

1. **Discovery**: Agents expose capabilities at `/.well-known/agent.json`
2. **Task Creation**: JSON-RPC 2.0 at `/a2a/v1/tasks`
3. **Lifecycle**: submitted → working → completed/failed
4. **Streaming**: SSE at `/a2a/v1/tasks/{id}/stream`

## Example: Multi-Agent Workflow

```python
# Step 1: Discover available agents
research_agent = service.discover("http://researcher:7000")
code_agent = service.discover("http://code-runner:7000")

# Step 2: Research phase
research_result = service.delegate(
    agent_url="http://researcher:7000",
    skill_id="deep_research",
    message="Research best practices for Python async",
)

# Step 3: Code phase with research context
code_result = service.delegate(
    agent_url="http://code-runner:7000",
    skill_id="code_generation",
    message=f"Implement async handler based on: {research_result.summary}",
)
```

## Integration Points

| Endpoint | Purpose |
|----------|---------|
| `/.well-known/agent.json` | Agent Card discovery |
| `/a2a/v1/tasks` | Task management |
| `/a2a/v1/tasks/{id}/stream` | SSE streaming |
| `/a2a/health` | Health check |

## Agent Card Structure

```json
{
  "name": "PMOVES Code Executor",
  "description": "Secure code execution agent",
  "version": "1.0.0",
  "capabilities": [
    {"id": "code_execution", "name": "Code Execution"}
  ],
  "skills": [
    {"id": "python_run", "name": "Python Runner"}
  ]
}
```

## Best Practices

1. **Always discover first**: Check capabilities before delegating
2. **Set appropriate timeouts**: Long tasks need longer timeouts
3. **Handle failures gracefully**: Check task.state before accessing artifacts
4. **Use metadata**: Pass context via metadata for traceability
