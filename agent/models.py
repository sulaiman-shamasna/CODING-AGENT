"""Data models for the coding agent."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Represents a user task/request."""

    id: str = Field(description="Unique task identifier")
    description: str = Field(description="Task description from user")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    workspace_path: str = Field(description="Path to the workspace/codebase")
    created_at: str = Field(description="Task creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """A message in the conversation history."""

    role: str = Field(description="Message role: system, user, or assistant")
    content: str = Field(description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Result from a search operation."""

    source: str = Field(description="Source of the result (file path, etc.)")
    content: str = Field(description="Result content")
    relevance_score: float = Field(default=0.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanningState(BaseModel):
    """State during the planning phase."""

    task: Task
    conversation_history: List[Message] = Field(default_factory=list)
    context_size: int = Field(default=0, description="Current context window usage")
    search_results: List[SearchResult] = Field(default_factory=list)
    plan: Optional[str] = Field(default=None, description="Generated execution plan")
    sub_agent_results: List[Dict[str, Any]] = Field(default_factory=list)


class CodeChange(BaseModel):
    """Represents a code change to be applied."""

    file_path: str = Field(description="Path to the file to modify")
    operation: str = Field(description="Operation: create, update, or delete")
    content: Optional[str] = Field(default=None, description="New file content")
    diff: Optional[str] = Field(default=None, description="Diff of changes")


class ExecutionState(BaseModel):
    """State during the execution phase."""

    task: Task
    plan: str = Field(description="Execution plan from planning phase")
    code_changes: List[CodeChange] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    script_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Result from running tests."""

    framework: str = Field(description="Test framework used")
    passed: int = Field(default=0, description="Number of tests passed")
    failed: int = Field(default=0, description="Number of tests failed")
    skipped: int = Field(default=0, description="Number of tests skipped")
    output: str = Field(default="", description="Test output")
    error_messages: List[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Result from the verification phase."""

    task: Task
    tests_passed: bool = Field(default=False, description="Whether tests passed")
    test_results: Optional[TestResult] = Field(default=None)
    llm_judgment: Optional[Dict[str, Any]] = Field(default=None)
    quality_score: float = Field(default=0.0, description="Overall quality score (0-1)")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class AgentState(BaseModel):
    """Overall agent state for LangGraph."""

    task: Task
    iteration: int = Field(default=0, description="Current iteration number")
    phase: str = Field(default="planning", description="Current phase")
    conversation_history: List[Message] = Field(default_factory=list)
    
    # Phase-specific states
    planning_state: Optional[PlanningState] = Field(default=None)
    execution_state: Optional[ExecutionState] = Field(default=None)
    verification_result: Optional[VerificationResult] = Field(default=None)
    
    # Control flags
    should_continue: bool = Field(default=True, description="Whether to continue looping")
    completion_reason: Optional[str] = Field(
        default=None, description="Reason for completion"
    )
    
    # Results
    final_output: Optional[Dict[str, Any]] = Field(default=None)


class SubAgentTask(BaseModel):
    """Task for a sub-agent."""

    id: str = Field(description="Sub-agent task identifier")
    specialization: str = Field(description="Sub-agent specialization type")
    description: str = Field(description="Task description for sub-agent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context for sub-agent")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Sub-agent result")


class ToolCall(BaseModel):
    """Represents a tool invocation."""

    tool_name: str = Field(description="Name of the tool")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = Field(default=None)
    error: Optional[str] = Field(default=None)

