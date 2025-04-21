"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useMathTutor } from "@/hooks/use-math-tutor";
import { AgentOutput } from "@/types/api";

// Definición de los tipos de mensajes
export type MessageType = "system" | "user" | "assistant";

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
}

// Interfaz del contexto
interface TutorContextType {
  messages: Message[];
  isLoading: boolean;
  sessionId: string | null;
  currentOutput: AgentOutput | null;
  masteryLevel: number;
  error?: { message: string };
  
  // Acciones
  startSession: (options: {
    theme?: string;
    learningPath?: string;
    initialMessage?: string;
    diagnosticResults?: any[];
  }) => Promise<void>;
  
  sendMessage: (content: string) => Promise<void>;
  endSession: () => Promise<void>;
  clearMessages: () => void;
}

// Crear el contexto
const TutorContext = createContext<TutorContextType | undefined>(undefined);

// Generar ID único para mensajes
const generateId = () => Math.random().toString(36).substring(2, 9);

// Provider component
export function TutorProvider({ children }: { children: ReactNode }) {
  // Estado para los mensajes
  const [messages, setMessages] = useState<Message[]>([]);
  
  // Usar el hook de MathTutor
  const {
    sessionId,
    agentOutput,
    isLoading,
    masteryLevel,
    startSession: startTutorSession,
    sendMessage: sendTutorMessage,
    endSession: endTutorSession,
  } = useMathTutor();

  // Agregar mensaje del asistente cuando recibimos una respuesta
  useEffect(() => {
    if (agentOutput && agentOutput.text) {
      addMessage("assistant", agentOutput.text);
    }
  }, [agentOutput]);

  // Agregar un mensaje a la lista
  const addMessage = (type: MessageType, content: string) => {
    const newMessage: Message = {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, newMessage]);
  };

  // Iniciar una sesión
  const startSession = async (options: {
    theme?: string;
    learningPath?: string;
    initialMessage?: string;
    diagnosticResults?: any[];
  }) => {
    // Limpiar mensajes anteriores
    clearMessages();
    
    // Agregar mensaje inicial del sistema
    addMessage("system", "¡Bienvenido a tu sesión de aprendizaje! Estoy aquí para ayudarte.");
    
    // Si hay un mensaje inicial, agregarlo
    if (options.initialMessage) {
      addMessage("user", options.initialMessage);
    }
    
    // Iniciar la sesión
    await startTutorSession({
      personalized_theme: options.theme,
      learning_path: options.learningPath,
      initial_message: options.initialMessage,
      diagnostic_results: options.diagnosticResults,
    });
  };

  // Enviar un mensaje
  const sendMessage = async (content: string) => {
    // Agregar el mensaje del usuario
    addMessage("user", content);
    
    // Enviar al tutor
    await sendTutorMessage(content);
  };

  // Finalizar sesión
  const endSession = async () => {
    await endTutorSession();
    clearMessages();
  };

  // Limpiar mensajes
  const clearMessages = () => {
    setMessages([]);
  };

  // Valor del contexto
  const value: TutorContextType = {
    messages,
    isLoading,
    sessionId,
    currentOutput: agentOutput,
    masteryLevel,
    startSession,
    sendMessage,
    endSession,
    clearMessages,
  };

  return <TutorContext.Provider value={value}>{children}</TutorContext.Provider>;
}

// Hook para usar el contexto
export function useTutor() {
  const context = useContext(TutorContext);
  
  if (context === undefined) {
    throw new Error("useTutor debe ser usado dentro de un TutorProvider");
  }
  
  return context;
}