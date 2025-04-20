import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils" 
import { Message } from "@/contexts/TutorProvider"

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
              // *** Use message.type instead of message.role ***
              message.type === "assistant" ? "bg-blue-50" : message.type === "user" ? "bg-gray-50" : "bg-purple-50", // Added system style
            )}
          >
            <Avatar className={message.type === "assistant" ? "bg-blue-100" : message.type === "user" ? "bg-gray-200" : "bg-purple-100"}>
              {/* *** Use message.type for Avatar logic *** */}
              <AvatarFallback>
                {message.type === "assistant" ? "AI" : message.type === "user" ? "You" : "SYS"}
              </AvatarFallback>
              {message.type === "assistant" && (
                // Update placeholder or use a real image source if available
                <AvatarImage src="/images/logo.png" alt="Math Tutor" />
              )}
               {message.type === "user" && (
                 // Optional: Add a user avatar placeholder if desired
                 // <AvatarImage src="/path/to/user-avatar.png" alt="You" />
                 <></>
               )}
            </Avatar>
            <div className="flex-1">
              {/* *** Use message.type for displaying the role name *** */}
              <div className="font-medium mb-1">
                 {message.type === "assistant" ? "Math Tutor" : message.type === "user" ? "You" : "System"}
              </div>
              <div className="text-sm text-gray-700 whitespace-pre-wrap">{message.content}</div>
            </div>
          </div>
        ))
      )}

      {/* Loading indicator (remains the same, assuming assistant is loading) */}
      {isLoading && (
        <div className="flex items-start gap-3 rounded-lg p-3 bg-blue-50">
          <Avatar className="bg-blue-100">
            <AvatarFallback>AI</AvatarFallback>
            <AvatarImage src="/images/logo.png" alt="Math Tutor" />
          </Avatar>
          <div className="flex-1">
            <div className="font-medium mb-1">Math Tutor</div>
            <div className="text-sm text-gray-700">
              <div className="flex space-x-1 items-center h-5"> {/* Adjust height */}
                <div
                  className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                ></div>
                <div
                  className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                ></div>
                <div
                  className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce"
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