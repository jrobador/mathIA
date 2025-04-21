def test_parallel_session_isolation():
    """Test that multiple sessions maintain isolated state."""
    from fastapi.testclient import TestClient
    from main import app
    
    with TestClient(app) as client:
        # Create two sessions with different themes and topics
        session1_response = client.post("/session/start", json={
            "personalized_theme": "space",
            "learning_path": "fractions"
        })
        session1_id = session1_response.json()["session_id"]
        
        session2_response = client.post("/session/start", json={
            "personalized_theme": "ocean",
            "learning_path": "addition"
        })
        session2_id = session2_response.json()["session_id"]
        
        # Mock the background task completion
        from app.api.endpoints.session import active_sessions
        active_sessions[session1_id]["content_ready"] = True
        active_sessions[session2_id]["content_ready"] = True
        
        # Get status of both sessions
        status1 = client.get(f"/session/{session1_id}/status")
        status2 = client.get(f"/session/{session2_id}/status")
        
        # Verify sessions have different state
        assert status1.json()["current_topic"].startswith("fractions")
        assert status2.json()["current_topic"].startswith("addition")
        
        # Process input for session1
        client.post(f"/session/{session1_id}/process", json={"message": "My answer is 1/2"})
        
        # Verify processing didn't affect session2
        status2_after = client.get(f"/session/{session2_id}/status")
        assert status2_after.json()["last_updated"] == status2.json()["last_updated"]