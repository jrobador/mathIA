/**
 * Client API for interacting with the Math Tutor backend
 * Provides methods for managing sessions and communication with the agent
 */

// Types for the client
interface MathTutorConfig {
  baseUrl?: string;
  headers?: Record<string, string>;
}

interface SessionConfig {
  initial_topic?: string;
  initial_cpa_phase?: string;
  initial_difficulty?: string;
  difficulty_adjustment_rate?: number;
  enable_audio?: boolean;
  enable_images?: boolean;
  language?: string;
  diagnostic_score?: number;
  diagnostic_details?: Array<DiagnosticQuestionResult>;
}

interface StartSessionOptions {
  personalized_theme?: string;
  initial_message?: string | null;
  config?: SessionConfig | null;
  diagnostic_results?: DiagnosticResults | null;
  learning_path?: string | null;
}

interface DiagnosticQuestionResult {
  id: number;
  correct: boolean;
  question_type?: string;
  concept_tested?: string;
}

interface DiagnosticResults {
  score: number;
  correct_answers: number;
  total_questions: number;
  recommended_level: string;
  question_results: DiagnosticQuestionResult[];
}

interface AgentOutput {
  text?: string;
  image_url?: string;
  audio_url?: string;
  feedback?: {
    type?: string;
    message?: string;
  };
  prompt_for_answer?: boolean;
  evaluation?: string;
}

interface StartSessionResponse {
  session_id: string;
  initial_output: AgentOutput;
  status: string;
}

interface ProcessInputResponse {
  session_id: string;
  agent_output: AgentOutput;
  mastery_level?: number;
}

interface SessionStatusResponse {
  session_id: string;
  current_topic: string;
  mastery_levels: Record<string, number>;
  current_cpa_phase: string;
  is_active: boolean;
  created_at?: number;
  last_updated?: number;
}

