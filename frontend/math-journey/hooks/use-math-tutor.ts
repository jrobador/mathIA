"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import MathTutorClient from "@/app/api/mathTutorClient";
import { AgentOutput, DiagnosticQuestionResult } from "@/types/api";
import { toast } from "sonner";

interface UseMathTutorOptions {
  autoConnect?: boolean;
  maxRetries?: number;
}

interface UseMathTutorReturn {
  client: MathTutorClient;
  sessionId: string | null;
  agentOutput: AgentOutput | null;
  lastMessage: string | null;
  isLoading: boolean;
  masteryLevel: number;
  error: Error | null;
  
  startSession: (options: {
    personalized_theme?: string;
    initial_message?: string;
    learning_path?: string;
    diagnostic_results?: DiagnosticQuestionResult[];
  }) => Promise<void>;
  
  sendMessage: (message: string) => Promise<void>;
  endSession: () => Promise<void>;
  resetState: () => void;
  prepareForUnmount: () => void; // New method to signal true unmounting
}

export function useMathTutor(options: UseMathTutorOptions = {}): UseMathTutorReturn {
  const { autoConnect = false, maxRetries = 2 } = options;
  
  // State
  const [client] = useState(() => new MathTutorClient());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);
  
  // Tracking refs
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(false);
  const autoConnectPerformedRef = useRef<boolean>(false);
  const messageRequestPendingRef = useRef<boolean>(false);
  const retryCountRef = useRef<number>(0);
  const willUnmountRef = useRef<boolean>(false); // New ref to track true unmounting

  // Start a tutoring session
  const startSession = useCallback(async (options: {
    personalized_theme?: string;
    initial_message?: string;
    learning_path?: string;
    diagnostic_results?: DiagnosticQuestionResult[];
  }) => {
    // Implementation remains the same
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
      
      toast("Could not start the tutoring session");
      
      if (isRecovering) {
        setIsRecovering(false);
      }
    } finally {
      setIsLoading(false);
      sessionRequestPendingRef.current = false;
    }
  }, [client, sessionId, isRecovering]);

  // Send a message implementation remains the same
  const sendMessage = useCallback(async (message: string) => {
    // Implementation remains unchanged
    if (!sessionId) {
      console.warn("No active session");
      toast("Session not available. Starting a new session...");
      
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
    
    // Rest of the implementation remains the same...
    messageRequestPendingRef.current = true;
    setIsLoading(true);
    setError(null);
    setLastMessage(message);
    
    try {
      retryCountRef.current = 0;
      let currentSessionId = sessionId;
      
      const retryMessage = async (): Promise<void> => {
        // Existing implementation...
        try {
          console.log(`Sending message using session: ${currentSessionId}`);
          const response = await client.processInput(message, currentSessionId);
          
          setAgentOutput(response.agent_output);
          
          if (response.mastery_level !== undefined) {
            setMasteryLevel(response.mastery_level);
          }
          
          retryCountRef.current = 0;
          console.log("Response received:", response);
          
        } catch (err: any) {
          // Existing error handling...
          retryCountRef.current++;
          
          const isSessionNotFound = err.message && err.message.includes("not found");
          
          if (isSessionNotFound && retryCountRef.current <= maxRetries) {
            console.warn(`Session ${currentSessionId} not found, attempting to create new session...`);
            
            setSessionId(null);
            
            try {
              const theme = localStorage.getItem("learningTheme") || "space";
              const learningPath = localStorage.getItem("learningPath") || "addition";
              const studentName = localStorage.getItem("studentName") || "";
              
              const sessionResponse = await client.startSession({
                personalized_theme: theme,
                learning_path: learningPath,
                initial_message: `Hi, I'm ${studentName}. I want to learn ${learningPath}.`
              });
              
              currentSessionId = sessionResponse.session_id;
              setSessionId(currentSessionId);
              
              console.log(`Created new session: ${currentSessionId}, retrying message...`);
              
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              throw new Error("Forcing retry with new session");
            } catch (sessionErr) {
              console.error("Failed to create recovery session:", sessionErr);
              throw err;
            }
          }
          
          if (retryCountRef.current <= maxRetries) {
            console.warn(`Message error (attempt ${retryCountRef.current}/${maxRetries}), retrying...`);
            toast(`Retrying... (${retryCountRef.current}/${maxRetries})`, {
              duration: 1500
            });
            
            await new Promise(resolve => setTimeout(resolve, 1500));
            return retryMessage();
          }
          
          throw err;
        }
      };
      
      await retryMessage();
      
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error processing message:", error);
      
      toast(error.message || "Could not process your message");
      
      if (error.message.includes("not found") || error.message.includes("No active session")) {
        console.warn("Session no longer exists, clearing local session state");
        setSessionId(null);
      }
    } finally {
      setIsLoading(false);
      messageRequestPendingRef.current = false;
    }
  }, [client, sessionId, isRecovering, maxRetries, startSession]);

  // End the current tutoring session
  const endSession = useCallback(async () => {
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
    setIsRecovering(false);
  }, []);

  // New method to signal true unmounting
  const prepareForUnmount = useCallback(() => {
    console.log("Preparing for unmount - will clean up session");
    willUnmountRef.current = true;
  }, []);

  // Auto-connect logic with modified cleanup
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
    
    // FIXED: Only end session on true unmount
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
    masteryLevel,
    error,
    startSession,
    sendMessage,
    endSession,
    resetState,
    prepareForUnmount // Export the new method
  };
}