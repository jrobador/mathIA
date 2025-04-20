"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import AudioControls from "@/components/audio-controls"
import LessonVisual from "@/components/lesson-visual"
import { motion } from "framer-motion"
import { ArrowLeftIcon, ArrowRightIcon } from "@radix-ui/react-icons"

export default function LessonPage() {
  const [studentName, setStudentName] = useState("")
  const [learningPath, setLearningPath] = useState("")
  const [learningTheme, setLearningTheme] = useState("")
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)

  // Get stored preferences
  useEffect(() => {
    setStudentName(localStorage.getItem("studentName") || "friend")
    setLearningPath(localStorage.getItem("learningPath") || "addition")
    setLearningTheme(localStorage.getItem("learningTheme") || "space")
  }, [])

  // Auto-play audio when page loads
  useEffect(() => {
    if (learningPath && learningTheme) {
      const timer = setTimeout(() => {
        setIsAudioPlaying(true)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [learningPath, learningTheme])

  // Simulate audio playing and completion
  useEffect(() => {
    if (isAudioPlaying) {
      const timer = setTimeout(() => {
        setIsAudioPlaying(false)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [isAudioPlaying])

  // Update progress based on current step
  useEffect(() => {
    setProgress((currentStep / (lessonSteps.length - 1)) * 100)
  }, [currentStep])

  const handleNextStep = () => {
    if (currentStep < lessonSteps.length - 1) {
      setCurrentStep((prev) => prev + 1)
      setIsAudioPlaying(true)
    }
  }

  const handlePrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1)
      setIsAudioPlaying(true)
    }
  }

  const handlePlayAudio = () => {
    setIsAudioPlaying(true)
  }

  // Example lesson steps for addition
  const lessonSteps: {
    title: string
    visual: "concrete" | "pictorial" | "abstract" | "interactive"
    audioText: string
    visualData: {
      type: string
      values: number[]
      showCombined?: boolean
    }
  }[] = [
    {
      title: "Introduction to Addition",
      visual: "concrete",
      audioText: `Let's learn about addition, ${studentName}! Addition means combining groups of objects to find the total.`,
      visualData: {
        type: "blocks",
        values: [3, 2],
      },
    },
    {
      title: "Concrete Representation",
      visual: "concrete",
      audioText: "Here we have 3 blocks and 2 blocks. When we put them together, we get 5 blocks in total.",
      visualData: {
        type: "blocks",
        values: [3, 2],
        showCombined: true,
      },
    },
    {
      title: "Pictorial Representation",
      visual: "pictorial",
      audioText: "Now let's see this as a picture. 3 circles plus 2 circles equals 5 circles.",
      visualData: {
        type: "circles",
        values: [3, 2],
        showCombined: true,
      },
    },
    {
      title: "Abstract Representation",
      visual: "abstract",
      audioText: "Finally, we can write this as numbers: 3 + 2 = 5",
      visualData: {
        type: "equation",
        values: [3, 2],
      },
    },
    {
      title: "Let's Practice",
      visual: "interactive",
      audioText: "Now it's your turn to try! What is 4 + 3?",
      visualData: {
        type: "interactive",
        values: [4, 3],
      },
    },
  ]

  const currentLesson = lessonSteps[currentStep]

  return (
    <main className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
        <img
          src="/images/learning-background.png"
          alt="Magical learning background"
          className="w-full h-full object-cover"
        />
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-white/30 backdrop-blur-sm z-10">
        <div
          className="h-full bg-indigo-600 transition-all duration-500 ease-in-out"
          style={{ width: `${progress}%` }}
        ></div>
      </div>

      {/* Lesson title */}
      <div className="p-4 flex justify-between items-center z-10 bg-white/20 backdrop-blur-md border-b border-white/30">
        <h1 className="text-xl md:text-2xl font-bold text-white drop-shadow-md">{currentLesson.title}</h1>
        <div className="text-sm text-white/80">
          Step {currentStep + 1} of {lessonSteps.length}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-grow flex flex-col items-center justify-center p-4 z-10">
        {/* Visual area - takes up most of the screen */}
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-4xl aspect-video bg-white/90 rounded-2xl shadow-xl overflow-hidden mb-8 border border-white/40"
        >
          <LessonVisual visualType={currentLesson.visual} theme={learningTheme} data={currentLesson.visualData} />
        </motion.div>

        {/* Audio controls */}
        <div className="w-full max-w-2xl">
          <AudioControls isPlaying={isAudioPlaying} onPlay={handlePlayAudio} audioText={currentLesson.audioText} />
        </div>
      </div>

      {/* Navigation buttons */}
      <div className="p-6 flex justify-between z-10 bg-white/20 backdrop-blur-md border-t border-white/30">
        <Button
          variant="outline"
          size="lg"
          onClick={handlePrevStep}
          disabled={currentStep === 0}
          className="px-6 bg-white/50 backdrop-blur-sm border-white/60 text-indigo-900 hover:bg-white/70"
        >
          <ArrowLeftIcon className="mr-2 h-4 w-4" /> Previous
        </Button>

        <Button
          size="lg"
          onClick={handleNextStep}
          disabled={currentStep === lessonSteps.length - 1}
          className="bg-indigo-600/80 hover:bg-indigo-700/90 px-6 text-white shadow-lg transition-all duration-300 hover:shadow-indigo-500/30 hover:shadow-xl border border-indigo-400/30"
        >
          Next <ArrowRightIcon className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </main>
  )
}