// Default API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class MathTutorClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private currentSessionId: string | null;
  private requestTimeoutMs: number;

  /**
   * Initialize the API client with optional configuration
   */
  constructor(config: MathTutorConfig = {}) {
    this.baseUrl = config.baseUrl || API_BASE_URL;
    this.headers = {
      'Content-Type': 'application/json',
      ...(config.headers || {}),
    };
    this.currentSessionId = null;
    this.requestTimeoutMs = 30000; // 30 second timeout
    
    // Try to restore session from localStorage if available
    this.restoreSession();
  }

  /**
   * Start a new tutoring session
   */
  async startSession({
    personalized_theme = 'espacio',
    initial_message = null,
    config = null,
    diagnostic_results = null,
    learning_path = null
  }: StartSessionOptions = {}): Promise<StartSessionResponse> {
    try {
      // Configure session based on inputs
      let sessionConfig: SessionConfig = config || {};
      
      // Apply diagnostic results if available
      if (diagnostic_results) {
        sessionConfig.initial_difficulty = diagnostic_results.recommended_level || 'beginner';
        sessionConfig.diagnostic_score = diagnostic_results.score;
        sessionConfig.diagnostic_details = diagnostic_results.question_results;
      }
      
      // Set initial topic based on learning path
      if (learning_path) {
        sessionConfig.initial_topic = this.mapLearningPathToTopic(learning_path);
      }

      // Make API request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.requestTimeoutMs);
      
      const response = await fetch(`${this.baseUrl}/session/start`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          personalized_theme,
          initial_message,
          config: sessionConfig,
          learning_path
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error starting session');
      }

      const data: StartSessionResponse = await response.json();
      
      // Store session ID
      this.currentSessionId = data.session_id;
      this.saveSession();
      
      console.log("Session started:", data.session_id);
      
      return data;
    } catch (error) {
      console.error('Error starting session:', error);
      throw error;
    }
  }

  /**
   * Process user input in an active session
   */
  async processInput(message: string, sessionId: string | null = null): Promise<ProcessInputResponse> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No active session. Start a session first.');
    }
    
    try {
      // Make API request with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.requestTimeoutMs);
      
      const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/process`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ message }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error processing input');
      }
      
      const data: ProcessInputResponse = await response.json();
      
      // Enhance URLs if they're relative
      if (data.agent_output) {
        if (data.agent_output.image_url && data.agent_output.image_url.startsWith('/')) {
          data.agent_output.image_url = `${this.baseUrl}${data.agent_output.image_url}`;
        }
        
        if (data.agent_output.audio_url && data.agent_output.audio_url.startsWith('/')) {
          data.agent_output.audio_url = `${this.baseUrl}${data.agent_output.audio_url}`;
        }
      }
      
      return data;
    } catch (error) {
      console.error('Error processing input:', error);
      throw error;
    }
  }
  
  /**
   * Get the current status of a session
   */
  async getSessionStatus(sessionId: string | null = null): Promise<SessionStatusResponse> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No active session.');
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/status`, {
        method: 'GET',
        headers: this.headers,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error getting session status');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error getting session status:', error);
      throw error;
    }
  }
  
  /**
   * End an active session
   */
  async endSession(sessionId: string | null = null): Promise<boolean> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      console.warn('No active session to end.');
      return false;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/session/${targetSessionId}`, {
        method: 'DELETE',
        headers: this.headers,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error ending session');
      }
      
      if (targetSessionId === this.currentSessionId) {
        this.currentSessionId = null;
        this.clearSession();
      }
      
      return true;
    } catch (error) {
      console.error('Error ending session:', error);
      throw error;
    }
  }
  
  /**
   * Submit feedback about a session
   */
  async submitFeedback(rating: number, comments: string = "", sessionId: string | null = null): Promise<any> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No active session for feedback.');
    }
    
    try {
      const queryParams = new URLSearchParams({
        rating: rating.toString(),
        ...(comments ? { comments } : {})
      });
      
      const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/feedback?${queryParams}`, {
        method: 'POST',
        headers: this.headers,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error sending feedback');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error sending feedback:', error);
      throw error;
    }
  }
  
  /**
   * Format diagnostic results for the backend API
   */
  formatDiagnosticResults(diagnosticResults: DiagnosticQuestionResult[]): DiagnosticResults | null {
    if (!diagnosticResults || !Array.isArray(diagnosticResults)) {
      return null;
    }
    
    const correctAnswers = diagnosticResults.filter(r => r.correct).length;
    const totalQuestions = diagnosticResults.length;
    const percentCorrect = (correctAnswers / totalQuestions) * 100;
    
    let recommendedLevel = "initial";
    if (percentCorrect >= 80) recommendedLevel = "advanced";
    else if (percentCorrect >= 50) recommendedLevel = "intermediate";
    else if (percentCorrect >= 30) recommendedLevel = "beginner";
    
    return {
      score: percentCorrect,
      correct_answers: correctAnswers,
      total_questions: totalQuestions,
      recommended_level: recommendedLevel,
      question_results: diagnosticResults
    };
  }
  
  /**
   * Get the current session ID
   */
  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }
  
  /**
   * Set the current session ID manually
   */
  setCurrentSessionId(sessionId: string): void {
    this.currentSessionId = sessionId;
    this.saveSession();
  }
  
  /**
   * Check if there is an active session
   */
  hasActiveSession(): boolean {
    return this.currentSessionId !== null;
  }
  
  /**
   * Map learning path to initial topic
   */
  private mapLearningPathToTopic(learningPath: string): string {
    const pathToTopic: Record<string, string> = {
      'fractions': 'fractions_introduction',
      'addition': 'addition_introduction',
      'subtraction': 'subtraction_introduction',
      'multiplication': 'multiplication_introduction',
      'division': 'division_introduction'
    };
    
    return pathToTopic[learningPath] || 'fractions_introduction';
  }
  
  /**
   * Save session to localStorage
   */
  private saveSession(): void {
    if (typeof window !== 'undefined' && this.currentSessionId) {
      try {
        localStorage.setItem('mathTutorSessionId', this.currentSessionId);
      } catch (e) {
        console.warn('Could not save session to localStorage', e);
      }
    }
  }
  
  /**
   * Restore session from localStorage
   */
  private restoreSession(): void {
    if (typeof window !== 'undefined') {
      try {
        const savedSessionId = localStorage.getItem('mathTutorSessionId');
        if (savedSessionId) {
          this.currentSessionId = savedSessionId;
        }
      } catch (e) {
        console.warn('Could not restore session from localStorage', e);
      }
    }
  }
  
  /**
   * Clear session from localStorage
   */
  private clearSession(): void {
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('mathTutorSessionId');
      } catch (e) {
        console.warn('Could not clear session from localStorage', e);
      }
    }
  }
}

export default MathTutorClient;