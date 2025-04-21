import pytest
from app.agent.roadmap import (
    get_roadmap, get_next_topic_id, get_topic_sequence, get_all_roadmaps_info,
    get_roadmap_topic_info, LearningRoadmap, RoadmapTopic, AVAILABLE_ROADMAPS
)

class TestRoadmapFunctions:
    """Tests for roadmap functionality and topic progression."""
    
    def test_get_roadmap(self):
        """Test retrieving a roadmap by ID."""
        # Get an existing roadmap
        fractions_roadmap = get_roadmap("fractions")
        assert fractions_roadmap is not None
        assert fractions_roadmap.id == "fractions"
        assert fractions_roadmap.title == "Fractions"
        
        # Try to get a non-existent roadmap
        nonexistent_roadmap = get_roadmap("nonexistent")
        assert nonexistent_roadmap is None
    
    def test_get_topic_sequence(self):
        """Test retrieving a sequence of topics for a roadmap."""
        # Get sequence for fractions roadmap
        fractions_sequence = get_topic_sequence("fractions")
        assert isinstance(fractions_sequence, list)
        assert len(fractions_sequence) > 0
        assert "fractions_introduction" in fractions_sequence
        
        # First topic should be introduction
        assert fractions_sequence[0] == "fractions_introduction"
        
        # Test getting sequence for non-existent roadmap
        nonexistent_sequence = get_topic_sequence("nonexistent")
        assert nonexistent_sequence == []
    
    def test_get_next_topic_id(self):
        """Test determining the next topic ID in a sequence."""
        # Test valid progression through fractions roadmap
        assert get_next_topic_id("fractions", "fractions_introduction") == "fractions_equivalent"
        assert get_next_topic_id("fractions", "fractions_equivalent") == "fractions_comparison"
        
        # Test last topic in roadmap (should return None)
        last_topic = get_topic_sequence("fractions")[-1]
        assert get_next_topic_id("fractions", last_topic) is None
        
        # Test invalid topic ID
        assert get_next_topic_id("fractions", "invalid_topic") is None
        
        # Test invalid roadmap ID
        assert get_next_topic_id("invalid_roadmap", "fractions_introduction") is None
    
    def test_get_all_roadmaps_info(self):
        """Test retrieving info about all available roadmaps."""
        roadmaps_info = get_all_roadmaps_info()
        assert isinstance(roadmaps_info, list)
        assert len(roadmaps_info) >= 5  # Should have at least 5 roadmaps
        
        # Verify structure of info
        for info in roadmaps_info:
            assert "id" in info
            assert "title" in info
            assert "description" in info
            assert "topic_count" in info
    
    def test_get_roadmap_topic_info(self):
        """Test retrieving detailed info about a specific topic."""
        # Get info for a topic with prerequisites
        fraction_addition_info = get_roadmap_topic_info("fractions", "fractions_addition")
        assert fraction_addition_info is not None
        assert fraction_addition_info["title"] == "Adding Fractions"
        assert "prerequisite_topics" in fraction_addition_info
        assert len(fraction_addition_info["prerequisite_topics"]) > 0
        
        # Check next topic information
        assert fraction_addition_info["next_topic"]["id"] == "fractions_subtraction"
        
        # Get info for the first topic
        first_topic_info = get_roadmap_topic_info("fractions", "fractions_introduction")
        assert first_topic_info is not None
        assert len(first_topic_info.get("prerequisite_topics", [])) == 0
        
        # Get info for the last topic
        last_topic = get_topic_sequence("fractions")[-1]
        last_topic_info = get_roadmap_topic_info("fractions", last_topic)
        assert last_topic_info is not None
        assert last_topic_info["next_topic"] is None
        
        # Test invalid topic/roadmap
        assert get_roadmap_topic_info("fractions", "invalid_topic") is None
        assert get_roadmap_topic_info("invalid_roadmap", "fractions_introduction") is None
    
    def test_roadmap_classes(self):
        """Test the RoadmapTopic and LearningRoadmap classes."""
        # Create a test topic
        topic = RoadmapTopic(
            id="test_topic",
            title="Test Topic",
            description="A test topic for unit testing",
            prerequisites=["prerequisite_topic"],
            required_mastery=0.8,
            subtopics=["Concept A", "Concept B"]
        )
        
        # Test topic properties
        assert topic.id == "test_topic"
        assert topic.title == "Test Topic"
        assert topic.required_mastery == 0.8
        assert len(topic.subtopics) == 2
        
        # Test topic to_dict conversion
        topic_dict = topic.to_dict()
        assert topic_dict["id"] == "test_topic"
        assert topic_dict["prerequisites"] == ["prerequisite_topic"]
        
        # Create a test roadmap with topics
        topics = [
            topic,
            RoadmapTopic(id="test_topic_2", title="Test Topic 2", description="Another test topic")
        ]
        
        roadmap = LearningRoadmap(
            id="test_roadmap",
            title="Test Roadmap",
            description="A test roadmap for unit testing",
            topics=topics
        )
        
        # Test roadmap properties
        assert roadmap.id == "test_roadmap"
        assert len(roadmap.topics) == 2
        
        # Test get_topic_ids
        topic_ids = roadmap.get_topic_ids()
        assert topic_ids == ["test_topic", "test_topic_2"]
        
        # Test get_topic_by_id
        retrieved_topic = roadmap.get_topic_by_id("test_topic")
        assert retrieved_topic is not None
        assert retrieved_topic.id == "test_topic"
        
        # Test get_next_topic
        next_topic = roadmap.get_next_topic("test_topic")
        assert next_topic is not None
        assert next_topic.id == "test_topic_2"
        
        # Test no next topic at the end
        assert roadmap.get_next_topic("test_topic_2") is None
        
        # Test roadmap to_dict conversion
        roadmap_dict = roadmap.to_dict()
        assert roadmap_dict["id"] == "test_roadmap"
        assert len(roadmap_dict["topics"]) == 2