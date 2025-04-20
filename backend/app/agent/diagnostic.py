# -*- coding: utf-8 -*-
"""
Utilities for processing diagnostic results and adapting the agent's state.

This module contains functions to interpret the results of the initial 
diagnostic test and configure the student's learning state accordingly.
"""

from typing import Dict, List, Any, Optional
from enum import Enum

class DifficultySetting(str, Enum):
    """Enum representing possible difficulty levels."""
    INITIAL = "initial"     # Default starting level before assessment
    BEGINNER = "beginner"   # Low starting point
    INTERMEDIATE = "intermediate" # Medium starting point
    ADVANCED = "advanced"     # High starting point

class DiagnosticResult:
    """Represents the result of a complete diagnostic test."""
    def __init__(
        self,
        score: float, # Overall score, potentially normalized or weighted
        correct_answers: int, # Number of questions answered correctly
        total_questions: int, # Total number of questions in the diagnostic
        recommended_level: DifficultySetting, # Suggested starting difficulty based on performance
        question_results: Optional[List[Dict[str, Any]]] = None # Detailed results per question
    ):
        self.score = score
        self.correct_answers = correct_answers
        self.total_questions = total_questions
        self.recommended_level = recommended_level
        # List of dicts, where each dict has info like {"question_id": "q1", "correct": True, "concept_tested": "fractions_addition"}
        self.question_results = question_results or [] 
    
    @property
    def percent_correct(self) -> float:
        """Returns the percentage of correct answers."""
        if not self.total_questions: # Avoid division by zero
            return 0.0
        return (self.correct_answers / self.total_questions) * 100.0 # Ensure float division and percentage
    
    def get_strengths(self) -> List[str]:
        """Identifies strengths (concepts answered correctly) based on question results."""
        if not self.question_results:
            return []
        
        strengths = {} # Dictionary to count correct answers per concept
        for question in self.question_results:
            # Check if the question was correct and tagged with a concept
            if question.get("correct", False) and "concept_tested" in question:
                concept = question["concept_tested"]
                strengths[concept] = strengths.get(concept, 0) + 1
        
        # Return concepts where at least one question was answered correctly
        return [concept for concept, count in strengths.items() if count > 0]
    
    def get_weaknesses(self) -> List[str]:
        """Identifies weaknesses (concepts answered incorrectly) based on question results."""
        if not self.question_results:
            return []
        
        weaknesses = {} # Dictionary to count incorrect answers per concept
        for question in self.question_results:
            # Check if the question was incorrect (not True) and tagged with a concept
            # Note: Defaults `correct` to True if missing, meaning missing 'correct' flag isn't counted as weakness.
            if not question.get("correct", True) and "concept_tested" in question: 
                concept = question["concept_tested"]
                weaknesses[concept] = weaknesses.get(concept, 0) + 1
        
        # Return all concepts where at least one question was answered incorrectly
        return [concept for concept, count in weaknesses.items() if count > 0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the diagnostic result object to a dictionary."""
        return {
            "score": self.score,
            "correct_answers": self.correct_answers,
            "total_questions": self.total_questions,
            "recommended_level": self.recommended_level.value, # Store enum value
            "percent_correct": self.percent_correct,
            "strengths": self.get_strengths(),
            "weaknesses": self.get_weaknesses(),
            "question_results": self.question_results # Include detailed results
        }

def difficulty_to_mastery_level(difficulty: DifficultySetting) -> float:
    """
    Converts a recommended difficulty setting to an initial mastery level (0.0-1.0).
    Higher difficulty implies higher assumed starting mastery for the initial topic.
    
    Args:
        difficulty: The recommended DifficultySetting enum value.
    
    Returns:
        An initial mastery level float between 0.0 and 1.0.
    """
    mapping = {
        DifficultySetting.INITIAL: 0.1,    # Very low starting point
        DifficultySetting.BEGINNER: 0.3,   # Low starting point
        DifficultySetting.INTERMEDIATE: 0.5, # Medium starting point
        DifficultySetting.ADVANCED: 0.7    # Higher starting point (still needs practice)
    }
    # Return the mapped value, or default to INITIAL level if difficulty is not found
    return mapping.get(difficulty, mapping[DifficultySetting.INITIAL]) 

def apply_diagnostic_to_state(state: Dict[str, Any], diagnostic: DiagnosticResult) -> Dict[str, Any]:
    """
    Applies the results from a diagnostic test to the student's session state.
    Updates initial mastery and potentially the starting CPA phase based on the diagnostic.
    
    Args:
        state: The current student session state dictionary.
        diagnostic: The DiagnosticResult object containing test results.
    
    Returns:
        The updated student session state dictionary.
    """
    # Get the initial mastery level based on the recommended difficulty
    mastery_level = difficulty_to_mastery_level(diagnostic.recommended_level)
    
    # Update topic_mastery for the *current* topic in the state
    # Assumes the diagnostic relates primarily to the starting topic.
    # More complex logic could update multiple topics based on question_results.
    current_topic = state.get("current_topic", "fractions_introduction") # Get current or default topic
    if "topic_mastery" not in state:
        state["topic_mastery"] = {} # Initialize mastery dict if it doesn't exist
    
    # Set the initial mastery for the current topic
    state["topic_mastery"][current_topic] = mastery_level
    
    # Adjust the starting CPA phase based on the initial mastery level
    if mastery_level < 0.3:
        state["current_cpa_phase"] = "Concrete"
    elif mastery_level < 0.6:
        state["current_cpa_phase"] = "Pictorial"
    else:
        state["current_cpa_phase"] = "Abstract"
        
    # Store the full diagnostic results dictionary in the state for reference
    state["diagnostic_results"] = diagnostic.to_dict()
    
    print(f"Applied diagnostic: Topic '{current_topic}' mastery set to {mastery_level:.2f}, phase set to {state['current_cpa_phase']}")
    
    return state

def create_diagnostic_result_from_json(data: Dict[str, Any]) -> Optional[DiagnosticResult]:
    """
    Safely creates a DiagnosticResult object from a JSON-like dictionary.
    Handles potential type errors or missing keys.
    
    Args:
        data: Dictionary containing diagnostic data (e.g., parsed from JSON).
    
    Returns:
        A DiagnosticResult object if the data is valid, otherwise None.
    """
    if not isinstance(data, dict): # Ensure input is a dictionary
        return None
    
    try:
        # Extract and cast values, providing defaults
        score = float(data.get("score", 0.0))
        correct_answers = int(data.get("correct_answers", 0))
        total_questions = int(data.get("total_questions", 0))
        
        # Convert recommended_level string (e.g., "beginner") to DifficultySetting enum
        level_str = data.get("recommended_level", "initial") # Default to "initial"
        try:
            recommended_level = DifficultySetting(level_str.lower()) # Convert to lowercase for robustness
        except ValueError:
            print(f"Warning: Invalid recommended_level '{level_str}' received. Defaulting to INITIAL.")
            recommended_level = DifficultySetting.INITIAL # Default if string is invalid
        
        # Get question results list, default to empty list
        question_results = data.get("question_results", [])
        if not isinstance(question_results, list): # Ensure it's a list
             print(f"Warning: 'question_results' is not a list. Setting to empty.")
             question_results = []

        # Create and return the DiagnosticResult object
        return DiagnosticResult(
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            recommended_level=recommended_level,
            question_results=question_results
        )
    except (ValueError, TypeError) as e:
        # Handle potential errors during casting (e.g., float("abc")) or type issues
        print(f"Error creating DiagnosticResult from data: {e}. Data: {data}")
        return None 