// FILE: MathTutorClient.ts
// (Assuming this is located at something like "@/app/api/MathTutorClient.ts")

/**
 * Cliente API para interactuar con el backend del agente matemático
 * Ahora soporta comunicación vía WebSockets y HTTP como fallback
 */

import {
  MathTutorClientConfig,
  StartSessionOptions,
  StartSessionResponse,
  ProcessInputResponse,
  SessionStatusResponse,
  DiagnosticQuestionResult,
  DiagnosticResults,
  AgentOutput,
} from "@/types/api"; // Adjust path if needed

// Configuración API por defecto
const API_BASE_URL = 
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

class MathTutorClient {
  private baseUrl: string;
  private wsBaseUrl: string;
  private headers: Record<string, string>;
  private currentSessionId: string | null;
  private wsConnection: WebSocket | null;
  private messageCallbacks: Map<string, (data: any) => void>; // For request-response over WS
  private messageHandlers: Array<(data: any) => void>; // For broadcast/push messages
  private reconnectAttempts: number;
  private maxReconnectAttempts: number;
  private reconnectTimeout: number;
  private processingRequest: boolean; // Simple lock to prevent concurrent sends
  private reconnectTimer: ReturnType<typeof setTimeout> | null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout = 3000000;

  /**
   * Initialize the API client with optional configuration
   */
  constructor(config: MathTutorClientConfig = {}) {
    this.baseUrl = config.baseUrl || API_BASE_URL;
    // Ensure wsBaseUrl replaces http/https correctly
    this.wsBaseUrl = this.baseUrl.replace(/^http/, "ws");
    this.headers = {
      "Content-Type": "application/json",
      ...(config.headers || {}),
    };
    this.currentSessionId = null;
    this.wsConnection = null;
    this.messageCallbacks = new Map();
    this.messageHandlers = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5; // Or make configurable
    this.reconnectTimeout = 1000; // Initial reconnect delay
    this.processingRequest = false;
    this.reconnectTimer = null;

    // Try to restore session ID from localStorage if available
    // **Crucially, we no longer automatically connect here**
    this._restoreSession();
    console.log(`Client initialized. Restored session ID (if any): ${this.currentSessionId}`);
  }

  public getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  public hasActiveSession(): boolean {
    // Check both the internal ID and WebSocket state for robustness
    return this.currentSessionId !== null;
     // Or potentially: return this.currentSessionId !== null && this.isWebSocketConnected();
     // Depending on the desired definition of "active". Let's stick with just ID check for now.
  }

  async requestContinue(sessionId: string | null = null): Promise<void> {
    const targetSessionId = sessionId || this.currentSessionId;
    if (!targetSessionId) {
      console.error("No active session ID available for requestContinue.");
      throw new Error("No hay una sesión activa.");
    }

    if (!this.isWebSocketConnected()) {
      console.warn(`WebSocket not connected for session ${targetSessionId}. Cannot send 'continue'. Trying HTTP fallback (if available/implemented).`);
      // Optional: Implement an HTTP fallback if your backend supports GET /api/sessions/{id}/continue
      // For now, we'll throw an error if WS is not connected for this action.
      throw new Error("Connection lost. Cannot continue session.");
    }
    try {
      this.wsConnection?.send(
        JSON.stringify({
          action: "continue",
          requestId: uuidv4(), // Still good practice to include an ID
        })
      );
      // We don't wait for a specific response here, the hook will handle the incoming agent_response
    } catch (error) {
      console.error("Error sending 'continue' action via WebSocket:", error);
      throw error; // Re-throw to be caught by the calling hook/component
    }
  }

  /**
   * Start a new tutoring session using the /ws/new_session endpoint.
   */
  async startSession({
    personalized_theme = "space",
    // initial_message = null, // Not directly used in this backend version's create_session
    config = null,
    diagnostic_results = null,
    learning_path = null,
  }: StartSessionOptions = {}): Promise<StartSessionResponse> {
    console.log("Attempting to start new session via WebSocket...");
  
    // Ensure any previous connection attempts are cleared
    if (this.wsConnection) {
        console.log("Closing existing WS connection before starting new session.");
        // Prevent automatic reconnection attempts from the old connection
        this.maxReconnectAttempts = 0; // Temporarily disable reconnect
        this.wsConnection.close();
        this.wsConnection = null;
        this.maxReconnectAttempts = 5; // Restore reconnect setting
    }
    if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
    }
    this.currentSessionId = null; // Clear any restored ID
    this._clearSession(); // Clear from localStorage too
  
  
    // Determine topic_id based on learning_path or default
    const topicId = learning_path
      ? this._mapLearningPathToTopic(learning_path)
      : "fractions_introduction"; // Default topic
  
