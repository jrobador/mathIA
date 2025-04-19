"use client"

import { useState, useCallback } from "react"
import { v4 as uuidv4 } from "uuid"

// Mock API client - replace with actual implementation
const api = {
  startSession: async () => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    return { sessionId: uuidv4() }
  },

  processMessage: async (sessionId: string, message: string) => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500))

    // Mock response based on input
    const isNumber = /^\d+$/.test(message)
    const isAddition = /^\d+\s*\+\s*\d+$/.test(message)

    let response = {
      text: "I'm not sure how to respond to that. Can you try asking about a math problem?",
      visual: null,
      audio: null,
      feedback: null,
    }

    if (isNumber) {
      const num = Number.parseInt(message)
      if (num % 2 === 0) {
        response = {
          text: `Yes, ${num} is an even number! Even numbers can be divided by 2 with no remainder.`,
          visual: {
            url: "/placeholder.svg?height=200&width=300",
            type: "pictorial",
            alt: `Visual representation of ${num} as an even number`,
          },
          audio: "https://example.com/audio.mp3", // Mock URL
          feedback: {
            type: "correct",
            message: "You've identified an even number correctly!",
          },
        }
      } else {
        response = {
          text: `Yes, ${num} is an odd number! Odd numbers have a remainder of 1 when divided by 2.`,
          visual: {
            url: "/placeholder.svg?height=200&width=300",
            type: "pictorial",
            alt: `Visual representation of ${num} as an odd number`,
          },
          audio: "https://example.com/audio.mp3", // Mock URL
          feedback: {
            type: "correct",
            message: "You've identified an odd number correctly!",
          },
        }
      }
    } else if (isAddition) {
      const [a, b] = message.split("+").map((n) => Number.parseInt(n.trim()))
      const sum = a + b
      response = {
        text: `Let's solve ${a} + ${b}. We can count ${a} objects, then add ${b} more objects, and count the total to get ${sum}.`,
        visual: {
          url: "/placeholder.svg?height=200&width=300",
          type: "concrete",
          alt: `Visual representation of ${a} + ${b} = ${sum}`,
        },
        audio: "https://example.com/audio.mp3", // Mock URL
        feedback: {
          type: "hint",
          message: `Try counting ${a} blocks, then add ${b} more blocks, and count how many you have in total.`,
        },
      }
    }

    return response
  },
}

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
}

type Visual = {
  url: string
  type: "concrete" | "pictorial" | "abstract"
  alt: string
}

type Feedback = {
  type: "correct" | "incorrect" | "hint"
  message: string
}

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [currentVisual, setCurrentVisual] = useState<Visual | undefined>(undefined)
  const [currentAudio, setCurrentAudio] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const startSession = useCallback(async () => {
    setIsLoading(true)
    try {
      const { sessionId } = await api.startSession()
      setSessionId(sessionId)

      // Add initial welcome message
      setMessages([
        {
          id: uuidv4(),
          role: "assistant",
          content:
            "Hi there! I'm your Math Buddy. I'm here to help you learn math using the Singapore Method. What would you like to work on today? You can try asking about numbers, addition, or other math concepts.",
        },
      ])

      setProgress(5) // Initial progress
    } catch (error) {
      console.error("Failed to start session:", error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) return

      // Add user message
      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content,
      }

      setMessages((prev) => [...prev, userMessage])
      setIsLoading(true)

      try {
        const response = await api.processMessage(sessionId, content)

        // Add assistant message
        const assistantMessage: Message = {
          id: uuidv4(),
          role: "assistant",
          content: response.text,
        }

        setMessages((prev) => [...prev, assistantMessage])

        // Update visual, audio, and feedback
        if (response.visual) {
          setCurrentVisual(response.visual)
        }

        if (response.audio) {
          setCurrentAudio(response.audio)
        }

        if (response.feedback) {
          setFeedback(response.feedback)
        }

        // Update progress (in a real app, this would come from the backend)
        setProgress((prev) => Math.min(prev + 10, 100))
      } catch (error) {
        console.error("Failed to process message:", error)
      } finally {
        setIsLoading(false)
      }
    },
    [sessionId],
  )

  return {
    sessionId,
    messages,
    currentVisual,
    currentAudio,
    feedback,
    isLoading,
    progress,
    startSession,
    sendMessage,
  }
}
