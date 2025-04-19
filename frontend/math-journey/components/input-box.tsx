"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PaperPlaneIcon } from "@radix-ui/react-icons"

interface InputBoxProps {
  onSubmit: (input: string) => void
  isLoading: boolean
}

export default function InputBox({ onSubmit, isLoading }: InputBoxProps) {
  const [input, setInput] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Focus the input when the component mounts
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSubmit(input)
      setInput("")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your answer here..."
        disabled={isLoading}
        className="flex-1 text-base py-6"
      />
      <Button type="submit" disabled={!input.trim() || isLoading} className="bg-blue-600 hover:bg-blue-700">
        <PaperPlaneIcon className="h-4 w-4" />
        <span className="sr-only">Send</span>
      </Button>
    </form>
  )
}
