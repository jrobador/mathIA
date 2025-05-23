"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner"; // Use sonner for feedback
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircledIcon, CrossCircledIcon, ArrowRightIcon } from "@radix-ui/react-icons"; // Icons for toasts
import { useTutor } from "@/contexts/TutorProvider";
import { EvaluationResult } from "@/types/api";
import ReactMarkdown from "react-markdown";
import { Volume2, Loader2, RefreshCw, AlertCircle } from "lucide-react";

export default function LessonPage() {
  // Use the TutorContext
  const {
    sessionId,
    currentOutput, 
    isLoading: isTutorLoading,
    isEvaluationReceived,
    masteryLevel,
    startSession,
    sendMessage,
    requestContinue,
    clearEvaluationState,
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
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  
  // References
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionStartAttemptedRef = useRef(false);
  const userInfoLoadedRef = useRef(false);
  const toastShownRef = useRef(false);
  const [forceShowContinue, setForceShowContinue] = useState(false);

  
  // --- useEffect Hooks ---

  // Load user info
  useEffect(() => {
    if (typeof window !== 'undefined' && !userInfoLoadedRef.current) {
      userInfoLoadedRef.current = true; 
      setStudentName(localStorage.getItem("studentName") || "learner"); 
      setLearningPath(localStorage.getItem("learningPath") || "addition"); 
      setLearningTheme(localStorage.getItem("learningTheme") || "space");
    }
  }, []);

  useEffect(() => {
    // Check for the exact Congratulations messages from the backend
    const isCongratulationsMessage = 
      currentOutput?.text?.includes("Congratulations! You have mastered the current topic") || 
      currentOutput?.text?.includes("Congratulations! You have completed all the topics");
    
    // Set the flag if we detect a topic change message
    if (currentOutput?.action_type === "topic_change" || isCongratulationsMessage) {
      console.log("Topic advancement detected - forcing continue button to show");
      setForceShowContinue(true);
    } else {
      setForceShowContinue(false);
    }
  }, [currentOutput]);

  // Start session logic
  useEffect(() => {
    const initializeSession = async () => {
      if (sessionId || sessionStartAttemptedRef.current || isTutorLoading || !userInfoLoadedRef.current || !learningPath) { return; }
      try {
        sessionStartAttemptedRef.current = true; 
        const diagnosticResultsJson = localStorage.getItem("diagnosticResults"); 
        let diagnosticResults = null;
        if (diagnosticResultsJson) { 
          try { 
            const parsedResults = JSON.parse(diagnosticResultsJson); 
            diagnosticResults = parsedResults.question_results || []; 
          } catch (e) { 
            console.error("Error parsing diagnostic results:", e); 
          } 
        }
        await startSession({ 
          theme: learningTheme, 
          learningPath: learningPath, 
          initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`, 
          diagnosticResults: diagnosticResults 
        });
      } catch (error) {
        console.error("Failed to start session via context:", error); 
        setErrorState({ isError: true, message: "Failed to start the learning session. Please try refreshing." }); 
        toast.error("Failed to start session"); 
        sessionStartAttemptedRef.current = false;
      }
    };
    if (userInfoLoadedRef.current) { initializeSession(); }
  }, [sessionId, isTutorLoading, startSession, learningPath, learningTheme, studentName]);

  // Play audio function - IMPROVED to handle errors better
  const playAudio = useCallback((url: string | null | undefined) => {
    if (!url) return;
    
    try {
      if (audioRef.current) {
        // First pause any current playback
        audioRef.current.pause();
        
        // Check if URL is actually changing to avoid unnecessary reloads
        if (audioRef.current.src !== url) {
          audioRef.current.src = url;
        }
        
        // Reset to beginning
        audioRef.current.currentTime = 0;
        
        // Track playback state
        setIsPlayingAudio(true);
        
        // Play with proper error handling
        audioRef.current.play()
          .then(() => {
            console.log("Audio playing successfully");
          })
          .catch(err => {
            console.warn("Error playing audio:", err);
            setIsPlayingAudio(false);
            // Don't show errors to users for audio - it's not critical
          });
      }
    } catch (err) {
      console.warn("Exception in playAudio:", err);
      setIsPlayingAudio(false);
    }
  }, []);

  // Audio event listeners - IMPROVED
  useEffect(() => {
    const audio = audioRef.current;
    
    const handleEnded = () => {
      setIsPlayingAudio(false);
    };
    
    const handleError = (e: ErrorEvent) => {
      console.warn("Audio error event:", e);
      setIsPlayingAudio(false);
    };
    
    if (audio) {
      audio.addEventListener('ended', handleEnded);
      audio.addEventListener('error', handleError as EventListener);
      
      return () => {
        audio.removeEventListener('ended', handleEnded);
        audio.removeEventListener('error', handleError as EventListener);
      };
    }
  }, []);

  // Effect to handle toast display for evaluation - FIXED
  useEffect(() => {
    if (isEvaluationReceived && currentOutput && currentOutput.evaluation) {
      console.log("🔔 Showing evaluation toast for existing content");
      
      // Only show toast if not shown already for this evaluation 
      if (!toastShownRef.current) {
        const isCorrect = currentOutput.evaluation === EvaluationResult.CORRECT;
        const toastDuration = 6000; 
        
        // Show toast with predefined messages
        toast.custom((id) => (
          <div className={`${isCorrect ? 'bg-green-100 border-l-4 border-green-500' : 'bg-orange-100 border-l-4 border-orange-500'} p-4 rounded shadow-lg`}>
            <div className="flex">
              {isCorrect ? 
                <CheckCircledIcon className="text-green-600 h-5 w-5 mt-0.5 mr-3 flex-shrink-0" /> :
                <CrossCircledIcon className="text-orange-600 h-5 w-5 mt-0.5 mr-3 flex-shrink-0" />
              }
              <div>
                <p className={isCorrect ? "font-bold text-green-800" : "font-bold text-orange-800"}>
                  {isCorrect ? "Correct!" : "Not quite right"}
                </p>
                <p className={isCorrect ? "text-green-700" : "text-orange-700"}>
                  {isCorrect ? "Great job! You got it right." : "Try again with a different approach."}
                </p>
              </div>
            </div>
          </div>
        ), { duration: toastDuration, position: "top-center" });
        
        // Mark that we've shown a toast for this evaluation
        toastShownRef.current = true;
        
        // If there's audio and we're not already playing, play it
        if (currentOutput.audio_url && !isPlayingAudio) {
          playAudio(currentOutput.audio_url);
        }
      }
    } else {
      // Reset toast shown ref when there's no evaluation
      toastShownRef.current = false;
    }
  }, [isEvaluationReceived, currentOutput, playAudio, isPlayingAudio]);

  // Effect to handle media updates for non-evaluation content
  useEffect(() => {
    if (currentOutput && !isEvaluationReceived) {
      // Update audio/image keys for fresh loads when not in evaluation mode
      if (currentOutput.audio_url) setAudioKey(Date.now());
      if (currentOutput.image_url) setImageKey(Date.now());
    }
  }, [currentOutput, isEvaluationReceived]);

  // Handle submitting an answer - IMPROVED error handling
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim() || isTutorLoading) { 
      return; 
    }
    
    try { 
      console.log("Submitting answer:", userAnswer);
      
      // Clear any existing evaluation states
      clearEvaluationState();
      
      // Reset toast shown ref
      toastShownRef.current = false;
      
      // Pause any playing audio to avoid interference
      if (audioRef.current && !audioRef.current.paused) {
        audioRef.current.pause();
        setIsPlayingAudio(false);
      }
      
      // Send the message
      await sendMessage(userAnswer); 
      setUserAnswer(""); 
    }
    catch (error) { 
      console.error("Error submitting answer:", error); 
      setErrorState({ isError: true, message: "Failed to send answer." }); 
      toast.error("Failed to send answer"); 
    }
  };

  // Handle Continue button click - IMPROVED
  const handleContinue = async () => {
    if (isTutorLoading) return;
    
    try { 
      console.log("Manually requesting continue..."); 
      
      // Clear any evaluation states
      clearEvaluationState();
      
      // Pause any playing audio to avoid interference
      if (audioRef.current && !audioRef.current.paused) {
        audioRef.current.pause();
        setIsPlayingAudio(false);
      }
      
      // Send the continue request
      await requestContinue();
    }
    catch (error) { 
      console.error("Error requesting continue:", error); 
      setErrorState({ isError: true, message: "Failed to continue." }); 
      toast.error("Failed to continue"); 
    }
  };

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && 
        currentOutput?.prompt_for_answer && 
        userAnswer.trim() && 
        !isTutorLoading) { 
      handleSubmitAnswer(); 
    }
  };

  // Handle number pad - FIXED
  const handleNumberInput = (input: string) => {
    // Always allow number pad input, even during evaluation
    if (input === "clear") {
      setUserAnswer("");
    } else if (input === "backspace") {
      setUserAnswer(prev => prev.slice(0, -1));
    } else if (userAnswer.length < 10) {
      setUserAnswer(prev => prev + input);
    }
  };

  // Handle refresh
  const handleRefresh = () => { 
    sessionStartAttemptedRef.current = false; 
    setErrorState({ isError: false, message: "" }); 
    window.location.reload(); 
  };

  // Progress calculation
  const progress = Math.round((masteryLevel || 0) * 100);

  // Theme styles
  const getThemeStyles = () => {
    switch (learningTheme) {
      case "magic": return { primaryColor: "text-purple-700", bgGradient: "from-purple-50 to-indigo-100", accentColor: "bg-purple-600", buttonColor: "bg-purple-600 hover:bg-purple-700", borderColor: "border-purple-200" };
      case "heroes": return { primaryColor: "text-red-600", bgGradient: "from-red-50 to-orange-100", accentColor: "bg-red-600", buttonColor: "bg-red-600 hover:bg-red-700", borderColor: "border-red-200" };
      case "royalty": return { primaryColor: "text-blue-700", bgGradient: "from-blue-50 to-indigo-100", accentColor: "bg-blue-600", buttonColor: "bg-blue-600 hover:bg-blue-700", borderColor: "border-blue-200" };
      default: return { primaryColor: "text-indigo-700", bgGradient: "from-indigo-50 to-white", accentColor: "bg-indigo-600", buttonColor: "bg-indigo-600 hover:bg-indigo-700", borderColor: "border-indigo-200" };
    }
  };
  const themeStyles = getThemeStyles();
  
  // SIMPLIFIED: Loading state depends solely on hook's isLoading
  const isLoading = isTutorLoading;

  // UPDATED: Button/input visibility logic
  // CRITICAL FIX: Show answer input regardless of evaluation
  const showAnswerInput = 
    currentOutput?.prompt_for_answer && 
    !isLoading && 
    !errorState.isError;

  // CRITICAL FIX: Never show continue button during evaluation  
  const showContinueButton = 
  forceShowContinue || (
    currentOutput && 
    (!currentOutput.prompt_for_answer || currentOutput.action_type === "topic_change") && 
    !currentOutput.is_final_step && 
    !isLoading && 
    !errorState.isError && 
    !isEvaluationReceived
  );

  return (
    <main className={`min-h-screen flex flex-col items-center justify-center bg-gradient-to-b ${themeStyles.bgGradient} p-4 relative overflow-hidden`} >
      <div className="absolute inset-0 z-0"> {/* Background */}
         <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
         <img src="/images/learning-background.png" alt="Learning background" className="w-full h-full object-cover" />
      </div>
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">
        {/* Header, Progress, Debug Indicator */}
        <div className="w-full flex justify-between items-center mb-4">
          <div className={`text-sm ${themeStyles.primaryColor} font-medium`}>
            {learningPath && learningPath.charAt(0).toUpperCase() + learningPath.slice(1)} Journey
          </div>
        </div>
        <div className="w-full max-w-md mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Your progress</span> <span>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2 bg-gray-200" />
          <div className="flex justify-end mt-1">
            <span className="text-sm text-gray-600">{progress < 33 ? "🌱" : progress < 66 ? "🌳" : "⭐"}</span>
          </div>
        </div>
        
        {/* Central Audio Player - CRITICAL FIX: No audio source by default */}
        <audio 
          ref={audioRef} 
          className="hidden" 
          onEnded={() => setIsPlayingAudio(false)}
          onError={() => setIsPlayingAudio(false)}
        />

        {/* Content Area */}
        <AnimatePresence mode="wait">
          {/* LOADING STATE */}
          {isLoading && !isEvaluationReceived && (
            <motion.div 
              key="loading" 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }} 
              transition={{ duration: 0.2 }} 
              className="w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border border-gray-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center"
            >
              <Loader2 className="h-12 w-12 text-indigo-600 animate-spin mb-4" /> 
              <p className="text-lg text-gray-600 mb-2">Loading...</p> 
              <p className="text-sm text-gray-500">Please wait.</p>
            </motion.div>
          )}
          
          {/* ERROR STATE */}
          {errorState.isError && !isLoading && !isEvaluationReceived && (
            <motion.div 
              key="error" 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }} 
              className="w-full max-w-3xl bg-red-50 rounded-2xl shadow-xl my-4 md:my-6 relative border border-red-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center"
            >
              <div className="bg-red-100 p-4 rounded-full mb-4"><AlertCircle className="h-10 w-10 text-red-500" /></div> 
              <h2 className="text-xl font-semibold text-red-700 mb-2">Something went wrong</h2> 
              <p className="text-gray-700 mb-6 text-center max-w-md">{errorState.message || "..."}</p> 
              <Button onClick={handleRefresh} className="bg-red-600 hover:bg-red-700 text-white">
                <RefreshCw className="h-4 w-4 mr-2" /> Try Again
              </Button>
            </motion.div>
          )}
          
          {/* MAIN CONTENT: Show always, including during evaluation */}
          {currentOutput && (!isLoading || isEvaluationReceived) && !errorState.isError && (
            <motion.div
              // Unique key for remounting on significant content change
              key={`content-${currentOutput.action_type || ""}-${currentOutput.text?.slice(0, 15) || ""}-${sessionId || ""}`}
              initial={{ opacity: 0 }}
              animate={{
                opacity: isEvaluationReceived ? 0.9 : 1,
                scale: isEvaluationReceived ? 0.98 : 1,
                // Add special animation for topic change
                y: currentOutput.action_type === "topic_change" ? [0, -5, 0] : 0
              }}
              exit={{ opacity: 0 }}
              transition={{
                duration: 0.4,
                // Add spring effect for topic change
                ...(currentOutput.action_type === "topic_change" && {
                  type: "spring",
                  stiffness: 300,
                  damping: 15
                })
              }}
              className={`w-full max-w-3xl
                ${currentOutput.action_type === "topic_change"
                  ? "bg-gradient-to-br from-indigo-50 to-blue-100" // Special background for topic change
                  : "bg-white" // Default background
                }
                rounded-2xl shadow-xl my-4 md:my-6 relative border
                ${currentOutput.action_type === "topic_change"
                  ? "border-blue-300" // Special border for topic change
                  : themeStyles.borderColor // Default border
                }
                overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-between`}
            >
              <div className="flex flex-col justify-between h-full">
                {/* Add celebration icons for topic advancement */}
                {currentOutput.action_type === "topic_change" && (
                  <>
                    {/* Positioned Icons */}
                    <div className="absolute top-4 right-4 animate-pulse">
                      <span className="text-3xl">🎉</span>
                    </div>
                    <div className="absolute top-4 left-4 animate-pulse delay-100">
                      <span className="text-3xl">🌟</span>
                    </div>
                    <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                      <div className="flex space-x-2">
                        <span className="text-2xl animate-bounce">🎊</span>
                        <span className="text-2xl animate-bounce delay-150">🎯</span>
                        <span className="text-2xl animate-bounce delay-300">🎊</span>
                      </div>
                    </div>
                  </>
                )}

                {/* REARRANGED: Image at the top - Adjusted for 1024x1024 image size */}
                {currentOutput?.image_url && (
                  <div className="mb-6 flex justify-center pt-4">
                    <div className="relative h-[350px] md:h-[400px] w-full max-w-lg rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                      <img
                        key={imageKey} // Use key to force re-render if URL changes but component doesn't remount
                        src={currentOutput.image_url}
                        alt="Math visual"
                        className="w-full h-full object-contain"
                        // Fallback image on error
                        onError={(e) => { (e.target as HTMLImageElement).src = "/images/placeholder-math.png"; }}
                      />
                    </div>
                  </div>
                )}

                {/* Add special achievement badge for topic change */}
                {currentOutput.action_type === "topic_change" && (
                  <div className="mb-4 text-center">
                    <div className="inline-block bg-indigo-600 text-white px-4 py-1 rounded-full text-sm font-medium shadow-md">
                      Topic Mastered!
                    </div>
                  </div>
                )}

                {/* REARRANGED: Audio button in the middle - Centered with flex */}
                <div className="flex justify-center mb-4">
                  {currentOutput?.audio_url && currentOutput.audio_url.trim() !== '' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => playAudio(currentOutput.audio_url!)}
                      className="flex items-center bg-white/80 hover:bg-indigo-50"
                      disabled={isPlayingAudio}
                    >
                      <Volume2 className="h-4 w-4 mr-2 text-indigo-600" />
                      {isPlayingAudio ? "Playing..." : "Play Audio"}
                    </Button>
                  )}
                </div>

                {/* REARRANGED: Text content moved to the middle/bottom */}
                <div className="flex-grow text-center mb-4 overflow-y-auto">
                  {/* Main Text Content */}
                  <div className={`text-xl md:text-2xl font-bold ${currentOutput.action_type === "topic_change" ? "text-indigo-700" : themeStyles.primaryColor} mb-4 prose max-w-none`}>
                    <ReactMarkdown>{currentOutput?.text || ""}</ReactMarkdown>
                  </div>

                  {/* Add next topic preview for topic change */}
                  {currentOutput.action_type === "topic_change" && currentOutput.new_topic_title && (
                    <div className="mt-4 p-3 bg-white/80 rounded-lg border border-indigo-200 inline-block shadow-sm">
                      <p className="text-sm text-gray-500 mb-1">Next Topic:</p>
                      <p className="font-semibold text-indigo-800">{currentOutput.new_topic_title}</p>
                    </div>
                  )}
                </div>

                {/* Bottom Area - Input or Continue Button */}
                <div className="mt-auto pt-4 flex-shrink-0">
                  {/* Input Area */}
                  {showAnswerInput && (
                    <div className="mt-4">
                      {/* Display User Input */}
                      <div className="flex justify-center items-center mb-4">
                        <div
                          className={`flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[120px] md:min-w-[140px] h-[50px] md:h-[60px] border ${themeStyles.borderColor} shadow-sm cursor-text`}
                          onKeyDown={handleKeyPress} // Handle keyboard events if needed (e.g., Enter to submit)
                          tabIndex={0} // Make it focusable
                        >
                          <span className="text-2xl md:text-3xl font-bold text-indigo-900 tracking-wider">
                            {userAnswer || "_"}
                          </span>
                        </div>
                      </div>

                      {/* Number Pad */}
                      <div className="w-full max-w-[280px] md:max-w-[320px] mx-auto grid grid-cols-3 gap-2">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, "clear", 0, "backspace"].map((btn) => (
                          <Button
                            key={btn}
                            variant={btn === "clear" ? "destructive" : "outline"}
                            className={`h-12 text-lg font-medium transition-colors ${
                              btn === "clear"
                                ? "bg-red-100 border-red-300 text-red-700 hover:bg-red-200" // Adjusted clear button style
                                : "bg-white/80 backdrop-blur-sm border-indigo-100/60 hover:bg-indigo-50/90"
                            }`}
                            onClick={() => handleNumberInput(btn.toString())}
                          >
                            {btn === "backspace" ? "⌫" : btn === "clear" ? "Clear" : btn}
                          </Button>
                        ))}
                      </div>

                      {/* Submit Button */}
                      <div className="mt-6 flex justify-center">
                        <Button
                          size="lg"
                          onClick={handleSubmitAnswer}
                          className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                          disabled={!userAnswer.trim() || isLoading}
                        >
                          {isLoading ? (
                            <>
                              <Loader2 className="h-5 w-5 animate-spin mr-2" /> Processing...
                            </>
                          ) : (
                            <>
                              Check Answer <ArrowRightIcon className="ml-2 h-5 w-5" />
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Continue Button */}
                  {showContinueButton && (
                    <div className="mt-6 flex justify-center">
                      <Button
                        size="lg"
                        onClick={handleContinue}
                        className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <>
                            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading...
                          </>
                        ) : (
                          <>
                            Continue <ArrowRightIcon className="ml-2 h-5 w-5" />
                          </>
                        )}
                      </Button>
                    </div>
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