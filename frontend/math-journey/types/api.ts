// Add or update the types in types/api.ts to ensure consistency

/**
 * Tipos para la API del Tutor Matemático
 * Actualizados para soportar la nueva funcionalidad WebSocket y diagnóstico
 */

// Enumeración para resultados de evaluación
export enum EvaluationResult {
  CORRECT = "Correct",
  INCORRECT_CONCEPTUAL = "Incorrect_Conceptual",
  INCORRECT_CALCULATION = "Incorrect_Calculation",
  UNCLEAR = "Unclear"
}

// Enumeración para niveles de dificultad
export enum DifficultySetting {
  INITIAL = "initial",
  BEGINNER = "beginner",
  INTERMEDIATE = "intermediate",
  ADVANCED = "advanced"
}

// Configuración del Cliente API
export interface MathTutorClientConfig {
  baseUrl?: string;
  headers?: Record<string, string>;
}

// Opciones para iniciar sesión
export interface StartSessionOptions {
  personalized_theme?: string;
  learning_path?: string | null;
  config?: SessionConfig | null;
  diagnostic_results?: DiagnosticQuestionResult[] | null;
  initial_message?: string | null;
}

// Respuesta de inicio de sesión
export interface StartSessionResponse {
  session_id: string;
  initial_output: AgentOutput;
  status: string;
}

// Respuesta de procesamiento de entrada
export interface ProcessInputResponse {
  session_id: string;
  agent_output: AgentOutput;
  mastery_level?: number;
}

// Estado de la sesión
export interface SessionStatusResponse {
  session_id: string;
  current_topic: string;
  mastery_levels: Record<string, number>;
  current_cpa_phase: string;
  is_active: boolean;
  content_ready: boolean;
  agent_output?: AgentOutput;
  error?: string;
  created_at: number;
  last_updated: number;
}

// Configuración del tutor
export interface SessionConfig {
  initial_topic?: string;
  initial_cpa_phase?: string;
  initial_difficulty?: string;
  difficulty_adjustment_rate?: number;
  enable_audio?: boolean;
  enable_images?: boolean;
  language?: string;
  user_id?: string;
  diagnostic_score?: number;
  diagnostic_details?: any[];
}

// Resultado de una pregunta diagnóstica
export interface DiagnosticQuestionResult {
  question_id: string;
  correct: boolean;
  concept_tested?: string;
}

// Resultados del diagnóstico completo
export interface DiagnosticResults {
  score: number;
  correct_answers: number;
  total_questions: number;
  recommended_level: string;
  question_results?: DiagnosticQuestionResult[];
}

// Salida del agente
export interface AgentOutput {
  text: string;
  image_url?: string | null;
  audio_url?: string | null;
  prompt_for_answer?: boolean;
  evaluation?: string | null;
  is_final_step?: boolean;
  action_type?: string;     // Added to store action from backend
  content_type?: string;    // Added to store content_type from backend
  waiting_for_input?: boolean; // Added to explicitly track input state
  state_metadata?: any; // Added to store metadata from backend
}

// Mensaje WebSocket
export interface WebSocketMessage {
  type: string;
  data?: any;
  requestId?: string;
  message?: string;
}

// Estado de conexión WebSocket
export enum WebSocketState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3
}