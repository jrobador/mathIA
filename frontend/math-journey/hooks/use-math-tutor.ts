"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import MathTutorClient from "@/app/api/mathTutorClient";
import { AgentOutput, DiagnosticQuestionResult } from "@/types/api";
import { toast } from "sonner";

interface UseMathTutorOptions {
  autoConnect?: boolean;
}

interface UseMathTutorReturn {
  client: MathTutorClient;
  sessionId: string | null;
  agentOutput: AgentOutput | null;
  lastMessage: string | null;
  isLoading: boolean;
  masteryLevel: number;
  error: Error | null;
  
  // Methods to interact with the API
  startSession: (options: {
    personalized_theme?: string;
    initial_message?: string;
    learning_path?: string;
    diagnostic_results?: DiagnosticQuestionResult[];
  }) => Promise<void>;
  
  sendMessage: (message: string) => Promise<void>;
  endSession: () => Promise<void>;
  
  // Utility methods
  resetState: () => void;
}

export function useMathTutor(options: UseMathTutorOptions = {}): UseMathTutorReturn {
  const { autoConnect = false } = options;
  
  // State
  const [client] = useState(() => new MathTutorClient());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  
  // BUGFIX: Add session request tracking refs
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(false);
  const autoConnectPerformedRef = useRef<boolean>(false);

  // Start a tutoring session
  const startSession = useCallback(async (options: {
    personalized_theme?: string;
    initial_message?: string;
    learning_path?: string;
    diagnostic_results?: DiagnosticQuestionResult[];
  }) => {
    // BUGFIX: Prevent concurrent session creation requests
    if (sessionRequestPendingRef.current) {
      console.log("Session request already in progress, ignoring duplicate request");
      return;
    }
    
    // BUGFIX: Don't start a new session if one is already active
    if (sessionId || sessionStartedRef.current) {
      console.log("Session already active, ignoring new session request");
      return;
    }
    
    sessionRequestPendingRef.current = true;
    setIsLoading(true);
    setError(null);
    
    try {
      const { personalized_theme, initial_message, learning_path, diagnostic_results } = options;
      
      // Format diagnostic results if provided
      const formattedDiagnostic = diagnostic_results 
        ? client.formatDiagnosticResults(diagnostic_results)
        : null;
        
      console.log("Starting new session...");
      
      // Call the API
      const response = await client.startSession({
        personalized_theme,
        initial_message,
        learning_path,
        diagnostic_results: formattedDiagnostic
      });
      
      // Update state
      setSessionId(response.session_id);
      setAgentOutput(response.initial_output);
      sessionStartedRef.current = true;
      
      console.log("Session started:", response.session_id);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error starting session:", error);
      
      toast("Could not start the tutoring session");
    } finally {
      setIsLoading(false);
      sessionRequestPendingRef.current = false;
    }
  }, [client]);

  // Send a message to the tutor
  const sendMessage = useCallback(async (message: string) => {
    if (!sessionId) {
      console.warn("No active session");
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setLastMessage(message);
    
    try {
      const response = await client.processInput(message);
      
      setAgentOutput(response.agent_output);
      
      if (response.mastery_level !== undefined) {
        setMasteryLevel(response.mastery_level);
      }
      
      console.log("Response received", response);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error processing message:", error);
      
      toast("Could not process your message");
    } finally {
      setIsLoading(false);
    }
  }, [client, sessionId]);

  // End the current tutoring session
  const endSession = useCallback(async () => {
    if (!sessionId) {
      console.warn("No active session to end");
      return;
    }
    
    try {
      await client.endSession();
      resetState();
      // BUGFIX: Reset session tracking refs
      sessionStartedRef.current = false;
      console.log("Session ended");
    } catch (err) {
      const error = err as Error;
      console.error("Error ending session:", error);
      
      toast("Could not properly end the session");
    }
  }, [client, sessionId]);

  // Reset the internal state
  const resetState = useCallback(() => {
    setSessionId(null);
    setAgentOutput(null);
    setLastMessage(null);
    setMasteryLevel(0);
    setError(null);
  }, []);

  // Auto-connect logic
  useEffect(() => {
    // BUGFIX: Use refs to ensure auto-connect only happens once
    if (autoConnect && !sessionId && !isLoading && !autoConnectPerformedRef.current && !sessionRequestPendingRef.current) {
      const autoInitialize = async () => {
        // Mark auto-connect as in progress before any async operations
        autoConnectPerformedRef.current = true;
        
        // Retrieve preferences from localStorage
        const theme = localStorage.getItem("learningTheme") || "space";
        const learningPath = localStorage.getItem("learningPath") || "addition";
        const studentName = localStorage.getItem("studentName") || "";
        
        await startSession({
          personalized_theme: theme,
          initial_message: `Hi, I'm ${studentName}. I want to learn ${learningPath}.`,
          learning_path: learningPath
        });
      };
      
      autoInitialize();
    }
    
    // Clean up session on component unmount
    return () => {
      if (sessionId) {
        client.endSession().catch(console.error);
      }
    };
  }, [autoConnect, client, sessionId, isLoading, startSession]);

  return {
    client,
    sessionId,
    agentOutput,
    lastMessage,
    isLoading,
    masteryLevel,
    error,
    startSession,
    sendMessage,
    endSession,
    resetState
  };
}