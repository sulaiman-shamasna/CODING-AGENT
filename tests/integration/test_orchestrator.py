"""Integration tests for orchestrator."""

import pytest
from agent.config import AgentConfig
from agent.models import Task
from agent.orchestrator import AgentOrchestrator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    config = AgentConfig()
    orchestrator = AgentOrchestrator(config, "/tmp/test_workspace")

    assert orchestrator.llm_provider is not None
    assert orchestrator.context_manager is not None
    assert orchestrator.workflow is not None


@pytest.mark.integration
def test_workflow_building():
    """Test workflow graph building."""
    config = AgentConfig()
    orchestrator = AgentOrchestrator(config, "/tmp/test_workspace")

    # Workflow should be compiled
    assert orchestrator.workflow is not None

