"use client"

import { Button } from "@/components/ui/button"
import { SkipBackIcon as Backspace } from "lucide-react"

interface NumberPadProps {
  onInput: (value: string) => void
}

export default function NumberPad({ onInput }: NumberPadProps) {
  const buttons = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "clear", "0", "backspace"]

  return (
    <div className="grid grid-cols-3 gap-2">
      {buttons.map((btn) => (
        <Button
          key={btn}
          variant={btn === "clear" ? "destructive" : "outline"}
          className={`h-12 text-lg font-medium ${
            btn === "clear"
              ? "bg-red-500/80 hover:bg-red-600/90 border border-red-400/30"
              : "bg-white/80 backdrop-blur-sm border-indigo-100/60 hover:bg-indigo-50/90"
          }`}
          onClick={() => onInput(btn)}
        >
          {btn === "backspace" ? <Backspace className="h-5 w-5" /> : btn === "clear" ? "Clear" : btn}
        </Button>
      ))}
    </div>
  )
}
