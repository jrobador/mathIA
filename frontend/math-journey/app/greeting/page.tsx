"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import { ArrowRightIcon } from "@radix-ui/react-icons"

export default function GreetingPage() {
  const router = useRouter()
  const [studentName, setStudentName] = useState("")
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [currentTextIndex, setCurrentTextIndex] = useState(0)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Get name from localStorage
  useEffect(() => {
    const name = localStorage.getItem("studentName") || "friend"
    setStudentName(name)
  }, [])

  // Auto-play audio when page loads
  useEffect(() => {
    if (studentName) {
      const timer = setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.play()
          setIsAudioPlaying(true)
        }
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [studentName])

  // Handle audio events and text animation
  useEffect(() => {
    const audio = audioRef.current
    
    const handleTimeUpdate = () => {
      if (audio) {
        // Divide the audio into sections for text animation
        const audioDuration = audio.duration
        const section = audioDuration / 3
        
        if (audio.currentTime < section) {
          setCurrentTextIndex(0)
        } else if (audio.currentTime < section * 2) {
          setCurrentTextIndex(1)
        } else {
          setCurrentTextIndex(2)
        }
      }
    }
    
    const handleEnded = () => {
      setIsAudioComplete(true)
      setIsAudioPlaying(false)
    }
    
    if (audio) {
      audio.addEventListener('timeupdate', handleTimeUpdate)
      audio.addEventListener('ended', handleEnded)
      return () => {
        audio.removeEventListener('timeupdate', handleTimeUpdate)
        audio.removeEventListener('ended', handleEnded)
      }
    }
  }, [])

  const handleContinue = () => {
    router.push("/diagnostic")
  }

  const handlePlayAudio = () => {
    if (audioRef.current) {
      // Reset text index when replaying
      setCurrentTextIndex(0)
      audioRef.current.currentTime = 0
      audioRef.current.play()
      setIsAudioPlaying(true)
    }
  }

  const greetingTexts = [`Hey there, ${studentName}!`, "I'm your math tutor.", "Are you ready to start?"]

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
      <audio ref={audioRef} src="/audios/greeting.mp3" preload="auto" />

      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/20 backdrop-blur-lg rounded-3xl p-8 border border-white/40 shadow-xl">
        <ProgressDots totalSteps={6} currentStep={3} />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-3xl aspect-video bg-white/30 backdrop-blur-md rounded-2xl shadow-xl overflow-hidden mb-8 relative border border-indigo-100"
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="text-center"
            >
              <div className="h-48 flex flex-col items-center justify-center">
                {greetingTexts.map((text, index) => (
                  <motion.h1
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{
                      opacity: currentTextIndex >= index ? 1 : 0,
                      y: currentTextIndex >= index ? 0 : 10,
                    }}
                    transition={{ duration: 0.5 }}
                    className="text-4xl md:text-5xl font-bold text-indigo-600 mb-4"
                  >
                    {text}
                  </motion.h1>
                ))}
              </div>
            </motion.div>
          </div>
        </motion.div>

        <AudioControls
          isPlaying={isAudioPlaying}
          onPlay={handlePlayAudio}
          audioText={`Hey there, ${studentName}! I'm your math tutor. Are you ready to start?`}
        />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isAudioComplete ? 1 : 0 }}
          transition={{ duration: 0.5 }}
          className="mt-8"
        >
          <Button
            size="lg"
            onClick={handleContinue}
            className="bg-indigo-600/80 hover:bg-indigo-700/90 text-white px-10 py-6 rounded-full text-xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-indigo-500/30 hover:shadow-xl border border-indigo-400/30"
          >
            Yes, I'm Ready! <ArrowRightIcon className="ml-2 h-5 w-5" />
          </Button>
        </motion.div>
      </div>
    </main>
  )
}