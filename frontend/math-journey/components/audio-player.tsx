"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  RotateCcw, 
  AlertCircle,
  Loader2
} from "lucide-react"
import { toast } from "sonner"

interface AudioPlayerProps {
  audioUrl: string
  autoPlay?: boolean
  onPlaybackComplete?: () => void
}

export default function AudioPlayer({ 
  audioUrl, 
  autoPlay = false,
  onPlaybackComplete
}: AudioPlayerProps) {
  // Player state
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [showVolumeSlider, setShowVolumeSlider] = useState(false)
  
  // Loading and error states
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Reference to audio element
  const audioRef = useRef<HTMLAudioElement | null>(null)
  
  // Track if component is mounted (for cleanup)
  const isMounted = useRef(true)

  // Initialize and clean up audio element
  useEffect(() => {
    // Only attempt to load if we have a URL
    if (!audioUrl) {
      setError("No audio available")
      setIsLoading(false)
      return
    }
    
    setIsLoading(true)
    setError(null)
    
    // Create new audio element
    const audio = new Audio(audioUrl)
    audioRef.current = audio
    
    // Set initial volume
    audio.volume = volume
    
    // Set up event listeners
    const onLoadedMetadata = () => {
      if (!isMounted.current) return
      setDuration(audio.duration)
      setIsLoading(false)
      
      // Auto-play if enabled
      if (autoPlay) {
        audio.play()
          .then(() => setIsPlaying(true))
          .catch((err) => {
            console.error("Auto-play failed:", err)
            // Don't show error for auto-play failures (common due to browser policies)
          })
      }
    }
    
    const onTimeUpdate = () => {
      if (!isMounted.current) return
      setCurrentTime(audio.currentTime)
    }
    
    const onEnded = () => {
      if (!isMounted.current) return
      setIsPlaying(false)
      setCurrentTime(0)
      if (onPlaybackComplete) onPlaybackComplete()
    }
    
    const onError = (e: ErrorEvent) => {
      if (!isMounted.current) return
      console.error("Audio error:", e)
      setError("Could not load audio")
      setIsLoading(false)
      toast("Failed to load audio", {
        description: "Please try again or continue without audio.",
        duration: 3000
      })
    }
    
    // Add event listeners
    audio.addEventListener("loadedmetadata", onLoadedMetadata)
    audio.addEventListener("timeupdate", onTimeUpdate)
    audio.addEventListener("ended", onEnded)
    audio.addEventListener("error", onError as EventListener)
    
    // Handle edge case where audio might be cached and already loaded
    if (audio.readyState >= 2) {
      onLoadedMetadata()
    }
    
    // Cleanup function
    return () => {
      isMounted.current = false
      
      // Remove event listeners
      audio.removeEventListener("loadedmetadata", onLoadedMetadata)
      audio.removeEventListener("timeupdate", onTimeUpdate)
      audio.removeEventListener("ended", onEnded)
      audio.removeEventListener("error", onError as EventListener)
      
      // Stop and clean up audio
      audio.pause()
      audio.src = ""
      audioRef.current = null
    }
  }, [audioUrl, autoPlay, volume, onPlaybackComplete])

  // Handle play/pause toggling
  const togglePlayPause = () => {
    if (!audioRef.current || error) return
    
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
        .catch((err) => {
          console.error("Play failed:", err)
          toast("Couldn't play audio", {
            description: "There was a problem playing the audio.",
            duration: 3000
          })
        })
    }
    setIsPlaying(!isPlaying)
  }

  // Handle mute toggling
  const toggleMute = () => {
    if (!audioRef.current) return
    
    const newMutedState = !isMuted
    audioRef.current.muted = newMutedState
    setIsMuted(newMutedState)
  }

  // Handle seeking (time change)
  const handleSliderChange = (value: number[]) => {
    if (!audioRef.current) return
    
    const newTime = value[0]
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  // Handle volume change
  const handleVolumeChange = (value: number[]) => {
    if (!audioRef.current) return
    
    const newVolume = value[0]
    audioRef.current.volume = newVolume
    setVolume(newVolume)
    
    // If adjusting volume when muted, unmute
    if (isMuted && newVolume > 0) {
      audioRef.current.muted = false
      setIsMuted(false)
    }
    
    // If volume is set to 0, mute
    if (newVolume === 0 && !isMuted) {
      audioRef.current.muted = true
      setIsMuted(true)
    }
  }

  // Handle restarting the audio
  const handleRestart = () => {
    if (!audioRef.current) return
    
    audioRef.current.currentTime = 0
    setCurrentTime(0)
    
    if (!isPlaying) {
      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch(err => console.error("Restart play failed:", err))
    }
  }

  // Format time for display (mm:ss)
  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00"
    
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`
  }

  // Render different states
  if (isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-center h-12 bg-blue-50 rounded-md">
          <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
          <span className="ml-2 text-sm text-blue-700">Loading audio...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-center h-12 bg-red-50 rounded-md p-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="ml-2 text-sm text-red-700">{error}</span>
          <Button 
            variant="outline" 
            size="sm" 
            className="ml-auto h-7 text-xs"
            onClick={() => window.location.reload()}
          >
            Reload
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {/* Play/Pause Button */}
        <Button 
          variant="outline" 
          size="icon" 
          className={`h-8 w-8 ${isPlaying ? 'bg-blue-50' : ''}`} 
          onClick={togglePlayPause}
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>

        {/* Restart Button */}
        <Button 
          variant="outline" 
          size="icon" 
          className="h-8 w-8" 
          onClick={handleRestart}
        >
          <RotateCcw className="h-4 w-4" />
        </Button>

        {/* Time Slider */}
        <div className="flex-1 mx-2">
          <Slider 
            value={[currentTime]} 
            max={duration || 100} 
            step={0.1} 
            onValueChange={handleSliderChange} 
          />
        </div>

        {/* Time Display */}
        <span className="text-xs text-gray-500 min-w-[60px] text-right">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      {/* Volume Control */}
      <div className="flex items-center">
        <div 
          className="relative"
          onMouseEnter={() => setShowVolumeSlider(true)}
          onMouseLeave={() => setShowVolumeSlider(false)}
        >
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-7 w-7 text-gray-500 hover:text-gray-700" 
            onClick={toggleMute}
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </Button>
          
          {/* Volume Slider (shows on hover) */}
          {showVolumeSlider && (
            <div className="absolute bottom-full left-0 mb-2 p-2 bg-white shadow-lg rounded-lg w-32">
              <Slider
                value={[isMuted ? 0 : volume]}
                max={1}
                step={0.01}
                onValueChange={handleVolumeChange}
              />
            </div>
          )}
        </div>
        
        <p className="text-xs text-gray-500 ml-2">
          Listen to the explanation to better understand the concept
        </p>
      </div>
    </div>
  )
}