import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/app/lib/utils"

type Message = {
  id: string
  role: "user" | "assistant"
  content: string
}

interface ChatDisplayProps {
  messages: Message[]
  isLoading: boolean
}

export default function ChatDisplay({ messages, isLoading }: ChatDisplayProps) {
  return (
    <div className="space-y-4 px-1">
      {messages.length === 0 && !isLoading ? (
        <div className="text-center py-8 text-gray-500">
          <p>Your math tutor is ready to help you learn!</p>
        </div>
      ) : (
        messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex items-start gap-3 rounded-lg p-3",
              message.role === "assistant" ? "bg-blue-50" : "bg-gray-50",
            )}
          >
            <Avatar className={message.role === "assistant" ? "bg-blue-100" : "bg-gray-200"}>
              <AvatarFallback>{message.role === "assistant" ? "MB" : "You"}</AvatarFallback>
              {message.role === "assistant" && (
                <AvatarImage src="/placeholder.svg?height=40&width=40" alt="Math Buddy" />
              )}
            </Avatar>
            <div className="flex-1">
              <div className="font-medium mb-1">{message.role === "assistant" ? "Math Buddy" : "You"}</div>
              <div className="text-sm text-gray-700 whitespace-pre-wrap">{message.content}</div>
            </div>
          </div>
        ))
      )}

      {isLoading && (
        <div className="flex items-start gap-3 rounded-lg p-3 bg-blue-50">
          <Avatar className="bg-blue-100">
            <AvatarFallback>MB</AvatarFallback>
            <AvatarImage src="/placeholder.svg?height=40&width=40" alt="Math Buddy" />
          </Avatar>
          <div className="flex-1">
            <div className="font-medium mb-1">Math Buddy</div>
            <div className="text-sm text-gray-700">
              <div className="flex space-x-1">
                <div
                  className="h-2 w-2 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                ></div>
                <div
                  className="h-2 w-2 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                ></div>
                <div
                  className="h-2 w-2 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
