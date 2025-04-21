import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import asyncio

# Import your FastAPI app
from main import app

# Configure asyncio for testing
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as asyncio coroutine")

# Create a test client fixture
@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client

# Mock service fixtures
@pytest.fixture
def mock_services():
    """Fixture to mock all external services."""
    with patch('app.services.azure_openai.invoke_with_prompty', new_callable=AsyncMock) as mock_invoke, \
         patch('app.services.azure_image.generate_image', new_callable=AsyncMock) as mock_image, \
         patch('app.services.azure_speech.generate_speech', new_callable=AsyncMock) as mock_speech:
        
        # Configure dummy responses
        mock_invoke.return_value = "Mocked LLM response"
        mock_image.return_value = "http://example.com/mock-image.png"
        mock_speech.return_value = "http://example.com/mock-audio.mp3"
        
        yield {
            'invoke': mock_invoke,
            'image': mock_image,
            'speech': mock_speech
        }

@pytest.fixture
def mock_graph():
    """Fixture to mock the LangGraph functionality."""
    with patch('app.agent.graph.get_compiled_app') as mock_get_app:
        # Create mock graph instance
        mock_app = AsyncMock()
        mock_get_app.return_value = mock_app
        
        # Create default mock response
        mock_result = {
            "current_topic": "fractions_introduction",
            "topic_mastery": {"fractions_introduction": 0.3},
            "current_step_output": {
                "text": "Mocked output from the graph",
                "prompt_for_answer": False
            },
            "next": "determine_next_step"
        }
        mock_app.ainvoke.return_value = mock_result
        
        yield mock_app

@pytest.fixture
def mock_active_sessions():
    """Fixture to mock the active_sessions dictionary."""
    mock_session = {
        "test-session-id": {
            "state": {
                "current_topic": "fractions_introduction",
                "current_cpa_phase": "Concrete",
                "topic_mastery": {"fractions_introduction": 0.3},
                "current_step_output": {
                    "text": "Let's learn about fractions!",
                    "prompt_for_answer": False
                },
                "theory_presented_for_topics": ["fractions_introduction"],
                "consecutive_correct": 0,
                "consecutive_incorrect": 0
            },
            "created_at": 1682600000.0,
            "last_updated": 1682600100.0,
            "content_ready": True
        }
    }
    
    with patch('app.api.endpoints.session.active_sessions', mock_session):
        yield mock_session