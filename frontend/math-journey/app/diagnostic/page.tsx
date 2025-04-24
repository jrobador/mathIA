"use client"

import { useState, useEffect, useRef } from "react"
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
  id: number
  question_id: string
  type: QuestionType
  difficulty: DifficultySetting
  problem: string
  audioSrc: string
  visualData: {
    blocks?: number[]
    circles?: number[]
    equation?: {
      num1: number // Dividend for division
      num2: number // Divisor for division
      operation: "+" | "-" | "×" | "÷"
    }
  }
  correctAnswer: string
  explanation: string
  conceptTested: string
}

// Question bank with kid-friendly explanations (no changes needed from previous version)
const diagnosticQuestions: DiagnosticQuestion[] = [
    {
    id: 1,
    question_id: "diag_q1_concrete_count",
    type: "concrete",
    difficulty: DifficultySetting.INITIAL,
    problem: "How many blocks are there in total?",
    audioSrc: "/audios/diagnostic_1.mp3",
    visualData: { blocks: [3, 2] },
    correctAnswer: "5",
    explanation: "Look! We have 3 red blocks and 2 blue blocks. Let's count them all together: 1, 2, 3... 4, 5! So, 3 + 2 = 5 blocks.",
    conceptTested: "Counting and quantity recognition",
  },
  {
    id: 2,
    question_id: "diag_q2_pictorial_add",
    type: "pictorial",
    difficulty: DifficultySetting.BEGINNER,
    problem: "How many circles are there in total?",
    audioSrc: "/audios/diagnostic_2.mp3",
    visualData: { circles: [4, 3] },
    correctAnswer: "7",
    explanation: "See the two groups? One has 4 circles, the other has 3. If we join them, like bringing friends together, we have 4 + 3 = 7 circles playing!",
    conceptTested: "Basic addition with pictorial representation",
  },
  {
    id: 3,
    question_id: "diag_q3_abstract_add",
    type: "abstract",
    difficulty: DifficultySetting.BEGINNER,
    problem: "7 + 5 = ?",
    audioSrc: "/audios/diagnostic_3.mp3",
    visualData: { equation: { num1: 7, num2: 5, operation: "+" } },
    correctAnswer: "12",
    explanation: "Let's stack them up! Put the 7 on top and the 5 right below it in the ones place. Now add down the column: 7 plus 5 makes 12. Great job!",
    conceptTested: "Addition with numbers up to 20",
  },
  {
    id: 4,
    question_id: "diag_q4_abstract_sub",
    type: "abstract",
    difficulty: DifficultySetting.INTERMEDIATE,
    problem: "15 - 8 = ?",
    audioSrc: "/audios/diagnostic_4.mp3",
    visualData: { equation: { num1: 15, num2: 8, operation: "-" } },
    correctAnswer: "7",
    explanation: "Stack 'em up again: 15 on top, 8 below. Can we do 5 take away 8? Nope! So, we 'borrow' 1 ten from the left, making the 5 into 15. Now, 15 take away 8 is 7!",
    conceptTested: "Subtraction with numbers up to 20",
  },
  {
    id: 5,
    question_id: "diag_q5_abstract_mul",
    type: "abstract",
    difficulty: DifficultySetting.INTERMEDIATE,
    problem: "4 × 3 = ?",
    audioSrc: "/audios/diagnostic_5.mp3",
    visualData: { equation: { num1: 4, num2: 3, operation: "×" } },
    correctAnswer: "12",
    explanation: "4 × 3 means 4 groups of 3. We can line them up: the 4 on top, the 3 below. Then multiply: 3 times 4 is 12. It's like counting 3 four times: 3, 6, 9, 12!",
    conceptTested: "Basic multiplication",
  },
  {
    id: 6,
    question_id: "diag_q6_abstract_div",
    type: "abstract",
    difficulty: DifficultySetting.ADVANCED,
    problem: "20 ÷ 4 = ?",
    audioSrc: "/audios/diagnostic_6.mp3",
    visualData: { equation: { num1: 20, num2: 4, operation: "÷" } }, // num1 is dividend, num2 is divisor
    correctAnswer: "5",
    // Updated Explanation for the new visual
    explanation: "Let's set up the division! The number being shared (20) is first. Then comes a line, and the number we are dividing by (4) is next, with a line under it. We need to find the answer (?) that goes above the 4. How many times does 4 fit into 20? Let's count by 4s: 4, 8, 12, 16, 20. That's 5 times! So the answer is 5.",
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

// --- DiagnosticPage Component ---
// (Keep the rest of the component code exactly the same as the previous version:
// useState, useEffect, handlers, summary render, concrete/pictorial renders, main JSX structure)
// ... (Paste the entire DiagnosticPage component code from the previous response here) ...
// --- Only replace the renderAbstractVisual function below ---

export default function DiagnosticPage() {
  const router = useRouter()
  const [studentName, setStudentName] = useState("")
  const [showIntro, setShowIntro] = useState(true)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answer, setAnswer] = useState("")
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [audioReady, setAudioReady] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [results, setResults] = useState<{ id: number; correct: boolean }[]>([])
  const [diagnosticComplete, setDiagnosticComplete] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const currentQuestion = diagnosticQuestions[currentQuestionIndex]

  // useEffect hooks (keep as is from previous version)
  useEffect(() => {
    const name = localStorage.getItem("studentName") || "friend"
    setStudentName(name)
  }, [])

  useEffect(() => {
    if (!showIntro && !diagnosticComplete && !showFeedback && audioRef.current && currentQuestion?.audioSrc) {
       // Attempt to play only if src is loaded and ready state allows
       const playAudio = () => {
         audioRef.current?.play()
           .then(() => setIsAudioPlaying(true))
           .catch(error => {
             console.warn("Audio auto-play failed (user interaction might be needed):", error);
             // Might need a button press to enable audio initially in some browsers
             setIsAudioPlaying(false);
           });
       };

       // Use a timeout to allow component rendering and audio loading
       const timer = setTimeout(playAudio, 500);
       return () => clearTimeout(timer);
     } else if (audioRef.current) {
       // Pause if conditions are not met
       audioRef.current.pause();
       setIsAudioPlaying(false);
     }
  }, [currentQuestionIndex, showIntro, diagnosticComplete, showFeedback, currentQuestion?.audioSrc]); // Add audioSrc dependency


  useEffect(() => {
    const audio = audioRef.current
    const handleEnded = () => {
      setAudioReady(true)
      setIsAudioPlaying(false)
    }
     const handleCanPlay = () => {
      setAudioReady(true);
    }
    const handleLoadStart = () => {
      setIsAudioPlaying(false);
      setAudioReady(false); // Reset ready state on new load
    }

    if (audio) {
      audio.addEventListener('ended', handleEnded)
      audio.addEventListener('canplay', handleCanPlay);
      audio.addEventListener('loadstart', handleLoadStart); // Reset on new src load

       // Initial check in case already ready
       if (audio.readyState >= 3) { // HAVE_FUTURE_DATA or more
         setAudioReady(true);
       }

      return () => {
        audio.removeEventListener('ended', handleEnded)
        audio.removeEventListener('canplay', handleCanPlay);
        audio.removeEventListener('loadstart', handleLoadStart);
      }
    }
  }, [currentQuestion?.audioSrc]) // Re-attach listeners if audio element src changes

  // Event handlers (keep as is from previous version)
   const handleStartDiagnostic = () => {
    setShowIntro(false);
    // Audio will attempt to play via useEffect
  }

  const handleSubmit = () => {
    const isAnswerCorrect = answer === currentQuestion.correctAnswer;
    setIsCorrect(isAnswerCorrect);
    setShowFeedback(true);
    setAudioReady(false);

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsAudioPlaying(false);
    }

    const currentResult = { id: currentQuestion.id, correct: isAnswerCorrect };
    const updatedResults = [...results, currentResult];
    setResults(updatedResults);

    setTimeout(() => {
      setShowFeedback(false);
      setAnswer("");
      // setIsAudioPlaying(false); // Handled by useEffect on index change
      // setAudioReady(false); // Handled by useEffect on index change

      if (currentQuestionIndex < diagnosticQuestions.length - 1) {
        setCurrentQuestionIndex((prev) => prev + 1);
      } else {
        setDiagnosticComplete(true);
        const correctAnswers = updatedResults.filter((r) => r.correct).length;
        const totalQuestions = diagnosticQuestions.length;
        const percentCorrect = Math.round((correctAnswers / totalQuestions) * 100);
        let recommendedLevel: DifficultySetting = DifficultySetting.INITIAL;
        if (percentCorrect >= 80) recommendedLevel = DifficultySetting.ADVANCED;
        else if (percentCorrect >= 50) recommendedLevel = DifficultySetting.INTERMEDIATE;
        else if (percentCorrect >= 30) recommendedLevel = DifficultySetting.BEGINNER;

        const apiQuestionResults: ApiDiagnosticQuestionResult[] = updatedResults.map((result) => {
          const question = diagnosticQuestions.find(q => q.id === result.id);
          return {
            question_id: question?.question_id || `unknown_q${result.id}`,
            correct: result.correct,
            concept_tested: question?.conceptTested,
          };
        });

        const fullResultsObject: DiagnosticResults = {
          score: percentCorrect,
          correct_answers: correctAnswers,
          total_questions: totalQuestions,
          recommended_level: recommendedLevel,
          question_results: apiQuestionResults,
        };

        localStorage.setItem("diagnosticResults", JSON.stringify(fullResultsObject));
        localStorage.setItem("studentLevel", recommendedLevel);

        setTimeout(() => router.push("/learning-path"), 3000);
      }
    }, 3500);
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
       if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        setIsAudioPlaying(false);
       }
      setCurrentQuestionIndex((prev) => prev - 1)
      setAnswer("")
      setShowFeedback(false)
      // setIsAudioPlaying(false); // Handled by useEffect
      // setAudioReady(false); // Handled by useEffect
      setResults(prev => prev.slice(0, -1));
    }
  }

   const handlePlayAudio = () => {
    if (!showIntro && !diagnosticComplete && audioRef.current && audioReady) { // Check if ready
      audioRef.current.currentTime = 0
      audioRef.current.play()
         .then(() => setIsAudioPlaying(true))
         .catch(error => console.error("Audio play failed:", error));
      // Don't set audioReady false on replay, it should still be ready
    } else if (!audioReady) {
        console.log("Audio not ready yet.");
        // Optionally trigger a load if needed, though preload="auto" should handle it
        // audioRef.current?.load();
    }
  }

  const handleNumberInput = (num: string) => {
    if (showFeedback) return;

    if (num === "clear") {
      setAnswer("")
    } else if (num === "backspace") {
      setAnswer((prev) => prev.slice(0, -1))
    } else {
      if (answer.length < 3) { // Keep length limit
        setAnswer((prev) => prev + num)
      }
    }
  }

  // renderDiagnosticSummary (keep as is from previous version)
  const renderDiagnosticSummary = () => {
    const correctAnswers = results.filter((r) => r.correct).length
    const totalQuestions = diagnosticQuestions.length
    const percentCorrect = Math.round((correctAnswers / totalQuestions) * 100)
    const finalLevel = localStorage.getItem("studentLevel") || "initial"

    let levelText = "Initial Level", levelDescription = "We'll start with the most basic concepts to build a solid foundation.", levelColor = "text-blue-700"
    if (finalLevel === "advanced") { levelText = "Advanced Level"; levelDescription = "Excellent! You have a good grasp of fundamental concepts. We'll work on more complex challenges."; levelColor = "text-purple-700"; }
    else if (finalLevel === "intermediate") { levelText = "Intermediate Level"; levelDescription = "You have a good understanding of several concepts. We'll continue reinforcing and advancing."; levelColor = "text-indigo-700"; }
    else if (finalLevel === "beginner") { levelText = "Beginner Level"; levelDescription = "You know some basic concepts. We'll work on strengthening your understanding."; levelColor = "text-green-700"; }

    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center w-full px-2 md:px-4">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Diagnostic Completed!</h1>
        <div className="mb-6">
          <div className="text-xl md:text-2xl mb-2">Your score: <span className="font-bold">{correctAnswers} out of {totalQuestions}</span></div>
          <div className="w-full bg-gray-200 rounded-full h-4 mb-4"><div className="bg-indigo-700 h-4 rounded-full" style={{ width: `${percentCorrect}%` }}></div></div>
        </div>
        <h2 className={`text-2xl md:text-3xl font-bold mb-2 ${levelColor}`}>{levelText}</h2>
        <p className="text-lg md:text-xl text-gray-700 mb-6">{levelDescription}</p>
        <p className="text-lg">Get ready! We're finding the perfect learning spot for you...</p>
      </motion.div>
    )
  }

  // renderVisual, renderConcreteVisual, renderPictorialVisual (keep as is)
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
    // Ensure unique keys if multiple groups have same count
    let blockCounter = 0;
    return (<div className="flex flex-col items-center"><div className="flex flex-wrap items-center justify-center gap-4 md:gap-8 mb-4 min-h-[80px] md:min-h-[100px]">{blocks.map((count, groupIndex) => (<div key={`group-${groupIndex}`} className="flex flex-wrap gap-2 max-w-[180px] justify-center">{Array.from({ length: count }).map((_, i) => (<motion.div key={`block-${blockCounter++}`} initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: i * 0.05, duration: 0.3 }} className={`w-8 h-8 md:w-10 md:h-10 ${groupIndex === 0 ? "bg-red-600" : "bg-blue-600"} rounded-md flex items-center justify-center text-white font-bold shadow-md`}></motion.div>))}</div>))}</div></div>)
  }

  const renderPictorialVisual = (circles: number[]) => {
     // Ensure unique keys
     let circleCounter = 0;
     return (<div className="flex flex-col items-center"><div className="flex flex-wrap items-center justify-center gap-6 md:gap-10 mb-4 min-h-[120px] md:min-h-[140px]">{circles.map((count, groupIndex) => (<div key={`circle-group-${groupIndex}`} className="relative h-[120px] w-[120px] md:h-[140px] md:w-[140px]">{Array.from({ length: count }).map((_, i) => { const angle = (i / count) * Math.PI * 2 - Math.PI / 2; const radius = count <= 5 ? 40 : 50; const centerX = 60 + (140 - 120)/2; const centerY = 60 + (140 - 120)/2; const itemSize = 28; const x = centerX + radius * Math.cos(angle) - itemSize / 2; const y = centerY + radius * Math.sin(angle) - itemSize / 2; return (<motion.div key={`circle-${circleCounter++}`} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.1, duration: 0.3 }} className="absolute w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-md" style={{ left: `${x}px`, top: `${y}px`, backgroundColor: groupIndex === 0 ? "#6d28d9" : "#4338ca", }}></motion.div>) })}</div>))}</div></div>)
   }

  // --- UPDATED renderAbstractVisual ---
  const renderAbstractVisual = (equation: any) => {
    if (!equation) return null;
    // num1 is dividend, num2 is divisor for division
    const { num1, num2, operation } = equation;
    const num1Str = String(num1);
    const num2Str = String(num2); // Divisor for division

    const fontClass = "font-mono"; // Monospace for better alignment

    // --- Columnar Addition, Subtraction, Multiplication ---
    if (operation === "+" || operation === "-" || operation === "×") {
      const symbol = operation === "-" ? "−" : operation;
      const maxLen = Math.max(num1Str.length, num2Str.length);
       // Add 1 for operator space if needed, or handle alignment differently
      const totalWidth = Math.max(num1Str.length, num2Str.length + 2); // Ensure width accounts for operator

      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center justify-center min-h-[100px] md:min-h-[120px]"
        >
          <div
            className={`inline-flex flex-col items-end ${fontClass} text-3xl md:text-4xl lg:text-5xl font-bold text-indigo-900 space-y-1`}
            style={{ minWidth: `${totalWidth}ch` }} // Use calculated width
          >
            {/* Number 1 (right aligned) */}
            <span className="w-full text-right pr-1">{num1Str}</span>

            {/* Operator and Number 2 */}
            <div className="flex items-center w-full">
              {/* Operator aligned left within its space */}
              <span className="w-6 text-left">{symbol}</span>
              {/* Number 2 right aligned */}
              <span className="flex-1 text-right pr-1">{num2Str}</span>
            </div>

            {/* Divider Line */}
            <hr className={`w-full border-t-2 border-indigo-800 mt-1 mb-1`} />

            {/* Answer Placeholder (right aligned) */}
            <span className="w-full text-right pr-1 text-gray-400 text-3xl md:text-4xl">?</span>
          </div>
        </motion.div>
      );
    }

    // --- Division (Dividend | Divisor with line under Divisor) ---
    if (operation === "÷") {
      // num1 = Dividend (goes inside)
      // num2 = Divisor (goes outside left)
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          // Add padding top to make space for the answer '?'
          className="flex items-center justify-center min-h-[100px] md:min-h-[120px] relative pt-10 md:pt-12" // Added padding top
        >
          <div className={`flex items-start ${fontClass} text-3xl md:text-4xl lg:text-5xl font-bold text-indigo-900`}>
            {/* Divisor (num2) */}
            <span className="mr-1 mt-1">{num2Str}</span>

            {/* Box Symbol (Vertical line + Vinculum/horizontal line over dividend) */}
            <div className="relative border-l-2 border-indigo-800 pl-2">
              {/* Vinculum (line over dividend) */}
              <div className="border-t-2 border-indigo-800 px-2 py-1">
                {/* Dividend (num1) */}
                <span>{num1Str}</span>
              </div>
              {/* Answer Placeholder (Absolutely positioned ABOVE the vinculum) */}
              <span className="absolute -top-10 right-0 left-0 text-center text-gray-400 text-3xl md:text-4xl">
                 ?
              </span>
            </div>
          </div>
        </motion.div>
      );
    }


    // Fallback
    return (
      <div className="text-xl text-red-500">
        Visual not available
      </div>
    );
  };

   // --- Component Return (JSX) ---
   // (Ensure this part is identical to the previous version's return statement)
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

        {/* Audio element */}
        <audio
          key={currentQuestion?.audioSrc} // Force re-render on src change
          ref={audioRef}
          src={currentQuestion?.audioSrc}
          preload="auto"
          // onCanPlay={() => setAudioReady(true)} // Handled in useEffect
          // onEnded={() => setIsAudioPlaying(false)} // Handled in useEffect
        />


        {/* Main container */}
        <div className="max-w-4xl w-full flex flex-col items-center z-10 bg-white/30 backdrop-blur-md rounded-3xl p-4 md:p-6 border border-white/40 shadow-xl overflow-hidden">

          {/* Progress Dots */}
           <ProgressDots
                totalSteps={diagnosticQuestions.length + 3}
                currentStep={showIntro ? 4 : 4 + currentQuestionIndex}
            />

          {/* Content Area */}
          <motion.div
              key={showIntro ? 'intro' : (diagnosticComplete ? 'summary' : `question-${currentQuestionIndex}`)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              // Adjust min-height as needed based on content
              className="w-full max-w-3xl bg-white rounded-2xl shadow-xl my-4 md:my-6 relative border border-indigo-100 overflow-hidden p-4 md:p-6 min-h-[450px] md:min-h-[500px] flex flex-col justify-between"
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
                <div className="flex items-center justify-center h-full">
                   {renderDiagnosticSummary()}
                </div>
            ) : showFeedback ? (
              // Feedback View
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-center px-4 w-full flex flex-col items-center justify-center h-full"
              >
                 <h1 className={`text-3xl md:text-4xl font-bold ${isCorrect ? "text-green-600" : "text-orange-600"} mb-4`}>{isCorrect ? "Correct! 🎉" : "Not quite..."}</h1>
                 <p className="text-lg md:text-xl text-gray-800 mb-4">{isCorrect ? `Awesome! ${currentQuestion.correctAnswer} is the right answer.` : `That's okay! The correct answer is ${currentQuestion.correctAnswer}.`}</p>
                 <div className="bg-gray-100 p-4 rounded-lg max-w-lg mx-auto border border-gray-200 shadow-inner">
                    <p className="text-md md:text-lg text-gray-700 font-medium">Here's how:</p>
                    <p className="text-md md:text-lg text-gray-800 mt-1">{currentQuestion.explanation}</p>
                 </div>
              </motion.div>
            ) : (
              // Question View
              <motion.div
                className="text-center w-full px-2 md:px-4 flex flex-col justify-between h-full"
              >
                 {/* Top part: Problem + Visual */}
                 <div className="flex-grow flex flex-col">
                    <h1 className="text-xl md:text-2xl lg:text-3xl font-semibold text-indigo-900 mb-4">{currentQuestion.problem}</h1>
                    <div className="flex-grow flex justify-center items-center mb-4 md:mb-6 min-h-[150px]">
                       {renderVisual()}
                    </div>
                 </div>

                 {/* Bottom part: Answer display + Number Pad */}
                 <div className="mt-auto flex-shrink-0">
                    <div className="flex justify-center items-center mb-4">
                        <div className="flex items-center justify-center bg-indigo-100 rounded-xl px-4 md:px-6 py-2 md:py-3 min-w-[80px] md:min-w-[100px] h-[50px] md:h-[60px] border-2 border-indigo-300 shadow-inner">
                            <span className="text-2xl md:text-3xl font-bold text-indigo-900 tracking-wider">{answer || "_"}</span>
                        </div>
                    </div>
                    <div className="w-full max-w-[250px] md:max-w-[280px] mx-auto">
                        <NumberPad onInput={handleNumberInput} />
                    </div>
                 </div>
              </motion.div>
            )}
          </motion.div>

          {/* Audio Controls */}
          {!showIntro && !diagnosticComplete && !showFeedback && (
            <AudioControls
              isPlaying={isAudioPlaying}
              onPlay={handlePlayAudio}
              audioText=""
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
              <Button size="lg" onClick={handleSubmit} className="bg-green-600 hover:bg-green-700 text-white px-5 md:px-8 py-2 rounded-full text-base md:text-lg shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-green-600/30 hover:shadow-xl border border-green-400/30" disabled={!answer || showFeedback}>
                Check Answer <ArrowRightIcon className="ml-1 md:ml-2 h-3 w-3 md:h-4 md:w-4" />
               </Button>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}