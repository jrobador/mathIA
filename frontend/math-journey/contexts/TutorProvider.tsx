"use client";

import React, { JSX, createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useMathTutor } from "@/hooks/use-math-tutor";

// Definición de la interfaz AgentOutput que refleja la estructura real que recibimos
interface AgentOutput {
  text?: string;
  image_url?: string | null;
  audio_url?: string | null;
  evaluation?: string | null;
  prompt_for_answer?: boolean;
  is_final_step?: boolean;
}

// Definiciones de tipos
export enum MessageType {
  SYSTEM = "system",
  USER = "user",
  ASSISTANT = "assistant"
}

export interface MessageOptions {
  imageUrl?: string | null;
  audioUrl?: string | null;
  isEvaluation?: boolean;
  evaluationType?: string | null;
  isCorrect?: boolean;
}

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  imageUrl?: string | null;
  audioUrl?: string | null;
  isEvaluation?: boolean;
  evaluationType?: string | null;
  isCorrect?: boolean;
}

export interface StartSessionOptions {
  theme?: string;
  learningPath?: string;
  initialMessage?: string;
  diagnosticResults?: any[];
}

// Interfaz del contexto
interface TutorContextType {
  messages: Message[];
  isLoading: boolean;
  sessionId: string | null;
  currentOutput: AgentOutput | null;
  masteryLevel: number;
  isConnected: boolean;
  error?: Error | null;
  
  startSession: (options: StartSessionOptions) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  endSession: () => Promise<void>;
  clearMessages: () => void;
  prepareForUnmount: () => void;
}

// Crear el contexto con un valor inicial de undefined
const TutorContext = createContext<TutorContextType | undefined>(undefined);

// Generar ID único para mensajes
const generateId = () => Math.random().toString(36).substring(2, 9);

interface TutorProviderProps {
  children: ReactNode;
}

export function TutorProvider({ children }: TutorProviderProps): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  
  const {
    sessionId,
    agentOutput,
    isLoading,
    masteryLevel,
    isConnected,
    error,
    startSession: startTutorSession,
    sendMessage: sendTutorMessage,
    endSession: endTutorSession,
    prepareForUnmount,
  } = useMathTutor();

  // Procesar nuevas salidas del agente con verificación de tipo explícita
  useEffect(() => {
    // Asegurar que agentOutput sea tratado con el tipo correcto
    if (agentOutput) {
      const output = agentOutput as AgentOutput;
      
      if (output.text) {
        addMessage(MessageType.ASSISTANT, output.text, {
          imageUrl: output.image_url,
          audioUrl: output.audio_url,
          isEvaluation: output.evaluation ? true : false,
          evaluationType: output.evaluation,
          isCorrect: output.evaluation === "Correct"
        });
      }
    }
  }, [agentOutput]);

  const addMessage = (type: MessageType, content: string, options: MessageOptions = {}): void => {
    const newMessage: Message = {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
      ...options
    };
    
    setMessages((prev) => [...prev, newMessage]);
  };

  const startSession = async (options: StartSessionOptions = {}): Promise<void> => {
    clearMessages();
    
    addMessage(MessageType.SYSTEM, "¡Bienvenido a tu sesión de aprendizaje! Estoy aquí para ayudarte.");
    
    if (options.initialMessage) {
      addMessage(MessageType.USER, options.initialMessage);
    }
    
    await startTutorSession({
      personalized_theme: options.theme,
      learning_path: options.learningPath,
      initial_message: options.initialMessage,
      diagnostic_results: options.diagnosticResults,
    });
  };

  const sendMessage = async (content: string): Promise<void> => {
    addMessage(MessageType.USER, content);
    
    await sendTutorMessage(content);
  };

  const endSession = async (): Promise<void> => {
    await endTutorSession();
    clearMessages();
  };

  const clearMessages = (): void => {
    setMessages([]);
  };

  const value: TutorContextType = {
    messages,
    isLoading,
    sessionId,
    currentOutput: agentOutput as AgentOutput | null,
    masteryLevel,
    isConnected,
    error,
    startSession,
    sendMessage,
    endSession,
    clearMessages,
    prepareForUnmount
  };

  return <TutorContext.Provider value={value}>{children}</TutorContext.Provider>;
}

export function useTutor(): TutorContextType {
  const context = useContext(TutorContext);
  
  if (context === undefined) {
    throw new Error("useTutor debe ser usado dentro de un TutorProvider");
  }
  
  return context;
}