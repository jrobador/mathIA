// FILE: frontend/math-journey/hooks/use-math-tutor.ts
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import MathTutorClient from "@/app/api/MathTutorClient";
import {
  AgentOutput,
  DiagnosticQuestionResult as ApiDiagnosticQuestionResult,
  WebSocketMessage
} from "@/types/api";

interface StartSessionOptions {
  personalized_theme?: string;
  learning_path?: string;
  diagnostic_results?: ApiDiagnosticQuestionResult[];
}

interface UseMathTutorOptions {
  autoConnect?: boolean;
}

interface UseMathTutorReturn {
  client: MathTutorClient;
  sessionId: string | null;
  agentOutput: AgentOutput | null;
  isLoading: boolean;
  isConnected: boolean;
  masteryLevel: number;
  error: Error | null;
  isEvaluationReceived: boolean; // NEW STATE for tracking evaluation mode
  startSession: (options: StartSessionOptions) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  requestContinue: () => Promise<void>;
  endSession: () => Promise<void>;
  clearEvaluationState: () => void; // NEW FUNCTION to reset evaluation state
  resetState: () => void;
  prepareForUnmount: () => void;
}

export function useMathTutor(options: UseMathTutorOptions = {}): UseMathTutorReturn {
  const { autoConnect = false } = options;

  const [client] = useState<MathTutorClient>(() => new MathTutorClient());
  const [sessionId, setSessionId] = useState<string | null>(() => client.getCurrentSessionId());
  const [agentOutput, setAgentOutput] = useState<AgentOutput | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [masteryLevel, setMasteryLevel] = useState<number>(0);
  const [error, setError] = useState<Error | null>(null);
  
  // NEW STATE: Special state for tracking evaluation responses
  const [isEvaluationReceived, setIsEvaluationReceived] = useState<boolean>(false);
  
  const lastMessageRef = useRef<string | null>(null);
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(!!client.getCurrentSessionId());
  const autoConnectPerformedRef = useRef<boolean>(false);
  const willUnmountRef = useRef<boolean>(false);
  const continueAfterEvalRef = useRef<boolean>(false);
  const lastEvaluationTimeRef = useRef<number>(0);

  const resetState = useCallback(() => {
    setSessionId(null); 
    setAgentOutput(null); 
    setMasteryLevel(0); 
    setError(null); 
    setIsProcessing(false);
    setIsEvaluationReceived(false); // Reset evaluation state
    lastMessageRef.current = null;
  }, []);

  // NEW FUNCTION: Clear evaluation state
  const clearEvaluationState = useCallback(() => {
    setIsEvaluationReceived(false);
    continueAfterEvalRef.current = false;
  }, []);

  useEffect(() => {
    const checkConnectionInterval = setInterval(() => { 
      setIsConnected(client.isWebSocketConnected()); 
    }, 3000);
    
    const handlePushedMessage = (message: WebSocketMessage) => {
      console.log("Hook handlePushedMessage received (simplified):", message);
      
      // Get response data
      const responseData = message.data;
      
      // Process agent responses
      if (message.type === "agent_response" && responseData) {
        
        // CRITICAL FIX: Special handling for evaluation_result
        if (responseData.action === "evaluation_result") {
          console.log("⚠️ EVALUATION RESULT RECEIVED - Setting evaluation state");
          
          // Mark that we've received an evaluation but don't turn off loading yet
          setIsEvaluationReceived(true);
          lastEvaluationTimeRef.current = Date.now();
          
          // Create agent output to display the evaluation
          const evaluationOutput: AgentOutput = {
            text: responseData.text || "Result", 
            image_url: responseData.image_url, 
            audio_url: responseData.audio_url,
            prompt_for_answer: false, // Always false for evaluation results
            evaluation: responseData.evaluation_type,
            is_final_step: false,
            action_type: responseData.action,
            content_type: responseData.content_type,
            waiting_for_input: false,
            state_metadata: responseData.state_metadata
          };
          
          // Update agent output with evaluation (this updates the UI)
          setAgentOutput(evaluationOutput);
          
          // Update mastery if available in metadata
          if (responseData.state_metadata?.mastery !== undefined) { 
            setMasteryLevel(responseData.state_metadata.mastery); 
          }
          
          // Note: intentionally NOT turning off isProcessing here to prevent 
          // flickering between loading states. It will be handled by the component.
        }
        // Standard (non-evaluation) response handling
        else {
          console.log("Regular agent response received:", responseData.action);
          
          // Clear evaluation state when receiving non-evaluation content
          setIsEvaluationReceived(false);
          
          // Turn off processing state for normal responses
          setIsProcessing(false);
          
          // Create standard agent output
          const newAgentOutput: AgentOutput = {
            text: responseData.text || "Agent response", 
            image_url: responseData.image_url, 
            audio_url: responseData.audio_url,
            prompt_for_answer: responseData.waiting_for_input ?? responseData.state_metadata?.waiting_for_input ?? false,
            evaluation: responseData.evaluation_type || responseData.state_metadata?.last_evaluation || null,
            is_final_step: responseData.is_final_step || false, 
            action_type: responseData.action || responseData.executed_action_name || null,
            content_type: responseData.content_type || null, 
            waiting_for_input: responseData.waiting_for_input, 
            state_metadata: responseData.state_metadata
          };
          
          // Update agent output for non-evaluation responses
          setAgentOutput(newAgentOutput);
          
          // Update mastery if available
          if (responseData.state_metadata?.mastery !== undefined) { 
            setMasteryLevel(responseData.state_metadata.mastery); 
          }
        }
      } 
      // Process state updates
      else if (message.type === "state_update" && responseData) {
        // Update session ID and mastery level
        setSessionId(responseData.session_id);
        setMasteryLevel(responseData.mastery ?? responseData.topic_mastery?.[responseData.current_topic] ?? 0);
        
        // Always turn off processing for state updates
        setIsProcessing(false);
      } 
      // Process errors
      else if (message.type === "error") {
        const errorMessage = message.message ?? "Unknown server error"; 
        setError(new Error(errorMessage));
        
        // Check if session not found
        if (errorMessage.toLowerCase().includes("sesión no encontrada")) { 
          resetState(); 
          sessionStartedRef.current = false; 
        }
        
        // Always turn off processing for errors
        setIsProcessing(false);
      }
      // For all other message types (like pongs)
      else {
        // Do nothing - but still turn off processing in some cases
        if (message.type === "pong" || message.type === "state_update") {
          setIsProcessing(false);
        }
      }
    };
    
    // Register message handler
    client.addMessageHandler(handlePushedMessage);
    
    // Cleanup
    return () => { 
      clearInterval(checkConnectionInterval); 
      client.removeMessageHandler(handlePushedMessage); 
    };
  }, [client, resetState]); // Added resetState

  const startSession = useCallback(
    async (options: StartSessionOptions): Promise<void> => {
      if (isProcessing || sessionRequestPendingRef.current || (client.getCurrentSessionId() && !error)) { 
        return; 
      }
      
      // Mark that session start is pending and set processing state
      sessionRequestPendingRef.current = true; 
      setIsProcessing(true); 
      setError(null); 
      resetState();
      
      try {
        // Start the session
        const response = await client.startSession(options); 
        setSessionId(response.session_id);
        const initialMastery = response.initial_output?.state_metadata?.mastery ?? 0; 
        setMasteryLevel(initialMastery);
        setAgentOutput(response.initial_output); 
        sessionStartedRef.current = true;
      } catch (err) {
        // Handle errors
        const error = err as Error; 
        setError(error); 
        sessionStartedRef.current = false; 
        resetState();
      } finally {
        // Always clean up
        setIsProcessing(false); 
        sessionRequestPendingRef.current = false;
      }
    }, [client, isProcessing, error, resetState]
  );

  const sendMessage = useCallback(
    async (message: string): Promise<void> => {
      const currentSession = client.getCurrentSessionId(); 
      if (!currentSession) { 
        setError(new Error("No active session.")); 
        return; 
      }
      
      // Block if already processing
      if (isProcessing) { 
        console.warn("sendMessage blocked"); 
        return; 
      }
      
      // Clear any existing evaluation state
      setIsEvaluationReceived(false);
      
      // Set processing and store message
      setIsProcessing(true); 
      setError(null); 
      lastMessageRef.current = message;
      
      try { 
        // Send the message
        console.log("Sending message to server:", message);
        const response = await client.processInput(message, currentSession);
        
        // Check if response contains evaluation data (using our added custom properties)
        // We need to use indexing since these aren't part of the official type
        const hasEvaluation = !!(response as any).hasEvaluation;
        const evaluationText = (response as any).evaluationText || "";
        const isCorrect = !!(response as any).isCorrect;
        
        if (hasEvaluation) {
          console.log("Response includes evaluation result - displaying feedback");
          
          // Set the evaluation received flag to trigger toast display
          setIsEvaluationReceived(true);
          
          // Store the evaluation text in a ref for the toast component to access
          // (instead of adding it directly to AgentOutput which would cause type errors)
          if (typeof evaluationText === 'string' && evaluationText.trim()) {
            // Store in a ref that the component can access
            // If you don't have this ref already, you'd need to add:
            // const evaluationTextRef = useRef<string>("");
            // evaluationTextRef.current = evaluationText;
            
            // Alternatively, you can add this to global state if you have a state for it
            // Or use a different property that exists in AgentOutput
            
            // For now, we can use the text field of the agent output as fallback
            const combinedOutput: AgentOutput = {
              ...response.agent_output,
              evaluation: isCorrect ? "Correct" : "Incorrect", // Simplified evaluation state
              // Store feedback text in the text field if it's not already populated
              text: response.agent_output.text || evaluationText
            };
            
            // Set agent output to show the content
            setAgentOutput(combinedOutput);
          } else {
            // Just use the response as is if no evaluation text
            setAgentOutput({
              ...response.agent_output,
              evaluation: isCorrect ? "Correct" : "Incorrect"
            });
          }
          
          // Update mastery level if available
          if (response.mastery_level !== undefined) {
            setMasteryLevel(response.mastery_level);
          }
          
          // Turn off processing state as we've handled both parts
          setIsProcessing(false);
        } else {
          // Standard response handling 
          setIsEvaluationReceived(false);
          setIsProcessing(false);
          
          if (response.agent_output) {
            setAgentOutput(response.agent_output);
          }
          
          if (response.mastery_level !== undefined) {
            setMasteryLevel(response.mastery_level);
          }
        }
      } catch (err) {
        // Handle errors
        const error = err as Error; 
        setError(error); 
        setIsProcessing(false);
        
        // Check if session not found
        if (error.message.toLowerCase().includes("not found") || 
            error.message.toLowerCase().includes("no active session")) { 
          resetState(); 
          sessionStartedRef.current = false; 
        }
      }
    }, [client, isProcessing, resetState]
  );
  
  const requestContinue = useCallback(
    async (): Promise<void> => {
      const currentSession = client.getCurrentSessionId(); 
      if (!currentSession) { 
        setError(new Error("No active session.")); 
        return; 
      }
      
      // Block if already processing non-evaluation request
      if (isProcessing && !isEvaluationReceived) { 
        console.warn("requestContinue blocked - processing non-evaluation request"); 
        return; 
      }
      
      // If evaluation received, we allow continue but set a flag
      if (isEvaluationReceived) {
        continueAfterEvalRef.current = true;
        console.log("Continue after evaluation - setting special flag");
      }
      
      // Clear evaluation state
      setIsEvaluationReceived(false);
      
      // Set processing state
      setIsProcessing(true); 
      setError(null);
      
      try { 
        // Request continuation
        console.log("Requesting continue from server");
        await client.requestContinue(currentSession); 
        
        // Note: isProcessing will be set to false in handlePushedMessage when response arrives
      } catch (err) {
        // Handle errors
        const error = err as Error; 
        setError(error); 
        setIsProcessing(false);
        
        // Reset continue flag
        continueAfterEvalRef.current = false;
        
        // Check if session not found
        if (error.message.toLowerCase().includes("not found") || 
            error.message.toLowerCase().includes("no active session")) { 
          resetState(); 
          sessionStartedRef.current = false; 
        }
      }
    }, [client, isProcessing, isEvaluationReceived, resetState]
  );

  const endSession = useCallback(
    async (): Promise<void> => {
      if (!client.hasActiveSession()) { 
        return; 
      }
      
      const endedSessionId = client.getCurrentSessionId();
      
      try { 
        // End the session
        await client.endSession(endedSessionId); 
        resetState(); 
        sessionStartedRef.current = false; 
      } catch (err) { 
        // Handle errors
        const error = err as Error; 
        setError(error); 
        resetState(); 
        sessionStartedRef.current = false; 
      }
    }, [client, resetState]
  );

  const prepareForUnmount = useCallback(() => { 
    willUnmountRef.current = true; 
  }, []);

  // Auto-connect effect (unchanged)
  useEffect(() => {
    const themeSelected = typeof window !== 'undefined' && localStorage.getItem("learningTheme") !== null;
    if (autoConnect && themeSelected && !client.hasActiveSession() && !isProcessing && !autoConnectPerformedRef.current && !sessionRequestPendingRef.current) {
      const autoInitialize = async () => { 
        autoConnectPerformedRef.current = true; 
        const theme = localStorage.getItem("learningTheme") || "space"; 
        const path = localStorage.getItem("learningPath") || "addition"; 
        await startSession({ personalized_theme: theme, learning_path: path }); 
      };
      autoInitialize();
    }
  }, [autoConnect, client, isProcessing, startSession]);

  // Cleanup effect (unchanged)
  useEffect(() => {
    return () => { 
      if (willUnmountRef.current && client.hasActiveSession()) { 
        client.endSession().catch(console.error); 
      } 
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  return { 
    client, 
    sessionId: client.getCurrentSessionId(), 
    agentOutput, 
    isLoading: isProcessing && !isEvaluationReceived, // CRITICAL FIX: Don't show loading during evaluation
    isConnected, 
    masteryLevel, 
    error, 
    isEvaluationReceived, // Expose new state
    startSession, 
    sendMessage, 
    requestContinue, 
    endSession, 
    clearEvaluationState, // Expose new function
    resetState, 
    prepareForUnmount,
  };
}