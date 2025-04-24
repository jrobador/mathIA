// FILE: LessonPage.tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRightIcon } from "@radix-ui/react-icons";
import { useTutor } from "@/contexts/TutorProvider"; // Adjust path if needed
import { EvaluationResult } from "@/types/api"; // Adjust path if needed
import ReactMarkdown from "react-markdown";
import { Volume2, Loader2, RefreshCw, AlertCircle } from "lucide-react";

export default function LessonPage() {
  // Use the TutorContext
  const {
    sessionId,
    currentOutput,
    isLoading: isTutorLoading, // Renamed to avoid conflict
    masteryLevel,
    startSession,
    sendMessage,
    requestContinue, // <-- Get from context
    error: tutorError,
  } = useTutor();

  // Local state
  const [studentName, setStudentName] = useState("");
  const [learningPath, setLearningPath] = useState("");
  const [learningTheme, setLearningTheme] = useState("");
  const [userAnswer, setUserAnswer] = useState("");
  const [errorState, setErrorState] = useState<{
    isError: boolean;
    message: string;
  }>({
    isError: false,
    message: "",
  });
  const [audioKey, setAudioKey] = useState(Date.now());
  const [imageKey, setImageKey] = useState(Date.now());
  // Add state to track if input is required (regardless of evaluation state)
  const [forceInputRequired, setForceInputRequired] = useState(false);
  const [lastActionType, setLastActionType] = useState<string | null>(null);

  // References
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionStartAttemptedRef = useRef(false);
  const userInfoLoadedRef = useRef(false);

  // --- Existing useEffect hooks (userInfo, tutorError, startSession, content changes) ---
  // Load user info from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined' && !userInfoLoadedRef.current) {
      userInfoLoadedRef.current = true;
      setStudentName(localStorage.getItem("studentName") || "learner");
      setLearningPath(localStorage.getItem("learningPath") || "addition");
      setLearningTheme(localStorage.getItem("learningTheme") || "space");
    }
  }, []);

  // Handle tutor error state changes
  useEffect(() => {
    const initializeSession = async () => {
      // Check conditions more carefully
      if (sessionId || sessionStartAttemptedRef.current || isTutorLoading || !userInfoLoadedRef.current || !learningPath) {
        return;
      }
  
      try {
        sessionStartAttemptedRef.current = true; // Mark attempt
        console.log("Attempting to start new tutoring session...");
  
        // Get diagnostic results from localStorage to initialize the session properly
        const diagnosticResultsJson = localStorage.getItem("diagnosticResults");
        let diagnosticResults = null;
        
        // Parse diagnostic results if available
        if (diagnosticResultsJson) {
          try {
            const parsedResults = JSON.parse(diagnosticResultsJson);
            // Extract the question_results array which contains what the API expects
            diagnosticResults = parsedResults.question_results || [];
            console.log("Using diagnostic results:", diagnosticResults);
          } catch (e) {
            console.error("Error parsing diagnostic results:", e);
            // Continue without diagnostic results
          }
        }
  
        await startSession({
          theme: learningTheme,
          learningPath: learningPath,
          initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`,
          diagnosticResults: diagnosticResults,
        });
        console.log("Context startSession called.");
      } catch (error) {
        console.error("Failed to start session via context:", error);
        setErrorState({
          isError: true,
          message: "Failed to start the learning session. Please try refreshing.",
        });
        toast.error("Failed to start session");
        sessionStartAttemptedRef.current = false; // Allow retry on failure
      }
    };
  
    // Trigger session start only when user info is loaded
    if (userInfoLoadedRef.current) {
      initializeSession();
    }
  }, [sessionId, isTutorLoading, startSession, learningPath, learningTheme, studentName]);


  // Reset keys when content changes to force re-rendering components
  useEffect(() => {
    if (currentOutput) {
      console.log("New content received:", currentOutput);
      
      // Check if the action_type indicates input required
      if (currentOutput.action_type === "require_input") {
        console.log("Force showing input form based on require_input action");
        setForceInputRequired(true);
      } else {
        // Reset the force flag when we get a different action
        setForceInputRequired(false);
      }
      
      // Store the action type for reference in the UI logic
      if (currentOutput.action_type) {
        setLastActionType(currentOutput.action_type);
      }
      
      if (currentOutput.audio_url) setAudioKey(Date.now());
      if (currentOutput.image_url) setImageKey(Date.now());
      
      // Clear local error state if we receive new content
      if (errorState.isError && !tutorError) {
         setErrorState({ isError: false, message: "" });
      }
    }
  }, [currentOutput, errorState.isError, tutorError]);


  // Handle submitting an answer
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim() || isTutorLoading) {
      // Check context's isLoading
      return;
    }

    try {
      console.log("Submitting answer:", userAnswer);
      await sendMessage(userAnswer);
      setUserAnswer(""); // Clear input on successful send *request*
      setForceInputRequired(false); // Reset the force flag after submitting
    } catch (error) {
      console.error("Error submitting answer:", error);
      setErrorState({
        isError: true,
        message: "Failed to send your answer. Please try again.",
      });
      toast.error("Failed to send answer");
    }
  };

  // --- Handle Continue ---
  const handleContinue = async () => {
    if (isTutorLoading) {
      return; // Prevent multiple clicks while loading
    }
    try {
      console.log("Requesting continue...");
      await requestContinue(); // Call the context function
      
      // If this was previously requiring input, reset that state
      if (forceInputRequired) {
        setForceInputRequired(false);
      }
    } catch (error) {
      console.error("Error requesting continue:", error);
      setErrorState({
        isError: true,
        message: "Failed to continue to the next step. Please try again.",
      });
      toast.error("Failed to continue");
    }
  };

  // --- (handleKeyPress, handleNumberInput, playAudio, handleRefresh - unchanged) ---
  // Handle key press for submitting with enter
  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Check if the input element is focused? Might not be needed if div has tabIndex
    if (e.key === 'Enter' && (currentOutput?.prompt_for_answer || forceInputRequired) && userAnswer.trim() && !isTutorLoading) {
      handleSubmitAnswer();
    }
  };

  // Handle input for the number pad
  const handleNumberInput = (input: string) => {
    if (input === "clear") {
      setUserAnswer("");
    } else if (input === "backspace") {
      setUserAnswer(prev => prev.slice(0, -1));
    } else {
      if (userAnswer.length < 10) { // Limit input length
        setUserAnswer(prev => prev + input);
      }
    }
  };

  // Play audio function
  const playAudio = () => {
    if (audioRef.current) {
      audioRef.current.play().catch(err => console.error("Error playing audio:", err));
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    sessionStartAttemptedRef.current = false;
    setErrorState({ isError: false, message: "" });
    window.location.reload(); // Simple refresh
  };

  // --- (progress calculation, theme styles - unchanged) ---
  // Progress calculation
  const progress = Math.round((masteryLevel || 0) * 100);

  // Theme-based styling
  const getThemeStyles = () => {
    // ... (theme style definitions remain the same) ...
    switch (learningTheme) {
      case "magic":
        return {
          primaryColor: "text-purple-700",
          bgGradient: "from-purple-50 to-indigo-100",
          accentColor: "bg-purple-600",
          buttonColor: "bg-purple-600 hover:bg-purple-700",
          borderColor: "border-purple-200"
        }
      case "heroes":
        return {
          primaryColor: "text-red-600",
          bgGradient: "from-red-50 to-orange-100",
          accentColor: "bg-red-600",
          buttonColor: "bg-red-600 hover:bg-red-700",
          borderColor: "border-red-200"
        }
      case "royalty":
        return {
          primaryColor: "text-blue-700",
          bgGradient: "from-blue-50 to-indigo-100",
          accentColor: "bg-blue-600",
          buttonColor: "bg-blue-600 hover:bg-blue-700",
          borderColor: "border-blue-200"
        }
      default: // Default or space theme
        return {
          primaryColor: "text-indigo-700",
          bgGradient: "from-indigo-50 to-white",
          accentColor: "bg-indigo-600",
          buttonColor: "bg-indigo-600 hover:bg-indigo-700",
          borderColor: "border-indigo-200"
        }
    }
  };
  const themeStyles = getThemeStyles();

  // Use the isLoading state from the context directly
  const isLoading = isTutorLoading;

  // UPDATED: Determine if the Continue button should be shown
  // - Don't show continue when forceInputRequired is true (backend requires input)
  // - Don't show continue when action_type is 'pause'
  // - Don't show continue when prompt_for_answer is true
  // - Don't show continue during loading or errors
  const showContinueButton = currentOutput && 
                            !isLoading && 
                            !errorState.isError && 
                            !currentOutput.evaluation && 
                            !currentOutput.prompt_for_answer && 
                            !forceInputRequired &&
                            lastActionType !== "pause";
                            
  // UPDATED: Determine if the Answer input section should be shown
  // Show input when:
  // - prompt_for_answer is true OR forceInputRequired is true
  // - not during evaluation
  // - not during loading or errors
  const showAnswerInput = currentOutput && 
                         !isLoading && 
                         !errorState.isError && 
                         !currentOutput.evaluation && 
                         (currentOutput.prompt_for_answer || forceInputRequired);


  return (
    <main
      className={`min-h-screen flex flex-col items-center justify-center bg-gradient-to-b ${themeStyles.bgGradient} p-4 relative overflow-hidden`}
    >
      {/* Background image */}
      {/* ... (unchanged) ... */}
       <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
        <img
          src="/images/learning-background.png" // Make this dynamic based on theme?
          alt="Learning background"
          className="w-full h-full object-cover"
        />
      </div>

      {/* Main container */}
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">
        {/* Header navigation */}
        {/* ... (unchanged) ... */}
         <div className="w-full flex justify-between items-center mb-4">
          <div className={`text-sm ${themeStyles.primaryColor} font-medium`}>
            {learningPath && learningPath.charAt(0).toUpperCase() + learningPath.slice(1)} Journey
          </div>
          {/* Add other header elements if needed */}
        </div>


        {/* Progress indicator */}
        {/* ... (unchanged) ... */}
        <div className="w-full max-w-md mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Your progress</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2 bg-gray-200" />
          <div className="flex justify-end mt-1">
            <span className="text-sm text-gray-600">
              {progress < 33 ? "🌱 Just starting" : progress < 66 ? "🌳 Growing" : "⭐ Mastering"}
            </span>
          </div>
        </div>

        {/* Debug indicator - optional, helps during development */}
        {process.env.NODE_ENV === 'development' && (
          <div className="text-xs text-gray-500 mb-2">
            Debug: {forceInputRequired ? "Input Required" : "No forced input"} | 
            Action: {lastActionType || "none"} |
            Prompt: {currentOutput?.prompt_for_answer ? "Yes" : "No"}
          </div>
        )}

        {/* Content Area */}
        <AnimatePresence mode="wait">
          {/* Loading State */}
          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border border-gray-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center"
            >
              <Loader2 className="h-12 w-12 text-indigo-600 animate-spin mb-4" />
              <p className="text-lg text-gray-600 mb-2">Preparing next step...</p>
              <p className="text-sm text-gray-500">Please wait a moment.</p>
            </motion.div>
          )}

          {/* Error State */}
          {errorState.isError && !isLoading && ( // Don't show error if loading overlay is active
            <motion.div
              key="error"
              // ... (error state motion props - unchanged) ...
              className="w-full max-w-3xl bg-red-50 rounded-2xl shadow-xl my-4 md:my-6 relative border border-red-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center"
            >
               {/* ... (error icon, title, message - unchanged) ... */}
               <div className="bg-red-100 p-4 rounded-full mb-4">
                <AlertCircle className="h-10 w-10 text-red-500" />
              </div>
              <h2 className="text-xl font-semibold text-red-700 mb-2">Something went wrong</h2>
              <p className="text-gray-700 mb-6 text-center max-w-md">
                {errorState.message || "We're having trouble with your math session. Please try again."}
              </p>
              <Button
                onClick={handleRefresh}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                <RefreshCw className="h-4 w-4 mr-2" /> Try Again
              </Button>
            </motion.div>
          )}

          {/* Content View */}
          {currentOutput && !errorState.isError && !isLoading && (
            <motion.div
              key={currentOutput?.evaluation ? 'evaluation' + Date.now() : 'content' + Date.now()} // Add timestamp to ensure re-animation
              // ... (content motion props - unchanged) ...
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              className={`w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border ${themeStyles.borderColor} overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-between`}

            >
              {currentOutput?.evaluation ? (
                // --- Evaluation View ---
                <div className="flex flex-col justify-center items-center h-full text-center">
                  {/* ... (evaluation text - unchanged) ... */}
                  <h1 className={`text-2xl md:text-3xl font-bold ${
                    currentOutput.evaluation === EvaluationResult.CORRECT ? "text-green-700" : "text-orange-700"
                  } mb-3`}>
                    {currentOutput.evaluation === EvaluationResult.CORRECT ? "Great job!" : "Not quite right"}
                  </h1>
                  <div className="text-base md:text-lg text-gray-800 mb-3 max-w-lg">
                    <ReactMarkdown>{currentOutput.text || ""}</ReactMarkdown>
                  </div>
                  {/* Show Continue after evaluation */}
                  <div className="mt-6 flex justify-center">
                      <Button
                        size="lg"
                        onClick={handleContinue} // Use continue here too
                        className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading...
                          </>
                        ) : (
                          <>
                            Next Step <ArrowRightIcon className="ml-2 h-4 w-4" />
                          </>
                        )}
                      </Button>
                  </div>
                </div>
              ) : (
                // --- Standard Content View ---
                <div className="flex flex-col justify-between h-full">
                  {/* Top part: Content from backend */}
                  <div className="text-center mb-4"> {/* Added mb-4 */}
                    {/* ... (text, image, audio display - unchanged) ... */}
                      <div className={`text-xl md:text-2xl font-bold ${themeStyles.primaryColor} mb-4`}>
                        <ReactMarkdown>{currentOutput?.text || "Loading..."}</ReactMarkdown>
                      </div>
                      {currentOutput?.image_url && (
                        <div className="mb-6 flex justify-center">
                          <div className="relative h-[200px] w-full max-w-md rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                            <div key={imageKey} className="w-full h-full relative">
                              <img
                                src={currentOutput.image_url}
                                alt="Math visual"
                                className="w-full h-full object-contain"
                                onError={(e) => { (e.target as HTMLImageElement).src = "/images/placeholder-math.png"; }}
                              />
                            </div>
                          </div>
                        </div>
                      )}
                      {currentOutput?.audio_url && (
                        <div className="mb-4">
                          <audio key={audioKey} ref={audioRef} src={currentOutput.audio_url} className="hidden" />
                          <Button variant="outline" size="sm" onClick={playAudio} className="flex items-center bg-white/80 hover:bg-indigo-50">
                            <Volume2 className="h-4 w-4 mr-2 text-indigo-600" /> Play Audio
                          </Button>
                        </div>
                      )}
                  </div>

                  {/* Conditional Input/Continue Area */}
                  <div className="mt-auto pt-4"> {/* Ensure this area is pushed down */}
                    {showAnswerInput && (
                       // --- Answer Input Section --- (Number pad, input display, check button)
                       <div className="mt-4">
                            {/* ... (Input display div - unchanged) ... */}
                             <div className="flex justify-center items-center mb-4">
                                <div
                                  className={`flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[120px] md:min-w-[140px] h-[50px] md:h-[60px] border ${themeStyles.borderColor} shadow-sm`}
                                  onKeyDown={handleKeyPress}
                                  tabIndex={0} // Make it focusable for keydown
                                >
                                  <span className="text-2xl md:text-3xl font-bold text-indigo-900 tracking-wider">{userAnswer || "_"}</span>
                                </div>
                            </div>
                            {/* ... (Number pad div - unchanged) ... */}
                             <div className="w-full max-w-[280px] md:max-w-[320px] mx-auto grid grid-cols-3 gap-2">
                                {[1, 2, 3, 4, 5, 6, 7, 8, 9, "clear", 0, "backspace"].map((btn) => (
                                <Button
                                    key={btn}
                                    variant={btn === "clear" ? "destructive" : "outline"}
                                    className={`h-12 text-lg font-medium ${
                                    btn === "clear"
                                        ? "bg-red-500/80 hover:bg-red-600/90 border border-red-400/30 text-white" // Ensure text color
                                        : "bg-white/80 backdrop-blur-sm border-indigo-100/60 hover:bg-indigo-50/90"
                                    }`}
                                    onClick={() => handleNumberInput(btn.toString())}
                                    disabled={isLoading}
                                >
                                    {btn === "backspace" ? "⌫" : btn === "clear" ? "Clear" : btn}
                                </Button>
                                ))}
                            </div>
                            {/* ... (Submit button div - unchanged) ... */}
                             <div className="mt-6 flex justify-center">
                                <Button
                                size="lg"
                                onClick={handleSubmitAnswer}
                                className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                                disabled={!userAnswer.trim() || isLoading}
                                >
                                {isLoading ? (
                                    <> <Loader2 className="h-4 w-4 animate-spin mr-2" /> Processing... </>
                                ) : (
                                    <> Check Answer <ArrowRightIcon className="ml-2 h-4 w-4" /> </>
                                )}
                                </Button>
                            </div>
                       </div>
                    )}

                    {showContinueButton && (
                        // --- Continue Button Section ---
                        <div className="mt-6 flex justify-center">
                            <Button
                                size="lg"
                                onClick={handleContinue}
                                className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <> <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading... </>
                                ) : (
                                    <> Continue <ArrowRightIcon className="ml-2 h-4 w-4" /> </>
                                )}
                            </Button>
                        </div>
                    )}
                   </div> {/* End Conditional Input/Continue Area */}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}