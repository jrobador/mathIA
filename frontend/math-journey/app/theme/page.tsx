"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import Image from "next/image"

export default function ThemePage() {
  const router = useRouter()
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null)

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

  const handleThemeSelect = (theme: string) => {
    setSelectedTheme(theme)
    // Store selected theme
    localStorage.setItem("learningTheme", theme)

    // Navigate to lesson experience after a brief delay
    setTimeout(() => {
      router.push("/lesson")
    }, 500)
  }

  const handlePlayAudio = () => {
    setIsAudioPlaying(true)
  }

  const themes = [
    {
      id: "space",
      title: "Space Adventure",
      description: "Learn math with planets and stars",
      image: "/placeholder.svg?height=200&width=300",
    },
    {
      id: "animals",
      title: "Animal Kingdom",
      description: "Count and calculate with cute animals",
      image: "/placeholder.svg?height=200&width=300",
    },
    {
      id: "sports",
      title: "Sports Champions",
      description: "Score points with math and sports",
      image: "/placeholder.svg?height=200&width=300",
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
        <ProgressDots totalSteps={6} currentStep={6} />

        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl md:text-4xl font-bold text-indigo-600 mb-6 text-center"
        >
          Choose your learning theme
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
        >
          {themes.map((theme, index) => (
            <motion.div
              key={theme.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + index * 0.1, duration: 0.5 }}
              className={`cursor-pointer transform transition-all duration-200 ${
                selectedTheme === theme.id ? "scale-105 ring-4 ring-indigo-300" : "hover:scale-105"
              }`}
              onClick={() => handleThemeSelect(theme.id)}
            >
              <div className="bg-white/90 rounded-2xl shadow-xl overflow-hidden h-full border border-indigo-100">
                <div className="relative h-40 w-full">
                  <Image src={theme.image || "/placeholder.svg"} alt={theme.title} fill className="object-cover" />
                </div>
                <div className="p-6">
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">{theme.title}</h3>
                  <p className="text-gray-600">{theme.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <AudioControls
          isPlaying={isAudioPlaying}
          onPlay={handlePlayAudio}
          audioText="Would you like to learn with space, animals, or sports examples? Choose a theme that excites you!"
        />
      </div>
    </main>
  )
}
