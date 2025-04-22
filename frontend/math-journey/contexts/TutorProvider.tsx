"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useMathTutor } from "@/hooks/use-math-tutor";
import { AgentOutput } from "@/types/api";

// Message type definitions
export type MessageType = "system" | "user" | "assistant";

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
}

// Updated context interface with prepareForUnmount
interface TutorContextType {
  messages: Message[];
  isLoading: boolean;
  sessionId: string | null;
  currentOutput: AgentOutput | null;
  masteryLevel: number;
  error?: { message: string };
  
  startSession: (options: {
    theme?: string;
    learningPath?: string;
    initialMessage?: string;
    diagnosticResults?: any[];
  }) => Promise<void>;
  
  sendMessage: (content: string) => Promise<void>;
  endSession: () => Promise<void>;
  clearMessages: () => void;
  prepareForUnmount: () => void; // Added new method
}

const TutorContext = createContext<TutorContextType | undefined>(undefined);

const generateId = () => Math.random().toString(36).substring(2, 9);

export function TutorProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  
  const {
    sessionId,
    agentOutput,
    isLoading,
    masteryLevel,
    startSession: startTutorSession,
    sendMessage: sendTutorMessage,
    endSession: endTutorSession,
    prepareForUnmount, // Get the new method
  } = useMathTutor();

  useEffect(() => {
    if (agentOutput && agentOutput.text) {
      addMessage("assistant", agentOutput.text);
    }
  }, [agentOutput]);

  const addMessage = (type: MessageType, content: string) => {
    const newMessage: Message = {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, newMessage]);
  };

  const startSession = async (options: {
    theme?: string;
    learningPath?: string;
    initialMessage?: string;
    diagnosticResults?: any[];
  }) => {
    clearMessages();
    
    addMessage("system", "¡Bienvenido a tu sesión de aprendizaje! Estoy aquí para ayudarte.");
    
    if (options.initialMessage) {
      addMessage("user", options.initialMessage);
    }
    
    await startTutorSession({
      personalized_theme: options.theme,
      learning_path: options.learningPath,
      initial_message: options.initialMessage,
      diagnostic_results: options.diagnosticResults,
    });
  };

  const sendMessage = async (content: string) => {
    addMessage("user", content);
    
    await sendTutorMessage(content);
  };

  const endSession = async () => {
    await endTutorSession();
    clearMessages();
  };

  const clearMessages = () => {
    setMessages([]);
  };

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
    prepareForUnmount, // Expose the new method
  };

  return <TutorContext.Provider value={value}>{children}</TutorContext.Provider>;
}

export function useTutor() {
  const context = useContext(TutorContext);
  
  if (context === undefined) {
    throw new Error("useTutor debe ser usado dentro de un TutorProvider");
  }
  
  return context;
}