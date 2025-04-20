/**
 * Definiciones de tipos para la API del Tutor de Matemáticas
 * Proporciona interfaces TypeScript para la comunicación con el backend
 */

// Enumeraciones
export enum CPAPhase {
    CONCRETE = "Concrete",
    PICTORIAL = "Pictorial",
    ABSTRACT = "Abstract"
  }
  
  export enum DifficultySetting {
    INITIAL = "initial",
    BEGINNER = "beginner",
    INTERMEDIATE = "intermediate",
    ADVANCED = "advanced"
  }
  
  export enum LearningPath {
    FRACTIONS = "fractions",
    ADDITION = "addition",
    SUBTRACTION = "subtraction",
    MULTIPLICATION = "multiplication",
    DIVISION = "division"
  }
  
  export enum EvaluationResult {
    CORRECT = "Correct",
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual",
    INCORRECT_CALCULATION = "Incorrect_Calculation",
    UNCLEAR = "Unclear"
  }
  
  // Configuración
  export interface TutorConfig {
    initial_topic?: string;
    initial_cpa_phase?: CPAPhase | string;
    initial_difficulty?: DifficultySetting | string;
    difficulty_adjustment_rate?: number;
    enable_audio?: boolean;
    enable_images?: boolean;
    language?: string;
    diagnostic_score?: number;
    diagnostic_details?: DiagnosticQuestionResult[];
  }
  
  // Diagnóstico
  export interface DiagnosticQuestionResult {
    question_id: string;
    correct: boolean;
    question_type?: string;
    concept_tested?: string;
  }
  
  export interface DiagnosticResults {
    score: number;
    correct_answers: number;
    total_questions: number;
    recommended_level: DifficultySetting | string;
    question_results: DiagnosticQuestionResult[];
    strengths?: string[];
    weaknesses?: string[];
  }
  
  // Feedback y agente
  export interface FeedbackDetails {
    type?: string;
    message?: string;
  }
  
  export interface AgentOutput {
    text?: string;
    image_url?: string;
    audio_url?: string;
    feedback?: FeedbackDetails;
    prompt_for_answer?: boolean;
    evaluation?: EvaluationResult | string;
  }
  
  // Solicitudes
  export interface StartSessionRequest {
    personalized_theme?: string;
    initial_message?: string;
    config?: TutorConfig;
    diagnostic_results?: DiagnosticResults;
    learning_path?: LearningPath | string;
  }
  
  export interface ProcessInputRequest {
    message: string;
  }
  
  // Respuestas
  export interface StartSessionResponse {
    session_id: string;
    initial_output: AgentOutput;
    status: string;
  }
  
  export interface ProcessInputResponse {
    session_id: string;
    agent_output: AgentOutput;
    mastery_level?: number;
  }
  
  export interface SessionStatusResponse {
    session_id: string;
    current_topic: string;
    mastery_levels: Record<string, number>;
    current_cpa_phase: string;
    is_active: boolean;
    created_at?: number;
    last_updated?: number;
  }
  
  // Información de temas y roadmap
  export interface RoadmapTopic {
    id: string;
    title: string;
    description: string;
    cpa_phases: string[];
    prerequisites: string[];
    required_mastery: number;
    practice_problems_min: number;
    subtopics: string[];
  }
  
  export interface LearningRoadmapInfo {
    id: string;
    title: string;
    description: string;
    topic_count: number;
  }
  
  export interface RoadmapTopicInfo extends RoadmapTopic {
    prerequisite_topics?: Array<{
      id: string;
      title: string;
    }>;
    next_topic?: {
      id: string;
      title: string;
    };
  }
  
  // Tipos auxiliares para el cliente
  export interface MathTutorClientConfig {
    baseUrl?: string;
    headers?: Record<string, string>;
  }
  
  export interface StartSessionOptions {
    personalized_theme?: string;
    initial_message?: string | null;
    config?: TutorConfig | null;
    diagnostic_results?: DiagnosticResults | null;
    learning_path?: string | null;
  }