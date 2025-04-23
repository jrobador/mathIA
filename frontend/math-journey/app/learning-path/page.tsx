"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import { useMathTutor } from "@/hooks/use-math-tutor"
import { toast } from "sonner"

export default function LearningPathPage() {
  const router = useRouter()
  const { startSession } = useMathTutor()

  // States
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [studentName, setStudentName] = useState("")
  const [studentLevel, setStudentLevel] = useState("")
  const audioRef = useRef<HTMLAudioElement>(null)

  // Get diagnostic data from localStorage to use with API later
  useEffect(() => {
    setStudentName(localStorage.getItem("studentName") || "friend")
    setStudentLevel(localStorage.getItem("studentLevel") || "beginner")
  }, [])

  // Auto-play audio when page loads
  useEffect(() => {
    const timer = setTimeout(() => {
      if (audioRef.current) {
        audioRef.current.play()
        setIsAudioPlaying(true)
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  // Handle audio events
  useEffect(() => {
    const audio = audioRef.current
    
    const handleEnded = () => {
      // Instead of using isAudioComplete state, we could just set playing to false
      // setIsAudioComplete(true)
      setIsAudioPlaying(false)
    }
    
    if (audio) {
      audio.addEventListener('ended', handleEnded)
      return () => {
        audio.removeEventListener('ended', handleEnded)
      }
    }
  }, [])

  const handlePathSelect = async (path: string) => {
    setSelectedPath(path)
  
    // Store selected path
    localStorage.setItem("learningPath", path)
  
    try {
      // Pre-initialize session with diagnostic results
      const diagnosticResultsJson = localStorage.getItem("diagnosticResults")
      let diagnosticResults = null
      
      // Parse diagnostic results if available
      if (diagnosticResultsJson) {
        try {
          const parsedResults = JSON.parse(diagnosticResultsJson)
          // Only extract the question_results array which contains what the API expects
          diagnosticResults = parsedResults.question_results || null
          console.log("Using diagnostic results:", diagnosticResults)
        } catch (e) {
          console.error("Error parsing diagnostic results:", e)
          // Continue without diagnostic results
        }
      }
  
      // Start session in background while navigating
      // Use the correct property names that match the StartSessionOptions interface
      startSession({
        learning_path: path,
        diagnostic_results: diagnosticResults,
        // Remove initialMessage or initial_message if it's not in the interface
      }).catch((error: unknown) => {
        console.error("Error starting session:", error)
        // No need to show toast here, since we're navigating away
      })
  
      // Navigate to theme selection
      router.push("/theme")
    } catch (error) {
      console.error("Error selecting path:", error)
      toast("Couldn't start the session. Please try again.")
    }
  }

  const handlePlayAudio = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.play()
      setIsAudioPlaying(true)
    }
  }

  const learningPaths = [
    {
      id: "addition",
      title: "Addition",
      description: "Learn to combine numbers",
      color: "from-blue-500 to-blue-600",
      icon: "+",
    },
    {
      id: "subtraction",
      title: "Subtraction",
      description: "Learn to take away numbers",
      color: "from-green-500 to-green-600",
      icon: "-",
    },
    {
      id: "multiplication",
      title: "Multiplication",
      description: "Learn to multiply numbers",
      color: "from-purple-500 to-purple-600",
      icon: "×",
    },
    {
      id: "fractions",
      title: "Fractions",
      description: "Learn about parts of a whole",
      color: "from-yellow-500 to-yellow-600",
      icon: "½",
    },
  ]

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-indigo-50 to-white p-4 relative overflow-hidden">
      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
        <img
          src="/images/learning-background.png"
          alt="Magical learning background"
          className="w-full h-full object-cover"
        />
      </div>

      {/* Audio element */}
      <audio ref={audioRef} src="/audios/learning_path.mp3" preload="auto" />

      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/45 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">
        <ProgressDots totalSteps={6} currentStep={5} />

        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl md:text-4xl font-bold text-indigo-600 mb-6 text-center"
        >
          What would you like to learn today, {studentName}?
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-lg text-gray-700 mb-8 text-center"
        >
          {studentLevel === "advanced" ? 
            "Based on your diagnostic, you're ready for advanced concepts!" :
            studentLevel === "intermediate" ?
            "Your diagnostic shows you have a good foundation to build on." :
            "Let's build your math skills starting with the fundamentals!"}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          {learningPaths.map((path, index) => (
            <motion.div
              key={path.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.1, duration: 0.5 }}
              className={`cursor-pointer transform transition-all duration-200 ${
                selectedPath === path.id ? "scale-105 ring-4 ring-indigo-300" : "hover:scale-105"
              }`}
              onClick={() => handlePathSelect(path.id)}
            >
              <div className="bg-white/90 rounded-2xl shadow-xl overflow-hidden h-full border border-indigo-100">
                <div className={`h-24 bg-gradient-to-r ${path.color} flex items-center justify-center`}>
                  <span className="text-6xl font-bold text-white">{path.icon}</span>
                </div>
                <div className="p-6">
                  <h3 className="text-xl font-bold text-gray-800 mb-2">{path.title}</h3>
                  <p className="text-gray-600">{path.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <AudioControls
          isPlaying={isAudioPlaying}
          onPlay={handlePlayAudio}
          audioText={`What would you like to learn today, ${studentName}?`}
        />
      </div>
    </main>
  )
}