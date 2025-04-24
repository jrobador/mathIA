// FILE: frontend/math-journey/hooks/use-math-tutor.ts
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import MathTutorClient from "@/app/api/MathTutorClient"; 
import { 
  AgentOutput, 
  DiagnosticQuestionResult as ApiDiagnosticQuestionResult, 
  // Renamed to avoid conflict with local type
  WebSocketMessage 
} from "@/types/api"; 

interface StartSessionOptions {
  personalized_theme?: string;        // Backend property name
  learning_path?: string;             // Backend property name
  diagnostic_results?: ApiDiagnosticQuestionResult[]; // Using the imported type
}

interface UseMathTutorOptions {
  autoConnect?: boolean;
  // maxRetries?: number; // Removed as unused
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
  requestContinue: () => Promise<void>;
  endSession: () => Promise<void>;
  resetState: () => void;
  prepareForUnmount: () => void;
}

// If WebSocketMessage isn't imported, define a basic structure
// interface WebSocketMessage {
//   type: string;
//   data?: any;
//   message?: string; // Make message optional
//   requestId?: string;
// }

export function useMathTutor(options: UseMathTutorOptions = {}): UseMathTutorReturn {
  const { autoConnect = false } = options;

  // === State ===
  const [client] = useState<MathTutorClient>(() => new MathTutorClient());
  // Initialize sessionId using the client method (assuming it exists in MathTutorClient.ts)
  const [sessionId, setSessionId] = useState<string | null>(() => client.getCurrentSessionId());
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);

  // === Refs ===
  const sessionRequestPendingRef = useRef<boolean>(false);
  // Initialize based on potentially restored session ID (assuming client method exists)
  const sessionStartedRef = useRef<boolean>(!!client.getCurrentSessionId());
  const autoConnectPerformedRef = useRef<boolean>(false);
  // const messageRequestPendingRef = useRef<boolean>(false); // REMOVED - unused
  const willUnmountRef = useRef<boolean>(false);

  // === WebSocket Message Handling ===
  useEffect(() => {
    const checkConnectionInterval = setInterval(() => {
      setIsConnected(client.isWebSocketConnected());
    }, 3000);
  
    // Use the imported or defined WebSocketMessage type
    const handlePushedMessage = (message: WebSocketMessage) => {
      console.log("Hook received message:", message);
      setIsProcessing(false); // Turn off loading when ANY message arrives
  
      if (message.type === "agent_response") {
        console.log("Agent response data structure:", JSON.stringify(message.data, null, 2));
      }
  
      if (message.type === "agent_response" && message.data) {
        const agentData = message.data;
        
        // Create the agent output with additional properties
        setAgentOutput({
          text: agentData.text || "Agent response",
          image_url: agentData.image_url,
          audio_url: agentData.audio_url,
          prompt_for_answer: agentData.waiting_for_input ?? agentData.state_metadata?.waiting_for_input ?? false,
          evaluation: agentData.evaluation_type || agentData.state_metadata?.last_evaluation || null,
          is_final_step: agentData.is_final_step || false,
          // Add these new properties to capture backend action and content types
          action_type: agentData.action || agentData.executed_action_name || null,
          content_type: agentData.content_type || null
        });
        
        if (agentData.state_metadata?.mastery !== undefined) {
          setMasteryLevel(agentData.state_metadata.mastery);
        }
      } else if (message.type === "state_update" && message.data) {
        const stateData = message.data;
        setSessionId(stateData.session_id);
        setMasteryLevel(stateData.topic_mastery?.[stateData.current_topic] ?? 0);
      } else if (message.type === "error") {
        // Access message property safely using optional chaining
        const errorMessage = message.message ?? "Unknown server error";
        console.error("Received error message from backend/WS:", errorMessage);
        setError(new Error(errorMessage));
        // Check error message case-insensitively
        if (errorMessage.toLowerCase().includes("sesión no encontrada")) {
             console.warn("Resetting state due to 'session not found' error.");
             resetState(); // Ensure resetState is accessible here or defined above
             sessionStartedRef.current = false;
        }
      }
    };
  
    client.addMessageHandler(handlePushedMessage);
  
    return () => {
      clearInterval(checkConnectionInterval);
      client.removeMessageHandler(handlePushedMessage);
    };
  }, [client]);


  // === Action Functions ===

  // Define resetState *before* other functions that use it if not memoizing
   const resetState = useCallback(() => {
    setSessionId(null);
    setAgentOutput(null);
    setLastMessage(null);
    setMasteryLevel(0);
    setError(null);
    setIsRecovering(false);
    setIsProcessing(false);
    // Does not reset client instance
  }, []); // Empty dependency array is correct here


  const startSession = useCallback(
    async (options: StartSessionOptions): Promise<void> => {
      if (isProcessing || sessionRequestPendingRef.current) { return; }
      // Use client method here (assuming it exists)
      if ((client.getCurrentSessionId() || sessionStartedRef.current) && !isRecovering) { return; }
  
      sessionRequestPendingRef.current = true;
      setIsProcessing(true);
      setError(null);
  
      try {
        const { personalized_theme, learning_path, diagnostic_results } = options;
  
        console.log(`useMathTutor: Calling client.startSession... ${isRecovering ? "(recovery mode)" : ""}`);
  
        // No transformation needed - pass directly to client with correct property names
        const response = await client.startSession({
          personalized_theme,
          learning_path,
          diagnostic_results  // Pass directly with correct property name
        });
  
        setSessionId(response.session_id);
        setAgentOutput(response.initial_output);
        sessionStartedRef.current = true;
  
        if (isRecovering) { setIsRecovering(false); }
        console.log("useMathTutor: Session started successfully:", response.session_id);
  
      } catch (err) {
        const error = err as Error;
        setError(error);
        console.error("useMathTutor: Error starting session:", error);
        sessionStartedRef.current = false;
        if (isRecovering) {
          setIsRecovering(false);
        }
      } finally {
        setIsProcessing(false);
        sessionRequestPendingRef.current = false;
      }
    },
    [client, isProcessing, isRecovering, resetState]
  );


  const sendMessage = useCallback(
    async (message: string): Promise<void> => {
      const currentSession = client.getCurrentSessionId(); // Get ID directly
      if (!currentSession) {
        console.warn("sendMessage called but no active session ID.");
        setError(new Error("Cannot send message: No active session."));
        return;
      }
       if (isProcessing) { return; }

      setIsProcessing(true);
      setError(null);
      setLastMessage(message);

      try {
        console.log(`useMathTutor: Calling client.processInput for session ${currentSession}`);
        await client.processInput(message, currentSession);
        // Response handled by handlePushedMessage effect
      } catch (err) {
        const error = err as Error;
        setError(error);
        console.error("useMathTutor: Error sending message:", error);
        setIsProcessing(false);
        if (error.message.toLowerCase().includes("not found") || error.message.toLowerCase().includes("no active session")) {
            console.warn("Session seems invalid based on error, resetting state.");
            resetState(); // Call resetState
            sessionStartedRef.current = false;
        }
      }
    },
    [client, isProcessing, resetState] // Dependencies: client, isProcessing, resetState
  );


  const requestContinue = useCallback(async (): Promise<void> => {
    const currentSession = client.getCurrentSessionId(); // Get ID directly
    if (!currentSession) {
      console.warn("No active session to continue.");
      setError(new Error("Cannot continue: No active session."));
      return;
    }
    if (isProcessing) { return; }

    setIsProcessing(true);
    setError(null);

    try {
        console.log(`useMathTutor: Calling client.requestContinue for session ${currentSession}`);
        await client.requestContinue(currentSession);
         // Response handled by handlePushedMessage effect
    } catch (err) {
        const error = err as Error;
        setError(error);
        console.error("useMathTutor: Error requesting continue:", error);
        setIsProcessing(false);
    }
  }, [client, isProcessing]); // Dependencies: client, isProcessing


  const endSession = useCallback(async (): Promise<void> => {
     // Use client method here (assuming it exists)
    if (!client.hasActiveSession()) {
      console.warn("No active session to end.");
      return;
    }

    setIsProcessing(true);
    const endedSessionId = client.getCurrentSessionId(); // Get ID from client

    try {
        console.log(`useMathTutor: Calling client.endSession for session ${endedSessionId}`);
        await client.endSession(endedSessionId); // Pass potentially null ID, client should handle
        resetState(); // Call resetState
        sessionStartedRef.current = false;
        console.log(`useMathTutor: Session ${endedSessionId} ended and state reset.`);
    } catch (err) {
        const error = err as Error;
        setError(error);
        console.error("useMathTutor: Error ending session:", error);
        resetState(); // Still reset on error
        sessionStartedRef.current = false;
    } finally {
        setIsProcessing(false);
    }
  }, [client, resetState]); // Dependencies: client, resetState


  const prepareForUnmount = useCallback(() => {
    console.log("useMathTutor: Preparing for unmount - session cleanup will occur.");
    willUnmountRef.current = true;
  }, []);


  // === Effects for Auto-Connect and Cleanup ===

  useEffect(() => {
    // Only auto-connect if we have a theme already selected (added condition)
    const themeSelected = localStorage.getItem("learningTheme") !== null;
    
    if (autoConnect && themeSelected && !client.hasActiveSession() && 
        !isProcessing && !autoConnectPerformedRef.current && !sessionRequestPendingRef.current) {
      const autoInitialize = async () => {
        console.log("useMathTutor: Auto-connecting session...");
        autoConnectPerformedRef.current = true;
        
        const theme = localStorage.getItem("learningTheme") || "space";
        const path = localStorage.getItem("learningPath") || "addition";
        
        await startSession({
          personalized_theme: theme,
          learning_path: path,
          // diagnostic_results not needed here for auto-connect
        });
      };
      autoInitialize();
    }
  }, [autoConnect, client, isProcessing, startSession]);


  useEffect(() => {
    return () => {
       // Use client method here (assuming it exists)
      if (willUnmountRef.current && client.hasActiveSession()) {
        console.log("useMathTutor: Component unmounting intentionally - cleaning up session.");
        client.endSession().catch(console.error);
      } else if (client.hasActiveSession()) {
         console.log("useMathTutor: Component re-rendering or unmounting without prepareForUnmount - preserving session state.");
      }
    };
  // Client instance should be stable, so only client dependency needed for cleanup logic.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);


  // === Effect for Session Recovery (Optional) ===
  useEffect(() => {
    const currentSession = client.getCurrentSessionId(); // Get ID directly
    if (currentSession && lastMessage && !isProcessing && isRecovering) {
       console.log("useMathTutor: Resubmitting pending message after session recovery.");
       const timer = setTimeout(() => {
          setIsRecovering(false);
          sendMessage(lastMessage).catch(console.error);
       }, 500);
       return () => clearTimeout(timer);
     }
     else if (isRecovering && !isProcessing) {
         setIsRecovering(false);
     }
  }, [client, lastMessage, isProcessing, isRecovering, sendMessage]); // Added client dependency


  // === Return Value ===
  return {
    client,
    // Use ID directly from client state for consistency, or hook state if preferred
    sessionId: client.getCurrentSessionId(), // Or just return `sessionId` state variable
    agentOutput,
    lastMessage,
    isLoading: isProcessing,
    isConnected,
    masteryLevel,
    error,
    startSession,
    sendMessage,
    requestContinue,
    endSession,
    resetState,
    prepareForUnmount,
  };
}