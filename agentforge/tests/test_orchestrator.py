import os
from unittest.mock import patch

# Set a dummy API key before importing Orchestrator so ChatOpenAI doesn't crash on init
os.environ["OPENAI_API_KEY"] = "mock-key"

from agentforge.orchestrator import Orchestrator
from agentforge.logger import AgentLogger

async def main():
    logger = AgentLogger("test_runner")
    
    # Initialize the Orchestrator
    orchestrator = Orchestrator()

    # Mock the LLM's structured output
    class MockLLM:
        async def ainvoke(self, prompt):
            # We return pre-defined structured outputs for testing
            from agentforge.agents.schemas import Plan, PlanItem
            
            # The word 'parallel' is in the orchestrator's system prompt, 
            # so we explicitly check for the user task's unique keywords
            if "Payment Gateway Timeout" in prompt:
                return Plan(items=[
                    PlanItem(agent="triage", subtask="Triage latest bugs", confidence=1.0, parallel=True),
                    PlanItem(agent="dev", subtask="Create issue", confidence=0.9, parallel=True)
                ])
            elif "Generate my daily standup report" in prompt:
                return Plan(items=[
                    PlanItem(agent="standup", subtask="Report standup", confidence=0.99, parallel=False)
                ])
            else:
                 return Plan(items=[
                    PlanItem(agent="standup", subtask="Daily Standup", confidence=0.9, parallel=False),
                    PlanItem(agent="triage", subtask="Triage Severity 1 bugs", confidence=0.85, parallel=False),
                    PlanItem(agent="dev", subtask="Refactor authentication", confidence=0.9, parallel=False)
                ])

    # We patch the Orchestrator's internal LLM
    class MockStructured:
        def __init__(self, mock_llm):
            self.llm = mock_llm
            
        def with_structured_output(self, schema):
            return self.llm

    orchestrator.llm = MockStructured(MockLLM())

    # Mock the agents so they don't do real requests
    class MockAgent:
        async def run(self, subtask, state):
            # simulate some async work
            await asyncio.sleep(0.1)
            return {
                'success': True, 
                'output': f"Mock successfully completed: {subtask}", 
                'actions_taken': [f"Did action for: {subtask}"]
            }

    # Replace the actual agent registry with our mocks
    import agentforge.orchestrator
    original_registry = agentforge.orchestrator.AGENT_REGISTRY
    agentforge.orchestrator.AGENT_REGISTRY = {
        key: MockAgent for key in original_registry
    }

    # Real-life scenario simulations
    scenarios = [
        "Generate my daily standup report and post it to Notion and Slack.",
        "Please triage the latest github issues, classify them, and parallel to that create a new GitHub issue tracking the 'Payment Gateway Timeout' bug.",
        "Run my daily standup, triage any new severity 1 bugs, and create an issue about refactoring the authentication module."
    ]

    for i, task in enumerate(scenarios, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Running Scenario {i}")
        logger.info(f"User Request: {task}")
        logger.info(f"{'='*80}\n")
        
        try:
            await orchestrator.run(task)
        except Exception as e:
            logger.error(f"Scenario {i} encountered an error: {e}")
            
        print("\n")
        
    # Restore original registry
    agentforge.orchestrator.AGENT_REGISTRY = original_registry
    logger.info("All simulation scenarios completed.")

if __name__ == "__main__":
    asyncio.run(main())