    // Use WebSocket to create the session
    return new Promise<StartSessionResponse>((resolve, reject) => {
      let ws: WebSocket | null = null;
      try {
          ws = new WebSocket(`${this.wsBaseUrl}/ws/new_session`);
      } catch (error) {
           console.error("Failed to create WebSocket for new session:", error);
           // Immediately try HTTP fallback if WebSocket creation fails
           return this._startSessionHttp({ 
             personalized_theme, 
             learning_path, 
             config,
             diagnostic_results 
           })
                    .then(resolve)
                    .catch(reject); // This uses reject, so no warning
      }
  
      const connectionTimeout = setTimeout(() => {
        console.warn("WebSocket connection timeout for new session.");
        if (ws && ws.readyState !== WebSocket.OPEN) {
             ws.close(); // Attempt to close if stuck
             // Try HTTP fallback on timeout
             this._startSessionHttp({ 
               personalized_theme, 
               learning_path, 
               config,
               diagnostic_results
             })
                .then(resolve)
                .catch(reject); // This uses reject, so no warning
        }
      }, 1000000); // 10 second timeout for initial connection
  
      ws.onopen = () => {
        clearTimeout(connectionTimeout); // Clear timeout on successful open
        console.log("WebSocket connected for new session request.");
        
        // Format diagnostic results for sending
        const formattedDiagnosticResults = diagnostic_results 
          ? (Array.isArray(diagnostic_results) 
            ? diagnostic_results.map((result: DiagnosticQuestionResult) => ({
                question_id: result.question_id,
                correct: result.correct,
                concept_tested: result.concept_tested
              }))
            : null)
          : null;
        
        // Send the create_session request
        ws?.send(
          JSON.stringify({
            action: "create_session",
            data: {
              topic_id: topicId,
              personalized_theme,
              user_id: config?.user_id, // Pass user_id if available in config
              initial_mastery: 0.0, // Or pass if available
              diagnostic_results: formattedDiagnosticResults
            },
          })
        );
      };
  
      ws.onerror = (event) => {
        clearTimeout(connectionTimeout);
        console.error("WebSocket error on new session request:", event);
        // Close the potentially broken socket
        ws?.close();
        // Try HTTP fallback on error
        this._startSessionHttp({ 
          personalized_theme, 
          learning_path, 
          config,
          diagnostic_results
        })
          .then(resolve)
          .catch(reject); // This uses reject, so no warning
      };
  
      ws.onmessage = (event) => {
        clearTimeout(connectionTimeout); // Clear timeout on successful message
        try {
          const response = JSON.parse(event.data as string);
          console.log("Received response on new session WebSocket:", response);

          if (response.type === "session_created") {
            // --- Session Created Successfully ---
            const newSessionId = response.data.session_id;
            const initialResult = response.data.initial_result; // Get the first agent step result

            if (!newSessionId || !initialResult) {
                 console.error("Invalid session_created response:", response.data);
                 reject(new Error("Received invalid data from server after session creation."));
                 ws?.close();
                 return;
            }

            // Store session information
            this.currentSessionId = newSessionId;
            this._saveSession(); // Save to localStorage

            // Create the response object for the hook
            const sessionResponse: StartSessionResponse = {
              session_id: newSessionId,
              initial_output: { // Format the initial agent step result
                text: initialResult.text || "¡Bienvenido!", // Provide default text
                image_url: initialResult.image_url,
                audio_url: initialResult.audio_url,
                // Use waiting_for_input from the result's metadata or the result itself
                prompt_for_answer: initialResult.waiting_for_input ?? initialResult.state_metadata?.waiting_for_input ?? false,
                evaluation: initialResult.evaluation_type, // Map if needed
                is_final_step: initialResult.is_final_step || false,
              },
              status: "active",
            };

            // Normalize relative URLs to absolute
            this._normalizeContentUrls(sessionResponse.initial_output);

            // Close this temporary WebSocket connection
            ws?.close();

            // NOW, connect to the persistent WebSocket for this session
            this._connectToSessionWebSocket(); // Connect using the NEWLY set this.currentSessionId

            resolve(sessionResponse);
          } else if (response.type === "error") {
            reject(new Error(response.message || "Unknown error creating session"));
            ws?.close();
          } else {
            console.warn("Received unexpected message type on new session WebSocket:", response.type);
            reject(new Error(`Unexpected message type: ${response.type}`));
            ws?.close();
          }
        } catch (error) {
          console.error("Error parsing message on new session WebSocket:", error);
          reject(error as Error);
          ws?.close(); // Close on parse error
        }
      };
  
      ws.onclose = (event) => {
        clearTimeout(connectionTimeout); // Clear timeout if closed before message/error
        console.log(`New session WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
        // If it closes without resolving/rejecting, it might indicate a problem or that HTTP fallback was triggered.
        // Avoid rejecting here again if HTTP fallback is already handling it.
      };
    });
  }

  /**
   * Fallback: Start session via HTTP if WebSocket fails
   */
  private async _startSessionHttp({
    personalized_theme = 'space',
    // initial_message = null, // Not used by this endpoint
    config = null,
    diagnostic_results = null, // Now used for HTTP fallback
    learning_path = null
  }: StartSessionOptions = {}): Promise<StartSessionResponse> {
    console.warn("WebSocket failed, falling back to HTTP for starting session...");

    const topicId = learning_path ? this._mapLearningPathToTopic(learning_path) : 'fractions_introduction';

    try {
        // Prepare diagnostic results for HTTP request if available
        let calculatedMastery = 0.0;
        if (diagnostic_results && Array.isArray(diagnostic_results) && diagnostic_results.length > 0) {
            const totalQuestions = diagnostic_results.length;
            const correctAnswers = diagnostic_results.filter(r => r.correct).length;
            calculatedMastery = 0.1 + (0.7 * (correctAnswers / totalQuestions));
            console.log(`HTTP fallback: Calculated mastery from diagnostics: ${calculatedMastery.toFixed(2)}`);
        }

        const response = await fetch(`${this.baseUrl}/api/sessions`, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({
            topic_id: topicId,
            personalized_theme,
            initial_mastery: calculatedMastery, // Use calculated mastery from diagnostics if available
            user_id: config?.user_id,
            diagnostic_results: diagnostic_results // Include diagnostic results in HTTP request
          })
        });

        if (!response.ok) {
          let errorDetail = 'Error iniciando sesión vía HTTP';
          try {
              const errorData = await response.json();
              errorDetail = errorData.detail || errorDetail;
          } catch (e) { /* Ignore parse error */ }
          throw new Error(errorDetail);
        }

        const data = await response.json(); // Should match SessionResponse from http_routes

        if (!data.session_id || !data.result) {
             throw new Error("Invalid response from HTTP /api/sessions");
        }

        this.currentSessionId = data.session_id;
        this._saveSession();

        // Connect to the session WebSocket AFTER successfully starting via HTTP
        this._connectToSessionWebSocket();

        const initialResult = data.result;
        const sessionResponse: StartSessionResponse = {
            session_id: data.session_id,
            initial_output: {
                text: initialResult.text || "¡Bienvenido!",
                image_url: initialResult.image_url,
                audio_url: initialResult.audio_url,
                prompt_for_answer: initialResult.waiting_for_input ?? initialResult.state_metadata?.waiting_for_input ?? false,
                evaluation: initialResult.evaluation_type,
                is_final_step: initialResult.is_final_step || false,
            },
            status: "active"
        };
        this._normalizeContentUrls(sessionResponse.initial_output);
        return sessionResponse;

    } catch(error) {
        console.error("HTTP fallback for startSession failed:", error);
        throw error; // Re-throw the error to be caught by the caller
    }
  }

  /**
   * Process user input in an active session via WebSocket (preferred) or HTTP fallback.
   */
  async processInput(
    message: string,
    sessionId: string | null = null
  ): Promise<ProcessInputResponse> {
    if (this.processingRequest) {
      console.warn("Request already in progress, please wait.");
      throw new Error("Una solicitud ya está en progreso. Por favor espere.");
    }
  
    const targetSessionId = sessionId || this.currentSessionId;
    if (!targetSessionId) {
      console.error("No active session ID available for processInput.");
      throw new Error("No hay una sesión activa. Inicie una sesión primero.");
    }
  
    this.processingRequest = true;
  
    // Prefer WebSocket
    if (this.isWebSocketConnected()) {
      console.log(`Sending input via WebSocket for session ${targetSessionId}`);
      return new Promise<ProcessInputResponse>((resolve, reject) => {
        const requestId = uuidv4(); // Use a robust UUID
        
        // Track evaluation and next step responses
        let evaluationResponse: any = null;
        let nextStepResponse: any = null;
        let responsesReceived = 0;
        const expectedResponses = 2; // We expect two responses: evaluation + next step
  
        const timeoutHandle = setTimeout(() => {
          if (this.messageCallbacks.has(requestId)) {
            this.messageCallbacks.delete(requestId);
            console.error(`Timeout waiting for response to input request ${requestId}`);
            this.processingRequest = false; // Unlock on timeout
            reject(new Error("Tiempo de espera agotado para procesar la entrada."));
          }
        }, 6000000);
  
        this.messageCallbacks.set(requestId, (response) => {
          console.log(`Received WS response for request ${requestId}:`, response);
          
          if (response.type === "error") {
            clearTimeout(timeoutHandle);
            this.messageCallbacks.delete(requestId);
            this.processingRequest = false;
            reject(new Error(response.message || "Error procesando la entrada desde el servidor."));
            return;
          } 
          
          if (response.type === "agent_response") {
            const agentData = response.data;
            
            // Check which type of response this is
            if (agentData.action === "evaluation_result") {
              console.log("Received evaluation response");
              evaluationResponse = agentData;
              responsesReceived++;
            } else {
              console.log("Received next step response");
              nextStepResponse = agentData;
              responsesReceived++;
            }
            
            // If we've received all expected responses, resolve the promise
            if (responsesReceived >= expectedResponses || 
                (responsesReceived === 1 && !evaluationResponse)) { // Handle case where backend sends only one response
              
              clearTimeout(timeoutHandle);
              this.messageCallbacks.delete(requestId);
              this.processingRequest = false;
              
              // Decide which response to use as the primary one for the UI
              const primaryResponse = nextStepResponse || evaluationResponse;
              
              if (!primaryResponse) {
                reject(new Error("Incomplete response received from server."));
                return;
              }
              
              // Create response object using the next step content but tracking evaluation state
              const inputResponse: ProcessInputResponse = {
                session_id: targetSessionId,
                agent_output: {
                  text: primaryResponse.text || "",
                  image_url: primaryResponse.image_url,
                  audio_url: primaryResponse.audio_url,
                  prompt_for_answer: primaryResponse.waiting_for_input ?? primaryResponse.state_metadata?.waiting_for_input ?? false,
                  // Use evaluation from evaluation response if available, otherwise from primary response
                  evaluation: evaluationResponse?.evaluation_type || primaryResponse.evaluation_type || primaryResponse.last_evaluation || null,
                  is_final_step: primaryResponse.is_final_step || false,
                },
                mastery_level: primaryResponse.state_metadata?.mastery ?? 0,
              };
              
              // Add custom properties to the response object (will be accessible via indexing)
              (inputResponse as any).hasEvaluation = !!evaluationResponse;
              (inputResponse as any).evaluationText = evaluationResponse?.text || "";
              (inputResponse as any).isCorrect = !!evaluationResponse?.is_correct;
              
              this._normalizeContentUrls(inputResponse.agent_output);
              resolve(inputResponse);
            }
          } else {
            // For other message types, just log but don't resolve/reject yet
            console.warn("Received unexpected message type:", response.type);
          }
        });
  
        // Send the message
        this.wsConnection?.send(
          JSON.stringify({
            action: "submit_answer",
            requestId: requestId,
            data: {
              answer: message,
            },
          })
        );
      }).catch(error => {
        // Ensure lock is released on promise rejection as well
        this.processingRequest = false;
        throw error;
      });
    } else {
      // Fallback to HTTP
      console.warn(`WebSocket not connected for session ${targetSessionId}. Using HTTP fallback for processInput.`);
      try {
        const response = await fetch(
          `${this.baseUrl}/api/sessions/${targetSessionId}/answer`,
          {
            method: "POST",
            headers: this.headers,
            body: JSON.stringify({ answer: message }),
          }
        );
  
        if (!response.ok) {
          let errorDetail = "Error procesando la entrada vía HTTP";
           try {
              const errorData = await response.json();
              errorDetail = errorData.detail || errorDetail;
          } catch(e) { /* Ignore */ }
          throw new Error(errorDetail);
        }
  
        const data = await response.json();
  
        // Format the HTTP response to match ProcessInputResponse
        // Use next_step as primary response if available, otherwise use main data
        const relevantAgentData = data.next_step ? data.next_step : data;
        const evaluationData = data.next_step ? data : null; // If next_step exists, treat main data as evaluation
  
        const inputResponse: ProcessInputResponse = {
            session_id: targetSessionId,
            agent_output: {
                text: relevantAgentData.text || "",
                image_url: relevantAgentData.image_url,
                audio_url: relevantAgentData.audio_url,
                prompt_for_answer: relevantAgentData.waiting_for_input ?? relevantAgentData.state_metadata?.waiting_for_input ?? false,
                evaluation: evaluationData?.evaluation_type || relevantAgentData.evaluation_type || relevantAgentData.last_evaluation || null,
                is_final_step: relevantAgentData.is_final_step || false,
            },
            mastery_level: relevantAgentData.state_metadata?.mastery ?? 0,
        };
  
        // Add custom properties
        (inputResponse as any).hasEvaluation = !!evaluationData;
        (inputResponse as any).evaluationText = evaluationData?.text || "";
        (inputResponse as any).isCorrect = !!evaluationData?.is_correct;
  
        this._normalizeContentUrls(inputResponse.agent_output);
        this.processingRequest = false;
        return inputResponse;
  
      } catch (error) {
        this.processingRequest = false;
        console.error("HTTP fallback for processInput failed:", error);
        throw error;
      }
    }
  }

  /**
   * Get the current status of a session via WebSocket (preferred) or HTTP fallback.
   */
  async getSessionStatus(
    sessionId: string | null = null
  ): Promise<SessionStatusResponse> {
    const targetSessionId = sessionId || this.currentSessionId;
    if (!targetSessionId) {
        throw new Error("No active session ID available for getSessionStatus.");
    }

    // Prefer WebSocket
    if (this.isWebSocketConnected()) {
        console.log(`Requesting session status via WebSocket for ${targetSessionId}`);
        return new Promise<SessionStatusResponse>((resolve, reject) => {
            const requestId = uuidv4();
            const timeoutHandle = setTimeout(() => {
                if (this.messageCallbacks.has(requestId)) {
                    this.messageCallbacks.delete(requestId);
                    console.error(`Timeout waiting for status response ${requestId}`);
                    reject(new Error("Tiempo de espera agotado para obtener estado de sesión."));
                }
            }, 1000000);

            this.messageCallbacks.set(requestId, (response) => {
                clearTimeout(timeoutHandle);
                this.messageCallbacks.delete(requestId);
                console.log(`Received WS status response for request ${requestId}:`, response);
                if (response.type === "error") {
                    reject(new Error(response.message || "Error obteniendo estado de sesión desde el servidor."));
                } else if (response.type === "state_update") {
                    // The backend sends the full serialized state in response.data
                    const stateData = response.data;
                    // We might need to format this if the SessionStatusResponse type differs significantly
                    const statusResponse: SessionStatusResponse = {
                         session_id: stateData.session_id,
                         current_topic: stateData.current_topic,
                         mastery_levels: stateData.topic_mastery || {}, // Ensure it's an object
                         current_cpa_phase: stateData.current_cpa_phase,
                         is_active: true, // Assume active if we get state
                         content_ready: !stateData.waiting_for_input, // Example logic
                         // agent_output: undefined, // Status usually doesn't include latest output
                         error: undefined,
                         created_at: Date.parse(stateData.created_at), // Convert ISO string to timestamp number
                         last_updated: Date.parse(stateData.updated_at) // Convert ISO string to timestamp number
                    }
                    resolve(statusResponse);
                } else {
                    console.warn("Received unexpected message type for status request:", response.type);
                    reject(new Error(`Tipo de respuesta inesperado del servidor: ${response.type}`));
                }
            });

            this.wsConnection?.send(JSON.stringify({ action: "get_state", requestId }));
        });
    } else {
      // Fallback to HTTP
      console.warn(`WebSocket not connected for session ${targetSessionId}. Using HTTP fallback for getSessionStatus.`);
      try {
        const response = await fetch(
          `${this.baseUrl}/api/sessions/${targetSessionId}`,
          { method: "GET", headers: this.headers }
        );

        if (!response.ok) {
          let errorDetail = "Error obteniendo estado de sesión vía HTTP";
          try {
              const errorData = await response.json();
               errorDetail = errorData.detail || errorDetail;
          } catch(e) { /* Ignore */ }
          // If session not found via HTTP, clear the local storage
          if (response.status === 404) {
               console.log(`Session ${targetSessionId} not found via HTTP, clearing local storage.`);
               this._clearSession();
               this.currentSessionId = null;
          }
          throw new Error(errorDetail);
        }

        const stateData = await response.json(); // Expects full serialized state

        const statusResponse: SessionStatusResponse = {
             session_id: stateData.session_id,
             current_topic: stateData.current_topic,
             mastery_levels: stateData.topic_mastery || {},
             current_cpa_phase: stateData.current_cpa_phase,
             is_active: true,
             content_ready: !stateData.waiting_for_input,
             error: undefined,
             created_at: Date.parse(stateData.created_at),
             last_updated: Date.parse(stateData.updated_at)
        }

        return statusResponse;

      } catch (error) {
        console.error("HTTP fallback for getSessionStatus failed:", error);
        throw error;
      }
    }
  }

  /**
   * End an active session. Prefers closing WebSocket first.
   * Note: The backend currently doesn't have an explicit "end session" endpoint.
   * We will close the WebSocket and clear local state. The backend session
   * will eventually be cleaned up by the inactivity task.
   */
  async endSession(sessionId: string | null = null): Promise<boolean> {
    const targetSessionId = sessionId || this.currentSessionId;
    console.log(`Attempting to end session: ${targetSessionId}`);

    if (!targetSessionId) {
      console.warn("No active session ID to end.");
      return false;
    }

    // Clear any pending reconnection timers
    if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
    }

    // Prevent future reconnections for this client instance
    this.maxReconnectAttempts = 0;

    // Close the WebSocket connection if it exists and is open/connecting
    if (this.wsConnection && (this.wsConnection.readyState === WebSocket.OPEN || this.wsConnection.readyState === WebSocket.CONNECTING)) {
      console.log(`Closing WebSocket connection for session ${targetSessionId}.`);
      this.wsConnection.close(1000, "Client ending session"); // Send standard close code
    }
    this.wsConnection = null;


    // Clear local session state *immediately* regardless of backend
    if (targetSessionId === this.currentSessionId) {
        this.currentSessionId = null;
        this._clearSession(); // Clear from localStorage
        console.log(`Cleared local session state for ${targetSessionId}.`);
    }

    // Note: No explicit backend call to end/delete the session is made here,
    // relying on the backend's inactivity cleanup. If an explicit endpoint existed,
    // we would call it here (e.g., DELETE /api/sessions/{targetSessionId})

    return true; // Indicate local cleanup was successful
  }

  /**
   * Format diagnostic results for potential future use (currently not sent in startSession)
   */
  formatDiagnosticResults(
    diagnosticResults: DiagnosticQuestionResult[]
  ): DiagnosticResults | null {
     if (!diagnosticResults || !Array.isArray(diagnosticResults) || diagnosticResults.length === 0) {
      return null;
    }

    const correctAnswers = diagnosticResults.filter(r => r.correct).length;
    const totalQuestions = diagnosticResults.length;
    const percentCorrect = (correctAnswers / totalQuestions) * 100;

    let recommendedLevel = "initial"; // Default
    if (percentCorrect >= 80) recommendedLevel = "advanced";
    else if (percentCorrect >= 50) recommendedLevel = "intermediate";
    else if (percentCorrect >= 30) recommendedLevel = "beginner";


    return {
      score: percentCorrect,
      correct_answers: correctAnswers,
      total_questions: totalQuestions,
      recommended_level: recommendedLevel,
      question_results: diagnosticResults // Include original results
    };
  }

   /**
   * Register a global message handler for broadcast/push messages from the server.
   */
  addMessageHandler(handler: (data: any) => void): void {
    if (typeof handler === 'function' && !this.messageHandlers.includes(handler)) {
      this.messageHandlers.push(handler);
      console.log("Added message handler.");
    }
  }

  /**
   * Remove a registered message handler.
   */
  removeMessageHandler(handler: (data: any) => void): void {
    const index = this.messageHandlers.indexOf(handler);
    if (index !== -1) {
      this.messageHandlers.splice(index, 1);
      console.log("Removed message handler.");
    }
  }

  /**
   * Establishes the persistent WebSocket connection for the current session ID.
   * Handles connection logic, message routing, and reconnection.
   */
  private _connectToSessionWebSocket(): void {
    if (!this.currentSessionId) {
      console.error("Cannot connect to session WebSocket without a currentSessionId.");
      return;
    }
    if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
      console.log(`Already connected to session ${this.currentSessionId}.`);
      return;
    }
     if (this.wsConnection && this.wsConnection.readyState === WebSocket.CONNECTING) {
      console.log(`Connection attempt already in progress for session ${this.currentSessionId}.`);
      return;
    }


    const sessionWsUrl = `${this.wsBaseUrl}/ws/session/${this.currentSessionId}`;
    console.log(`Attempting to connect to WebSocket: ${sessionWsUrl}`);

    // Reset reconnect attempts if starting a fresh connection sequence
    // this.reconnectAttempts = 0; // Reset moved to successful open

    try {
        const ws = new WebSocket(sessionWsUrl);
        this.wsConnection = ws; // Assign immediately to prevent race conditions

        ws.onopen = async () => {
          console.log(`WebSocket connection established for session ${this.currentSessionId}`);
          this.reconnectAttempts = 0;

          // Verify connection with a simple ping-pong
          try {
            const verifyId = uuidv4();
            const verifyPromise = new Promise<boolean>((resolve, reject) => {
              // Set a timeout for the verification
              const verifyTimeout = setTimeout(() => {
                this.messageCallbacks.delete(verifyId);
                console.warn("Connection verification timed out");
                resolve(false); // Don't reject, just resolve with false
              }, 5000);

              // Set up the callback for the pong response
              this.messageCallbacks.set(verifyId, (response) => {
                clearTimeout(verifyTimeout);
                this.messageCallbacks.delete(verifyId);
                if (response.type === "pong") {
                  console.log("Connection verified with pong");
                  resolve(true);
                } else {
                  console.warn("Unexpected response type for verification", response.type);
                  resolve(false);
                }
              });
            });

            // Send the ping
            if (this.wsConnection?.readyState === WebSocket.OPEN) {
              this.wsConnection.send(JSON.stringify({
                action: "ping",
                timestamp: Date.now(),
                requestId: verifyId
              }));

              // Wait for the result
              const verified = await verifyPromise;
              if (!verified) {
                console.warn("Connection verification failed, will attempt reconnect");
                ws.close(); // Will trigger reconnection logic via onclose
                return;
              }
            }

            // If we get here, verification passed
            console.log("Connection verified and ready");
            this._startHeartbeat();
          } catch (error) {
            console.error("Error during connection verification:", error);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data as string);
            
            // Add URL normalization here for any agent response
            if (data.type === "agent_response" && data.data) {
              // Check if the data contains image or audio URLs that need normalization
              if (data.data.image_url || data.data.audio_url) {
                console.log("Before URL normalization:", {
                  image: data.data.image_url, 
                  audio: data.data.audio_url
                });
                
                // Normalize URLs directly in the data
                if (data.data.image_url && typeof data.data.image_url === 'string' && data.data.image_url.startsWith('/')) {
                  const backendUrl = "http://127.0.0.1:8000"; // Hardcode for testing
                  const base = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
                  data.data.image_url = `${base}${data.data.image_url}`;
                }
                
                if (data.data.audio_url && typeof data.data.audio_url === 'string' && data.data.audio_url.startsWith('/')) {
                  const backendUrl = "http://127.0.0.1:8000"; // Hardcode for testing
                  const base = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
                  data.data.audio_url = `${base}${data.data.audio_url}`;
                }
                
                console.log("After URL normalization:", {
                  image: data.data.image_url, 
                  audio: data.data.audio_url
                });
              }
            }
            
            // Log message for debugging
            console.log("WebSocket message received:", {
              type: data.type,
              requestId: data.requestId,
              callbacksAvailable: Array.from(this.messageCallbacks.keys()),
              dataAction: data.data?.action || "none"
            });
        
            // Track if this is an agent response that modifies state
            const isAgentResponse = data.type === "agent_response";
            
            // 1. Check if it's a response to a specific request via requestId
            if (data.requestId && this.messageCallbacks.has(data.requestId)) {
              console.log(`Processing callback for requestId: ${data.requestId}`);
              
              // Critical: Save a reference to the callback before potentially removing it
              const callback = this.messageCallbacks.get(data.requestId);
              
              // Call the callback with the data
              callback?.(data);
              
              // For evaluation responses, keep the callback for the next message
              if (isAgentResponse && data.data?.action === "evaluation_result") {
                console.log(`Keeping callback for requestId: ${data.requestId} as it's an evaluation response`);
                // Don't delete the callback yet, as we expect the next step content with the same ID
              } else if (isAgentResponse && data.data?.action === "present_content") {
                // If we get a content message after an evaluation, it's a follow-up
                // Check if the callback is still registered (means we processed eval already)
                if (this.messageCallbacks.has(data.requestId)) {
                  console.log(`Processing content after evaluation for requestId: ${data.requestId}`);
                  // We can now remove the callback after the complete sequence
                  this.messageCallbacks.delete(data.requestId);
                }
              } else {
                // For non-evaluation responses, clean up the callback immediately
                console.log(`Removing callback for requestId: ${data.requestId} after processing`);
                this.messageCallbacks.delete(data.requestId);
              }
            } 
            // 2. If it might be related to a submit_answer but missing requestId
            else if (isAgentResponse && this.processingRequest) {
              console.log("Received agent_response during active request, trying to match");
              
              // Find pending callbacks (newest first since that's likely the current request)
              const pendingRequestIds = Array.from(this.messageCallbacks.keys());
              
              if (pendingRequestIds.length > 0) {
                // Start with the newest request ID (typically the current one)
                const latestRequestId = pendingRequestIds[pendingRequestIds.length - 1];
                console.log(`Matching to latest pending request: ${latestRequestId}`);
                const callback = this.messageCallbacks.get(latestRequestId);
                callback?.(data);
                
                // For evaluation responses, keep the callback for the next message
                if (isAgentResponse && data.data?.action === "evaluation_result") {
                  console.log(`Keeping callback for matched request: ${latestRequestId}`);
                  // Keep the callback for follow-up messages
                } else {
                  console.log(`Removing callback for matched request: ${latestRequestId}`);
                  this.messageCallbacks.delete(latestRequestId);
                }
              }
            }
            // 3. If not a specific response, treat as a push/broadcast message
            else {
              // For all other messages (like pongs), notify general handlers
              this.messageHandlers.forEach((handler) => {
                try {
                  handler(data);
                } catch (handlerError) {
                  console.error("Error executing general message handler:", handlerError);
                }
              });
            }
            
            // After processing all messages, if this was the final practice content
            // and we're still in processing state, turn it off
            if (isAgentResponse && 
                data.data?.action === "present_content" && 
                this.processingRequest) {
              console.log("Request cycle complete, releasing processingRequest lock");
              this.processingRequest = false;
            }
            
          } catch (error) {
            console.error("Error parsing message on session WebSocket:", error);
          }
        };
        
