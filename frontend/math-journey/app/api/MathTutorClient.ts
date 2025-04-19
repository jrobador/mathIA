/**
 * Cliente API para interactuar con el backend del Tutor de Matemáticas
 * Proporciona métodos para gestionar sesiones y comunicación con el agente
 */

// Definición de tipos para TypeScript
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
  
  // Configuración por defecto de la API
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  
  class MathTutorClient {
    private baseUrl: string;
    private headers: Record<string, string>;
    private currentSessionId: string | null;
  
    /**
     * Inicializa el cliente API con configuración opcional
     * @param config - Configuración opcional
     */
    constructor(config: MathTutorConfig = {}) {
      this.baseUrl = config.baseUrl || API_BASE_URL;
      this.headers = {
        'Content-Type': 'application/json',
        ...(config.headers || {}),
      };
      this.currentSessionId = null;
    }
  
    /**
     * Inicia una nueva sesión de tutoría
     * @param options - Configuración de la sesión
     * @returns Datos de la sesión iniciada
     */
    async startSession({
      personalized_theme = 'espacio',
      initial_message = null,
      config = null,
      diagnostic_results = null,
      learning_path = null
    }: StartSessionOptions = {}): Promise<StartSessionResponse> {
      try {
        // Preparar configuración basada en diagnóstico si está disponible
        let sessionConfig: SessionConfig = config || {};
        
        // Si hay resultados de diagnóstico, usarlos para configurar el nivel inicial
        if (diagnostic_results) {
          sessionConfig.initial_difficulty = diagnostic_results.recommended_level || 'beginner';
          sessionConfig.diagnostic_score = diagnostic_results.score;
          sessionConfig.diagnostic_details = diagnostic_results.question_results;
        }
        
        // Si hay un camino de aprendizaje seleccionado, configurarlo
        if (learning_path) {
          sessionConfig.initial_topic = learning_path === 'addition' 
            ? 'addition_introduction' 
            : learning_path === 'subtraction'
              ? 'subtraction_introduction'
              : learning_path === 'multiplication'
                ? 'multiplication_introduction'
                : 'fractions_introduction'; // Default
        }
  
        const response = await fetch(`${this.baseUrl}/session/start`, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({
            personalized_theme,
            initial_message,
            config: sessionConfig
          }),
        });
  
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error iniciando sesión');
        }
  
        const data = await response.json();
        this.currentSessionId = data.session_id;
        return data;
      } catch (error) {
        console.error('Error al iniciar sesión:', error);
        throw error;
      }
    }
  
    /**
     * Procesa la entrada del usuario en una sesión activa
     * @param message - Mensaje del usuario
     * @param sessionId - ID de sesión opcional (usa currentSessionId por defecto)
     * @returns Respuesta del agente
     */
    async processInput(message: string, sessionId: string | null = null): Promise<ProcessInputResponse> {
      const targetSessionId = sessionId || this.currentSessionId;
      
      if (!targetSessionId) {
        throw new Error('No hay una sesión activa. Inicia una sesión primero.');
      }
      
      try {
        const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/process`, {
          method: 'POST',
          headers: this.headers,
          body: JSON.stringify({ message }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error procesando entrada');
        }
        
        return await response.json();
      } catch (error) {
        console.error('Error al procesar entrada:', error);
        throw error;
      }
    }
    
    /**
     * Obtiene el estado actual de una sesión
     * @param sessionId - ID de sesión (opcional, usa currentSessionId por defecto)
     * @returns Estado de la sesión
     */
    async getSessionStatus(sessionId: string | null = null): Promise<SessionStatusResponse> {
      const targetSessionId = sessionId || this.currentSessionId;
      
      if (!targetSessionId) {
        throw new Error('No hay una sesión activa.');
      }
      
      try {
        const response = await fetch(`${this.baseUrl}/session/${targetSessionId}/status`, {
          method: 'GET',
          headers: this.headers,
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error obteniendo estado de sesión');
        }
        
        return await response.json();
      } catch (error) {
        console.error('Error al obtener estado de sesión:', error);
        throw error;
      }
    }
    
    /**
     * Finaliza una sesión activa
     * @param sessionId - ID de sesión (opcional, usa currentSessionId por defecto)
     */
    async endSession(sessionId: string | null = null): Promise<boolean> {
      const targetSessionId = sessionId || this.currentSessionId;
      
      if (!targetSessionId) {
        console.warn('No hay una sesión activa para finalizar.');
        return false;
      }
      
      try {
        const response = await fetch(`${this.baseUrl}/session/${targetSessionId}`, {
          method: 'DELETE',
          headers: this.headers,
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Error finalizando sesión');
        }
        
        if (targetSessionId === this.currentSessionId) {
          this.currentSessionId = null;
        }
        
        return true;
      } catch (error) {
        console.error('Error al finalizar sesión:', error);
        throw error;
      }
    }
    
    /**
     * Envía feedback sobre una sesión
     * @param rating - Valoración (1-5)
     * @param comments - Comentarios opcionales
     * @param sessionId - ID de sesión (opcional, usa currentSessionId por defecto)
     */
    async submitFeedback(rating: number, comments: string = "", sessionId: string | null = null): Promise<any> {
      const targetSessionId = sessionId || this.currentSessionId;
      
      if (!targetSessionId) {
        throw new Error('No hay una sesión activa para enviar feedback.');
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
          throw new Error(errorData.detail || 'Error enviando feedback');
        }
        
        return await response.json();
      } catch (error) {
        console.error('Error al enviar feedback:', error);
        throw error;
      }
    }
    
    /**
     * Procesa los resultados del diagnóstico para formatearlos correctamente
     * para el backend
     * @param diagnosticResults - Resultados del diagnóstico del frontend
     * @returns Resultados formateados para el backend
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
     * Obtiene el ID de la sesión actual
     * @returns ID de la sesión actual o null si no hay sesión activa
     */
    getCurrentSessionId(): string | null {
      return this.currentSessionId;
    }
    
    /**
     * Establece el ID de sesión actual manualmente
     * @param sessionId - ID de sesión a establecer
     */
    setCurrentSessionId(sessionId: string): void {
      this.currentSessionId = sessionId;
    }
  }
  
  export default MathTutorClient;