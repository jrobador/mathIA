"use client"

import { Button } from "@/components/ui/button"
import { Play, Pause, Volume2 } from "lucide-react"
import { motion } from "framer-motion"

interface AudioControlsProps {
  isPlaying: boolean
  onPlay: () => void
  audioText: string
}

export default function AudioControls({ isPlaying, onPlay, audioText }: AudioControlsProps) {
  return (
    <div className="flex items-center justify-center gap-4 p-3 bg-white/30 backdrop-blur-md rounded-full border border-white/40 shadow-md">
      <Button
        variant="outline"
        size="icon"
        className={`h-12 w-12 rounded-full ${isPlaying ? "bg-indigo-100/90" : "bg-white/80"} border-white/60 shadow-sm`}
        onClick={onPlay}
        disabled={isPlaying}
      >
        {isPlaying ? <Pause className="h-6 w-6 text-indigo-600" /> : <Play className="h-6 w-6 text-indigo-600" />}
      </Button>

      <div className="flex items-center gap-2 bg-indigo-50/80 backdrop-blur-sm rounded-full px-4 py-2 border border-indigo-100/60">
        <Volume2 className="h-4 w-4 text-indigo-600" />

        <div className="relative h-6 flex items-center">
          {isPlaying ? (
            <div className="flex space-x-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <motion.div
                  key={i}
                  className="h-1.5 w-1.5 bg-indigo-600 rounded-full"
                  animate={{
                    height: ["6px", "12px", "6px"],
                  }}
                  transition={{
                    duration: 0.5,
                    repeat: Number.POSITIVE_INFINITY,
                    delay: i * 0.1,
                    ease: "easeInOut",
                  }}
                />
              ))}
            </div>
          ) : (
            <span className="text-sm text-indigo-600">Play audio explanation</span>
          )}
        </div>
      </div>
    </div>
  )
}