        ws.onclose = (event) => {
          console.log(
            `Session WebSocket closed for ${this.currentSessionId}. Code: ${event.code}, Reason: '${event.reason}', Clean: ${event.wasClean}`
          );

          // Clear the reference if this specific socket closed
          if (this.wsConnection === ws) {
               this.wsConnection = null;
          }


          // --- Reconnection Logic ---
          // Don't attempt to reconnect if the close was initiated intentionally (code 1000)
          // or if max attempts reached, or if no session ID exists anymore
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts && this.currentSessionId) {
            this.reconnectAttempts++;
            // Exponential backoff
            const delay = this.reconnectTimeout * Math.pow(1.5, this.reconnectAttempts - 1);
            console.log(
              `Attempting WebSocket reconnection in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
            );

            // Clear previous timer if any
             if (this.reconnectTimer) {
               clearTimeout(this.reconnectTimer);
             }


            this.reconnectTimer = setTimeout(() => {
                // Double-check we still have a session ID before reconnecting
                if (this.currentSessionId) {
                    console.log("Executing reconnect attempt...");
                    this._connectToSessionWebSocket(); // Try connecting again
                } else {
                     console.log("Session ID cleared, aborting reconnect attempt.");
                }
            }, delay);

          } else if (event.code === 1000) {
               console.log("WebSocket closed normally by client or server.");
          } else if (!this.currentSessionId){
               console.log("No current session ID, stopping reconnection attempts.");
          } else {
            console.warn(
              `Max WebSocket reconnection attempts (${this.maxReconnectAttempts}) reached for session ${this.currentSessionId}. Giving up.`
            );
            // Consider notifying the user state (e.g., via a message handler)
             this.messageHandlers.forEach(h => h({ type: 'connection_error', message: 'Connection lost permanently.'}));
          }
        };
      } catch (error) {
            console.error("Failed to create WebSocket for session connection:", error);
            // Maybe schedule a reconnect attempt here too?
      }
  }

  private _startHeartbeat(): void {
    // Clear any existing heartbeat
    this._clearHeartbeat();
    
    // Start a new heartbeat interval
    this.heartbeatInterval = setInterval(() => {
      if (this.wsConnection?.readyState === WebSocket.OPEN) {
        console.log("Sending heartbeat ping...");
        this.wsConnection.send(JSON.stringify({
          action: "ping",
          timestamp: Date.now()
        }));
      } else {
        console.log("Connection not open, skipping heartbeat");
        this._clearHeartbeat(); // Clear if connection is not open
      }
    }, this.heartbeatTimeout);
  }
  
  private _clearHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // --- Session Persistence ---

  /**
   * Save current session ID and timestamp to localStorage.
   */
  private _saveSession(): void {
    if (typeof window !== "undefined" && this.currentSessionId) {
      try {
        localStorage.setItem("mathTutorSessionId", this.currentSessionId);
        localStorage.setItem("mathTutorSessionTimestamp", Date.now().toString());
        // console.log(`Saved session ${this.currentSessionId} to localStorage.`);
      } catch (e) {
        console.warn("Could not save session to localStorage", e);
      }
    }
  }

  /**
   * Restore session ID from localStorage if valid and not expired.
   * **Does not automatically connect anymore.**
   */
  private _restoreSession(): void {
    if (typeof window !== "undefined") {
      try {
        const savedSessionId = localStorage.getItem("mathTutorSessionId");
        const sessionTimestamp = localStorage.getItem("mathTutorSessionTimestamp");

        // Session expiry check (e.g., 1 hour)
        const SESSION_MAX_AGE = 60 * 60 * 1000; // 1 hour in ms
        const isSessionExpired = sessionTimestamp
          ? Date.now() - parseInt(sessionTimestamp, 10) > SESSION_MAX_AGE
          : true; // Treat as expired if no timestamp

        if (savedSessionId && !isSessionExpired) {
          console.log(`Restoring session ID from localStorage: ${savedSessionId}`);
          this.currentSessionId = savedSessionId;
          
          // Add this line to establish the WebSocket connection:
          this._connectToSessionWebSocket();
        } else {
          if (savedSessionId) { // Only log/clear if there *was* an ID
            console.log(`Stored session ${savedSessionId} is expired or invalid. Clearing.`);
            this._clearSession();
          }
        }
      } catch (e) {
        console.warn("Could not restore session from localStorage", e);
        this._clearSession(); // Clear if error during restore
      }
    }
  }

  /**
   * Clear session ID and timestamp from localStorage.
   */
  private _clearSession(): void {
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem("mathTutorSessionId");
        localStorage.removeItem("mathTutorSessionTimestamp");
        // console.log("Cleared session from localStorage.");
      } catch (e) {
        console.warn("Could not clear session from localStorage", e);
      }
    }
  }


  // --- Utility Methods ---

  /**
   * Checks if the WebSocket connection is currently open.
   */
  isWebSocketConnected(): boolean {
    return this.wsConnection?.readyState === WebSocket.OPEN;
  }

  /**
   * Normalize relative URLs in agent output to absolute URLs based on the API base URL.
   */
  private _normalizeContentUrls(agentOutput: AgentOutput | null): void {
    if (!agentOutput) return;
    try {
      console.log("Before URL normalization in method:", 
        {image: agentOutput.image_url, audio: agentOutput.audio_url});
        
      const makeAbsolute = (url: string | null | undefined): string | null | undefined => {
        if (url && typeof url === 'string' && url.startsWith('/')) {
          // Force use http://127.0.0.1:8000 for local development
          const backendUrl = "http://127.0.0.1:8000"; // Hardcode for testing
          const base = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
          const absoluteUrl = `${base}${url}`;
          console.log(`Converting ${url} → ${absoluteUrl}`);
          return absoluteUrl;
        }
        return url;
      };
  
      agentOutput.image_url = makeAbsolute(agentOutput.image_url);
      agentOutput.audio_url = makeAbsolute(agentOutput.audio_url);
      
      console.log("After URL normalization in method:", 
        {image: agentOutput.image_url, audio: agentOutput.audio_url});
    } catch (error) {
      console.warn("Failed to normalize content URLs:", error);
    }
  }

  /**
   * Map a user-friendly learning path name to the backend's initial topic ID.
   */
  private _mapLearningPathToTopic(learningPath: string): string {
    const path = learningPath?.toLowerCase().trim() || 'fractions'; // Default to fractions
    const map: Record<string, string> = {
      fractions: "fractions_introduction",
      addition: "addition_introduction",
      subtraction: "subtraction_introduction",
      multiplication: "multiplication_introduction",
      division: "division_introduction",
      // Add more mappings as needed
    };
    return map[path] || "fractions_introduction"; // Default if path not found
  }

  // Helper for generating unique IDs (consider using a library like uuid)
}

// Simple UUID v4 generator if needed (use a library for production)
function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}


export default MathTutorClient;