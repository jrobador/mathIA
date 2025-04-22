"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import MathTutorClient from "@/app/api/MathTutorClient";
import { AgentOutput, DiagnosticQuestionResult } from "@/types/api";

interface UseMathTutorOptions {
  autoConnect?: boolean;
  maxRetries?: number;
}

interface StartSessionOptions {
  personalized_theme?: string;
  initial_message?: string;
  learning_path?: string;
  diagnostic_results?: DiagnosticQuestionResult[];
}

interface UseMathTutorReturn {
  client: MathTutorClient;
  sessionId: string | null;
  agentOutput: AgentOutput | null;
  lastMessage: string | null;
  isLoading: boolean;
  isConnected: boolean;
  masteryLevel: number;
  error: Error | null;
  
  startSession: (options: StartSessionOptions) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  endSession: () => Promise<void>;
  resetState: () => void;
  prepareForUnmount: () => void;
}

export function useMathTutor(options: UseMathTutorOptions = {}): UseMathTutorReturn {
  const { autoConnect = false } = options;
  
  // State
  const [client] = useState<MathTutorClient>(() => new MathTutorClient());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);
  
  // Tracking refs
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(false);
  const autoConnectPerformedRef = useRef<boolean>(false);
  const messageRequestPendingRef = useRef<boolean>(false);
  const willUnmountRef = useRef<boolean>(false);

  // Configure WebSocket message handlers
  useEffect(() => {
    // Periodically check connection status
    const checkConnectionInterval = setInterval(() => {
      if (client && typeof client.isWebSocketConnected === 'function') {
        setIsConnected(client.isWebSocketConnected());
      }
    }, 3000);

    // Add message handler to client
    const handleAgentResponse = (data: { type: string; data?: any }) => {
      if (data.type === "agent_response" && data.data) {
        // Update state with agent response
        setAgentOutput({
          text: data.data.text || "Agent response",
          image_url: data.data.image_url,
          audio_url: data.data.audio_url,
          prompt_for_answer: data.data.requires_input || false,
          evaluation: data.data.evaluation_type,
          is_final_step: data.data.is_final_step || false
        });
        
        // Update mastery level if available
        if (data.data.state_metadata?.mastery) {
          setMasteryLevel(data.data.state_metadata.mastery);
        }
      }
    };
    
    // Register handler if client supports it
    if (client && typeof client.addMessageHandler === 'function') {
      client.addMessageHandler(handleAgentResponse);
    }
    
    // Cleanup when unmounting
    return () => {
      clearInterval(checkConnectionInterval);
      
      if (client && typeof client.removeMessageHandler === 'function') {
        client.removeMessageHandler(handleAgentResponse);
      }
    };
  }, [client]);

  // Start a tutoring session
  const startSession = useCallback(async (options: StartSessionOptions): Promise<void> => {
    if (sessionRequestPendingRef.current) {
      console.log("Session request already in progress, ignoring duplicate request");
      return;
    }
    
    if ((sessionId || sessionStartedRef.current) && !isRecovering) {
      console.log("Session already active, ignoring new session request");
      return;
    }
    
    sessionRequestPendingRef.current = true;
    setIsLoading(true);
    setError(null);
    
    try {
      const { personalized_theme, initial_message, learning_path, diagnostic_results } = options;
      
      const formattedDiagnostic = diagnostic_results 
        ? client.formatDiagnosticResults(diagnostic_results)
        : null;
        
      console.log(`Starting new session... ${isRecovering ? '(recovery mode)' : ''}`);
      
      const response = await client.startSession({
        personalized_theme,
        initial_message,
        learning_path,
        diagnostic_results: formattedDiagnostic
      });
      
      setSessionId(response.session_id);
      setAgentOutput(response.initial_output);
      sessionStartedRef.current = true;
      
      if (isRecovering) {
        setIsRecovering(false);
      }
      
      console.log("Session started:", response.session_id);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error starting session:", error);
      
      if (isRecovering) {
        setIsRecovering(false);
      }
    } finally {
      setIsLoading(false);
      sessionRequestPendingRef.current = false;
    }
  }, [client, sessionId, isRecovering]);

  // Send a message to the tutor
  const sendMessage = useCallback(async (message: string): Promise<void> => {
    if (!sessionId) {
      console.warn("No active session");
      
      if (!isRecovering && !sessionRequestPendingRef.current) {
        console.log("Attempting session recovery...");
        setIsRecovering(true);
        
        const theme = localStorage.getItem("learningTheme") || "space";
        const learningPath = localStorage.getItem("learningPath") || "addition";
        const studentName = localStorage.getItem("studentName") || "";
        
        try {
          await startSession({
            personalized_theme: theme,
            learning_path: learningPath,
            initial_message: `Hi, I'm ${studentName}. I want to learn ${learningPath}.`
          });
          
          setLastMessage(message);
        } catch (err) {
          console.error("Recovery failed:", err);
          setError(err as Error);
          setIsRecovering(false);
        }
      }
      
      return;
    }
    
    messageRequestPendingRef.current = true;
    setIsLoading(true);
    setError(null);
    setLastMessage(message);
    
    try {
      const response = await client.processInput(message, sessionId);
      
      if (response.agent_output) {
        setAgentOutput(response.agent_output);
      }
      
      if (response.mastery_level !== undefined) {
        setMasteryLevel(response.mastery_level);
      }
      
      console.log("Response received:", response);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error processing message:", error);
      
      if (error.message.includes("not found") || error.message.includes("No active session")) {
        console.warn("Session no longer exists, clearing local session state");
        setSessionId(null);
      }
    } finally {
      setIsLoading(false);
      messageRequestPendingRef.current = false;
    }
  }, [client, sessionId, isRecovering, startSession]);

  // End the current tutoring session
  const endSession = useCallback(async (): Promise<void> => {
    if (!sessionId) {
      console.warn("No active session to end");
      return;
    }
    
    try {
      await client.endSession();
      resetState();
      sessionStartedRef.current = false;
      console.log("Session ended");
    } catch (err) {
      const error = err as Error;
      console.error("Error ending session:", error);
      
      // Still reset local state even if API call fails
      resetState();
      sessionStartedRef.current = false;
    }
  }, [client, sessionId]);

  // Reset the internal state
  const resetState = useCallback(() => {
    setSessionId(null);
    setAgentOutput(null);
    setLastMessage(null);
    setMasteryLevel(0);
    setError(null);
    setIsRecovering(false);
  }, []);

  // Signal true unmounting
  const prepareForUnmount = useCallback(() => {
    console.log("Preparing for unmount - will clean up session");
    willUnmountRef.current = true;
  }, []);

  // Auto-connect logic
  useEffect(() => {
    if (autoConnect && !sessionId && !isLoading && !autoConnectPerformedRef.current && !sessionRequestPendingRef.current) {
      const autoInitialize = async () => {
        autoConnectPerformedRef.current = true;
        
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
    
    // Only end session on true unmount
    return () => {
      if (sessionId && willUnmountRef.current) {
        console.log("Component unmounting - cleaning up session:", sessionId);
        client.endSession().catch(console.error);
      } else if (sessionId) {
        console.log("Component re-rendering - preserving session:", sessionId);
      }
    };
  }, [autoConnect, client, sessionId, isLoading, startSession]);
  
  // Process pending message after recovery
  useEffect(() => {
    if (sessionId && lastMessage && !isLoading && isRecovering) {
      const timer = setTimeout(() => {
        console.log("Resubmitting pending message after recovery");
        sendMessage(lastMessage).catch(console.error);
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [sessionId, lastMessage, isLoading, isRecovering, sendMessage]);

  return {
    client,
    sessionId,
    agentOutput,
    lastMessage,
    isLoading,
    isConnected,
    masteryLevel,
    error,
    startSession,
    sendMessage,
    endSession,
    resetState,
    prepareForUnmount
  };
}