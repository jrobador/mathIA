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
  startSession: (options: StartSessionOptions) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  requestContinue: () => Promise<void>;
  endSession: () => Promise<void>;
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
  const lastMessageRef = useRef<string | null>(null);
  const sessionRequestPendingRef = useRef<boolean>(false);
  const sessionStartedRef = useRef<boolean>(!!client.getCurrentSessionId());
  const autoConnectPerformedRef = useRef<boolean>(false);
  const willUnmountRef = useRef<boolean>(false);

   const resetState = useCallback(() => {
    setSessionId(null); setAgentOutput(null); setMasteryLevel(0); setError(null); setIsProcessing(false); lastMessageRef.current = null;
  }, []);

  useEffect(() => {
    const checkConnectionInterval = setInterval(() => { setIsConnected(client.isWebSocketConnected()); }, 3000);
    const handlePushedMessage = (message: WebSocketMessage) => {
      console.log("Hook handlePushedMessage received (simplified):", message);
      if (message.type === "agent_response" || message.type === "state_update" || message.type === "error") {
          // Stop loading on any relevant message from backend after a request
          // This might turn off loading slightly early if backend sends multiple messages fast,
          // but it prevents getting stuck in loading.
          setIsProcessing(false);
      }
      const responseData = message.data;
      if (message.type === "agent_response" && responseData) {
            const newAgentOutput: AgentOutput = {
                text: responseData.text || "Agent response", image_url: responseData.image_url, audio_url: responseData.audio_url,
                prompt_for_answer: responseData.waiting_for_input ?? responseData.state_metadata?.waiting_for_input ?? false,
                evaluation: responseData.evaluation_type || responseData.state_metadata?.last_evaluation || null,
                is_final_step: responseData.is_final_step || false, action_type: responseData.action || responseData.executed_action_name || null,
                content_type: responseData.content_type || null, waiting_for_input: responseData.waiting_for_input, state_metadata: responseData.state_metadata
            };
            setAgentOutput(newAgentOutput);
            if (responseData.state_metadata?.mastery !== undefined) { setMasteryLevel(responseData.state_metadata.mastery); }
      } else if (message.type === "state_update" && responseData) {
            setSessionId(responseData.session_id);
            setMasteryLevel(responseData.state_metadata?.mastery ?? responseData.topic_mastery?.[responseData.current_topic] ?? 0);
      } else if (message.type === "error") {
            const errorMessage = message.message ?? "Unknown server error"; setError(new Error(errorMessage));
            if (errorMessage.toLowerCase().includes("sesión no encontrada")) { resetState(); sessionStartedRef.current = false; }
      }
    };
    client.addMessageHandler(handlePushedMessage);
    return () => { clearInterval(checkConnectionInterval); client.removeMessageHandler(handlePushedMessage); };
  }, [client, resetState]); // Added resetState

  const startSession = useCallback( async (options: StartSessionOptions): Promise<void> => {
      if (isProcessing || sessionRequestPendingRef.current || (client.getCurrentSessionId() && !error)) { return; }
      sessionRequestPendingRef.current = true; setIsProcessing(true); setError(null); resetState();
      try {
        const response = await client.startSession(options); setSessionId(response.session_id);
        const initialMastery = response.initial_output?.state_metadata?.mastery ?? 0; setMasteryLevel(initialMastery);
        setAgentOutput(response.initial_output); sessionStartedRef.current = true;
      } catch (err) {
        const error = err as Error; setError(error); sessionStartedRef.current = false; resetState();
      } finally {
        setIsProcessing(false); sessionRequestPendingRef.current = false;
      }
    }, [client, isProcessing, error, resetState]
  );

  const sendMessage = useCallback( async (message: string): Promise<void> => {
      const currentSession = client.getCurrentSessionId(); if (!currentSession) { setError(new Error("No active session.")); return; }
      if (isProcessing) { console.warn("sendMessage blocked"); return; }
      setIsProcessing(true); setError(null); lastMessageRef.current = message;
      try { await client.processInput(message, currentSession); }
      catch (err) {
        const error = err as Error; setError(error); setIsProcessing(false);
        if (error.message.toLowerCase().includes("not found") || error.message.toLowerCase().includes("no active session")) { resetState(); sessionStartedRef.current = false; }
      } // Loading turned off by handlePushedMessage
    }, [client, isProcessing, resetState]
  );

  const requestContinue = useCallback(async (): Promise<void> => {
    const currentSession = client.getCurrentSessionId(); if (!currentSession) { setError(new Error("No active session.")); return; }
    if (isProcessing) { console.warn("requestContinue blocked"); return; }
    setIsProcessing(true); setError(null);
    try { await client.requestContinue(currentSession); }
    catch (err) {
        const error = err as Error; setError(error); setIsProcessing(false);
         if (error.message.toLowerCase().includes("not found") || error.message.toLowerCase().includes("no active session")) { resetState(); sessionStartedRef.current = false; }
    } // Loading turned off by handlePushedMessage
  }, [client, isProcessing, resetState]);

  const endSession = useCallback(async (): Promise<void> => {
    if (!client.hasActiveSession()) { return; } const endedSessionId = client.getCurrentSessionId();
    try { await client.endSession(endedSessionId); resetState(); sessionStartedRef.current = false; }
    catch (err) { const error = err as Error; setError(error); resetState(); sessionStartedRef.current = false; }
  }, [client, resetState]);

  const prepareForUnmount = useCallback(() => { willUnmountRef.current = true; }, []);

  useEffect(() => { // Auto-connect effect (unchanged)
    const themeSelected = typeof window !== 'undefined' && localStorage.getItem("learningTheme") !== null;
    if (autoConnect && themeSelected && !client.hasActiveSession() && !isProcessing && !autoConnectPerformedRef.current && !sessionRequestPendingRef.current) {
      const autoInitialize = async () => { autoConnectPerformedRef.current = true; const theme = localStorage.getItem("learningTheme") || "space"; const path = localStorage.getItem("learningPath") || "addition"; await startSession({ personalized_theme: theme, learning_path: path }); };
      autoInitialize();
    }
  }, [autoConnect, client, isProcessing, startSession]);

  useEffect(() => { // Cleanup effect (unchanged)
    return () => { if (willUnmountRef.current && client.hasActiveSession()) { client.endSession().catch(console.error); } };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  return { client, sessionId: client.getCurrentSessionId(), agentOutput, isLoading: isProcessing, isConnected, masteryLevel, error, startSession, sendMessage, requestContinue, endSession, resetState, prepareForUnmount, };
}