"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"

export default function LearningPathPage() {
  const router = useRouter()
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)

  // Auto-play audio when page loads
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsAudioPlaying(true)
    }, 500)
    return () => clearTimeout(timer)
  }, [])

  // Simulate audio playing and completion
  useEffect(() => {
    if (isAudioPlaying) {
      const timer = setTimeout(() => {
        setIsAudioComplete(true)
        setIsAudioPlaying(false)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isAudioPlaying])

  const handlePathSelect = (path: string) => {
    setSelectedPath(path)
    // Store selected path
    localStorage.setItem("learningPath", path)

    // Navigate to theme selection after a brief delay
    setTimeout(() => {
      router.push("/theme")
    }, 500)
  }

  const handlePlayAudio = () => {
    setIsAudioPlaying(true)
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

      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/20 backdrop-blur-lg rounded-3xl p-8 border border-white/40 shadow-xl">
        <ProgressDots totalSteps={6} currentStep={5} />

        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl md:text-4xl font-bold text-indigo-600 mb-6 text-center"
        >
          What would you like to learn today?
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
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
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">{path.title}</h3>
                  <p className="text-gray-600">{path.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <AudioControls
          isPlaying={isAudioPlaying}
          onPlay={handlePlayAudio}
          audioText="What would you like to learn today? Choose a math topic that interests you."
        />
      </div>
    </main>
  )
}
