"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import AudioControls from "@/components/audio-controls"
import ProgressDots from "@/components/progress-dots"
import { motion } from "framer-motion"
import { ArrowRightIcon, ArrowLeftIcon } from "@radix-ui/react-icons"
import { Eraser } from "lucide-react"
import { DiagnosticResults, DiagnosticQuestionResult as ApiDiagnosticQuestionResult, DifficultySetting } from "@/types/api"

type QuestionType = "concrete" | "pictorial" | "abstract"

interface DiagnosticQuestion {
  id: number // Keep internal ID for finding the question
  question_id: string // Add string ID for API
  type: QuestionType
  difficulty: DifficultySetting
  problem: string
  audioText: string
  visualData: {
    blocks?: number[]
    circles?: number[]
    equation?: {
      num1: number
      num2: number
      operation: "+" | "-" | "×" | "÷"
    }
  }
  correctAnswer: string
  explanation: string
  conceptTested: string
}

// Question bank (ADD question_id)
const diagnosticQuestions: DiagnosticQuestion[] = [
  {
    id: 1,
    question_id: "diag_q1_concrete_count", // Added string ID
    type: "concrete",
    difficulty: DifficultySetting.INITIAL,
    problem: "How many blocks are there in total?",
    audioText: "Look at these blocks. How many blocks are there in total?",
    visualData: { blocks: [3, 2] },
    correctAnswer: "5",
    explanation: "There are 3 red blocks and 2 blue blocks. 3 + 2 = 5 blocks in total.",
    conceptTested: "Counting and quantity recognition",
  },
  {
    id: 2,
    question_id: "diag_q2_pictorial_add", // Added string ID
    type: "pictorial",
    difficulty: DifficultySetting.BEGINNER,
    problem: "How many circles are there in total?",
    audioText: "Look at these groups of circles. How many circles are there in total?",
    visualData: { circles: [4, 3] },
    correctAnswer: "7",
    explanation: "There are 4 circles in the first group and 3 circles in the second group. 4 + 3 = 7 circles in total.",
    conceptTested: "Basic addition with pictorial representation",
  },
  {
    id: 3,
    question_id: "diag_q3_abstract_add", // Added string ID
    type: "abstract",
    difficulty: DifficultySetting.BEGINNER,
    problem: "7 + 5 = ?",
    audioText: "What is seven plus five?",
    visualData: { equation: { num1: 7, num2: 5, operation: "+" } },
    correctAnswer: "12",
    explanation: "To add 7 + 5, we can break down 5 into 3 + 2. Then: 7 + 3 = 10, and 10 + 2 = 12.",
    conceptTested: "Addition with numbers up to 20",
  },
  {
    id: 4,
    question_id: "diag_q4_abstract_sub", // Added string ID
    type: "abstract",
    difficulty: DifficultySetting.INTERMEDIATE,
    problem: "15 - 8 = ?",
    audioText: "What is fifteen minus eight?",
    visualData: { equation: { num1: 15, num2: 8, operation: "-" } },
    correctAnswer: "7",
    explanation: "To subtract 15 - 8, we can think: 15 - 5 = 10, and then 10 - 3 = 7.",
    conceptTested: "Subtraction with numbers up to 20",
  },
  {
    id: 5,
    question_id: "diag_q5_abstract_mul", // Added string ID
    type: "abstract",
    difficulty: DifficultySetting.INTERMEDIATE,
    problem: "4 × 3 = ?",
    audioText: "What is four times three?",
    visualData: { equation: { num1: 4, num2: 3, operation: "×" } },
    correctAnswer: "12",
    explanation: "4 × 3 means 4 groups of 3, or 3 + 3 + 3 + 3 = 12.",
    conceptTested: "Basic multiplication",
  },
  {
    id: 6,
    question_id: "diag_q6_abstract_div", // Added string ID
    type: "abstract",
    difficulty: DifficultySetting.ADVANCED,
    problem: "20 ÷ 4 = ?",
    audioText: "What is twenty divided by four?",
    visualData: { equation: { num1: 20, num2: 4, operation: "÷" } },
    correctAnswer: "5",
    explanation: "20 ÷ 4 means dividing 20 into 4 equal groups. Each group will have 5 elements.",
    conceptTested: "Basic division",
  },
]

