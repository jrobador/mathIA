"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { SparklesIcon } from "@heroicons/react/24/outline"

export default function ThemePage() {
  const router = useRouter()
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null)
  const [customThemeName, setCustomThemeName] = useState("")
  const [customThemeDescription, setCustomThemeDescription] = useState("")
  const [studentName, setStudentName] = useState("learner") // Initialize with default value
  const audioRef = useRef<HTMLAudioElement>(null)

  // Progress dots logic
  const diagnosticQuestionsCount = 6
  const stepsBeforeTheme = 4
  const currentStepNumber = stepsBeforeTheme + diagnosticQuestionsCount + 1
  const totalStepsEstimate = currentStepNumber + 1

  // Get student name from localStorage safely within useEffect
  useEffect(() => {
    const name = localStorage.getItem("studentName") || "learner"
    setStudentName(name)
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
      setIsAudioComplete(true)
      setIsAudioPlaying(false)
    }
    
    if (audio) {
      audio.addEventListener('ended', handleEnded)
      return () => {
        audio.removeEventListener('ended', handleEnded)
      }
    }
  }, [])

  // Handle selection of predefined themes
  const handleThemeSelect = (themeId: string) => { 
    setSelectedTheme(themeId)
    localStorage.setItem("learningTheme", themeId)
    setTimeout(() => router.push("/lesson"), 500)
  }

  // Handle saving the custom theme from the dialog
  const handleSaveCustomTheme = () => {
    const finalName = customThemeName.trim() || "My Custom Adventure"
    const finalDescription = customThemeDescription.trim() || "An exciting world to learn math!"

    console.log("Saving custom theme:", { name: finalName, description: finalDescription })

    // Set the main theme identifier to "custom"
    localStorage.setItem("learningTheme", "custom")
    // Store the custom name and description
    localStorage.setItem("customThemeName", finalName)
    localStorage.setItem("customThemeDescription", finalDescription)

    // Navigate to the lesson page
    setTimeout(() => {
      router.push("/lesson")
    }, 100)
  }

  const handlePlayAudio = () => { 
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.play()
      setIsAudioPlaying(true)
    }
  }

  // Theme data
  const themes = [
     { id: "magic", title: "Magical Math School", description: "Solve problems with spells, potions, and enchanted objects!", image: "/images/magic-school.png", alt: "A whimsical magic school castle with stars", },
     { id: "royalty", title: "Royal Kingdom", description: "Count jewels, plan royal feasts, and build castles!", image: "/images/royal-kingdom.png", alt: "A fairytale castle with flags and a sparkling crown", },
     { id: "heroes", title: "Superhero Adventure", description: "Use your math superpowers to help heroes save the city!", image: "/images/superhero-city.png", alt: "A vibrant city skyline with superhero silhouettes", },
  ]

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-indigo-50 to-white p-4 relative overflow-hidden">
      {/* Background image */}
      <div className="absolute inset-0 z-0"> 
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" /> 
        <img src="/images/learning-background.png" alt="Magical learning background" className="w-full h-full object-cover" /> 
      </div>

      {/* Audio element */}
      <audio ref={audioRef} src="/audios/theme.mp3" preload="auto" />

      {/* Container */}
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/45 rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">

        {/* Progress Dots */}
        <ProgressDots totalSteps={totalStepsEstimate} currentStep={currentStepNumber} />

        {/* Title */}
        <motion.h1 
          initial={{ opacity: 0, y: -20 }} 
          animate={{ opacity: 1, y: 0 }} 
          className="text-3xl md:text-4xl font-bold text-indigo-600 mb-6 text-center mt-4"
        >
          Choose Your Adventure!
        </motion.h1>

        {/* Theme Selection Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.5 }} 
          className="w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-4"
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
                  <Image 
                    src={theme.image} 
                    alt={theme.alt} 
                    fill 
                    className="object-cover" 
                    sizes="(max-width: 768px) 100vw, 300px" 
                  /> 
                </div>
                <div className="p-6"> 
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">{theme.title}</h3> 
                  <p className="text-gray-600">{theme.description}</p> 
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Section: Create Your Own (using Dialog) */}
        <motion.div 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          transition={{ delay: 0.8 }} 
          className="w-full flex flex-col items-center justify-center my-4"
        >

          {/* Dialog Trigger Button */}
          <Dialog>
            <DialogTrigger asChild>
              <Button 
                variant="outline" 
                size="lg" 
                className="mt-3 bg-white/80 hover:bg-white border-indigo-300 text-indigo-700 hover:text-indigo-800 shadow-sm hover:shadow-md transition-all"
              >
                <SparklesIcon className="h-5 w-5 mr-2 text-yellow-500" />
                Create Your Own Adventure!
              </Button>
            </DialogTrigger>

            {/* Dialog Content */}
            <DialogContent className="sm:max-w-[425px] bg-white">
              <DialogHeader>
                <DialogTitle>Create Your Custom Adventure</DialogTitle>
                <DialogDescription>
                  Tell us about the world you want to learn math in!
                </DialogDescription>
              </DialogHeader>
              {/* Form Content with Name and Description */}
              <div className="grid gap-4 py-4">
                {/* Name Input */}
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="theme-name" className="text-right">
                    Name
                  </Label>
                  <Input
                    id="theme-name"
                    value={customThemeName}
                    onChange={(e) => setCustomThemeName(e.target.value)}
                    placeholder="e.g., Dinosaur Jungle Quest"
                    className="col-span-3"
                  />
                </div>
                {/* Description Textarea */}
                <div className="grid grid-cols-4 items-start gap-4">
                  <Label htmlFor="theme-description" className="text-right pt-1">
                    Description
                  </Label>
                  <Textarea
                    id="theme-description"
                    value={customThemeDescription}
                    onChange={(e) => setCustomThemeDescription(e.target.value)}
                    placeholder="Describe your adventure! What characters or places are involved?"
                    className="col-span-3 min-h-[80px]"
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <DialogClose asChild>
                  <Button type="button" variant="secondary">Cancel</Button>
                </DialogClose>
                <Button
                  type="button"
                  onClick={handleSaveCustomTheme}
                  disabled={!customThemeName.trim()}
                >
                  Start This Adventure!
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </motion.div>

        {/* Audio Controls */}
        <div className="mt-auto pt-4">
          <AudioControls isPlaying={isAudioPlaying} onPlay={handlePlayAudio} audioText="Choose your learning adventure!" />
        </div>
      </div>
    </main>
  )
}