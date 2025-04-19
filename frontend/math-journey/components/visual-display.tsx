import Image from "next/image"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface VisualDisplayProps {
  visual?: {
    url: string
    type: "concrete" | "pictorial" | "abstract"
    alt: string
  }
}

export default function VisualDisplay({ visual }: VisualDisplayProps) {
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

      <div className="relative h-48 w-full overflow-hidden rounded-lg border border-gray-200">
        <Image src={visual.url || "/placeholder.svg"} alt={visual.alt} fill className="object-contain" />
      </div>
    </div>
  )
}