// NumberPad Component (keep as is)
const NumberPad = ({ onInput }: { onInput: (value: string) => void }) => {
  return (
    <div className="grid grid-cols-3 gap-2">
      {[1, 2, 3].map((num) => (<button key={`num-${num}`} onClick={() => onInput(num.toString())} className="rounded py-3 text-lg font-semibold bg-indigo-100 border border-indigo-300 text-indigo-900 hover:bg-indigo-200 active:bg-indigo-300 transition-colors shadow-sm">{num}</button>))}
      {[4, 5, 6].map((num) => (<button key={`num-${num}`} onClick={() => onInput(num.toString())} className="rounded py-3 text-lg font-semibold bg-indigo-100 border border-indigo-300 text-indigo-900 hover:bg-indigo-200 active:bg-indigo-300 transition-colors shadow-sm">{num}</button>))}
      {[7, 8, 9].map((num) => (<button key={`num-${num}`} onClick={() => onInput(num.toString())} className="rounded py-3 text-lg font-semibold bg-indigo-100 border border-indigo-300 text-indigo-900 hover:bg-indigo-200 active:bg-indigo-300 transition-colors shadow-sm">{num}</button>))}
      <button onClick={() => onInput("clear")} className="rounded py-3 text-lg font-semibold bg-red-500 text-white hover:bg-red-600 active:bg-red-700 transition-colors shadow-sm">Clear</button>
      <button onClick={() => onInput("0")} className="rounded py-3 text-lg font-semibold bg-indigo-100 border border-indigo-300 text-indigo-900 hover:bg-indigo-200 active:bg-indigo-300 transition-colors shadow-sm">0</button>
      <button onClick={() => onInput("backspace")} className="rounded py-3 flex items-center justify-center bg-gray-200 border border-gray-300 text-gray-700 hover:bg-gray-300 active:bg-gray-400 transition-colors shadow-sm"><Eraser className="h-5 w-5" /></button>
    </div>
  )
}


