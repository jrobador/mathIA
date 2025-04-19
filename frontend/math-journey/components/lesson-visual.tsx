"use client"

import { useState } from "react"
import { motion } from "framer-motion"

interface LessonVisualProps {
  visualType: "concrete" | "pictorial" | "abstract" | "interactive"
  theme: string
  data: {
    type: string
    values: number[]
    showCombined?: boolean
  }
}

export default function LessonVisual({ visualType, theme, data }: LessonVisualProps) {
  const [userAnswer, setUserAnswer] = useState("")
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null)

  const handleAnswerSubmit = (answer: string) => {
    const correctAnswer = data.values[0] + data.values[1]
    setUserAnswer(answer)
    setIsCorrect(Number.parseInt(answer) === correctAnswer)
  }

  // Get theme-specific colors and images
  const getThemeColors = () => {
    switch (theme) {
      case "space":
        return {
          primary: "bg-blue-500",
          secondary: "bg-purple-500",
          itemImage: "🪐",
        }
      case "animals":
        return {
          primary: "bg-green-500",
          secondary: "bg-yellow-500",
          itemImage: "🐶",
        }
      case "sports":
        return {
          primary: "bg-red-500",
          secondary: "bg-orange-500",
          itemImage: "⚽",
        }
      default:
        return {
          primary: "bg-blue-500",
          secondary: "bg-purple-500",
          itemImage: "🪐",
        }
    }
  }

  const themeColors = getThemeColors()

  // Render different visual types based on the CPA approach
  const renderVisual = () => {
    const { values, showCombined } = data
    const sum = values[0] + values[1]

    switch (visualType) {
      case "concrete":
        return (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="flex items-center justify-center gap-8 mb-8">
              <div className="flex flex-wrap gap-2 justify-center max-w-[200px]">
                {Array.from({ length: values[0] }).map((_, i) => (
                  <motion.div
                    key={`first-${i}`}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: i * 0.1, duration: 0.3 }}
                    className={`w-12 h-12 ${themeColors.primary} rounded-md flex items-center justify-center text-white text-2xl`}
                  >
                    {themeColors.itemImage}
                  </motion.div>
                ))}
              </div>

              <div className="text-4xl font-bold text-indigo-600">+</div>

              <div className="flex flex-wrap gap-2 justify-center max-w-[200px]">
                {Array.from({ length: values[1] }).map((_, i) => (
                  <motion.div
                    key={`second-${i}`}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: values[0] * 0.1 + i * 0.1, duration: 0.3 }}
                    className={`w-12 h-12 ${themeColors.secondary} rounded-md flex items-center justify-center text-white text-2xl`}
                  >
                    {themeColors.itemImage}
                  </motion.div>
                ))}
              </div>
            </div>

            {showCombined && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className="flex flex-col items-center"
              >
                <div className="text-2xl font-bold text-indigo-600 mb-4">Combined</div>
                <div className="flex flex-wrap gap-2 justify-center max-w-[400px]">
                  {Array.from({ length: sum }).map((_, i) => (
                    <div
                      key={`combined-${i}`}
                      className={`w-12 h-12 ${i < values[0] ? themeColors.primary : themeColors.secondary} rounded-md flex items-center justify-center text-white text-2xl`}
                    >
                      {themeColors.itemImage}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )

      case "pictorial":
        return (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="flex items-center justify-center gap-8 mb-8">
              <div>
                <motion.svg width="120" height="120" viewBox="0 0 120 120">
                  {Array.from({ length: values[0] }).map((_, i) => {
                    const angle = (i / values[0]) * Math.PI * 2
                    const radius = 50
                    const cx = 60 + radius * Math.cos(angle)
                    const cy = 60 + radius * Math.sin(angle)

                    return (
                      <motion.circle
                        key={`first-${i}`}
                        cx={cx}
                        cy={cy}
                        r="10"
                        fill="#6366f1"
                        initial={{ r: 0 }}
                        animate={{ r: 10 }}
                        transition={{ delay: i * 0.1, duration: 0.3 }}
                      />
                    )
                  })}
                </motion.svg>
              </div>

              <div className="text-4xl font-bold text-indigo-600">+</div>

              <div>
                <motion.svg width="120" height="120" viewBox="0 0 120 120">
                  {Array.from({ length: values[1] }).map((_, i) => {
                    const angle = (i / values[1]) * Math.PI * 2
                    const radius = 50
                    const cx = 60 + radius * Math.cos(angle)
                    const cy = 60 + radius * Math.sin(angle)

                    return (
                      <motion.circle
                        key={`second-${i}`}
                        cx={cx}
                        cy={cy}
                        r="10"
                        fill="#8b5cf6"
                        initial={{ r: 0 }}
                        animate={{ r: 10 }}
                        transition={{ delay: values[0] * 0.1 + i * 0.1, duration: 0.3 }}
                      />
                    )
                  })}
                </motion.svg>
              </div>
            </div>

            {showCombined && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className="flex flex-col items-center"
              >
                <div className="text-2xl font-bold text-indigo-600 mb-4">Combined</div>
                <svg width="240" height="120" viewBox="0 0 240 120">
                  {Array.from({ length: sum }).map((_, i) => {
                    const perRow = 5
                    const row = Math.floor(i / perRow)
                    const col = i % perRow
                    const cx = 30 + col * 40
                    const cy = 30 + row * 40

                    return (
                      <circle
                        key={`combined-${i}`}
                        cx={cx}
                        cy={cy}
                        r="15"
                        fill={i < values[0] ? "#6366f1" : "#8b5cf6"}
                      />
                    )
                  })}
                </svg>
              </motion.div>
            )}
          </div>
        )

      case "abstract":
        return (
          <div className="flex flex-col items-center justify-center h-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="text-6xl font-bold text-indigo-600 flex items-center gap-4"
            >
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.5 }}>
                {values[0]}
              </motion.span>
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.5 }}>
                +
              </motion.span>
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.5 }}>
                {values[1]}
              </motion.span>
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8, duration: 0.5 }}>
                =
              </motion.span>
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0, duration: 0.5 }}>
                {sum}
              </motion.span>
            </motion.div>
          </div>
        )

      case "interactive":
        return (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-4xl font-bold text-indigo-600 mb-8 flex items-center gap-4">
              <span>{values[0]}</span>
              <span>+</span>
              <span>{values[1]}</span>
              <span>=</span>
              <div className="w-20 h-16 border-b-4 border-indigo-600 flex items-center justify-center">
                {isCorrect !== null ? (
                  <span className={isCorrect ? "text-green-600" : "text-red-600"}>{userAnswer}</span>
                ) : (
                  <span className="text-gray-400">?</span>
                )}
              </div>
            </div>

            {isCorrect === null ? (
              <div className="grid grid-cols-3 gap-2 max-w-xs">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map((num) => (
                  <button
                    key={num}
                    className="bg-white hover:bg-indigo-50 border-2 border-indigo-200 rounded-lg p-4 text-2xl font-bold text-indigo-600 transition-colors"
                    onClick={() => handleAnswerSubmit(num.toString())}
                  >
                    {num}
                  </button>
                ))}
              </div>
            ) : (
              <div className={`text-2xl font-bold ${isCorrect ? "text-green-600" : "text-red-600"} mt-4`}>
                {isCorrect ? "Great job! That's correct!" : `Not quite. The answer is ${values[0] + values[1]}.`}
              </div>
            )}
          </div>
        )

      default:
        return <div>Loading visual...</div>
    }
  }

  return <div className="w-full h-full flex items-center justify-center p-4">{renderVisual()}</div>
}
