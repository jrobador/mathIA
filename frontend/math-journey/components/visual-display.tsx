"use client"

import { useState } from "react"
import Image from "next/image"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, AlertCircle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface VisualDisplayProps {
  visual?: {
    url: string
    type: "concrete" | "pictorial" | "abstract"
    alt: string
  }
}

export default function VisualDisplay({ visual }: VisualDisplayProps) {
  const [isLoading, setIsLoading] = useState(visual ? true : false)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  // Handle retry for failed images
  const handleRetry = () => {
    if (!visual) return
    
    setIsLoading(true)
    setError(null)
    setRetryCount(prev => prev + 1)
  }

  if (!visual) {
    return (
      <div className="flex items-center justify-center h-48 bg-gray-100 rounded-lg">
        <p className="text-gray-500 text-sm">No visual aid available yet</p>
      </div>
    )
  }

  return (
    <div>
      <Tabs defaultValue={visual.type} className="mb-2">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger
            value="concrete"
            disabled={visual.type !== "concrete"}
            className={visual.type === "concrete" ? "text-blue-700" : ""}
          >
            Concrete
          </TabsTrigger>
          <TabsTrigger
            value="pictorial"
            disabled={visual.type !== "pictorial"}
            className={visual.type === "pictorial" ? "text-blue-700" : ""}
          >
            Pictorial
          </TabsTrigger>
          <TabsTrigger
            value="abstract"
            disabled={visual.type !== "abstract"}
            className={visual.type === "abstract" ? "text-blue-700" : ""}
          >
            Abstract
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="relative h-48 w-full overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
            <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100 z-10 p-4">
            <AlertCircle className="h-6 w-6 text-red-500 mb-2" />
            <p className="text-red-700 text-sm text-center mb-2">{error}</p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleRetry} 
              className="flex items-center"
            >
              <RefreshCw className="h-4 w-4 mr-1" /> Reload Image
            </Button>
          </div>
        )}

        <Image 
          src={`${visual.url}${retryCount > 0 ? `?retry=${retryCount}` : ''}`}
          alt={visual.alt} 
          fill 
          className="object-contain"
          onLoadStart={() => setIsLoading(true)}
          onLoad={() => {
            setIsLoading(false)
            setError(null)
          }}
          onError={() => {
            setIsLoading(false)
            setError("Unable to load visual aid")
          }}
        />
      </div>
      
      <div className="mt-2">
        <p className="text-xs text-gray-500">
          {visual.type === "concrete" 
            ? "Physical representation using real-world objects" 
            : visual.type === "pictorial" 
              ? "Visual model representation of the concept"
              : "Abstract mathematical symbols and notation"
          }
        </p>
      </div>
    </div>
  )
}