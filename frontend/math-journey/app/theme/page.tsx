"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import Image from "next/image"
import { Button } from "@/components/ui/button" // Import Button if you want a button style
import { SparklesIcon } from "@heroicons/react/24/outline" // Example icon (install @heroicons/react)

export default function ThemePage() {
  const router = useRouter()
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null)

  // Determine current step for progress dots (adjust as needed)
  const diagnosticQuestionsCount = 6 // Assuming 6 questions
  const stepsBeforeTheme = 4 // Greeting(1) + Name(1) + Ready(1) + Diagnostic Intro(1)
  const currentStepNumber = stepsBeforeTheme + diagnosticQuestionsCount + 1
  const totalStepsEstimate = currentStepNumber + 2 // +1 for custom create page, +1 for lesson(s)

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
      }, 6000) // Increased duration slightly for longer prompt
      return () => clearTimeout(timer)
    }
  }, [isAudioPlaying])

  const handleThemeSelect = (themeId: string) => {
    setSelectedTheme(themeId)
    localStorage.setItem("learningTheme", themeId)
    setTimeout(() => {
      router.push("/lesson") // Navigate to the lesson page
    }, 500)
  }

  // *** NEW: Handler for creating own theme ***
  const handleCreateOwn = () => {
    setSelectedTheme("custom") // Indicate custom selection visually if needed
    localStorage.setItem("learningTheme", "custom") // Mark theme as custom
    console.log("Navigating to create custom theme...")
    // Navigate to a dedicated page for custom theme creation, or directly to lesson
    // For now, let's assume navigation to a setup page, or adjust as needed.
    setTimeout(() => {
       router.push("/create-theme") // Example route - adjust this
    }, 300)
  }

  const handlePlayAudio = () => {
    setIsAudioPlaying(true)
  }

  // Themes data (same as before)
  const themes = [
    {
      id: "magic",
      title: "Magical Math School",
      description: "Solve problems with spells, potions, and enchanted objects!",
      image: "/images/magic-school.png",
      alt: "A whimsical magic school castle with stars",
    },
    {
      id: "royalty",
      title: "Royal Kingdom",
      description: "Count jewels, plan royal feasts, and build castles!",
      image: "/images/royal-kingdom.png",
      alt: "A fairytale castle with flags and a sparkling crown",
    },
    {
      id: "heroes",
      title: "Superhero Adventure",
      description: "Use your math superpowers to help heroes save the city!",
      image: "/images/superhero-city.png",
      alt: "A vibrant city skyline with superhero silhouettes",
    },
  ]

  // *** UPDATED AUDIO TEXT ***
  const audioPrompt = `Choose your learning adventure, ${localStorage.getItem("studentName") || "learner"}! Pick a Magical School, Royal Kingdom, or Superhero Adventure. Or, create your very own!`;

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

      {/* Container */}
      <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-violet-200/80 rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">

        {/* Progress Dots */}
        <ProgressDots
            totalSteps={totalStepsEstimate}
            currentStep={currentStepNumber}
        />

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
          // Reduced bottom margin to make space for the new section
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

        {/* *** NEW SECTION: Create Your Own *** */}
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }} // Delay slightly after cards appear
            className="w-full flex flex-col items-center justify-center my-4" // Added margin top/bottom
        >
            {/* Separator Text */}
            <div className="relative w-full max-w-sm flex justify-center items-center my-2">
                 <div className="absolute inset-0 flex items-center" aria-hidden="true">
                     <div className="w-full border-t border-indigo-300/60"></div>
                 </div>
                 <div className="relative bg-violet-200/80 px-3 text-sm font-medium text-indigo-700">
                     OR
                 </div>
            </div>

            {/* Button/Link to Create Own */}
            {/* Option 1: Using ShadCN Button */}
             <Button
                variant="outline" // Or choose another variant
                size="lg"
                className="mt-3 bg-white/80 hover:bg-white border-indigo-300 text-indigo-700 hover:text-indigo-800 shadow-sm hover:shadow-md transition-all"
                onClick={handleCreateOwn}
            >
                 <SparklesIcon className="h-5 w-5 mr-2 text-yellow-500" /> {/* Example icon */}
                 Create Your Own Adventure!
             </Button>

             {/* Option 2: Simple Clickable Div (if Button component is not available/desired)
             <div
                className="mt-3 cursor-pointer inline-flex items-center px-6 py-3 border border-indigo-300 rounded-full shadow-sm text-base font-medium text-indigo-700 bg-white/80 hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all"
                onClick={handleCreateOwn}
                role="button" // Accessibility
                tabIndex={0} // Accessibility
            >
                <SparklesIcon className="h-5 w-5 mr-2 text-yellow-500" />
                Create Your Own Adventure!
            </div>
            */}
        </motion.div>
        {/* *** END OF NEW SECTION *** */}


        {/* Audio Controls - Positioned at the bottom */}
        <div className="mt-auto pt-4"> {/* Pushes audio controls down */}
            <AudioControls
              isPlaying={isAudioPlaying}
              onPlay={handlePlayAudio}
              audioText={audioPrompt} // Use the updated audio prompt
            />
        </div>
      </div>
    </main>
  )
}