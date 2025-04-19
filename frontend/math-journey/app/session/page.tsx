"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { HelpCircle } from "lucide-react"
import Link from "next/link"
import ChatDisplay from "@/components/chat-display"
import VisualDisplay from "@/components/visual-display"
import AudioPlayer from "@/components/audio-player"
import InputBox from "@/components/input-box"
import FeedbackDisplay from "@/components/feedback-display"
import { useSession } from "@/hooks/use-session"
import { ArrowLeftIcon } from "@radix-ui/react-icons"

export default function SessionPage() {
  const { toast } = useToast()
  const { sessionId, messages, currentVisual, currentAudio, feedback, isLoading, progress, startSession, sendMessage } =
    useSession()

  useEffect(() => {
    // Start a new session when the component mounts
    if (!sessionId) {
      startSession()
    }
  }, [sessionId, startSession])

  const handleSubmit = async (input: string) => {
    if (!input.trim()) return

    try {
      await sendMessage(input)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send your message. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white p-4">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-6">
          <Link href="/">
            <Button variant="ghost" className="flex items-center text-blue-700">
              <ArrowLeftIcon className="mr-2 h-4 w-4" /> Back to Home
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Need help?</span>
            <Button variant="outline" size="sm" className="text-blue-700">
              <HelpCircle className="h-4 w-4 mr-1" /> Help
            </Button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Chat and Input */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-4 h-[calc(70vh-2rem)] flex flex-col">
              <div className="flex-grow overflow-y-auto mb-4">
                <ChatDisplay messages={messages} isLoading={isLoading} />
              </div>
              <div>
                <InputBox onSubmit={handleSubmit} isLoading={isLoading} />
              </div>
            </Card>

            {feedback && (
              <Card className="p-4">
                <FeedbackDisplay feedback={feedback} />
              </Card>
            )}
          </div>

          {/* Right column - Visual, Audio, Progress */}
          <div className="space-y-4">
            <Card className="p-4">
              <h3 className="text-lg font-medium mb-3 text-blue-700">Visual Aid</h3>
              <VisualDisplay visual={currentVisual} />
            </Card>

            {currentAudio && (
              <Card className="p-4">
                <h3 className="text-lg font-medium mb-3 text-blue-700">Audio Explanation</h3>
                <AudioPlayer audioUrl={currentAudio} />
              </Card>
            )}

            <Card className="p-4">
              <h3 className="text-lg font-medium mb-3 text-blue-700">Your Progress</h3>
              <Progress value={progress} className="h-2 mb-2" />
              <p className="text-sm text-gray-600">
                {progress < 33 ? "Just getting started!" : progress < 66 ? "Making good progress!" : "Almost there!"}
              </p>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}
