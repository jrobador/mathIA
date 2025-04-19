import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowRightIcon } from "@radix-ui/react-icons"

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/30 to-indigo-900/60 mix-blend-multiply" />
        <img
          src="/images/learning-background.png"
          alt="Magical learning background"
          className="w-full h-full object-cover"
        />
      </div>

      <div 
        className="max-w-3xl w-full text-center z-10 bg-white/20 backdrop-blur-lg rounded-3xl p-8 shadow-xl"
        style={{ 
          boxShadow: "0 0 20px 5px rgba(255, 255, 255, 0.2), 0 8px 25px -5px rgba(0, 0, 0, 0.1)",
          background: "linear-gradient(135deg, rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0.15))"
        }}
      >
        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 tracking-tight drop-shadow-lg font-serif">
          Math Journey
        </h1>

        <div 
          className="relative w-full aspect-video max-w-2xl mx-auto mb-8 rounded-2xl overflow-hidden bg-white/30 backdrop-blur-md"
          style={{ 
            boxShadow: "0 0 15px 3px rgba(255, 255, 255, 0.15), 0 8px 20px -4px rgba(0, 0, 0, 0.1)",
            background: "linear-gradient(135deg, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0.15))"
          }}>
          <div className="absolute inset-0 flex items-center justify-center">
            <img
              src="/images/logo.png"
              alt="Math Journey Logo"
              className="w-auto h-5/6 object-contain drop-shadow-lg"
            />
          </div>
        </div>

        <p className="text-xl text-white mb-10 max-w-lg mx-auto drop-shadow-md">
          An immersive journey to master mathematics through visual learning and guided discovery
        </p>

        <Link href="/name">
          <Button
            size="lg"
            className="bg-indigo-600/80 hover:bg-indigo-700/90 text-white px-10 py-7 rounded-full text-xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-indigo-500/30 hover:shadow-xl backdrop-blur-sm border border-indigo-400/30"
          >
            Begin Journey <ArrowRightIcon className="ml-2 h-5 w-5" />
          </Button>
        </Link>
      </div>
    </main>
  )
}