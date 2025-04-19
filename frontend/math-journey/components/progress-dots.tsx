interface ProgressDotsProps {
  totalSteps: number
  currentStep: number
}

export default function ProgressDots({ totalSteps, currentStep }: ProgressDotsProps) {
  return (
    <div className="flex justify-center space-x-2 mb-8">
      {Array.from({ length: totalSteps }).map((_, index) => (
        <div
          key={index}
          className={`h-2.5 w-2.5 rounded-full transition-all duration-300 ${
            index + 1 === currentStep
              ? "bg-indigo-600 scale-125"
              : index + 1 < currentStep
                ? "bg-indigo-400"
                : "bg-gray-300"
          }`}
        />
      ))}
    </div>
  )
}