export default function DiagnosticPage() {
  const router = useRouter()
  const [studentName, setStudentName] = useState("")
  const [showIntro, setShowIntro] = useState(true)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answer, setAnswer] = useState("")
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [isAudioComplete, setIsAudioComplete] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [results, setResults] = useState<{ id: number; correct: boolean }[]>([])
  const [diagnosticComplete, setDiagnosticComplete] = useState(false)

  const currentQuestion = diagnosticQuestions[currentQuestionIndex]

  // Get name from localStorage
  useEffect(() => {
    const name = localStorage.getItem("studentName") || "friend"
    setStudentName(name)
  }, [])


  // Auto-play audio when page loads or question changes (only if intro is passed)
  useEffect(() => {
    if (!showIntro && !diagnosticComplete && !showFeedback) {
      const timer = setTimeout(() => {
        setIsAudioPlaying(true)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [currentQuestionIndex, showIntro, diagnosticComplete, showFeedback])

  // Simulate audio playing and completion
  useEffect(() => {
    if (isAudioPlaying) {
      const audioDuration = showFeedback ? 3000 : 4000
      const timer = setTimeout(() => {
        setIsAudioComplete(true)
        setIsAudioPlaying(false)
      }, audioDuration)
      return () => clearTimeout(timer)
    }
  }, [isAudioPlaying, showFeedback])

  const handleStartDiagnostic = () => {
    setShowIntro(false)
    setIsAudioPlaying(false)
    setIsAudioComplete(false)
  }

  const handleSubmit = () => {
    const isAnswerCorrect = answer === currentQuestion.correctAnswer;
    setIsCorrect(isAnswerCorrect);
    setShowFeedback(true);
    setIsAudioPlaying(true); // Play feedback audio

    // Store the result for the current question
    const currentResult = { id: currentQuestion.id, correct: isAnswerCorrect };
    const updatedResults = [...results, currentResult];
    setResults(updatedResults);

    // --- Transition logic ---
    setTimeout(() => {
      setShowFeedback(false);
      setAnswer("");
      setIsAudioPlaying(false);
      setIsAudioComplete(false);

      if (currentQuestionIndex < diagnosticQuestions.length - 1) {
        // Move to the next question
        setCurrentQuestionIndex((prev) => prev + 1);
      } else {
        // --- Diagnostic is complete ---
        setDiagnosticComplete(true);

        // Calculate final results
        const correctAnswers = updatedResults.filter((r) => r.correct).length;
        const totalQuestions = diagnosticQuestions.length;
        const percentCorrect = (correctAnswers / totalQuestions) * 100;

        // Determine recommended level
        let recommendedLevel: DifficultySetting = DifficultySetting.INITIAL;
        if (percentCorrect >= 80) recommendedLevel = DifficultySetting.ADVANCED;
        else if (percentCorrect >= 50) recommendedLevel = DifficultySetting.INTERMEDIATE;
        else if (percentCorrect >= 30) recommendedLevel = DifficultySetting.BEGINNER;

        // *** Format results for API ***
        const apiQuestionResults: ApiDiagnosticQuestionResult[] = updatedResults.map((result) => {
          const question = diagnosticQuestions.find(q => q.id === result.id);
          return {
            question_id: question?.question_id || `unknown_q${result.id}`, // Use string ID
            correct: result.correct,
            concept_tested: question?.conceptTested,
          };
        });

        // *** Create the full DiagnosticResults object ***
        const fullResultsObject: DiagnosticResults = {
          score: percentCorrect,
          correct_answers: correctAnswers,
          total_questions: totalQuestions,
          recommended_level: recommendedLevel,
          question_results: apiQuestionResults,
          // strengths/weaknesses could be calculated here if needed based on conceptTested
        };

        // *** Store the full results object in localStorage ***
        localStorage.setItem("diagnosticResults", JSON.stringify(fullResultsObject));
        localStorage.setItem("studentLevel", recommendedLevel); // Keep this for convenience if needed elsewhere

        // Navigate after a delay
        setTimeout(() => router.push("/learning-path"), 3000);
      }
    }, 3500); // Delay for feedback viewing
  };


  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex((prev) => prev - 1)
      setAnswer("")
      setShowFeedback(false)
      setIsAudioPlaying(false)
      setIsAudioComplete(false)
      // Remove the last result if going back means re-answering
      setResults(prev => prev.slice(0, -1));
    }
  }

  const handlePlayAudio = () => {
    if (!showIntro && !diagnosticComplete) {
        setIsAudioPlaying(true)
    }
  }

 const handleNumberInput = (num: string) => {
    if (showFeedback) return;

    if (num === "clear") {
      setAnswer("")
    } else if (num === "backspace") {
      setAnswer((prev) => prev.slice(0, -1))
    } else {
      if (answer.length < 3) {
        setAnswer((prev) => prev + num)
      }
    }
  }


  // renderDiagnosticSummary (uses final results from state)
   const renderDiagnosticSummary = () => {
    // Recalculate based on the final 'results' state
    const correctAnswers = results.filter((r) => r.correct).length
    const totalQuestions = diagnosticQuestions.length
    const percentCorrect = Math.round((correctAnswers / totalQuestions) * 100)
    const finalLevel = localStorage.getItem("studentLevel") || "initial" // Get stored level

    let levelText = "Initial Level", levelDescription = "We'll start with the most basic concepts to build a solid foundation.", levelColor = "text-blue-700"
    if (finalLevel === "advanced") { levelText = "Advanced Level"; levelDescription = "Excellent! You have a good grasp of fundamental concepts. We'll work on more complex challenges."; levelColor = "text-purple-700"; }
    else if (finalLevel === "intermediate") { levelText = "Intermediate Level"; levelDescription = "You have a good understanding of several concepts. We'll continue reinforcing and advancing."; levelColor = "text-indigo-700"; }
    else if (finalLevel === "beginner") { levelText = "Beginner Level"; levelDescription = "You know some basic concepts. We'll work on strengthening your understanding."; levelColor = "text-green-700"; }

    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center w-full px-2 md:px-4">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Diagnostic Completed</h1>
        <div className="mb-6">
          <div className="text-xl md:text-2xl mb-2">Your score: <span className="font-bold">{correctAnswers} of {totalQuestions}</span></div>
          <div className="w-full bg-gray-200 rounded-full h-4 mb-4"><div className="bg-indigo-700 h-4 rounded-full" style={{ width: `${percentCorrect}%` }}></div></div>
        </div>
        <h2 className={`text-2xl md:text-3xl font-bold mb-2 ${levelColor}`}>{levelText}</h2>
        <p className="text-lg md:text-xl text-gray-700 mb-6">{levelDescription}</p>
        <p className="text-lg">We'll take you to select your learning topic shortly...</p>
      </motion.div>
    )
  }

  // renderVisual, renderConcreteVisual, renderPictorialVisual, renderAbstractVisual (keep as is)
  const renderVisual = () => {
    const question = currentQuestion
    switch (question.type) {
      case "concrete": return renderConcreteVisual(question.visualData.blocks || [])
      case "pictorial": return renderPictorialVisual(question.visualData.circles || [])
      case "abstract": return renderAbstractVisual(question.visualData.equation)
      default: return null
    }
  }
  const renderConcreteVisual = (blocks: number[]) => {
    return (<div className="flex flex-col items-center"><div className="flex flex-wrap items-center justify-center gap-4 md:gap-8 mb-4 min-h-[80px] md:min-h-[100px]">{blocks.map((count, groupIndex) => (<div key={`group-${groupIndex}`} className="flex flex-wrap gap-2 max-w-[180px] justify-center">{Array.from({ length: count }).map((_, i) => (<motion.div key={`block-${groupIndex}-${i}`} initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: i * 0.1, duration: 0.3 }} className={`w-8 h-8 md:w-10 md:h-10 ${groupIndex === 0 ? "bg-red-600" : "bg-blue-600"} rounded-md flex items-center justify-center text-white font-bold shadow-md`}></motion.div>))}</div>))}</div></div>)
  }
  const renderPictorialVisual = (circles: number[]) => {
     return (<div className="flex flex-col items-center"><div className="flex flex-wrap items-center justify-center gap-6 md:gap-10 mb-4 min-h-[120px] md:min-h-[140px]">{circles.map((count, groupIndex) => (<div key={`circle-group-${groupIndex}`} className="relative h-[120px] w-[120px] md:h-[140px] md:w-[140px]">{Array.from({ length: count }).map((_, i) => { const angle = (i / count) * Math.PI * 2 - Math.PI / 2; const radius = count <= 5 ? 40 : 50; const centerX = 60 + (140 - 120)/2; const centerY = 60 + (140 - 120)/2; const itemSize = 28; const x = centerX + radius * Math.cos(angle) - itemSize / 2; const y = centerY + radius * Math.sin(angle) - itemSize / 2; return (<motion.div key={`circle-${groupIndex}-${i}`} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.1, duration: 0.3 }} className="absolute w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-md" style={{ left: `${x}px`, top: `${y}px`, backgroundColor: groupIndex === 0 ? "#6d28d9" : "#4338ca", }}></motion.div>) })}</div>))}</div></div>)
   }
   const renderAbstractVisual = (equation: any) => {
    if (!equation) return null
    const { num1, num2, operation } = equation
    let symbol = "+"; if(operation === "-") symbol = "−"; if(operation === "×") symbol = "×"; if(operation === "÷") symbol = "÷";
    return (<div className="flex flex-col items-center justify-center min-h-[80px] md:min-h-[100px]"><motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }} className="text-3xl md:text-4xl lg:text-5xl font-bold text-indigo-900 flex items-center gap-3 md:gap-4"><motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.5 }}>{num1}</motion.span><motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.5 }}>{symbol}</motion.span><motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.5 }}>{num2}</motion.span><motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8, duration: 0.5 }}>=</motion.span><motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0, duration: 0.5 }}>?</motion.span></motion.div></div>)
  }


  return (
    <div className="w-full overflow-x-hidden">
      <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-indigo-50 to-white p-4 relative overflow-x-hidden">
        {/* Background image */}
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
          <img
            src="/images/learning-background.png"
            alt="Magical learning background"
            className="w-full h-full object-cover"
          />
        </div>

        {/* Main container */}
        <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">

          {/* Progress Dots */}
           <ProgressDots
                totalSteps={diagnosticQuestions.length + 3}
                currentStep={showIntro ? 4 : 4 + currentQuestionIndex}
            />

          {/* Content Area */}
          <motion.div
              key={showIntro ? 'intro' : (diagnosticComplete ? 'summary' : currentQuestionIndex)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border border-indigo-100 overflow-hidden p-4 md:p-6 min-h-[400px] md:min-h-[450px] flex flex-col justify-center"
          >
            {showIntro ? (
               <motion.div
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 transition={{ delay: 0.2 }}
                 className="text-center flex flex-col items-center justify-center h-full"
               >
                 <h1 className="text-3xl md:text-4xl font-bold text-indigo-800 mb-4">
                    Alright, {studentName}!
                 </h1>
                 <p className="text-lg md:text-xl text-gray-700 mb-8 max-w-lg mx-auto">
                    Before we start our learning adventure, let's do a quick activity.
                    Just a few questions to see what you already know, so I can help you best!
                 </p>
                 <Button
                   size="lg"
                   onClick={handleStartDiagnostic}
                   className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-full text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-indigo-500/30 hover:shadow-xl border border-indigo-400/30"
                 >
                   Let's Start! <ArrowRightIcon className="ml-2 h-4 w-4" />
                 </Button>
               </motion.div>

            ) : diagnosticComplete ? (
                renderDiagnosticSummary()
            ) : showFeedback ? (
              // Feedback View
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-center px-4 w-full"
              >
                 <h1 className={`text-2xl md:text-3xl font-bold ${isCorrect ? "text-green-700" : "text-orange-700"} mb-3`}>{isCorrect ? "Correct!" : "Not quite right"}</h1>
                 <p className="text-base md:text-lg text-gray-800 mb-3">{isCorrect ? `Well done! ${currentQuestion.correctAnswer} is the correct answer.` : `The correct answer is ${currentQuestion.correctAnswer}.`}</p>
                 <div className="bg-gray-100 p-3 md:p-4 rounded-lg max-w-lg mx-auto border border-gray-200"><p className="text-sm md:text-md text-gray-800">{currentQuestion.explanation}</p></div>
              </motion.div>
            ) : (
              // Question View
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className="text-center w-full px-2 md:px-4 flex flex-col justify-between h-full"
              >
                 <div> {/* Top part: Problem + Visual */}
                    <h1 className="text-xl md:text-2xl font-bold text-indigo-900 mb-4">{currentQuestion.problem}</h1>
                    <div className="mb-4 md:mb-6 flex justify-center">{renderVisual()}</div>
                 </div>
                 <div> {/* Bottom part: Answer display + Number Pad */}
                    <div className="flex justify-center items-center mb-4"><div className="flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[80px] md:min-w-[100px] h-[50px] md:h-[60px] border border-indigo-200 shadow-sm"><span className="text-2xl md:text-3xl font-bold text-indigo-900">{answer || "_"}</span></div></div>
                    <div className="w-full max-w-[250px] md:max-w-[280px] mx-auto"><NumberPad onInput={handleNumberInput} /></div>
                 </div>
              </motion.div>
            )}
          </motion.div>

          {/* Audio Controls */}
          {!showIntro && !diagnosticComplete && (
            <AudioControls
              isPlaying={isAudioPlaying}
              onPlay={handlePlayAudio}
              audioText={showFeedback ? (isCorrect ? "Well done! That's the correct answer." : "Not quite right. Let's look at the explanation.") : (currentQuestion?.audioText || "")}
            />
          )}

          {/* Navigation Buttons */}
          {!showIntro && !diagnosticComplete && !showFeedback && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="mt-4 md:mt-6 flex gap-3 md:gap-4"
            >
              {currentQuestionIndex > 0 && (
                <Button variant="outline" size="lg" onClick={handlePrevious} className="bg-white hover:bg-gray-50 text-indigo-800 border-indigo-300 px-3 md:px-5 py-2 rounded-full text-base md:text-lg shadow-md transition-all duration-300"><ArrowLeftIcon className="mr-1 md:mr-2 h-3 w-3 md:h-4 md:w-4" /> Previous</Button>
              )}
              <Button size="lg" onClick={handleSubmit} className="bg-indigo-800 hover:bg-indigo-900 text-white px-5 md:px-8 py-2 rounded-full text-base md:text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-indigo-600/30 hover:shadow-xl border border-indigo-500/30" disabled={!answer || showFeedback}><ArrowRightIcon className="ml-1 md:ml-2 h-3 w-3 md:h-4 md:w-4" /> Check Answer </Button>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}