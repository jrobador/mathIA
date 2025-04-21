import pytest
from unittest.mock import patch, AsyncMock
from app.schemas.session import LearningPath

def test_root_endpoint(client):
    """Test the root endpoint works."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "Welcome" in response.json()["message"]

def test_start_session(client, mock_graph, mock_services):
    """Test starting a new session."""
    # Patch generate_session_content_background to avoid actual execution
    with patch('app.api.endpoints.session.generate_session_content_background', new_callable=AsyncMock) as mock_gen, \
         patch('uuid.uuid4', return_value="test-session-id"):
        
        # Setup the request data
        request_data = {
            "personalized_theme": "space",
            "learning_path": LearningPath.FRACTIONS.value,
            "config": {
                "enable_audio": True
            }
        }
        
        # Make the request
        response = client.post("/session/start", json=request_data)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-id"
        assert data["status"] == "initializing"
        assert "initial_output" in data
        
        # Verify background task was called
        assert mock_gen.called

def test_process_input(client, mock_graph, mock_active_sessions):
    """Test processing user input for an existing session."""
    # Make the request to process input
    response = client.post(
        "/session/test-session-id/process",
        json={"message": "My answer is 3/4"}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-id"
    assert "agent_output" in data

def test_get_session_status(client, mock_active_sessions):
    """Test getting session status."""
    # Make the request
    response = client.get("/session/test-session-id/status")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-id"
    assert data["current_topic"] == "fractions_introduction"
    assert data["is_active"] is True

def test_end_session(client, mock_active_sessions):
    """Test ending a session."""
    # Make the request
    response = client.delete("/session/test-session-id")
    
    # Check response
    assert response.status_code == 204

def test_session_not_found(client):
    """Test behavior when session is not found."""
    response = client.get("/session/nonexistent-session/status")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_node_functions():
    """Test individual node functions directly."""
    from app.agent.nodes import determine_next_step
    
    # Create a test state
    state = {
        "current_topic": "fractions_introduction",
        "topic_mastery": {"fractions_introduction": 0.1},
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "last_action_type": None,
        "theory_presented_for_topics": []
    }
    
    # Test with various mocks
    with patch('app.services.azure_openai.invoke_with_prompty', new_callable=AsyncMock) as mock_invoke, \
         patch('app.services.azure_image.generate_image', new_callable=AsyncMock) as mock_image, \
         patch('app.services.azure_speech.generate_speech', new_callable=AsyncMock) as mock_speech:
        
        # Configure mocks
        mock_invoke.return_value = "Mocked response"
        mock_image.return_value = "http://example.com/image.png" 
        mock_speech.return_value = "http://example.com/audio.mp3"
        
        # Test the determine_next_step function
        result = await determine_next_step(state)
        
        # Check it returns the expected structure
        assert isinstance(result, dict)
        assert "next" in result