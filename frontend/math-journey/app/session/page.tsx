"use client"

import { useEffect, useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { toast } from "sonner"
import { HelpCircle, Info } from "lucide-react"
import Link from "next/link"
import ChatDisplay from "@/components/chat-display"
import VisualDisplay from "@/components/visual-display" // Use the correct component
import AudioPlayer from "@/components/audio-player"
import InputBox from "@/components/input-box"
import FeedbackDisplay from "@/components/feedback-display"
import { useTutor } from "@/contexts/TutorProvider"
import { ArrowLeftIcon } from "@radix-ui/react-icons"
import { EvaluationResult } from "@/types/api" // Import necessary types

// Define the structure expected by VisualDisplay
interface VisualProp {
  url: string;
  alt: string;
  // Type is removed as we only get URL from backend
}

export default function LessonPage() {
  // *** Use the Tutor context hook ***
  const {
    sessionId,
    messages, // Use messages from context
    currentOutput, // Use currentOutput from context
    isLoading,
    masteryLevel, // Use masteryLevel from context
    startSession,
    sendMessage,
  } = useTutor();

  // --- State derived from context ---
  const [studentName, setStudentName] = useState("")
  const [learningPath, setLearningPath] = useState("")
  const [learningTheme, setLearningTheme] = useState("")

  useEffect(() => {
    setStudentName(localStorage.getItem("studentName") || "learner")
    setLearningPath(localStorage.getItem("learningPath") || "addition")
    setLearningTheme(localStorage.getItem("learningTheme") || "space")
  }, [])

  // Start a session automatically if needed
  useEffect(() => {
    if (!sessionId && !isLoading && learningPath && studentName) {
      const diagnosticResultsJson = localStorage.getItem("diagnosticResults");
      const diagnosticResults = diagnosticResultsJson ? JSON.parse(diagnosticResultsJson) : null;

      startSession({
        theme: learningTheme,
        learningPath: learningPath,
        initialMessage: `Hi, I'm ${studentName}. Let's start learning ${learningPath}!`,
        diagnosticResults: diagnosticResults?.question_results // Pass only the results part if needed by the API schema
      }).catch(error => {
        console.error("Auto-start session failed:", error);
        toast("Failed to start the learning session. Please try refreshing.", { duration: 5000 });
      });
    }
  }, [sessionId, isLoading, startSession, learningPath, learningTheme, studentName]);

  const handleSubmit = async (input: string) => {
    if (!input.trim()) return

    try {
      await sendMessage(input)
    } catch (error) {
      console.error("Error sending message:", error);
      toast("Failed to send your message. Please try again.")
    }
  }

  // --- Derive component props from currentOutput ---
  const derivedVisual: VisualProp | undefined = useMemo(() => {
    if (currentOutput?.image_url) {
      return {
        url: currentOutput.image_url,
        alt: currentOutput.text?.substring(0, 50) || "Math visual aid", // Generate basic alt text
        // Type is removed
      };
    }
    return undefined;
  }, [currentOutput]);

  const derivedAudio: string | undefined = useMemo(() => {
    return currentOutput?.audio_url;
  }, [currentOutput]);

  const derivedFeedback: { type: "correct" | "incorrect" | "hint"; message: string } | null = useMemo(() => {
    if (currentOutput?.evaluation) {
      const evaluation = currentOutput.evaluation as EvaluationResult;
      const message = currentOutput.feedback?.message || currentOutput.text || "Let's continue!";

      if (evaluation === EvaluationResult.CORRECT) {
        return { type: "correct", message: message || "Excellent work!" };
      } else if (evaluation === EvaluationResult.INCORRECT_CALCULATION || evaluation === EvaluationResult.INCORRECT_CONCEPTUAL) {
        return { type: "incorrect", message: message || "That wasn't quite right. Take another look." };
      } else { // UNCLEAR or other
        return { type: "hint", message: message || "Let's try that again." };
      }
    }
    return null;
  }, [currentOutput]);

  const progress = useMemo(() => {
    // Convert mastery level (0.0 - 1.0) to percentage (0 - 100)
    return Math.round(masteryLevel * 100);
  }, [masteryLevel]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-indigo-50 to-white p-4">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-6">
          <Link href="/learning-path"> {/* Link back to path selection */}
            <Button variant="ghost" className="flex items-center text-indigo-700">
              <ArrowLeftIcon className="mr-2 h-4 w-4" /> Back to Topics
            </Button>
          </Link>
          {sessionId && (
             <div className="flex items-center gap-2 text-sm text-gray-500">
                <Info size={16} /> Session ID: {sessionId.substring(0, 8)}...
             </div>
          )}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Need help?</span>
            <Button variant="outline" size="sm" className="text-indigo-700">
              <HelpCircle className="h-4 w-4 mr-1" /> Help
            </Button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Chat and Input */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-4 h-[calc(70vh-2rem)] flex flex-col shadow-lg border border-indigo-100">
              <div className="flex-grow overflow-y-auto mb-4 scrollbar-thin scrollbar-thumb-indigo-200 scrollbar-track-gray-100">
                <ChatDisplay messages={messages} isLoading={isLoading} />
              </div>
              <div>
                {/* Pass derived state to InputBox */}
                <InputBox onSubmit={handleSubmit} isLoading={isLoading} />
              </div>
            </Card>

            {/* Use derivedFeedback */}
            {derivedFeedback && (
              <Card className="p-4 shadow-md border border-indigo-100">
                <FeedbackDisplay feedback={derivedFeedback} />
              </Card>
            )}
          </div>

          {/* Right column - Visual, Audio, Progress */}
          <div className="space-y-4">
            <Card className="p-4 shadow-md border border-indigo-100">
              <h3 className="text-lg font-medium mb-3 text-indigo-700">Visual Aid</h3>
              {/* Pass derivedVisual to VisualDisplay */}
              <VisualDisplay visual={derivedVisual} />
            </Card>

            {/* Use derivedAudio */}
            {derivedAudio && (
              <Card className="p-4 shadow-md border border-indigo-100">
                <h3 className="text-lg font-medium mb-3 text-indigo-700">Audio Explanation</h3>
                <AudioPlayer audioUrl={derivedAudio} autoPlay={true} />
              </Card>
            )}

            <Card className="p-4 shadow-md border border-indigo-100">
              <h3 className="text-lg font-medium mb-3 text-indigo-700">Your Progress</h3>
              {/* Use derived progress */}
              <Progress value={progress} className="h-2 mb-2" />
              <p className="text-sm text-gray-600">
                Mastery: {progress}%{" "}
                {progress < 33 ? "🌱" : progress < 66 ? "🌳" : "⭐"}
              </p>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}