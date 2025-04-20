"use client"

import { useState, useEffect } from "react"
import Image from "next/image"
import { Loader2, AlertCircle, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface VisualProp {
  url: string;
  alt: string;
}

interface VisualDisplayProps {
  visual?: VisualProp 
}

export default function VisualDisplay({ visual }: VisualDisplayProps) {
  const [isLoading, setIsLoading] = useState(visual ? true : false)
  const [error, setError] = useState<string | null>(null)
  const [imageKey, setImageKey] = useState(visual?.url || Date.now().toString());

  useEffect(() => {
    if (visual) {
      setIsLoading(true);
      setError(null);
      setImageKey(visual.url);
    } else {
      setIsLoading(false);
      setError(null);
    }
  }, [visual?.url]);

  const handleRetry = () => {
    if (!visual) return;
    setIsLoading(true);
    setError(null);
    setImageKey(`${visual.url}?retry=${Date.now()}`);
  };

  if (!visual) {
    return (
      <div className="flex items-center justify-center h-48 bg-gray-100 rounded-lg">
        <p className="text-gray-500 text-sm">No visual aid available</p>
      </div>
    )
  }

  return (
    <div>
      {/* Visual Area */}
      <div className="relative h-48 w-full overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
        {isLoading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100/80 z-10">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-50 z-10 p-4">
            <AlertCircle className="h-6 w-6 text-red-500 mb-2" />
            <p className="text-red-700 text-sm text-center mb-2">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              className="flex items-center text-xs h-7"
            >
              <RefreshCw className="h-3 w-3 mr-1" /> Retry
            </Button>
          </div>
        )}

        <Image
          key={imageKey}
          src={visual.url}
          alt={visual.alt}
          fill
          className="object-contain p-2"
          onLoad={() => {
            setIsLoading(false);
            setError(null);
          }}
          onError={() => {
            setIsLoading(false);
            setError("Unable to load visual aid");
          }}
          unoptimized={visual.url.includes("localhost")}
        />
      </div>
      {/* Optional: Add a caption or context if needed */}
      {/* <p className="text-xs text-gray-500 mt-1">{visual.alt}</p> */}
    </div>
  )
}