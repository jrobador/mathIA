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
  const { autoConnect = false, maxRetries = 2 } = options;
  
  // State
  const [client] = useState(() => new MathTutorClient());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  
  // Add recovery state to track if we're recovering from an error
  const [isRecovering, setIsRecovering] = useState<boolean>(false);
  
  // BUGFIX: Add request tracking refs
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(false);
  const autoConnectPerformedRef = useRef<boolean>(false);
  const messageRequestPendingRef = useRef<boolean>(false);
  const retryCountRef = useRef<number>(0);

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
    
    // BUGFIX: Don't start a new session if one is already active, unless we're in recovery mode
    if ((sessionId || sessionStartedRef.current) && !isRecovering) {
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
        
      console.log(`Starting new session... ${isRecovering ? '(recovery mode)' : ''}`);
      
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
      
      // If we were in recovery mode, exit that mode
      if (isRecovering) {
        setIsRecovering(false);
      }
      
      console.log("Session started:", response.session_id);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error starting session:", error);
      
      toast("Could not start the tutoring session");
      
      // Exit recovery mode on failure
      if (isRecovering) {
        setIsRecovering(false);
      }
    } finally {
      setIsLoading(false);
      sessionRequestPendingRef.current = false;
    }
  }, [client, sessionId, isRecovering]);

  // Send a message to the tutor with improved error handling and recovery
  const sendMessage = useCallback(async (message: string) => {
    if (!sessionId) {
      console.warn("No active session");
      toast("Session not available. Starting a new session...");
      
      // Try to restart the session
      if (!isRecovering && !sessionRequestPendingRef.current) {
        console.log("Attempting session recovery...");
        setIsRecovering(true);
        
        // Get settings from localStorage for recovery
        const theme = localStorage.getItem("learningTheme") || "space";
        const learningPath = localStorage.getItem("learningPath") || "addition";
        const studentName = localStorage.getItem("studentName") || "";
        
        try {
          await startSession({
            personalized_theme: theme,
            learning_path: learningPath,
            initial_message: `Hi, I'm ${studentName}. I want to learn ${learningPath}.`
          });
          
          // Store the message to be sent after recovery
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
      retryCountRef.current = 0;
      
      // BUGFIX: Add critical recovery capability
      let currentSessionId = sessionId;
      
      const retryMessage = async (): Promise<void> => {
        try {
          console.log(`Sending message using session: ${currentSessionId}`);
          const response = await client.processInput(message, currentSessionId);
          
          setAgentOutput(response.agent_output);
          
          if (response.mastery_level !== undefined) {
            setMasteryLevel(response.mastery_level);
          }
          
          // Reset retry counter on success
          retryCountRef.current = 0;
          console.log("Response received:", response);
          
        } catch (err: any) {
          retryCountRef.current++;
          
          // Check if this is a "Session not found" error
          const isSessionNotFound = err.message && err.message.includes("not found");
          
          // If session is missing but we have less than max retries, try auto-recovery
          if (isSessionNotFound && retryCountRef.current <= maxRetries) {
            console.warn(`Session ${currentSessionId} not found, attempting to create new session...`);
            
            // Clear the local session ID 
            setSessionId(null);
            
            // Try to create a new session
            try {
              const theme = localStorage.getItem("learningTheme") || "space";
              const learningPath = localStorage.getItem("learningPath") || "addition";
              const studentName = localStorage.getItem("studentName") || "";
              
              const sessionResponse = await client.startSession({
                personalized_theme: theme,
                learning_path: learningPath,
                initial_message: `Hi, I'm ${studentName}. I want to learn ${learningPath}.`
              });
              
              // Update the session ID for the retry
              currentSessionId = sessionResponse.session_id;
              setSessionId(currentSessionId);
              
              console.log(`Created new session: ${currentSessionId}, retrying message...`);
              
              // Wait briefly for session setup before retry
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              // Use the new session to send the message (will be handled by next retry)
              throw new Error("Forcing retry with new session");
            } catch (sessionErr) {
              console.error("Failed to create recovery session:", sessionErr);
              throw err; // Re-throw the original error
            }
          }
          
          // For other errors or if we've reached max retries
          if (retryCountRef.current <= maxRetries) {
            console.warn(`Message error (attempt ${retryCountRef.current}/${maxRetries}), retrying...`);
            toast(`Retrying... (${retryCountRef.current}/${maxRetries})`, {
              duration: 1500
            });
            
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, 1500));
            return retryMessage();
          }
          
          // If we've reached max retries and still failing, throw the error
          throw err;
        }
      };
      
      // Start the retry chain
      await retryMessage();
      
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error("Error processing message:", error);
      
      toast(error.message || "Could not process your message");
      
      // Check for specific errors that indicate the session is gone
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
    setIsRecovering(false);
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
  
  // Process pending message after recovery
  useEffect(() => {
    if (sessionId && lastMessage && !isLoading && isRecovering) {
      // Small delay to ensure session is fully established
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
    resetState
  };
}