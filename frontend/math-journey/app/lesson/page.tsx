"use client"

import { useEffect, useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"
import { motion, AnimatePresence } from "framer-motion"
import { ArrowRightIcon } from "@radix-ui/react-icons"
import { useTutor } from "@/contexts/TutorProvider"
import { EvaluationResult } from "@/types/api"
import ReactMarkdown from 'react-markdown'
import { Volume2, Loader2, RefreshCw, AlertCircle } from "lucide-react"

export default function LessonPage() {
  
  // Use the TutorContext
  const {
    sessionId,
    currentOutput,
    isLoading: isTutorLoading,
    masteryLevel,
    startSession,
    sendMessage,
    error: tutorError,
  } = useTutor()

  // Local state
  const [studentName, setStudentName] = useState("")
  const [learningPath, setLearningPath] = useState("")
  const [learningTheme, setLearningTheme] = useState("")
  const [userAnswer, setUserAnswer] = useState("")
  const [isLocalLoading, setIsLocalLoading] = useState(false)
  const [errorState, setErrorState] = useState<{isError: boolean, message: string}>({
    isError: false,
    message: ""
  })
  const [audioKey, setAudioKey] = useState(Date.now())
  const [imageKey, setImageKey] = useState(Date.now())

  // References
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const sessionStartAttemptedRef = useRef(false)
  const userInfoLoadedRef = useRef(false)
  const answerSubmitInProgressRef = useRef(false)
  
  // Load user info from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined' && !userInfoLoadedRef.current) {
      userInfoLoadedRef.current = true
      
      setStudentName(localStorage.getItem("studentName") || "learner")
      setLearningPath(localStorage.getItem("learningPath") || "addition")
      setLearningTheme(localStorage.getItem("learningTheme") || "space")
    }
  }, [])

  // Handle tutor error state changes
  useEffect(() => {
    if (tutorError) {
      console.error("Tutor error:", tutorError)
      setErrorState({
        isError: true,
        message: tutorError.message || "An error occurred with the tutoring session."
      })
    }
  }, [tutorError])

  // Auto start session when component mounts
  useEffect(() => {
    const initializeSession = async () => {
      if (sessionStartAttemptedRef.current || sessionId || isTutorLoading) {
        return
      }

      if (!learningPath || !studentName) {
        console.log("Waiting for user info to load before starting session")
        return
      }

      try {
        sessionStartAttemptedRef.current = true
        setIsLocalLoading(true)
        console.log("Starting new tutoring session...")

        const diagnosticResultsJson = localStorage.getItem("diagnosticResults")
        const diagnosticResults = diagnosticResultsJson ? JSON.parse(diagnosticResultsJson) : null

        await startSession({
          theme: learningTheme,
          learningPath: learningPath,
          initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`,
          diagnosticResults: diagnosticResults?.question_results
        })

        console.log("Session started successfully")
      } catch (error) {
        console.error("Failed to start session:", error)
        setErrorState({
          isError: true,
          message: "Failed to start the learning session. Please try refreshing."
        })
        toast("Failed to start the learning session")
        
        // Reset flag to allow trying again
        setTimeout(() => {
          sessionStartAttemptedRef.current = false
        }, 5000)
      } finally {
        setIsLocalLoading(false)
      }
    }

    initializeSession()
  }, [sessionId, isTutorLoading, startSession, learningPath, learningTheme, studentName])

  // Reset keys when content changes to force re-rendering components
  useEffect(() => {
    if (currentOutput) {
      console.log("New content received:", {
        hasText: !!currentOutput.text,
        hasImage: !!currentOutput.image_url,
        hasAudio: !!currentOutput.audio_url,
        promptForAnswer: currentOutput.prompt_for_answer,
        evaluation: currentOutput.evaluation,
      })

      // Force remounting of audio and image components
      if (currentOutput.audio_url) setAudioKey(Date.now())
      if (currentOutput.image_url) setImageKey(Date.now())
      
      // Clear error state if we get valid content
      if (errorState.isError) {
        setErrorState({ isError: false, message: "" })
      }
    }
  }, [currentOutput, errorState.isError])

  // Handle submitting an answer
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim() || answerSubmitInProgressRef.current) {
      return
    }
    
    try {
      answerSubmitInProgressRef.current = true
      setIsLocalLoading(true)
      console.log("Submitting answer:", userAnswer)
      
      // Send the user's answer to the backend
      await sendMessage(userAnswer)
      
      // Clear the input field after successful submission
      setUserAnswer("")
    } catch (error) {
      console.error("Error submitting answer:", error)
      setErrorState({
        isError: true,
        message: "Failed to send your answer. Please try again."
      })
      toast("Failed to send your answer")
    } finally {
      setIsLocalLoading(false)
      answerSubmitInProgressRef.current = false
    }
  }

  // Handle key press for submitting with enter
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && userAnswer.trim() && !isLocalLoading && !isTutorLoading) {
      handleSubmitAnswer()
    }
  }

  // Handle input for the number pad
  const handleNumberInput = (input: string) => {
    if (input === "clear") {
      setUserAnswer("")
    } else if (input === "backspace") {
      setUserAnswer(prev => prev.slice(0, -1))
    } else {
      // Limit input length
      if (userAnswer.length < 10) {
        setUserAnswer(prev => prev + input)
      }
    }
  }

  // Play audio function
  const playAudio = () => {
    if (audioRef.current) {
      audioRef.current.play().catch(err => console.error("Error playing audio:", err))
    }
  }

  // Handle refresh
  const handleRefresh = () => {
    sessionStartAttemptedRef.current = false
    answerSubmitInProgressRef.current = false
    setErrorState({ isError: false, message: "" })
    
    // Either refresh the page or restart the session
    window.location.reload()
  }

  // Progress calculation
  const progress = Math.round((masteryLevel || 0) * 100)

  // Theme-based styling
  const getThemeStyles = () => {
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
      default:
        return {
          primaryColor: "text-indigo-700",
          bgGradient: "from-indigo-50 to-white",
          accentColor: "bg-indigo-600",
          buttonColor: "bg-indigo-600 hover:bg-indigo-700",
          borderColor: "border-indigo-200"
        }
    }
  }

  const themeStyles = getThemeStyles()

  // Determine if we're in a loading state
  const isLoading = isLocalLoading || isTutorLoading
  
  return (
    <main className={`min-h-screen flex flex-col items-center justify-center bg-gradient-to-b ${themeStyles.bgGradient} p-4 relative overflow-hidden`}>
      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
        <img
          src="/images/learning-background.png"
          alt="Magical learning background"
          className="w-full h-full object-cover"
        />
      </div>

      {/* Main container */}
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">
        {/* Header navigation */}
        <div className="w-full flex justify-between items-center mb-4">
          <div className={`text-sm ${themeStyles.primaryColor}`}>
            {learningPath && learningPath.charAt(0).toUpperCase() + learningPath.slice(1)} Journey
          </div>
        </div>

        {/* Progress indicator */}
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
              <p className="text-lg text-gray-600 mb-2">Setting up your math lesson...</p>
              <p className="text-sm text-gray-500">This might take a moment if images are being generated.</p>
            </motion.div>
          )}

          {/* Error State */}
          {errorState.isError && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-3xl bg-red-50 rounded-2xl shadow-xl my-4 md:my-6 relative border border-red-200 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center items-center"
            >
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
              key={currentOutput?.evaluation ? 'evaluation' : 'content'}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
              className={`w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border ${themeStyles.borderColor} overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-between`}
            >
              {currentOutput?.evaluation ? (
                // Evaluation view - when the backend has evaluated an answer
                <div className="flex flex-col justify-center items-center h-full text-center">
                  <h1 className={`text-2xl md:text-3xl font-bold ${
                    currentOutput.evaluation === EvaluationResult.CORRECT ? "text-green-700" : "text-orange-700"
                  } mb-3`}>
                    {currentOutput.evaluation === EvaluationResult.CORRECT ? "Great job!" : "Not quite right"}
                  </h1>
                  <div className="text-base md:text-lg text-gray-800 mb-3 max-w-lg">
                    <ReactMarkdown>{currentOutput.text || ""}</ReactMarkdown>
                  </div>
                </div>
              ) : (
                // Standard content view - shows content and input when needed
                <div className="flex flex-col justify-between h-full">
                  {/* Top part: Content from backend */}
                  <div className="text-center">
                    <div className={`text-xl md:text-2xl font-bold ${themeStyles.primaryColor} mb-4`}>
                      <ReactMarkdown>{currentOutput?.text || "Loading your math lesson..."}</ReactMarkdown>
                    </div>
                    
                    {/* Visual element */}
                    {currentOutput?.image_url && (
                      <div className="mb-6 flex justify-center">
                        <div className="relative h-[200px] w-full max-w-md rounded-lg overflow-hidden border border-gray-200">
                          <div key={imageKey} className="w-full h-full relative">
                            <img 
                              src={currentOutput.image_url} 
                              alt="Math visual"
                              className="w-full h-full object-contain" 
                              onError={(e) => {
                                console.error("Image failed to load:", e);
                                (e.target as HTMLImageElement).src = "/images/placeholder-math.png";
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Audio element */}
                    {currentOutput?.audio_url && (
                      <div className="mb-4">
                        <audio 
                          key={audioKey}
                          ref={audioRef}
                          src={currentOutput.audio_url}
                          className="hidden"
                          onError={(e) => console.error("Audio failed to load:", e)}
                        />
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={playAudio}
                          className="flex items-center bg-white/80 hover:bg-indigo-50"
                        >
                          <Volume2 className="h-4 w-4 mr-2 text-indigo-600" />
                          Play Audio Explanation
                        </Button>
                      </div>
                    )}
                  </div>
                  
                  {/* Only show input when backend requests an answer */}
                  {currentOutput?.prompt_for_answer && (
                    <div className="mt-4">
                      <div className="flex justify-center items-center mb-4">
                        <div 
                          className={`flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[120px] md:min-w-[140px] h-[50px] md:h-[60px] border ${themeStyles.borderColor} shadow-sm`}
                          onKeyDown={handleKeyPress}
                          tabIndex={0}
                        >
                          <span className="text-2xl md:text-3xl font-bold text-indigo-900">{userAnswer || "_"}</span>
                        </div>
                      </div>
                      
                      {/* Number pad */}
                      <div className="w-full max-w-[280px] md:max-w-[320px] mx-auto grid grid-cols-3 gap-2">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, "clear", 0, "backspace"].map((btn) => (
                          <Button
                            key={btn}
                            variant={btn === "clear" ? "destructive" : "outline"}
                            className={`h-12 text-lg font-medium ${
                              btn === "clear"
                                ? "bg-red-500/80 hover:bg-red-600/90 border border-red-400/30"
                                : "bg-white/80 backdrop-blur-sm border-indigo-100/60 hover:bg-indigo-50/90"
                            }`}
                            onClick={() => handleNumberInput(btn.toString())}
                            disabled={isLoading}
                          >
                            {btn === "backspace" ? "⌫" : btn === "clear" ? "Clear" : btn}
                          </Button>
                        ))}
                      </div>
                      
                      {/* Submit button */}
                      <div className="mt-6 flex justify-center">
                        <Button
                          size="lg"
                          onClick={handleSubmitAnswer}
                          className={`${themeStyles.buttonColor} text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl border border-indigo-400/30`}
                          disabled={!userAnswer.trim() || isLoading}
                        >
                          {isLoading ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin mr-2" />
                              Processing...
                            </>
                          ) : (
                            <>
                              Check Answer <ArrowRightIcon className="ml-2 h-4 w-4" />
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}