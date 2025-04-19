"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import { ArrowRightIcon } from "@radix-ui/react-icons"

export default function WelcomePage() {
  const router = useRouter()
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)

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

  const handleContinue = () => {
    router.push("/name")
  }

  const handlePlayAudio = () => {
    setIsAudioPlaying(true)
  }

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
        <ProgressDots totalSteps={6} currentStep={1} />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-3xl aspect-video bg-white/90 rounded-2xl shadow-xl overflow-hidden mb-8 relative border border-indigo-100"
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="text-center"
            >
              <h1 className="text-4xl md:text-5xl font-bold text-indigo-600 mb-4">Welcome to Math Journey!</h1>
              <p className="text-xl text-gray-600 max-w-md mx-auto">
                I'll be your personal math tutor on this adventure.
              </p>
            </motion.div>
          </div>
        </motion.div>

        <AudioControls
          isPlaying={isAudioPlaying}
          onPlay={handlePlayAudio}
          audioText="Welcome to Math Journey! I'll be your personal math tutor on this adventure. Let's explore the world of mathematics together!"
        />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="mt-8"
        >
          <Button
            size="lg"
            onClick={handleContinue}
            className="bg-indigo-600/80 hover:bg-indigo-700/90 text-white px-10 py-6 rounded-full text-xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-indigo-500/30 hover:shadow-xl border border-indigo-400/30"
            disabled={!isAudioComplete && !isAudioPlaying}
          >
            Continue <ArrowRightIcon className="ml-2 h-5 w-5" />
          </Button>
        </motion.div>
      </div>
    </main>
  )
}
