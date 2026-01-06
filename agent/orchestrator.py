"""Main orchestrator using LangGraph state machine."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from agent.models import (
    AgentState,
    Task,
    TaskStatus,
    Message,
    PlanningState,
    ExecutionState,
    VerificationResult,
    TestResult,
    SubAgentTask,
)
from agent.config import AgentConfig
from agent.llm.factory import create_llm_provider
from agent.llm.base import BaseLLMProvider

# Planning components
from agent.planning.context_manager import ContextManager
from agent.planning.shell_search import ShellSearch
from agent.planning.semantic_search import SemanticSearch
from agent.planning.subagent import SubAgentDispatcher
from agent.tools.embeddings import EmbeddingManager

# Execution components
from agent.execution.mcp_client import MCPClient
from agent.execution.script_runner import ScriptRunner
from agent.execution.code_generator import CodeGenerator
from agent.tools.file_ops import FileOperations

# Verification components
from agent.verification.test_runner import TestRunner
from agent.verification.llm_judge import LLMJudge
from agent.verification.visual_verifier import VisualVerifier


class AgentOrchestrator:
    """Main orchestrator for the coding agent."""

    def __init__(self, config: AgentConfig, workspace_path: str):
        """
        Initialize orchestrator.

        Args:
            config: Agent configuration
            workspace_path: Path to workspace
        """
        self.config = config
        self.workspace_path = workspace_path

        # Initialize LLM provider
        self.llm_provider = create_llm_provider(config)

        # Initialize components
        self._init_components()

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

    def _init_components(self) -> None:
        """Initialize all agent components."""
        # Planning
        self.context_manager = ContextManager(
            self.llm_provider, self.config.context_window_size
        )
        self.shell_search = ShellSearch(self.workspace_path)
        self.embedding_manager = EmbeddingManager(self.llm_provider)
        self.semantic_search = SemanticSearch(
            self.embedding_manager,
            self.workspace_path,
            self.config.chroma_persist_directory,
        )
        self.subagent_dispatcher = SubAgentDispatcher(self.llm_provider)

        # Execution
        self.mcp_client = MCPClient()
        self.script_runner = ScriptRunner(self.workspace_path)
        self.file_ops = FileOperations(self.workspace_path)
        self.code_generator = CodeGenerator(self.llm_provider, self.file_ops)

        # Verification
        self.test_runner = TestRunner(self.workspace_path)
        self.llm_judge = LLMJudge(self.llm_provider)
        self.visual_verifier = VisualVerifier(self.mcp_client, self.workspace_path)

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("plan", self._planning_node)
        workflow.add_node("execute", self._execution_node)
        workflow.add_node("verify", self._verification_node)
        workflow.add_node("analyze", self._analysis_node)

        # Add edges
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "verify")
        workflow.add_edge("verify", "analyze")

        # Conditional edge from analyze
        workflow.add_conditional_edges(
            "analyze",
            self._should_continue,
            {
                "continue": "plan",  # Loop back to planning
                "end": END,  # End workflow
            },
        )

        return workflow.compile()

    async def _planning_node(self, state: AgentState) -> AgentState:
        """Planning phase node."""
        print(f"\n=== Planning Phase (Iteration {state.iteration + 1}) ===")

        # Update task status
        state.task.status = TaskStatus.PLANNING
        state.phase = "planning"

        # Check context and compact if needed
        if self.context_manager.should_compact():
            print("Compacting context...")
            await self.context_manager.compact_context()

        # Initialize planning state
        planning_state = PlanningState(
            task=state.task,
            conversation_history=self.context_manager.conversation_history,
        )

        # Shell search for relevant files
        print("Searching codebase...")
        file_results = self.shell_search.search_files("*.py", max_results=20)
        planning_state.search_results.extend(file_results)

        # Semantic search if available
        try:
            semantic_results = await self.semantic_search.search(
                state.task.description, max_results=5
            )
            planning_state.search_results.extend(semantic_results)
        except Exception as e:
            print(f"Semantic search unavailable: {e}")

        # Create plan using LLM
        plan_prompt = self._create_plan_prompt(state.task, planning_state)
        self.context_manager.add_message(
            Message(role="user", content=plan_prompt)
        )

        response = await self.llm_provider.generate(
            self.context_manager.get_messages(),
            temperature=0.7,
            max_tokens=2000,
        )

        planning_state.plan = response.content
        self.context_manager.add_message(
            Message(role="assistant", content=response.content)
        )

        print(f"Plan generated:\n{response.content[:500]}...")

        # Update state
        state.planning_state = planning_state
        return state

    async def _execution_node(self, state: AgentState) -> AgentState:
        """Execution phase node."""
        print("\n=== Execution Phase ===")

        state.task.status = TaskStatus.EXECUTING
        state.phase = "executing"

        if not state.planning_state or not state.planning_state.plan:
            print("No plan available, skipping execution")
            return state

        plan = state.planning_state.plan

        # Initialize execution state
        execution_state = ExecutionState(task=state.task, plan=plan)

        # Generate code changes
        print("Generating code changes...")
        try:
            # Get relevant existing files
            existing_files = {}
            for result in state.planning_state.search_results[:5]:
                try:
                    content = self.shell_search.read_file(result.source)
                    existing_files[result.source] = content
                except Exception:
                    pass

            code_changes = await self.code_generator.generate_code_changes(
                plan, existing_files
            )
            execution_state.code_changes = code_changes

            print(f"Generated {len(code_changes)} code changes")

            # Preview changes
            preview_results = self.code_generator.apply_changes(
                code_changes, preview=True
            )

            # Apply changes
            print("Applying code changes...")
            apply_results = self.code_generator.apply_changes(
                code_changes, preview=False
            )

            for result in apply_results:
                if result["success"]:
                    print(f"  ✓ {result['operation']} {result['file_path']}")
                else:
                    print(f"  ✗ {result['operation']} {result['file_path']}: {result.get('error')}")

        except Exception as e:
            print(f"Code generation failed: {e}")
            execution_state.errors.append(str(e))

        # Update state
        state.execution_state = execution_state
        return state

    async def _verification_node(self, state: AgentState) -> AgentState:
        """Verification phase node."""
        print("\n=== Verification Phase ===")

        state.task.status = TaskStatus.VERIFYING
        state.phase = "verifying"

        # Initialize verification result
        verification_result = VerificationResult(task=state.task)

        # Run tests
        print("Running tests...")
        try:
            test_result = await self.test_runner.run_tests()
            verification_result.test_results = test_result
            verification_result.tests_passed = (
                test_result.failed == 0 and test_result.passed > 0
            )

            print(
                f"Tests: {test_result.passed} passed, "
                f"{test_result.failed} failed, "
                f"{test_result.skipped} skipped"
            )

        except Exception as e:
            print(f"Test execution failed: {e}")
            verification_result.issues.append(f"Test execution error: {e}")

        # LLM judgment
        print("Evaluating code quality...")
        try:
            if state.execution_state and state.execution_state.code_changes:
                judgment = await self.llm_judge.judge_completion(
                    state.task.description,
                    state.execution_state.code_changes,
                    verification_result.test_results.output
                    if verification_result.test_results
                    else "",
                )

                verification_result.llm_judgment = judgment
                verification_result.quality_score = judgment.get("quality_score", 0.0)
                verification_result.issues.extend(judgment.get("issues", []))
                verification_result.suggestions.extend(
                    judgment.get("suggestions", [])
                )

                print(f"Quality score: {verification_result.quality_score:.2f}")

        except Exception as e:
            print(f"LLM judgment failed: {e}")

        # Update state
        state.verification_result = verification_result
        return state

    async def _analysis_node(self, state: AgentState) -> AgentState:
        """Analysis node to decide next steps."""
        print("\n=== Analysis Phase ===")

        state.iteration += 1

        # Check termination conditions
        if state.iteration >= self.config.max_iterations:
            print(f"Max iterations ({self.config.max_iterations}) reached")
            state.should_continue = False
            state.completion_reason = "max_iterations"
            state.task.status = TaskStatus.COMPLETED
            return state

        # Check if task is complete
        if state.verification_result:
            tests_passed = state.verification_result.tests_passed
            quality_good = state.verification_result.quality_score >= 0.7

            if tests_passed and quality_good:
                print("✓ Task completed successfully!")
                state.should_continue = False
                state.completion_reason = "success"
                state.task.status = TaskStatus.COMPLETED
                return state
            else:
                print(
                    f"Issues found (tests_passed={tests_passed}, "
                    f"quality={state.verification_result.quality_score:.2f}), continuing..."
                )

                # Add feedback to context for next iteration
                feedback = self._create_feedback_message(state.verification_result)
                self.context_manager.add_message(
                    Message(role="user", content=feedback)
                )

        state.should_continue = True
        return state

    def _should_continue(self, state: AgentState) -> str:
        """Conditional edge function."""
        return "continue" if state.should_continue else "end"

    def _create_plan_prompt(
        self, task: Task, planning_state: PlanningState
    ) -> str:
        """Create planning prompt."""
        search_context = "\n".join(
            [
                f"- {result.source}: {result.content[:200]}"
                for result in planning_state.search_results[:10]
            ]
        )

        return f"""Task: {task.description}

