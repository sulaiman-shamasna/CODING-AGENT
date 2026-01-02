"""Unit tests for data models."""

import pytest
from agent.models import Task, TaskStatus, Message, AgentState


def test_task_creation():
    """Test task creation."""
    task = Task(
        id="test_1",
        description="Test task",
        workspace_path="/workspace",
        created_at="2024-01-01T00:00:00",
    )
    assert task.status == TaskStatus.PENDING
    assert task.description == "Test task"


def test_message_creation():
    """Test message creation."""
    message = Message(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"


def test_agent_state():
    """Test agent state creation."""
    task = Task(
        id="test_1",
        description="Test",
        workspace_path="/workspace",
        created_at="2024-01-01",
    )
    state = AgentState(task=task)
    assert state.iteration == 0
    assert state.should_continue is True
    assert state.phase == "planning"

