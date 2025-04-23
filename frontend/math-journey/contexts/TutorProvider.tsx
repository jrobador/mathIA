// FILE: frontend/math-journey/contexts/TutorProvider.tsx
"use client";

import React, { JSX, createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react"; // Added useCallback
import { useMathTutor } from "@/hooks/use-math-tutor";
import { AgentOutput} from "@/types/api";


export interface StartSessionOptions {
  theme?: string;              // Frontend property
  learningPath?: string;       // Frontend property
  initialMessage?: string;     // For UI display only
  diagnosticResults?: any[];   // Type appropriately for diagnostic results
}

export enum MessageType {
  SYSTEM = "system",
  USER = "user",
  ASSISTANT = "assistant",
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

// Interface defining the context's value
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
  requestContinue: () => Promise<void>; // Function exposed by the context
  endSession: () => Promise<void>;
  clearMessages: () => void;
  prepareForUnmount: () => void;
}

const TutorContext = createContext<TutorContextType | undefined>(undefined);

const generateId = () => Math.random().toString(36).substring(2, 9);

interface TutorProviderProps {
  children: ReactNode;
}

export function TutorProvider({ children }: TutorProviderProps): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);

  // Get functions and state from the underlying hook
  const {
    sessionId,
    agentOutput,
    isLoading,
    masteryLevel,
    isConnected,
    error,
    startSession: startTutorSession, // Renamed from hook
    sendMessage: sendTutorMessage, // Renamed from hook
    requestContinue: requestTutorContinue, // Renamed from hook
    endSession: endTutorSession, // Renamed from hook
    prepareForUnmount, // Pass through directly
  } = useMathTutor();

  // Effect to add assistant messages when agentOutput changes
  useEffect(() => {
    if (agentOutput?.text) { // Check if agentOutput and text exist
      // Check if the last message is already this exact message to prevent duplicates
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.type !== MessageType.ASSISTANT || lastMsg?.content !== agentOutput.text) {
         addMessage(MessageType.ASSISTANT, agentOutput.text, {
            imageUrl: agentOutput.image_url,
            audioUrl: agentOutput.audio_url,
            isEvaluation: !!agentOutput.evaluation,
            evaluationType: agentOutput.evaluation,
            isCorrect: agentOutput.evaluation === "Correct", // Assuming "Correct" string value
         });
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentOutput]); // Dependency: agentOutput

  // Helper function to add messages to the local state
  const addMessage = useCallback((type: MessageType, content: string, options: MessageOptions = {}): void => {
    const newMessage: Message = {
      id: generateId(),
      type,
      content,
      timestamp: new Date(),
      ...options,
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []); // No dependencies needed if it only uses generateId and setMessages


  // Context function to start a session
  const startSession = useCallback(async (options: StartSessionOptions = {}): Promise<void> => {
    setMessages([]); // Clear previous messages
    addMessage(MessageType.SYSTEM, "Welcome to your learning session! I'm here to help.");
  
    // Add the initial user message to the UI if provided
    if (options.initialMessage) {
      addMessage(MessageType.USER, options.initialMessage);
    }
  
    // Call the hook's start session function
    await startTutorSession({
      // Map options from UI/component call to options expected by the hook
      personalized_theme: options.theme,
      learning_path: options.learningPath,
      diagnostic_results: options.diagnosticResults // Pass the diagnostic results to the hook
    });
  }, [addMessage, startTutorSession]); // Dependencies


  // Context function to send a user message
  const sendMessage = useCallback(async (content: string): Promise<void> => {
    addMessage(MessageType.USER, content); // Add user message to UI
    await sendTutorMessage(content); // Call the hook's send message function
  }, [addMessage, sendTutorMessage]); // Dependencies


  // Context function to request continuation
  const requestContinue = useCallback(async (): Promise<void> => {
    // Optional: Add a system message to indicate action?
    // addMessage(MessageType.SYSTEM, "Continuing...");
    // Call the hook's request continue function (CORRECTED NAME)
    await requestTutorContinue();
  }, [requestTutorContinue /*, addMessage */]); // Dependencies


  // Context function to end the session
  const endSession = useCallback(async (): Promise<void> => {
    await endTutorSession(); // Call hook's end session function
    setMessages([]); // Clear messages on session end
     addMessage(MessageType.SYSTEM, "Session ended. See you next time!");
  }, [endTutorSession, addMessage]); // Dependencies


  // Context function to clear messages manually (if needed)
  const clearMessages = useCallback((): void => {
    setMessages([]);
  }, []); // No dependencies


  // Create the context value object
  const value: TutorContextType = {
    messages,
    isLoading,
    sessionId,
    currentOutput: agentOutput, // Pass agentOutput directly
    masteryLevel,
    isConnected,
    error,
    startSession,
    sendMessage,
    requestContinue, // Expose the context's requestContinue function
    endSession,
    clearMessages,
    prepareForUnmount, // Pass through directly
  };

  return <TutorContext.Provider value={value}>{children}</TutorContext.Provider>;
}

// Hook to consume the context
export function useTutor(): TutorContextType {
  const context = useContext(TutorContext);
  if (context === undefined) {
    throw new Error("useTutor must be used within a TutorProvider");
  }
  return context;
}