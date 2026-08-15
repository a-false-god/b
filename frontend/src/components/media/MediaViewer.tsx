import { useState } from "react"
import { ImageOff, Film, Image as ImageIcon } from "lucide-react"

interface MediaViewerProps {
  media?: string | null
  mediaKind?: string | null
  className?: string
}

export function MediaViewer({ media, mediaKind, className = "" }: MediaViewerProps) {
  const [hasError, setHasError] = useState(false)

  // Reset error state when media filename changes
  const [currentMedia, setCurrentMedia] = useState(media)
  if (media !== currentMedia) {
    setCurrentMedia(media)
    setHasError(false)
  }

  if (!media) {
    return (
      <div
        className={`w-full aspect-video rounded-[12px] border border-border bg-secondary/30 flex flex-col items-center justify-center text-muted-foreground select-none p-4 text-center ${className}`}
      >
        <ImageIcon className="w-8 h-8 mb-2 text-muted-foreground/50" />
        <span className="text-xs font-mono font-medium text-muted-foreground">
          Pytanie bez pliku multimedialnego
        </span>
      </div>
    )
  }

  const isVideo =
    mediaKind === "video" ||
    media.toLowerCase().endsWith(".mp4") ||
    media.toLowerCase().endsWith(".wmv")

  const mediaUrl = `/media/${media}`

  if (hasError) {
    return (
      <div
        className={`w-full aspect-video rounded-[12px] border border-border bg-secondary/40 flex flex-col items-center justify-center text-muted-foreground select-none p-4 text-center ${className}`}
      >
        {isVideo ? (
          <Film className="w-8 h-8 mb-2 text-accent/70" />
        ) : (
          <ImageOff className="w-8 h-8 mb-2 text-muted-foreground/60" />
        )}
        <span className="text-xs font-semibold text-foreground/80 mb-0.5">
          {isVideo ? "Materiał wideo" : "Ilustracja sytuacyjna"}
        </span>
        <span className="text-[11px] font-mono text-muted-foreground max-w-[90%] truncate">
          {media}
        </span>
      </div>
    )
  }

  return (
    <div
      className={`w-full aspect-video rounded-[12px] overflow-hidden border border-border bg-black/90 flex items-center justify-center relative ${className}`}
    >
      {isVideo ? (
        <video
          key={media}
          src={mediaUrl}
          playsInline
          preload="metadata"
          autoPlay
          muted
          loop
          controls
          className="w-full h-full object-contain"
          onError={() => setHasError(true)}
        />
      ) : (
        <img
          key={media}
          src={mediaUrl}
          alt="Materiał sytuacyjny do pytania"
          loading="lazy"
          className="w-full h-full object-contain"
          onError={() => setHasError(true)}
        />
      )}
    </div>
  )
}
