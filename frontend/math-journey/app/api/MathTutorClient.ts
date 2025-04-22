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
  AgentOutput
} from "@/types/api";

// Configuración API por defecto
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class MathTutorClient {
  private baseUrl: string;
  private wsBaseUrl: string;
  private headers: Record<string, string>;
  private currentSessionId: string | null;
  private wsConnection: WebSocket | null;
  private messageCallbacks: Map<string, (data: any) => void>;
  private messageHandlers: Array<(data: any) => void>;
  private reconnectAttempts: number;
  private maxReconnectAttempts: number;
  private reconnectTimeout: number;
  private processingRequest: boolean;
  private reconnectTimer: ReturnType<typeof setTimeout> | null;

  /**
   * Initialize the API client with optional configuration
   */
  constructor(config: MathTutorClientConfig = {}) {
    this.baseUrl = config.baseUrl || API_BASE_URL;
    this.wsBaseUrl = this.baseUrl.replace(/^http/, 'ws');
    this.headers = {
      'Content-Type': 'application/json',
      ...(config.headers || {})
    };
    this.currentSessionId = null;
    this.wsConnection = null;
    this.messageCallbacks = new Map();
    this.messageHandlers = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = 1000;
    this.processingRequest = false;
    this.reconnectTimer = null;
    
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
      let sessionConfig = config || {};
      
      // Apply diagnostic results if available
      if (diagnostic_results) {
        sessionConfig.initial_difficulty = diagnostic_results.recommended_level || 'beginner';
      }
      
      // Set initial topic based on learning path
      if (learning_path) {
        sessionConfig.initial_topic = this._mapLearningPathToTopic(learning_path);
      }

      console.log("Iniciando nueva sesión vía WebSocket...");
      
      // Create WebSocket connection to start new session
      return new Promise<StartSessionResponse>((resolve, reject) => {
        const ws = new WebSocket(`${this.wsBaseUrl}/ws/new_session`);
        
        ws.onopen = () => {
          console.log("WebSocket conectado para nueva sesión");
          ws.send(JSON.stringify({
            action: 'create_session',
            data: {
              topic_id: sessionConfig.initial_topic || this._mapLearningPathToTopic(learning_path || 'fractions'),
              personalized_theme,
              user_id: config?.user_id,
              initial_mastery: 0.0
            }
          }));
        };
        
        ws.onerror = (event) => {
          console.error("Error de WebSocket:", event);
          reject(new Error("Error de conexión WebSocket"));
          
          // Try fallback with HTTP
          this._startSessionHttp({
            personalized_theme,
            initial_message,
            learning_path,
            diagnostic_results
          }).then(resolve).catch(reject);
        };
        
        ws.onmessage = (event) => {
          try {
            const response = JSON.parse(event.data);
            console.log("Respuesta WebSocket de nueva sesión:", response);
            
            if (response.type === "session_created") {
              // Store session information
              this.currentSessionId = response.data.session_id;
              this._saveSession();
              
              // Create response object
              const sessionResponse: StartSessionResponse = {
                session_id: response.data.session_id,
                initial_output: {
                  text: response.data.result.text || "¡Bienvenido a tu sesión de aprendizaje!",
                  image_url: response.data.result.image_url,
                  audio_url: response.data.result.audio_url,
                  prompt_for_answer: response.data.result.requires_input || false
                },
                status: "active"
              };
              
              // Normalize URLs
              this._normalizeContentUrls(sessionResponse.initial_output);
              
              // Close temporary connection
              ws.close();
              
              // Connect to the session WebSocket
              this._connectToSessionWebSocket();
              
              resolve(sessionResponse);
            } else if (response.type === "error") {
              reject(new Error(response.message || "Error al crear la sesión"));
              ws.close();
            }
          } catch (error) {
            console.error("Error procesando mensaje WebSocket:", error);
            reject(error as Error);
            ws.close();
          }
        };
        
        ws.onclose = () => {
          console.log("WebSocket de nueva sesión cerrado");
        };
      });
      
    } catch (error) {
      console.error('Error iniciando sesión:', error);
      throw error;
    }
  }

  /**
   * Fallback: Start session via HTTP if WebSocket fails
   */
  private async _startSessionHttp({
    personalized_theme = 'space',
    initial_message = null,
    config = null,
    diagnostic_results = null,
    learning_path = null
  }: StartSessionOptions = {}): Promise<StartSessionResponse> {
    console.log("Fallback: Iniciando sesión vía HTTP...");
    
    const response = await fetch(`${this.baseUrl}/api/sessions`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        topic_id: learning_path ? this._mapLearningPathToTopic(learning_path) : 'fractions_introduction',
        personalized_theme,
        initial_mastery: 0.0
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Error iniciando sesión vía HTTP');
    }
    
    const data = await response.json();
    this.currentSessionId = data.session_id;
    this._saveSession();
    
    // Connect to the session WebSocket after starting it via HTTP
    this._connectToSessionWebSocket();
    
    return {
      session_id: data.session_id,
      initial_output: data.result,
      status: "active"
    };
  }

  /**
   * Process user input in an active session
   */
  async processInput(message: string, sessionId: string | null = null): Promise<ProcessInputResponse> {
    if (this.processingRequest) {
      console.warn("Ya hay una solicitud en proceso");
      throw new Error('Una solicitud ya está en progreso. Por favor espere.');
    }
    
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No hay una sesión activa. Inicie una sesión primero.');
    }
    
    this.processingRequest = true;
    
    try {
      // Check if WebSocket is available
      if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
        // Use WebSocket for communication
        return new Promise<ProcessInputResponse>((resolve, reject) => {
          // Generate unique ID for the request
          const requestId = Math.random().toString(36).substring(2, 9);
          
          // Set up callback for this request
          this.messageCallbacks.set(requestId, (data) => {
            // Remove the callback once called
            this.messageCallbacks.delete(requestId);
            
            if (data.type === "error") {
              reject(new Error(data.message || "Error procesando la entrada"));
            } else if (data.type === "agent_response") {
              // Create response object
              const inputResponse: ProcessInputResponse = {
                session_id: targetSessionId,
                agent_output: {
                  text: data.data.text || "He procesado tu entrada.",
                  image_url: data.data.image_url,
                  audio_url: data.data.audio_url,
                  prompt_for_answer: data.data.requires_input || false,
                  evaluation: data.data.evaluation_type,
                  is_final_step: data.data.is_final_step || false
                },
                mastery_level: data.data.state_metadata?.mastery || 0
              };
              
              // Normalize URLs
              this._normalizeContentUrls(inputResponse.agent_output);
              
              resolve(inputResponse);
            } else {
              reject(new Error("Tipo de respuesta inesperado"));
            }
          });
          
          // Send message via WebSocket
          this.wsConnection?.send(JSON.stringify({
            action: 'submit_answer',
            requestId,
            data: {
              answer: message
            }
          }));
          
          // Set timeout in case no response is received
          setTimeout(() => {
            if (this.messageCallbacks.has(requestId)) {
              this.messageCallbacks.delete(requestId);
              reject(new Error("Tiempo de espera agotado"));
            }
          }, 30000);
        }).finally(() => {
          this.processingRequest = false;
        });
      } else {
        // Fallback to HTTP API
        console.log("WebSocket no disponible, usando HTTP para enviar mensaje...");
        const response = await fetch(`${this.baseUrl}/api/sessions/${targetSessionId}/answer`, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({ answer: message })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error procesando la entrada vía HTTP');
        }
        
        const data = await response.json();
        this.processingRequest = false;
        
        // Normalize URLs
        if (data.agent_output) {
          this._normalizeContentUrls(data.agent_output);
        }
        
        return data as ProcessInputResponse;
      }
    } catch (error) {
      console.error('Error procesando la entrada:', error);
      this.processingRequest = false;
      throw error;
    }
  }

  /**
   * Get the current status of a session
   */
  async getSessionStatus(sessionId: string | null = null): Promise<SessionStatusResponse> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      throw new Error('No hay una sesión activa.');
    }
    
    try {
      // Check if WebSocket is available
      if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
        return new Promise<SessionStatusResponse>((resolve, reject) => {
          // Generate unique ID for the request
          const requestId = Math.random().toString(36).substring(2, 9);
          
          // Set up callback for this request
          this.messageCallbacks.set(requestId, (data) => {
            // Remove the callback once called
            this.messageCallbacks.delete(requestId);
            
            if (data.type === "error") {
              reject(new Error(data.message || "Error obteniendo estado de sesión"));
            } else if (data.type === "state_update") {
              resolve(data.data as SessionStatusResponse);
            } else {
              reject(new Error("Tipo de respuesta inesperado"));
            }
          });
          
          // Send message via WebSocket
          this.wsConnection?.send(JSON.stringify({
            action: 'get_state',
            requestId
          }));
          
          // Set timeout in case no response is received
          setTimeout(() => {
            if (this.messageCallbacks.has(requestId)) {
              this.messageCallbacks.delete(requestId);
              reject(new Error("Tiempo de espera agotado"));
            }
          }, 5000);
        });
      } else {
        // Fallback to HTTP API
        const response = await fetch(`${this.baseUrl}/api/sessions/${targetSessionId}`, {
          method: 'GET',
          headers: this.headers,
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error obteniendo estado de sesión');
        }
        
        const data = await response.json();
        
        // Normalize URLs in agent_output if present
        if (data.agent_output) {
          this._normalizeContentUrls(data.agent_output);
        }
        
        return data as SessionStatusResponse;
      }
    } catch (error) {
      console.error('Error obteniendo estado de sesión:', error);
      throw error;
    }
  }
  
  /**
   * End an active session
   */
  async endSession(sessionId: string | null = null): Promise<boolean> {
    const targetSessionId = sessionId || this.currentSessionId;
    
    if (!targetSessionId) {
      console.warn('No hay una sesión activa para finalizar.');
      return false;
    }
    
    try {
      // Close WebSocket connection if connected
      if (this.wsConnection) {
        this.wsConnection.close();
        this.wsConnection = null;
      }
      
      // Make HTTP request to end session
      const response = await fetch(`${this.baseUrl}/api/sessions/${targetSessionId}/reset`, {
        method: 'POST',
        headers: this.headers,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error finalizando sesión');
      }
      
      if (targetSessionId === this.currentSessionId) {
        this.currentSessionId = null;
        this._clearSession();
      }
      
      return true;
    } catch (error) {
      console.error('Error finalizando sesión:', error);
      
      // Even if there's an error, clean up the local session
      if (targetSessionId === this.currentSessionId) {
        this.currentSessionId = null;
        this._clearSession();
      }
      
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
   * Register a global message handler
   */
  addMessageHandler(handler: (data: any) => void): void {
    if (typeof handler === 'function' && !this.messageHandlers.includes(handler)) {
      this.messageHandlers.push(handler);
    }
  }
  
  /**
   * Remove a message handler
   */
  removeMessageHandler(handler: (data: any) => void): void {
    const index = this.messageHandlers.indexOf(handler);
    if (index !== -1) {
      this.messageHandlers.splice(index, 1);
    }
  }
  
  /**
   * Connect to a session's WebSocket
   */
  private _connectToSessionWebSocket(): void {
    if (!this.currentSessionId) {
      console.warn('No hay ID de sesión para conectar');
      return;
    }
    
    // Clear any existing connection
    if (this.wsConnection) {
      this.wsConnection.close();
    }
    
    // Reset reconnection attempts
    this.reconnectAttempts = 0;
    
    // Connect to the session WebSocket
    const ws = new WebSocket(`${this.wsBaseUrl}/ws/session/${this.currentSessionId}`);
    
    ws.onopen = () => {
      console.log(`WebSocket conectado a la sesión ${this.currentSessionId}`);
      this.wsConnection = ws;
      this.reconnectAttempts = 0;
      
      // Clear any reconnection timer
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Mensaje WebSocket de la sesión:", data);
        
        // Check if it's a response to a specific request
        if (data.requestId && this.messageCallbacks.has(data.requestId)) {
          const callback = this.messageCallbacks.get(data.requestId);
          if (callback) {
            callback(data);
          }
        } else {
          // Handle other types of messages
          // Notify all registered handlers
          this.messageHandlers.forEach(handler => {
            try {
              handler(data);
            } catch (handlerError) {
              console.error("Error en manejador de mensajes:", handlerError);
            }
          });
        }
      } catch (error) {
        console.error("Error procesando mensaje WebSocket:", error);
      }
    };
    
    ws.onerror = (event) => {
      console.error("Error de WebSocket:", event);
    };
    
    ws.onclose = (event) => {
      console.log(`Conexión WebSocket cerrada: ${event.code} - ${event.reason}`);
      this.wsConnection = null;
      
      // Try to reconnect if necessary
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = this.reconnectTimeout * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`Reconectando en ${delay}ms (intento ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        
        this.reconnectTimer = setTimeout(() => {
          if (this.currentSessionId) {
            this._connectToSessionWebSocket();
          }
        }, delay);
      } else {
        console.warn(`Intentos máximos de reconexión (${this.maxReconnectAttempts}) alcanzados`);
      }
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
    
    // Connect to the session WebSocket
    this._connectToSessionWebSocket();
  }
  
  /**
   * Check if there is an active session
   */
  hasActiveSession(): boolean {
    return this.currentSessionId !== null;
  }
  
  /**
   * Check if the WebSocket is connected
   */
  isWebSocketConnected(): boolean {
    return this.wsConnection !== null && this.wsConnection.readyState === WebSocket.OPEN;
  }
  
  /**
   * Normalize relative URLs in agent output to absolute URLs
   */
  private _normalizeContentUrls(agentOutput: AgentOutput): void {
    if (!agentOutput) return;
    
    try {
      if (agentOutput.image_url && typeof agentOutput.image_url === 'string' && agentOutput.image_url.startsWith('/')) {
        agentOutput.image_url = `${this.baseUrl}${agentOutput.image_url}`;
      }
      
      if (agentOutput.audio_url && typeof agentOutput.audio_url === 'string' && agentOutput.audio_url.startsWith('/')) {
        agentOutput.audio_url = `${this.baseUrl}${agentOutput.audio_url}`;
      }
    } catch (error) {
      console.warn('Error normalizando URLs de contenido:', error);
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
   * Save session to localStorage
   */
  private _saveSession(): void {
    if (typeof window !== 'undefined' && this.currentSessionId) {
      try {
        localStorage.setItem('mathTutorSessionId', this.currentSessionId);
        localStorage.setItem('mathTutorSessionTimestamp', Date.now().toString());
      } catch (e) {
        console.warn('No se pudo guardar la sesión en localStorage', e);
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
          console.log(`Restaurando sesión: ${savedSessionId}`);
          this.currentSessionId = savedSessionId;
          
          // Connect to the session WebSocket
          this._connectToSessionWebSocket();
        } else if (isSessionExpired) {
          console.log('Sesión expirada, limpiando');
          this._clearSession();
        }
      } catch (e) {
        console.warn('No se pudo restaurar la sesión desde localStorage', e);
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
        console.warn('No se pudo limpiar la sesión de localStorage', e);
      }
    }
  }
}

export default MathTutorClient;