Workspace: {self.workspace_path}

Relevant Code Found:
{search_context}

Please create a detailed plan to complete this task. Include:
1. Analysis of the current code
2. Changes needed
3. Files to create/modify
4. Testing strategy

Plan:"""

    def _create_feedback_message(
        self, verification_result: VerificationResult
    ) -> str:
        """Create feedback message from verification results."""
        feedback = "The previous attempt had issues:\n\n"

        if not verification_result.tests_passed:
            feedback += "Tests failed:\n"
            if verification_result.test_results:
                feedback += f"- {verification_result.test_results.failed} tests failed\n"
                for error in verification_result.test_results.error_messages[:3]:
                    feedback += f"  - {error}\n"

        if verification_result.issues:
            feedback += "\nIssues found:\n"
            for issue in verification_result.issues[:5]:
                feedback += f"- {issue}\n"

        if verification_result.suggestions:
            feedback += "\nSuggestions:\n"
            for suggestion in verification_result.suggestions[:3]:
                feedback += f"- {suggestion}\n"

        feedback += "\nPlease revise the approach and try again."
        return feedback

    async def run(self, task: Task) -> Dict[str, Any]:
        """
        Run the agent on a task.

        Args:
            task: Task to execute

        Returns:
            Final agent state as dictionary
        """
        print(f"\n{'='*60}")
        print(f"Starting Coding Agent")
        print(f"Task: {task.description}")
        print(f"{'='*60}")

        # Initialize state
        initial_state = AgentState(
            task=task,
            iteration=0,
            conversation_history=[
                Message(
                    role="system",
                    content="You are an expert coding agent. Complete tasks by planning, executing, and verifying your work.",
                )
            ],
        )

        # Initialize context manager
        for msg in initial_state.conversation_history:
            self.context_manager.add_message(msg)

        try:
            # Run workflow
            final_state = await self.workflow.ainvoke(initial_state)

            print(f"\n{'='*60}")
            print(f"Agent Completed")
            print(f"Reason: {final_state.completion_reason}")
            print(f"Iterations: {final_state.iteration}")
            if final_state.verification_result:
                print(f"Quality Score: {final_state.verification_result.quality_score:.2f}")
            print(f"{'='*60}\n")

            return {
                "status": final_state.task.status,
                "iterations": final_state.iteration,
                "completion_reason": final_state.completion_reason,
                "verification_result": final_state.verification_result.model_dump()
                if final_state.verification_result
                else None,
            }

        except Exception as e:
            print(f"\nAgent failed with error: {e}")
            return {
                "status": TaskStatus.FAILED,
                "error": str(e),
                "iterations": initial_state.iteration,
            }

