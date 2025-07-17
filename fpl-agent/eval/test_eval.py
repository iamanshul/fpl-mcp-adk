import os
import pytest
import json
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Import the necessary ADK components
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types as genai_types

# Import your agent
from fpl_agent.agent import root_agent as fpl_root_agent

# --- Test Configuration ---
CURRENT_DIR = Path(__file__).parent
EVAL_DATA_DIR = CURRENT_DIR / "eval_data"
FPL_EVAL_SET_FILENAME = "fpl_eval_cases.test.json"


def load_eval_set(eval_set_name: str) -> list[dict]:
    """Loads the JSON evaluation file."""
    eval_set_path = EVAL_DATA_DIR / eval_set_name
    if not eval_set_path.exists():
        pytest.fail(f"Evaluation set not found: {eval_set_path}")
    try:
        with open(eval_set_path, "r") as f:
            return json.load(f)
    except Exception as e:
        pytest.fail(f"Error loading evaluation set {eval_set_path}: {e}")

# --- Pytest Fixtures ---
@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Loads the .env file."""
    load_dotenv(find_dotenv(".env"))

@pytest.fixture(scope="session")
def agent_runner() -> Runner:
    """Creates a single instance of the ADK Runner for all tests."""
    return Runner(
        agent=fpl_root_agent,
        app_name="fpl_agent",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService()
    )
@pytest.mark.parametrize("eval_case", load_eval_set(FPL_EVAL_SET_FILENAME))
@pytest.mark.asyncio
async def test_fpl_agent_custom_evaluation(eval_case: dict, agent_runner: Runner):
    """
    Runs a single evaluation case against the FPL agent.
    """
    query = eval_case.get("query")
    eval_case_id = eval_case.get("id", "unknown_id")
    expected_tool_calls = eval_case.get("expected_tool_calls", [])
    expected_output_contains = eval_case.get("expected_output_contains", [])
    expected_output_not_contains = eval_case.get("expected_output_not_contains", [])

    assert query is not None, f"Eval case {eval_case_id} is missing 'query'."
    print(f"\n--- Running Eval Case: {eval_case_id} ---")

    test_user_id = "test_eval_user"
    test_session_id = f"test_session_{eval_case_id}"

    # --- THIS IS THE FIX ---
    # The session service methods are asynchronous and must be awaited.
    try:
        session = await agent_runner.session_service.get_session(
            app_name=agent_runner.app_name, user_id=test_user_id, session_id=test_session_id
        )
        if not session:
            session = await agent_runner.session_service.create_session(
                app_name=agent_runner.app_name, user_id=test_user_id, session_id=test_session_id
            )
    except Exception as e:
        pytest.fail(f"Failed to create or get session {test_session_id}: {e}")
    # ----------------------------------------------------------------

    user_message = genai_types.Content(parts=[genai_types.Part(text=query)], role="user")
    final_response_text = ""
    actual_tool_calls = []

    async for event in agent_runner.run_async(
        user_id=test_user_id,
        session_id=test_session_id,
        new_message=user_message
    ):
        function_calls = event.get_function_calls()
        if function_calls:
            for fc in function_calls:
                print(f"Tool Call Detected: {fc.name}")
                actual_tool_calls.append(fc.name)
        if event.is_final_response():
            if event.content and event.content.parts and event.content.parts[0].text:
                final_response_text = event.content.parts[0].text.lower()
                break

    assert final_response_text, f"Agent did not produce a final response for {eval_case_id}."
    print(f"Final Response: '{final_response_text[:200]}...'")

    if expected_tool_calls:
        for expected_tool in expected_tool_calls:
            assert expected_tool in actual_tool_calls, \
                f"Case {eval_case_id}: Expected to call '{expected_tool}', but called {actual_tool_calls}"

    for substring in expected_output_contains:
        assert substring.lower() in final_response_text, \
            f"Case {eval_case_id}: Expected output to contain '{substring}'."

    for substring in expected_output_not_contains:
        assert substring.lower() not in final_response_text, \
            f"Case {eval_case_id}: Expected output NOT to contain '{substring}'."

    print(f"--- PASSED: {eval_case_id} ---")