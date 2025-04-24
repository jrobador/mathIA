// FILE: frontend/math-journey/app/lesson/page.tsx
"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner"; // Use sonner for feedback
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircledIcon, CrossCircledIcon, ArrowRightIcon } from "@radix-ui/react-icons"; // Icons for toasts
import { useTutor } from "@/contexts/TutorProvider";
import { AgentOutput, EvaluationResult } from "@/types/api";
import ReactMarkdown from "react-markdown";
import { Volume2, Loader2, RefreshCw, AlertCircle } from "lucide-react";

export default function LessonPage() {
  // Use the TutorContext
  const {
    sessionId,
    currentOutput, // This will now always reflect the latest step from the backend
    isLoading: isTutorLoading,
    masteryLevel,
    startSession,
    sendMessage,
    requestContinue, // Used by the Continue button
    error: tutorError,
  } = useTutor();

  // Local state
  const [studentName, setStudentName] = useState("");
  const [learningPath, setLearningPath] = useState("");
  const [learningTheme, setLearningTheme] = useState("");
  const [userAnswer, setUserAnswer] = useState("");
  const [errorState, setErrorState] = useState<{ isError: boolean; message: string }>({
    isError: false,
    message: "",
  });
  const [audioKey, setAudioKey] = useState(Date.now());
  const [imageKey, setImageKey] = useState(Date.now());

  // References
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionStartAttemptedRef = useRef(false);
  const userInfoLoadedRef = useRef(false);
  const lastProcessedOutputRef = useRef<AgentOutput | null>(null);

  // --- useEffect Hooks ---

  // Load user info
  useEffect(() => {
    if (typeof window !== 'undefined' && !userInfoLoadedRef.current) {
      userInfoLoadedRef.current = true; setStudentName(localStorage.getItem("studentName") || "learner"); setLearningPath(localStorage.getItem("learningPath") || "addition"); setLearningTheme(localStorage.getItem("learningTheme") || "space");
    }
  }, []);

  // Start session logic
   useEffect(() => {
    const initializeSession = async () => {
      if (sessionId || sessionStartAttemptedRef.current || isTutorLoading || !userInfoLoadedRef.current || !learningPath) { return; }
      try {
        sessionStartAttemptedRef.current = true; const diagnosticResultsJson = localStorage.getItem("diagnosticResults"); let diagnosticResults = null;
        if (diagnosticResultsJson) { try { const parsedResults = JSON.parse(diagnosticResultsJson); diagnosticResults = parsedResults.question_results || []; } catch (e) { console.error("Error parsing diagnostic results:", e); } }
        await startSession({ theme: learningTheme, learningPath: learningPath, initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`, diagnosticResults: diagnosticResults });
      } catch (error) {
        console.error("Failed to start session via context:", error); setErrorState({ isError: true, message: "Failed to start the learning session. Please try refreshing." }); toast.error("Failed to start session"); sessionStartAttemptedRef.current = false;
      }
    };
    if (userInfoLoadedRef.current) { initializeSession(); }
  }, [sessionId, isTutorLoading, startSession, learningPath, learningTheme, studentName]);

  // Play audio function
  const playAudio = useCallback((url: string | null | undefined) => {
    if (url && audioRef.current) { if (audioRef.current.src !== url) { audioRef.current.src = url; } audioRef.current.currentTime = 0; audioRef.current.play().catch(err => console.error("Error playing audio:", err)); }
  }, []);

  // --- useEffect for processing currentOutput and showing toast ---
  useEffect(() => {
    if (currentOutput && currentOutput !== lastProcessedOutputRef.current) {
        lastProcessedOutputRef.current = currentOutput;
        console.log("Hook processing new currentOutput:", JSON.stringify(currentOutput));

        // Case 1: Received an Evaluation Result
        if (currentOutput.evaluation && currentOutput.action_type === 'evaluation_result') {
            console.log("Displaying evaluation feedback toast.");
            const isCorrect = currentOutput.evaluation === EvaluationResult.CORRECT;
            const toastOptions = { duration: 4000, icon: isCorrect ? <CheckCircledIcon className="text-green-500" /> : <CrossCircledIcon className="text-orange-500" /> };
            if (isCorrect) { toast.success(currentOutput.text || "Correct!", toastOptions); }
            else { toast.warning(currentOutput.text || "Not quite right.", toastOptions); }
            if (currentOutput.audio_url) { setTimeout(() => playAudio(currentOutput.audio_url), 150); }
            // --- NO AUTOMATIC requestContinue HERE ---
        }
        // Case 2: Received Non-Evaluation Content
        else {
            if (currentOutput.audio_url) setAudioKey(Date.now());
            if (currentOutput.image_url) setImageKey(Date.now());
        }
        if (errorState.isError && !tutorError) { setErrorState({ isError: false, message: "" }); }
    }
  }, [currentOutput, errorState.isError, playAudio, tutorError]); // Removed requestContinue and isTutorLoading from deps
  // --- END useEffect ---

  // Handle submitting an answer
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim() || isTutorLoading) { return; }
    try { await sendMessage(userAnswer); setUserAnswer(""); }
    catch (error) { console.error("Error submitting answer:", error); setErrorState({ isError: true, message: "Failed to send answer." }); toast.error("Failed to send answer"); }
  };

  // Handle Continue button click
  const handleContinue = async () => {
    if (isTutorLoading) { return; }
    try { console.log("Requesting continue manually..."); await requestContinue(); }
    catch (error) { console.error("Error requesting continue:", error); setErrorState({ isError: true, message: "Failed to continue." }); toast.error("Failed to continue"); }
  };

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && currentOutput?.prompt_for_answer && userAnswer.trim() && !isTutorLoading) { handleSubmitAnswer(); }
  };

  // Handle number pad
  const handleNumberInput = (input: string) => {
    if (input === "clear") setUserAnswer(""); else if (input === "backspace") setUserAnswer(prev => prev.slice(0, -1)); else if (userAnswer.length < 10) setUserAnswer(prev => prev + input);
  };

  // Handle refresh
  const handleRefresh = () => { sessionStartAttemptedRef.current = false; setErrorState({ isError: false, message: "" }); window.location.reload(); };

  // Progress calculation
  const progress = Math.round((masteryLevel || 0) * 100);

  // Theme styles
  const getThemeStyles = () => { /* ... same as before ... */
    switch (learningTheme) {
      case "magic": return { primaryColor: "text-purple-700", bgGradient: "from-purple-50 to-indigo-100", accentColor: "bg-purple-600", buttonColor: "bg-purple-600 hover:bg-purple-700", borderColor: "border-purple-200" };
      case "heroes": return { primaryColor: "text-red-600", bgGradient: "from-red-50 to-orange-100", accentColor: "bg-red-600", buttonColor: "bg-red-600 hover:bg-red-700", borderColor: "border-red-200" };
      case "royalty": return { primaryColor: "text-blue-700", bgGradient: "from-blue-50 to-indigo-100", accentColor: "bg-blue-600", buttonColor: "bg-blue-600 hover:bg-blue-700", borderColor: "border-blue-200" };
      default: return { primaryColor: "text-indigo-700", bgGradient: "from-indigo-50 to-white", accentColor: "bg-indigo-600", buttonColor: "bg-indigo-600 hover:bg-indigo-700", borderColor: "border-indigo-200" };
    }
   };
  const themeStyles = getThemeStyles();
  const isLoading = isTutorLoading;

  // Determine button/input visibility
  // IMPORTANT: Check currentOutput FIRST before accessing its properties
  const showAnswerInput = currentOutput ? (currentOutput.prompt_for_answer && !isLoading && !errorState.isError) : false;
  const showContinueButton = currentOutput ? (!isLoading && !errorState.isError && !currentOutput.prompt_for_answer && !currentOutput.is_final_step) : false;

  // Debug info
  const debugInfo = {
    currentAction: currentOutput?.action_type || "none", currentPrompt: currentOutput?.prompt_for_answer ? "true" : "false",
    isLoading: isLoading ? "true" : "false", showInput: showAnswerInput ? "true": "false", showContinue: showContinueButton ? "true" : "false",
  };

  return (
    <main className={`min-h-screen flex flex-col items-center justify-center bg-gradient-to-b ${themeStyles.bgGradient} p-4 relative overflow-hidden`} >
      <div className="absolute inset-0 z-0"> {/* Background */}
         <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
         <img src="/images/learning-background.png" alt="Learning background" className="w-full h-full object-cover" />
      </div>
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">
        {/* Header, Progress, Debug Indicator (unchanged) */}
        <div className="w-full flex justify-between items-center mb-4"><div className={`text-sm ${themeStyles.primaryColor} font-medium`}>{learningPath && learningPath.charAt(0).toUpperCase() + learningPath.slice(1)} Journey</div></div>
        <div className="w-full max-w-md mb-4"><div className="flex justify-between text-sm text-gray-600 mb-1"><span>Your progress</span> <span>{progress}%</span></div><Progress value={progress} className="h-2 bg-gray-200" /><div className="flex justify-end mt-1"><span className="text-sm text-gray-600">{progress < 33 ? "🌱" : progress < 66 ? "🌳" : "⭐"}</span></div></div>
        {process.env.NODE_ENV === 'development' && (<div className="text-xs text-gray-500 mb-2 p-2 bg-gray-100 rounded-md w-full text-left"><div><strong>Debug:</strong> Loading: {debugInfo.isLoading} | Input: {debugInfo.showInput} | Continue: {debugInfo.showContinue} | Action: {debugInfo.currentAction} | Prompt: {debugInfo.currentPrompt}</div></div>)}

        {/* Central Audio Player */}
        <audio ref={audioRef} className="hidden" />

        {/* Content Area */}
        <AnimatePresence mode="wait">
           {isLoading && ( /* Loading State */
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border border-gray-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center">
              <Loader2 className="h-12 w-12 text-indigo-600 animate-spin mb-4" /> <p className="text-lg text-gray-600 mb-2">Loading...</p> <p className="text-sm text-gray-500">Please wait.</p>
            </motion.div>
          )}
          {errorState.isError && !isLoading && ( /* Error State */
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full max-w-3xl bg-red-50 rounded-2xl shadow-xl my-4 md:my-6 relative border border-red-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center">
              <div className="bg-red-100 p-4 rounded-full mb-4"><AlertCircle className="h-10 w-10 text-red-500" /></div> <h2 className="text-xl font-semibold text-red-700 mb-2">Something went wrong</h2> <p className="text-gray-700 mb-6 text-center max-w-md">{errorState.message || "..."}</p> <Button onClick={handleRefresh} className="bg-red-600 hover:bg-red-700 text-white"><RefreshCw className="h-4 w-4 mr-2" /> Try Again</Button>
            </motion.div>
          )}
           {!isLoading && !errorState.isError && currentOutput && ( /* Main Content */
             <motion.div key={`content-${currentOutput.action_type}-${currentOutput.text?.slice(0, 15)}-${sessionId}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }} className={`w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border ${themeStyles.borderColor} overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-between`}>
                 <div className="flex flex-col justify-between h-full">
                  <div className="flex-grow text-center mb-4 overflow-y-auto"> {/* Top Content */}
                     <div className={`text-xl md:text-2xl font-bold ${themeStyles.primaryColor} mb-4 prose max-w-none`}><ReactMarkdown>{currentOutput?.text || ""}</ReactMarkdown></div>
                     {currentOutput?.image_url && (<div className="mb-6 flex justify-center"><div className="relative h-[200px] w-full max-w-md rounded-lg overflow-hidden border border-gray-200 bg-gray-50"><img key={imageKey} src={currentOutput.image_url} alt="Math visual" className="w-full h-full object-contain" onError={(e) => { (e.target as HTMLImageElement).src = "/images/placeholder-math.png"; }} /></div></div>)}
                     {currentOutput?.audio_url && (<div className="mb-4"><Button variant="outline" size="sm" onClick={() => playAudio(currentOutput.audio_url)} className="flex items-center bg-white/80 hover:bg-indigo-50"><Volume2 className="h-4 w-4 mr-2 text-indigo-600" /> Play Audio</Button></div>)}
                  </div>
                  <div className="mt-auto pt-4 flex-shrink-0"> {/* Bottom Area */}
                    {showAnswerInput && ( /* Input Area */
                       <div className="mt-4">
                         <div className="flex justify-center items-center mb-4"><div className={`flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[120px] md:min-w-[140px] h-[50px] md:h-[60px] border ${themeStyles.borderColor} shadow-sm`} onKeyDown={handleKeyPress} tabIndex={0} ><span className="text-2xl md:text-3xl font-bold text-indigo-900 tracking-wider">{userAnswer || "_"}</span></div></div>
                         <div className="w-full max-w-[280px] md:max-w-[320px] mx-auto grid grid-cols-3 gap-2">
                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, "clear", 0, "backspace"].map((btn) => (<Button key={btn} variant={btn === "clear" ? "destructive" : "outline"} className={`h-12 text-lg font-medium ${ btn === "clear" ? "bg-red-500/80 hover:bg-red-600/90 border border-red-400/30 text-white" : "bg-white/80 backdrop-blur-sm border-indigo-100/60 hover:bg-indigo-50/90" }`} onClick={() => handleNumberInput(btn.toString())} disabled={isLoading} >{btn === "backspace" ? "⌫" : btn === "clear" ? "Clear" : btn}</Button>))}
                         </div>
                         <div className="mt-6 flex justify-center"><Button size="lg" onClick={handleSubmitAnswer} className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`} disabled={!userAnswer.trim() || isLoading} >{isLoading ? ( <> <Loader2 className="h-4 w-4 animate-spin mr-2" /> Processing... </> ) : ( <> Check Answer <ArrowRightIcon className="ml-2 h-4 w-4" /> </> )}</Button></div>
                       </div>
                    )}
                    {showContinueButton && ( /* Continue Button */
                      <div className="mt-6 flex justify-center"><Button size="lg" onClick={handleContinue} className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`} disabled={isLoading}>{isLoading ? ( <> <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading... </> ) : ( <> Continue <ArrowRightIcon className="ml-2 h-4 w-4" /> </> )}</Button></div>
                    )}
                   </div>
                </div>
              </motion.div>
           )}
        </AnimatePresence>
      </div>
    </main>
  );
}