"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"
import { motion } from "framer-motion"
import { ArrowRightIcon } from "@radix-ui/react-icons"
import { useTutor } from "@/contexts/TutorProvider"
import { EvaluationResult } from "@/types/api"
import AudioControls from "@/components/audio-controls"
import AudioPlayer from "@/components/audio-player" // Import the actual audio player
import { Volume2 } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import Image from "next/image" // Use Next.js Image for better image handling

export default function LessonPage() {
  const router = useRouter()
  
  // Use the TutorContext
  const {
    sessionId,
    currentOutput,
    isLoading: isTutorLoading,
    masteryLevel,
    startSession,
    sendMessage,
  } = useTutor()

  // Local state
  const [studentName, setStudentName] = useState("")
  const [learningPath, setLearningPath] = useState("")
  const [learningTheme, setLearningTheme] = useState("")
  const [userAnswer, setUserAnswer] = useState("")
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [audioKey, setAudioKey] = useState(Date.now()) // Force audio component re-render
  const [imageKey, setImageKey] = useState(Date.now()) // Force image component re-render

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const imageRef = useRef<HTMLDivElement | null>(null);
  
  // BUGFIX: Add tracking refs to prevent duplicate session starts
  const sessionStartAttemptedRef = useRef(false)
  const userInfoLoadedRef = useRef(false)

  // Add debug logs for content
  useEffect(() => {
    if (currentOutput) {
      console.log("Content details:", {
        text: currentOutput.text?.substring(0, 50) + "...",
        hasImage: !!currentOutput.image_url,
        imageUrl: currentOutput.image_url,
        hasAudio: !!currentOutput.audio_url,
        audioUrl: currentOutput.audio_url,
      });
      
      // Reset keys to force component remounting when URLs change
      if (currentOutput.audio_url) setAudioKey(Date.now());
      if (currentOutput.image_url) setImageKey(Date.now());
    }
  }, [currentOutput]);

  // Get user info from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined' && !userInfoLoadedRef.current) {
      userInfoLoadedRef.current = true; // Mark info as loaded to prevent reloading
      
      setStudentName(localStorage.getItem("studentName") || "learner")
      setLearningPath(localStorage.getItem("learningPath") || "addition")
      setLearningTheme(localStorage.getItem("learningTheme") || "space")
    }
  }, [])

  // Start a session automatically if needed
  useEffect(() => {
    const startTutorSession = async () => {
      // BUGFIX: Check if a start attempt has already been made
      if (sessionStartAttemptedRef.current) {
        console.log("Session start already attempted, skipping");
        return;
      }
      
      // BUGFIX: Check if session is already active or loading
      if (sessionId || isTutorLoading) {
        console.log("Session already active or loading, skipping auto-start");
        return;
      }
      
      // BUGFIX: Check if we have the necessary info to start
      if (!learningPath || !studentName) {
        console.log("Missing required info for session start");
        return;
      }
      
      // Mark that we've attempted to start a session
      sessionStartAttemptedRef.current = true;
      console.log("Attempting to start tutor session from LessonPage");
      
      try {
        const diagnosticResultsJson = localStorage.getItem("diagnosticResults")
        const diagnosticResults = diagnosticResultsJson ? JSON.parse(diagnosticResultsJson) : null

        await startSession({
          theme: learningTheme,
          learningPath: learningPath,
          initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`,
          diagnosticResults: diagnosticResults?.question_results
        });
        
        console.log("Session started successfully from LessonPage");
      } catch (error) {
        console.error("Auto-start session failed:", error)
        toast("Failed to start the learning session. Please try refreshing.", { duration: 5000 })
        
        // Reset the flag if we failed, so we can try again if needed
        setTimeout(() => {
          sessionStartAttemptedRef.current = false;
        }, 5000);
      }
    };
    
    // Only run this effect once when component mounts and data is ready
    if (!sessionStartAttemptedRef.current && !sessionId && !isTutorLoading && learningPath && studentName) {
      startTutorSession();
    }
  }, [sessionId, isTutorLoading, startSession, learningPath, learningTheme, studentName]);

  // Handle submitting an answer
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim()) return
    
    setIsLoading(true)
    
    try {
      // Send the student's answer to the backend
      await sendMessage(userAnswer)
      
      // Clear the input field after sending
      setUserAnswer("")
    } catch (error) {
      console.error("Error sending answer:", error)
      toast("Failed to send your answer. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  // Handle number input for answer field
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

  // Manual audio play function for debugging
  const playAudioManually = () => {
    if (audioRef.current) {
      audioRef.current.play().catch(err => console.error("Error playing audio:", err));
    }
  };

  // Progress calculation (0-100)
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
      case "royalty":
        return {
          primaryColor: "text-blue-700",
          bgGradient: "from-blue-50 to-indigo-100",
          accentColor: "bg-blue-600",
          buttonColor: "bg-blue-600 hover:bg-blue-700",
          borderColor: "border-blue-200"
        }
      case "heroes":
        return {
          primaryColor: "text-red-600",
          bgGradient: "from-red-50 to-orange-100",
          accentColor: "bg-red-600",
          buttonColor: "bg-red-600 hover:bg-red-700",
          borderColor: "border-red-200"
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
        <motion.div
          key={currentOutput?.evaluation ? 'evaluation' : 'content'}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
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
              <div className="text-base md:text-lg text-gray-800 mb-3">
                {/* BUGFIX: Use markdown renderer or text cleaning */}
                <ReactMarkdown>{currentOutput.text || ""}</ReactMarkdown>
              </div>
            </div>
          ) : (
            // Standard content view - shows content and input when needed
            <div className="flex flex-col justify-between h-full">
              {/* Top part: Content from backend */}
              <div className="text-center">
                {/* BUGFIX: Use markdown renderer for text content */}
                <div className={`text-xl md:text-2xl font-bold ${themeStyles.primaryColor} mb-4`}>
                  <ReactMarkdown>
                    {currentOutput?.text || "Loading your math lesson..."}
                  </ReactMarkdown>
                </div>
                
                {/* Visual element (if provided by backend) - IMPROVED VERSION */}
                {currentOutput?.image_url && (
                  <div className="mb-6 flex justify-center">
                    <div className="relative h-[200px] w-full max-w-md rounded-lg overflow-hidden border border-gray-200">
                      {/* Use the imageKey to force remounting when URL changes */}
                      <div key={imageKey} className="w-full h-full relative" ref={imageRef}>
                        <img 
                          src={currentOutput.image_url} 
                          alt="Math visual"
                          className="w-full h-full object-contain" 
                          onError={(e) => console.error("Image failed to load:", e)}
                        />
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Direct audio element for debugging */}
                {currentOutput?.audio_url && (
                  <div className="mb-4">
                    <audio 
                      ref={audioRef}
                      controls
                      src={currentOutput.audio_url}
                      className="w-full"
                      onError={(e) => console.error("Audio failed to load:", e)}
                    />
                    <button 
                      onClick={playAudioManually}
                      className="mt-2 px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm"
                    >
                      Play Audio Manually
                    </button>
                  </div>
                )}
              </div>
              
              {/* Only show input when backend requests an answer */}
              {currentOutput?.prompt_for_answer && (
                <div className="mt-4">
                  <div className="flex justify-center items-center mb-4">
                    <div className={`flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[120px] md:min-w-[140px] h-[50px] md:h-[60px] border ${themeStyles.borderColor} shadow-sm`}>
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
                      Check Answer <ArrowRightIcon className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Audio Player - REPLACED WITH SIMPLER AUDIO ELEMENT ABOVE */}
        {/* Keeping the old code here for reference
        {currentOutput?.audio_url && (
          <div className="w-full max-w-md my-4">
            <div className="mb-2 flex items-center gap-2">
              <Volume2 className="h-4 w-4 text-indigo-600" />
              <span className="text-sm text-indigo-700">Audio explanation</span>
            </div>
            <AudioPlayer
              key={audioKey}
              audioUrl={currentOutput.audio_url}
              autoPlay={false}
              onPlaybackComplete={() => setIsAudioPlaying(false)}
            />
          </div>
        )}
        */}
      </div>
    </main>
  )
}