/**
 * Client API for interacting with the Math Tutor backend
 * Provides methods for managing sessions and communication with the agent
 */

import {
  MathTutorClientConfig,
  DiagnosticQuestionResult,
  DiagnosticResults,
  StartSessionOptions,
  StartSessionResponse,
  ProcessInputResponse,
  SessionStatusResponse,
  TutorConfig as SessionConfig, // Optional: Alias if needed
  AgentOutput
} from "@/types/api";

// Default API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class MathTutorClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private currentSessionId: string | null;
  private requestTimeoutMs: number;
  private quickTimeoutMs: number;
  private pollingIntervalMs: number;
  private requestRetryCount: number;
  // Track if a process request is in progress
  private processingRequest: boolean;

  /**
   * Initialize the API client with optional configuration
   */
  constructor(config: MathTutorClientConfig = {}) {
    this.baseUrl = config.baseUrl || API_BASE_URL;
    this.headers = {
      'Content-Type': 'application/json',
      ...(config.headers || {}),
    };
    this.currentSessionId = null;
    this.requestTimeoutMs = 90000; // Increased: 45 second timeout for regular requests
    this.quickTimeoutMs = 10000;   // Increased: 10 second timeout for quick responses
    this.pollingIntervalMs = 1500; // Increased: 1.5 second interval between polls
    this.requestRetryCount = 2;    // Number of retries for failed requests
    this.processingRequest = false; // Track if a process request is in flight
    
    // Try to restore session from localStorage if available
    this._restoreSession();
  }

  /**
   * Start a new tutoring session
   */
  async startSession({
    personalized_theme = 'space',
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
        sessionConfig.initial_topic = this._mapLearningPathToTopic(learning_path);
      }

      console.log("Sending session start request to backend...");
      
      // Make API request with a shorter timeout - we expect quick response now
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.quickTimeoutMs);
      
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
      
      // Store session ID immediately
      this.currentSessionId = data.session_id;
      this._saveSession();
      
      console.log("Session ID received:", data.session_id);
      
      // If status indicates content is still being generated, poll for completion
      if (data.status === "initializing") {
        console.log("Content is being generated in the background, polling for completion...");
        try {
          const completeData = await this.pollForSessionCompletion(data.session_id);
          
          // BUGFIX: Add more detailed logging
          if (completeData) {
            console.log("Polling complete, received data:", {
              has_content: true,
              content_ready: completeData.content_ready,
              has_agent_output: !!completeData.agent_output,
              agent_output_text: completeData.agent_output?.text ? completeData.agent_output.text.substring(0, 50) + '...' : 'none',
              has_error: !!completeData.error
            });
            
            // Update the initial output with the complete content if available
            if (completeData.agent_output) {
              // Check if agent_output has any valuable content before using it
              const hasContent = completeData.agent_output.text || 
                             completeData.agent_output.image_url || 
                             completeData.agent_output.audio_url;
              
              if (hasContent) {
                console.log("Content generation complete with valid output, updating response");
                data.initial_output = completeData.agent_output;
                data.status = "active";
                
                // Normalize URLs for image and audio
                this._normalizeContentUrls(data.initial_output);
                console.log("Content generation complete, updated response with full content");
              } else {
                console.warn("Agent output received but contains no usable content");
                // Create a fallback if the output exists but has no content
                data.initial_output = {
                  text: "Your math lesson is ready. Let's get started!",
                  prompt_for_answer: true
                };
                data.status = "active";
              }
            } else {
              console.warn("Content marked as ready but no agent_output available");
              // Create a fallback if no output is available
              data.initial_output = {
                text: "Your math lesson is ready. Let's begin!",
                prompt_for_answer: true
              };
              data.status = "active";
            }
          } else {
            console.warn("Polling completed but no data returned!");
            // Create a fallback if polling fails to return data
            data.initial_output = {
              text: "Your personalized math session is ready to begin.",
              prompt_for_answer: true
            };
            data.status = "active";
          }
        } catch (pollingError) {
          console.warn("Polling for content completion failed, returning initial response:", pollingError);
          // Create a fallback if polling fails with an error
          data.initial_output = {
            text: "Your math lesson is now ready to begin.",
            prompt_for_answer: true
          };
          data.status = "active";
        }
      } else if (data.initial_output) {
        // Normalize URLs for any content returned immediately
        this._normalizeContentUrls(data.initial_output);
      }
      
      return data;
    } catch (error) {
      console.error('Error starting session:', error);
      throw error;
    }
  }

  /**
   * Process user input in an active session with retry capability
   */
  async processInput(message: string, sessionId: string | null = null): Promise<ProcessInputResponse> {
    // BUGFIX: Prevent multiple concurrent requests
    if (this.processingRequest) {
      console.warn("Another request is already in progress, preventing concurrent requests");
      throw new Error('A request is already in progress. Please wait for it to complete.');
    }
    
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No active session. Start a session first.');
    }
    
    this.processingRequest = true;
    
    try {
      // Try up to retryCount times
      for (let attempt = 0; attempt <= this.requestRetryCount; attempt++) {
        try {
          // Make API request with timeout
          const controller = new AbortController();
          const timeoutId = setTimeout(() => {
            console.warn(`Request timeout after ${this.requestTimeoutMs}ms, aborting...`);
            controller.abort(new Error('Request timed out'));
          }, this.requestTimeoutMs);
          
          console.log(`Sending input to backend (attempt ${attempt + 1}/${this.requestRetryCount + 1})...`);
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
          
          // BUGFIX: Log successful response details
          console.log("Successfully processed input, received response:", {
            session_id: data.session_id,
            has_agent_output: !!data.agent_output,
            mastery_level: data.mastery_level
          });
          
          // Normalize URLs if output exists
          if (data.agent_output) {
            this._normalizeContentUrls(data.agent_output);
          }
          
          this.processingRequest = false;
          return data;
        } catch (err) {
          // If this was our last attempt, throw the error
          if (attempt === this.requestRetryCount) {
            throw err;
          }
          
          // Otherwise log it and retry after a delay
          console.warn(`Attempt ${attempt + 1} failed:`, err);
          console.log(`Retrying in ${this.pollingIntervalMs}ms...`);
          
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, this.pollingIntervalMs));
        }
      }
      
      // We should never reach here because the last failed attempt should throw
      throw new Error('All retry attempts failed');
    } catch (error) {
      console.error('Error processing input:', error);
      this.processingRequest = false;
      throw error;
    } finally {
      // Make sure we reset the flag even if an error occurred
      this.processingRequest = false;
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
      
      const data = await response.json();
      
      // Normalize URLs in agent output if present
      if (data.agent_output) {
        this._normalizeContentUrls(data.agent_output);
      }
      
      return data;
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
        this._clearSession();
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
   * Check if a session is healthy by requesting its status
   * Useful to verify if a restored session is still active on the server
   */
  async checkSessionHealth(sessionId: string | null = null): Promise<boolean> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      return false;
    }
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/status`, {
        method: 'GET',
        headers: this.headers,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      console.warn('Session health check failed:', error);
      return false;
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
   * Poll for session content completion
   * @param sessionId The session ID to poll for
   * @param maxAttempts Maximum number of polling attempts (default 60)
   * @returns The completed session status or null if timed out
   */
  private async pollForSessionCompletion(
    sessionId: string, 
    maxAttempts = 60
  ): Promise<SessionStatusResponse | null> {
    console.log(`Polling for session ${sessionId} content completion...`);
    
    let attempts = 0;
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3;
    
    while (attempts < maxAttempts) {
      try {
        attempts++;
        
        // Get the current status
        const status = await this.getSessionStatus(sessionId);
        
        // Reset consecutive errors counter on successful response
        consecutiveErrors = 0;
        
        // BUGFIX: More detailed logging to help debug issues
        const agentOutputDetails = status.agent_output ? {
          has_text: !!status.agent_output.text,
          text_length: status.agent_output.text ? status.agent_output.text.length : 0,
          has_image: !!status.agent_output.image_url,
          has_audio: !!status.agent_output.audio_url,
          prompt_for_answer: status.agent_output.prompt_for_answer
        } : 'null';
        
        console.log(`Poll attempt ${attempts}, status:`, {
          content_ready: status.content_ready,
          has_agent_output: !!status.agent_output,
          agent_output_details: agentOutputDetails,
          error: status.error,
          mastery: status.mastery_levels[status.current_topic]
        });
        
        // Check if content is ready or if there was an error
        if (status.content_ready || status.error) {
          console.log(`Session ${sessionId} content is ready after ${attempts} attempts`);
          
          // BUGFIX: If content is ready but agent_output is missing/empty despite our backend fixes,
          // we'll return the status anyway after enough attempts
          if (status.content_ready && (!status.agent_output || !status.agent_output.text)) {
            console.warn("Content marked as ready but agent_output is missing or empty!");
            
            // If we've made a lot of attempts, just return what we have
            if (attempts > maxAttempts / 2) {
              console.warn(`Returning current status after ${attempts} attempts despite missing output`);
              
              // Create a minimal local replacement if needed
              if (!status.agent_output) {
                console.warn("Creating minimal replacement agent_output");
                status.agent_output = {
                  text: "Your math lesson is ready. Please continue.",
                  prompt_for_answer: true
                };
              }
              
              return status;
            }
            
            // Otherwise wait and try again
            const retryWait = 1500; // Increased to 1.5 seconds
            console.log(`Waiting ${retryWait}ms to try again...`);
            await new Promise(resolve => setTimeout(resolve, retryWait));
            continue;
          }
          
          return status;
        }
        
        // Wait before trying again - increase wait time for later attempts
        const waitTime = Math.min(this.pollingIntervalMs * (1 + Math.floor(attempts / 10)), 3000);
        console.log(`Waiting for session content, attempt ${attempts}/${maxAttempts} (${waitTime}ms)...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        
      } catch (error) {
        console.error(`Error polling session status (attempt ${attempts}):`, error);
        consecutiveErrors++;
        
        // If we have too many consecutive errors, create a fallback response
        if (consecutiveErrors >= maxConsecutiveErrors) {
          console.warn(`${maxConsecutiveErrors} consecutive errors encountered, creating fallback response`);
          
          // Create a fallback response
          const fallbackResponse: SessionStatusResponse = {
            session_id: sessionId,
            current_topic: "unknown",
            mastery_levels: {},
            current_cpa_phase: "Concrete",
            is_active: true,
            content_ready: true,
            agent_output: {
              text: "We encountered an issue loading your math lesson. Please reload the page to try again.",
              prompt_for_answer: false
            },
            error: String(error),
            created_at: Date.now() / 1000,
            last_updated: Date.now() / 1000
          };
          
          return fallbackResponse;
        }
        
        // Wait a bit longer after errors
        await new Promise(resolve => setTimeout(resolve, this.pollingIntervalMs * 2));
      }
    }
    
    console.warn(`Polling timed out after ${maxAttempts} attempts for session ${sessionId}`);
    
    // Create a timeout response
    return {
      session_id: sessionId,
      current_topic: "unknown",
      mastery_levels: {},
      current_cpa_phase: "Concrete",
      is_active: true,
      content_ready: true,
      agent_output: {
        text: "It's taking longer than expected to prepare your math lesson. Please reload the page to try again.",
        prompt_for_answer: false
      },
      error: "Polling timeout",
      created_at: Date.now() / 1000,
      last_updated: Date.now() / 1000
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
    this._saveSession();
  }
  
  /**
   * Check if there is an active session
   */
  hasActiveSession(): boolean {
    return this.currentSessionId !== null;
  }
  
  /**
   * Normalizes relative URLs in agent output to absolute URLs
   */
  private _normalizeContentUrls(agentOutput: AgentOutput): void {
    if (!agentOutput) return;
    
    // BUGFIX: Add safety checks before URL manipulation
    try {
      if (agentOutput.image_url && typeof agentOutput.image_url === 'string' && agentOutput.image_url.startsWith('/')) {
        agentOutput.image_url = `${this.baseUrl}${agentOutput.image_url}`;
      }
      
      if (agentOutput.audio_url && typeof agentOutput.audio_url === 'string' && agentOutput.audio_url.startsWith('/')) {
        agentOutput.audio_url = `${this.baseUrl}${agentOutput.audio_url}`;
      }
    } catch (error) {
      console.warn('Error normalizing content URLs:', error);
    }
  }
  
  /**
   * Map learning path to initial topic
   */
  private _mapLearningPathToTopic(learningPath: string): string {
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
   * Retry mechanism for API calls
   * @param operation The async operation to retry
   * @param retries Maximum number of retries
   * @param delay Delay between retries in ms
   */
  private async _retryOperation<T>(
    operation: () => Promise<T>, 
    retries: number = 2,
    delay: number = 1000,
    backoff: number = 1.5
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      if (retries <= 0) throw error;
      
      console.warn(`Operation failed, retrying in ${delay}ms... (${retries} attempts left)`);
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return this._retryOperation(
        operation, 
        retries - 1, 
        Math.floor(delay * backoff),
        backoff
      );
    }
  }
  
  /**
   * Save session to localStorage
   */
  private _saveSession(): void {
    if (typeof window !== 'undefined' && this.currentSessionId) {
      try {
        localStorage.setItem('mathTutorSessionId', this.currentSessionId);
        localStorage.setItem('mathTutorSessionTimestamp', Date.now().toString());
      } catch (e) {
        console.warn('Could not save session to localStorage', e);
      }
    }
  }
  
  /**
   * Restore session from localStorage
   */
  private _restoreSession(): void {
    if (typeof window !== 'undefined') {
      try {
        const savedSessionId = localStorage.getItem('mathTutorSessionId');
        const sessionTimestamp = localStorage.getItem('mathTutorSessionTimestamp');
        
        // Only restore if session is less than 1 hour old
        const SESSION_MAX_AGE = 60 * 60 * 1000; // 1 hour in milliseconds
        const isSessionExpired = sessionTimestamp && 
          (Date.now() - parseInt(sessionTimestamp)) > SESSION_MAX_AGE;
          
        if (savedSessionId && !isSessionExpired) {
          console.log(`Restoring session: ${savedSessionId}`);
          this.currentSessionId = savedSessionId;
          
          // Verify session is still active on server
          this.checkSessionHealth(savedSessionId).then(isHealthy => {
            if (!isHealthy) {
              console.warn('Restored session is no longer active on server, clearing local session');
              this._clearSession();
              this.currentSessionId = null;
            }
          });
        } else if (isSessionExpired) {
          console.log('Session expired, clearing');
          this._clearSession();
        }
      } catch (e) {
        console.warn('Could not restore session from localStorage', e);
        this._clearSession();
      }
    }
  }
  
  /**
   * Clear session from localStorage
   */
  private _clearSession(): void {
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('mathTutorSessionId');
        localStorage.removeItem('mathTutorSessionTimestamp');
      } catch (e) {
        console.warn('Could not clear session from localStorage', e);
      }
    }
  }
}

export default MathTutorClient;