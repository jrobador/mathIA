from unittest.mock import patch, MagicMock

def test_graph_construction():
    """Test that the graph can be constructed without running it."""
    with patch('app.agent.graph.StateGraph') as mock_graph:
        # Mock instance
        mock_instance = MagicMock()
        mock_graph.return_value = mock_instance
        
        # Allow add_node, set_entry_point, etc. to be called without errors
        mock_instance.add_node.return_value = None
        mock_instance.add_edge.return_value = None
        mock_instance.add_conditional_edges.return_value = None
        mock_instance.set_entry_point.return_value = None
        mock_instance.compile.return_value = MagicMock()
        
        # Import here to trigger the patch
        from app.agent.graph import build_math_tutor_graph
        
        # Call the function that builds the graph
        graph = build_math_tutor_graph()
        
        # Simple check that the function returned something
        assert graph is not None
        
        # Check that key methods were called to set up the graph
        assert mock_instance.add_node.called
        assert mock_instance.set_entry_point.called
        assert mock_instance.add_conditional_edges.called

def test_api_endpoint_without_execution():
    """Test API endpoint structure without running the backend."""
    from fastapi.testclient import TestClient
    from main import app
    
    # Create a test client
    client = TestClient(app)
    
    # Just test that the API routes are registered and return something
    # even if it's an error - we're not testing functionality
    with patch('app.api.endpoints.session.active_sessions', {}):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()