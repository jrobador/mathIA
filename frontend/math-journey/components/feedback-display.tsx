import { CheckCircle, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { ExclamationTriangleIcon } from "@radix-ui/react-icons"

interface FeedbackDisplayProps {
  feedback: {
    type: "correct" | "incorrect" | "hint"
    message: string
  }
}

export default function FeedbackDisplay({ feedback }: FeedbackDisplayProps) {
  const { type, message } = feedback

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg",
        type === "correct" ? "bg-green-50" : type === "incorrect" ? "bg-red-50" : "bg-yellow-50",
      )}
    >
      <div className="mt-0.5">
        {type === "correct" ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : type === "incorrect" ? (
          <XCircle className="h-5 w-5 text-red-500" />
        ) : (
          <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
        )}
      </div>

      <div>
        <h4
          className={cn(
            "font-medium mb-1",
            type === "correct" ? "text-green-700" : type === "incorrect" ? "text-red-700" : "text-yellow-700",
          )}
        >
          {type === "correct" ? "Great job!" : type === "incorrect" ? "Not quite right" : "Hint"}
        </h4>
        <p className="text-sm text-gray-700">{message}</p>
      </div>
    </div>
  )
}
