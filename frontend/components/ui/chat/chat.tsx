"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import {
  Check,
  CheckCheck,
  ArrowUp,
  ChevronDown,
  Clock,
  AlertCircle,
  Reply,
  SmilePlus,
  MoreHorizontal,
  Pin,
  Pencil,
  Trash2,
  X,
  Paperclip,
  Image as ImageIcon,
  Smile,
  Upload,
  Plus,
  Play,
  Pause,
  Mic,
} from "lucide-react"
import { createPortal } from "react-dom"
import type {
  ChatUser,
  ChatConfig,
  ChatMessageData,
  MessageGroup,
  TypingUser,
  ChatTheme,
} from "./types"
import {
  groupMessages,
  useAutoScroll,
  useAutoResize,
  useTypingIndicator,
  formatTimestamp,
} from "./hooks"
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/prompt-kit/chain-of-thought"
import { ListChecks } from "lucide-react"

// ─── Context ──────────────────────────────────────────────────────────────────

const ChatContext = React.createContext<ChatConfig | null>(null)

function useChatContext() {
  const ctx = React.useContext(ChatContext)
  if (!ctx)
    throw new Error("Chat components must be wrapped in <ChatProvider>")
  return ctx
}

// ─── ChatProvider ─────────────────────────────────────────────────────────────

interface ChatProviderProps {
  currentUser: ChatUser
  theme?: ChatTheme
  dateFormat?: "relative" | "absolute" | "time-only"
  messageGroupingInterval?: number
  onReactionAdd?: (messageId: string, emoji: string) => void
  onReactionRemove?: (messageId: string, emoji: string) => void
  onReply?: (message: ChatMessageData) => void
  onEdit?: (message: ChatMessageData) => void
  onDelete?: (messageId: string) => void
  onPin?: (messageId: string) => void
  children: React.ReactNode
  style?: React.CSSProperties
  className?: string
}

function ChatProvider({
  currentUser,
  theme = "lunar",
  dateFormat = "relative",
  messageGroupingInterval = 120,
  onReactionAdd,
  onReactionRemove,
  onReply,
  onEdit,
  onDelete,
  onPin,
  children,
  style,
  className,
}: ChatProviderProps) {
  const config = React.useMemo<ChatConfig>(
    () => ({
      currentUser,
      dateFormat,
      messageGroupingInterval,
      onReactionAdd,
      onReactionRemove,
      onReply,
      onEdit,
      onDelete,
      onPin,
    }),
    [currentUser, dateFormat, messageGroupingInterval, onReactionAdd, onReactionRemove, onReply, onEdit, onDelete, onPin]
  )

  return (
    <ChatContext.Provider value={config}>
      <div data-chat-theme={theme} style={style} className={className}>
        {children}
      </div>
    </ChatContext.Provider>
  )
}

// ─── Quick emoji picker (6 common reactions) ──────────────────────────────────

const QUICK_REACTIONS = ["\u{1F44D}", "\u{2764}\u{FE0F}", "\u{1F602}", "\u{1F62E}", "\u{1F64F}", "\u{1F525}"]

function QuickReactionPicker({
  onSelect,
  onClose,
}: {
  onSelect: (emoji: string) => void
  onClose: () => void
}) {
  return (
    <div
      className="chat-toolbar-enter flex items-center gap-0.5 rounded-[10px] border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] p-1 shadow-[var(--chat-shadow-toolbar)]"
      onMouseLeave={onClose}
    >
      {QUICK_REACTIONS.map((emoji) => (
        <button
          key={emoji}
          onClick={() => {
            onSelect(emoji)
            onClose()
          }}
          className="flex size-8 items-center justify-center rounded-lg text-lg transition-transform hover:scale-125 hover:bg-[var(--chat-accent-soft)]"
          aria-label={`React with ${emoji}`}
        >
          {emoji}
        </button>
      ))}
    </div>
  )
}

// ─── ChatMessageActions (hover toolbar) ───────────────────────────────────────

interface ChatMessageActionsProps {
  message: ChatMessageData
  isOutgoing: boolean
}

function ChatMessageActions({ message, isOutgoing }: ChatMessageActionsProps) {
  const { onReply, onReactionAdd, onEdit, onDelete, onPin } = useChatContext()
  const [showReactions, setShowReactions] = React.useState(false)
  const [showMore, setShowMore] = React.useState(false)

  return (
    <div
      className={cn(
        "chat-toolbar-enter absolute -top-3 z-10 flex items-center gap-0.5 rounded-lg border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] p-0.5 opacity-0 shadow-[var(--chat-shadow-toolbar)] transition-opacity group-hover/message:opacity-100",
        isOutgoing ? "right-0" : "left-10"
      )}
    >
      {/* Reply */}
      <button
        onClick={() => onReply?.(message)}
        className="flex size-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
        aria-label="Reply"
      >
        <Reply className="size-3.5" />
      </button>

      {/* React — opens quick picker */}
      <div className="relative">
        <button
          onClick={() => setShowReactions(!showReactions)}
          className="flex size-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
          aria-label="Add reaction"
        >
          <SmilePlus className="size-3.5" />
        </button>
        {showReactions && (
          <div className="absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2">
            <QuickReactionPicker
              onSelect={(emoji) =>
                onReactionAdd?.(message.id, emoji)
              }
              onClose={() => setShowReactions(false)}
            />
          </div>
        )}
      </div>

      {/* More — dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowMore(!showMore)}
          className="flex size-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
          aria-label="More actions"
        >
          <MoreHorizontal className="size-3.5" />
        </button>
        {showMore && (
          <div
            className={cn(
              "chat-toolbar-enter absolute top-full z-20 mt-1 w-40 overflow-hidden rounded-lg border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] py-1 shadow-[var(--chat-shadow-toolbar)]",
              isOutgoing ? "right-0" : "left-0"
            )}
            onMouseLeave={() => setShowMore(false)}
          >
            {isOutgoing && (
              <button
                onClick={() => {
                  onEdit?.(message)
                  setShowMore(false)
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-[13px] text-[var(--chat-text-secondary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
              >
                <Pencil className="size-3.5" />
                Edit
              </button>
            )}
            <button
              onClick={() => {
                onPin?.(message.id)
                setShowMore(false)
              }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-[13px] text-[var(--chat-text-secondary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
            >
              <Pin className="size-3.5" />
              {message.isPinned ? "Unpin" : "Pin"}
            </button>
            {isOutgoing && (
              <button
                onClick={() => {
                  onDelete?.(message.id)
                  setShowMore(false)
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-[13px] text-[var(--chat-red)] transition-colors hover:bg-red-500/10"
              >
                <Trash2 className="size-3.5" />
                Delete
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── ChatMessageReply (quoted reply inside bubble) ────────────────────────────

function ChatMessageReply({
  replyTo,
  isOutgoing,
}: {
  replyTo: NonNullable<ChatMessageData["replyTo"]>
  isOutgoing: boolean
}) {
  // Outgoing bubbles set text color via --chat-bubble-outgoing-text which may
  // be white (Lunar, Midnight) or dark (Aurora, Ember).  Using `text-inherit`
  // + opacity lets the reply quote inherit that color and stay visible against
  // the bubble background regardless of theme.
  return (
    <div
      className={cn(
        "mb-1.5 flex items-start gap-2 rounded-lg border-l-2 px-2.5 py-1.5",
        isOutgoing
          ? "border-[var(--chat-bubble-outgoing-text)]/30 bg-[var(--chat-bubble-outgoing-text)]/10"
          : "border-[var(--chat-accent)] bg-[var(--chat-accent-soft)]"
      )}
    >
      <div className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-[12px] font-semibold",
            isOutgoing ? "text-inherit opacity-80" : "text-[var(--chat-accent)]"
          )}
        >
          {replyTo.senderName}
        </span>
        <span
          className={cn(
            "block truncate text-[12px]",
            isOutgoing ? "text-inherit opacity-60" : "text-[var(--chat-text-secondary)]"
          )}
        >
          {replyTo.text}
        </span>
      </div>
    </div>
  )
}

// ─── ChatMessage ──────────────────────────────────────────────────────────────

interface ChatMessageProps {
  message: ChatMessageData
  isOutgoing: boolean
  position: "solo" | "first" | "middle" | "last"
  showSender?: boolean
  showAvatar?: boolean
  className?: string
}

// ─── Voice Message ─────────────────────────────────────────────────────────

function ChatVoiceMessage({ voice, isOutgoing }: { voice: NonNullable<ChatMessageData["voice"]>; isOutgoing: boolean }) {
  const [playing, setPlaying] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const progressRef = React.useRef(0)

  React.useEffect(() => {
    progressRef.current = progress
  }, [progress])

  const totalMins = Math.floor(voice.duration / 60)
  const totalSecs = Math.floor(voice.duration % 60)
  const elapsed = progress * voice.duration
  const elapsedMins = Math.floor(elapsed / 60)
  const elapsedSecs = Math.floor(elapsed % 60)
  const timeLabel = playing || progress > 0
    ? `${elapsedMins}:${elapsedSecs.toString().padStart(2, "0")}`
    : `${totalMins}:${totalSecs.toString().padStart(2, "0")}`

  const progressIndex = Math.floor(progress * voice.waveform.length)

  React.useEffect(() => {
    if (!playing) return
    const fps = 20
    const step = 1 / (voice.duration * fps)
    const id = setInterval(() => {
      const next = progressRef.current + step
      if (next >= 1) {
        setProgress(0)
        setPlaying(false)
        clearInterval(id)
      } else {
        setProgress(next)
      }
    }, 1000 / fps)
    return () => clearInterval(id)
  }, [playing, voice.duration])

  const toggle = () => {
    if (!playing && progress === 0) setProgress(0)
    setPlaying((p) => !p)
  }

  return (
    <div className="mt-1.5 flex items-center gap-3">
      <button
        onClick={toggle}
        className="flex w-9 h-9 shrink-0 items-center justify-center rounded-full transition-colors"
        style={{ background: isOutgoing ? "rgba(255,255,255,0.20)" : "var(--chat-accent)" }}
        aria-label={playing ? "Pause voice message" : "Play voice message"}
      >
        {playing ? (
          <Pause className="w-4 h-4" style={{ color: "white" }} fill="white" />
        ) : (
          <Play className="w-4 h-4 ml-0.5" style={{ color: "white" }} fill="white" />
        )}
      </button>
      <div className="flex flex-1 items-center gap-[2px] h-8">
        {voice.waveform.map((v, i) => {
          const played = i < progressIndex
          return (
            <div
              key={i}
              className="w-[3px] rounded-full transition-opacity"
              style={{
                height: `${v * 100}%`,
                background: isOutgoing ? "white" : "var(--chat-accent)",
                opacity: played ? 1 : 0.6 + v * 0.4,
                ...(isOutgoing && !played ? { opacity: 0.4 + v * 0.3 } : {}),
              }}
            />
          )
        })}
      </div>
      <span className="text-[12px] shrink-0 opacity-60 tabular-nums">{timeLabel}</span>
    </div>
  )
}

function ChatMessage({
  message,
  isOutgoing,
  position,
  showSender = false,
  showAvatar = false,
  className,
}: ChatMessageProps) {
  const timestamp = new Date(message.timestamp)
  const { currentUser } = useChatContext()
  const radiusClass = getBubbleRadius(isOutgoing, position)
  const [lightboxImage, setLightboxImage] = React.useState<string | null>(null)

  return (
    <div
      className={cn(
        "chat-message group/message relative flex items-end gap-2",
        isOutgoing ? "flex-row-reverse" : "flex-row",
        position === "first" || position === "solo" ? "mt-4" : "mt-0.5",
        className
      )}
    >
      {/* Avatar slot — 32px, only for incoming, only on last/solo */}
      {!isOutgoing ? (
        <div className="w-8 shrink-0">
          {showAvatar && message.senderAvatar ? (
            <img
              src={message.senderAvatar}
              alt={message.senderName}
              className="size-8 rounded-full object-cover"
            />
          ) : showAvatar ? (
            <div className="flex size-8 items-center justify-center rounded-full bg-[var(--chat-bubble-incoming)] text-[11px] font-semibold text-[var(--chat-text-secondary)]">
              {message.senderName.charAt(0).toUpperCase()}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Bubble + reactions column */}
      <div className={cn("flex flex-col", isOutgoing ? "max-w-[75%]" : "max-w-full w-full")}>
        {/* Sender name — only first in group, incoming */}
        {showSender && !isOutgoing && (
          <span className="mb-0.5 ml-3 text-[14px] font-semibold leading-tight tracking-[-0.01em] text-[var(--chat-text-secondary)]">
            {message.senderName}
          </span>
        )}

        {/* Bubble — relative for hover toolbar positioning */}
        <div className="relative">
          {/* Hover actions toolbar */}
          <ChatMessageActions message={message} isOutgoing={isOutgoing} />

          <div
            className={cn(
              "relative",
              isOutgoing
                ? ["chat-bubble px-3.5 py-2", "bg-[var(--chat-bubble-outgoing)] text-[var(--chat-bubble-outgoing-text)]", radiusClass]
                : "text-[var(--chat-text-primary)] w-full py-2"
            )}
          >
            {/* Quoted reply */}
            {message.replyTo && (
              <ChatMessageReply
                replyTo={message.replyTo}
                isOutgoing={isOutgoing}
              />
            )}

            {/* Chain of Thought / Activities */}
            {!isOutgoing && message.activities && message.activities.length > 0 ? (
              <div className="mb-2 w-full max-w-full">
                <ChainOfThought defaultExpanded={message.activities.some(a => a.status === 'running')}>
                  {message.activities.map((activity) => (
                    <ChainOfThoughtStep key={activity.id}>
                      <ChainOfThoughtTrigger>
                        <span className="flex items-center gap-2">
                          {activity.status === 'running' ? (
                            <span className="block h-2.5 w-2.5 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
                          ) : activity.status === 'error' ? (
                            <AlertCircle className="h-3 w-3 text-red-400" />
                          ) : (
                            <Check className="h-3 w-3 text-emerald-400" />
                          )}
                          {activity.label}
                          {activity.meta && (
                            <span className="text-[10px] opacity-60">· {activity.meta}</span>
                          )}
                        </span>
                      </ChainOfThoughtTrigger>
                      {(activity.detail || activity.meta) && (
                        <ChainOfThoughtContent>
                          {activity.meta && (
                            <ChainOfThoughtItem>
                              {activity.meta}
                            </ChainOfThoughtItem>
                          )}
                          {activity.status === 'error' && activity.detail && (
                            <ChainOfThoughtItem>
                              <span className="text-red-400">{activity.detail}</span>
                            </ChainOfThoughtItem>
                          )}
                        </ChainOfThoughtContent>
                      )}
                    </ChainOfThoughtStep>
                  ))}
                </ChainOfThought>
              </div>
            ) : !isOutgoing && message.thinking ? (
              <div className="mb-2 w-full max-w-full">
                <ChainOfThought defaultExpanded={false}>
                  <ChainOfThoughtStep>
                    <ChainOfThoughtTrigger>Reasoning through the next step</ChainOfThoughtTrigger>
                    <ChainOfThoughtContent>
                      <ChainOfThoughtItem>
                        <span className="whitespace-pre-wrap">{message.thinking}</span>
                      </ChainOfThoughtItem>
                    </ChainOfThoughtContent>
                  </ChainOfThoughtStep>
                </ChainOfThought>
              </div>
            ) : null}

            {/* Text content */}
            {message.text ? (
              <div className="max-w-none break-words text-[15px] leading-[1.35] tracking-[-0.01em] space-y-2 [&_p]:whitespace-pre-wrap [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:bg-[var(--chat-bg-code)] [&_pre]:p-3 [&_pre]:rounded-md [&_pre]:overflow-x-auto [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-[var(--chat-bg-code)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-lg [&_h2]:font-bold [&_h2]:mt-3 [&_h2]:mb-1.5 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-2 [&_h3]:mb-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.text}
                </ReactMarkdown>
              </div>
            ) : !isOutgoing && message.status === 'sending' && (!message.activities || message.activities.length === 0) ? (
              <div className="flex items-center gap-1.5 py-1">
                <span className="block h-2 w-2 rounded-full bg-current opacity-40 animate-bounce [animation-delay:0ms]" />
                <span className="block h-2 w-2 rounded-full bg-current opacity-40 animate-bounce [animation-delay:150ms]" />
                <span className="block h-2 w-2 rounded-full bg-current opacity-40 animate-bounce [animation-delay:300ms]" />
              </div>
            ) : null}

            {/* Images */}
            {message.images && message.images.length > 0 && (
              <div className={cn("mt-1.5 flex flex-wrap gap-1.5", message.images.length === 1 ? "" : "")}>
                {message.images.map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => setLightboxImage(img.url)}
                    className="cursor-pointer rounded-lg overflow-hidden"
                    aria-label="View image"
                  >
                    <img
                      src={img.url}
                      alt={img.alt || "Image"}
                      width={img.width}
                      height={img.height}
                      className="max-h-[200px] max-w-full rounded-lg object-cover transition-opacity hover:opacity-90"
                      loading="lazy"
                    />
                  </button>
                ))}
              </div>
            )}

            {/* Code block */}
            {message.code && (
              <div className="chat-content-card mt-1.5 overflow-hidden">
                <div className="flex items-center justify-between bg-[var(--chat-bg-code)] px-3 py-1.5">
                  <span className="text-[11px] font-medium text-[var(--chat-text-tertiary)]">{message.code.language}</span>
                </div>
                <pre className="overflow-x-auto bg-[var(--chat-bg-code)] px-3 py-2">
                  <code className="text-[13px] leading-relaxed text-[var(--chat-text-primary)]" style={{ fontFamily: "var(--chat-font-mono)" }}>
                    {message.code.code}
                  </code>
                </pre>
              </div>
            )}

            {/* File attachments */}
            {message.files && message.files.length > 0 && (
              <div className="mt-1.5 flex flex-col gap-1.5">
                {message.files.map((file, idx) => (
                  <div key={idx} className="chat-content-card flex items-center gap-2.5 px-3 py-2">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-[var(--chat-accent-soft)]">
                      <Paperclip className="size-3.5 text-[var(--chat-accent)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium text-[var(--chat-text-primary)]">{file.name}</p>
                      <p className="text-[11px] text-[var(--chat-text-tertiary)]">{file.size < 1024 ? `${file.size} B` : file.size < 1048576 ? `${(file.size / 1024).toFixed(0)} KB` : `${(file.size / 1048576).toFixed(1)} MB`}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Link preview */}
            {message.linkPreview && (
              <a
                href={message.linkPreview.url}
                target="_blank"
                rel="noopener noreferrer"
                className="chat-content-card mt-1.5 block hover:opacity-90 transition-opacity"
              >
                {message.linkPreview.image && (
                  <img src={message.linkPreview.image} alt="" className="h-32 w-full object-cover" loading="lazy" />
                )}
                <div className="px-3 py-2">
                  <p className="text-[13px] font-semibold text-[var(--chat-text-primary)]">{message.linkPreview.title}</p>
                  <p className="mt-0.5 text-[12px] text-[var(--chat-text-secondary)]">{message.linkPreview.description}</p>
                  <p className="mt-1 text-[11px] text-[var(--chat-accent)]">{message.linkPreview.url}</p>
                </div>
              </a>
            )}

            {/* Voice message */}
            {message.voice && (
              <ChatVoiceMessage voice={message.voice} isOutgoing={isOutgoing} />
            )}

            {/* Inline timestamp + status + edited label */}
            <div
              className={cn(
                "mt-1 flex items-center gap-1",
                isOutgoing ? "justify-end" : "justify-start"
              )}
            >
              {message.isEdited && (
                <span className="text-[10px] italic opacity-50">edited</span>
              )}
              <time className="text-[11px] tracking-[0.02em] opacity-60">
                {formatTimestamp(timestamp)}
              </time>
              {isOutgoing && message.status && (
                <ChatMessageStatus status={message.status} />
              )}
            </div>
          </div>

          {/* Pin indicator */}
          {message.isPinned && (
            <div className="absolute -top-1.5 -right-1.5">
              <Pin className="size-3 rotate-45 text-[var(--chat-orange)]" />
            </div>
          )}
        </div>

        {/* Reactions bar */}
        {message.reactions && message.reactions.length > 0 && (
          <ChatMessageReactions
            messageId={message.id}
            reactions={message.reactions}
            isOutgoing={isOutgoing}
            currentUserId={currentUser.id}
          />
        )}

        {/* Read receipts (group chat) — small stacked avatars */}
        {message.readBy && message.readBy.length > 0 && (
          <ChatReadReceipts
            readBy={message.readBy}
            isOutgoing={isOutgoing}
          />
        )}
      </div>

      {/* Image lightbox */}
      {lightboxImage && typeof document !== "undefined" && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setLightboxImage(null)}
        >
          <button
            onClick={() => setLightboxImage(null)}
            className="absolute top-4 right-4 flex size-10 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
            aria-label="Close lightbox"
          >
            <X className="size-5" />
          </button>
          <img
            src={lightboxImage}
            alt=""
            className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>,
        document.body
      )}
    </div>
  )
}

// ─── Bubble radius helper ─────────────────────────────────────────────────────

function getBubbleRadius(
  isOutgoing: boolean,
  position: "solo" | "first" | "middle" | "last"
): string {
  if (isOutgoing) {
    switch (position) {
      case "solo":
        return "rounded-[18px_18px_4px_18px]"
      case "first":
        return "rounded-[18px_18px_4px_18px]"
      case "middle":
        return "rounded-[18px_4px_4px_18px]"
      case "last":
        return "rounded-[18px_4px_18px_18px]"
    }
  } else {
    switch (position) {
      case "solo":
        return "rounded-[18px_18px_18px_4px]"
      case "first":
        return "rounded-[18px_18px_18px_4px]"
      case "middle":
        return "rounded-[4px_18px_18px_4px]"
      case "last":
        return "rounded-[4px_18px_18px_18px]"
    }
  }
}

// ─── ChatMessageStatus ────────────────────────────────────────────────────────

function ChatMessageStatus({
  status,
}: {
  status: NonNullable<ChatMessageData["status"]>
}) {
  switch (status) {
    case "sending":
      return <Clock className="size-3 animate-pulse opacity-50" />
    case "sent":
      return <Check className="size-3 opacity-60" />
    case "delivered":
      return <CheckCheck className="size-3.5 opacity-60" />
    case "read":
      return (
        <CheckCheck className="chat-status-read size-3.5 text-[var(--chat-accent)]" />
      )
    case "failed":
      return (
        <AlertCircle className="size-3.5 cursor-pointer text-[var(--chat-red)]" />
      )
  }
}

// ─── ChatMessageReactions (interactive) ───────────────────────────────────────

function ChatMessageReactions({
  messageId,
  reactions,
  isOutgoing,
  currentUserId,
}: {
  messageId: string
  reactions: NonNullable<ChatMessageData["reactions"]>
  isOutgoing: boolean
  currentUserId: string
}) {
  const { onReactionAdd, onReactionRemove } = useChatContext()

  return (
    <div
      className={cn(
        "mt-1 flex flex-wrap gap-1",
        isOutgoing ? "justify-end" : "justify-start"
      )}
    >
      {reactions.map((r) => {
        const hasReacted = r.userIds.includes(currentUserId)
        return (
          <button
            key={r.emoji}
            onClick={() => {
              if (hasReacted) {
                onReactionRemove?.(messageId, r.emoji)
              } else {
                onReactionAdd?.(messageId, r.emoji)
              }
            }}
            className={cn(
              "chat-reaction-pop flex h-[26px] items-center gap-1 rounded-full border px-2 text-xs tabular-nums transition-all hover:scale-105",
              hasReacted
                ? "border-[var(--chat-accent)]/30 bg-[var(--chat-accent-soft)]"
                : "border-[var(--chat-border)] bg-[var(--chat-bg-sidebar)] hover:bg-[var(--chat-accent-soft)]"
            )}
            aria-label={`${r.emoji} ${r.count} reaction${r.count !== 1 ? "s" : ""}`}
          >
            <span className="text-sm">{r.emoji}</span>
            <span
              className={cn(
                "text-[12px] font-medium",
                hasReacted
                  ? "text-[var(--chat-accent)]"
                  : "text-[var(--chat-text-secondary)]"
              )}
            >
              {r.count}
            </span>
          </button>
        )
      })}
      {/* Add reaction button — visible on hover */}
      <button
        onClick={() => {
          // Toggle first available reaction for demo; in prod this opens a picker
          onReactionAdd?.(messageId, "\u{1F44D}")
        }}
        className="flex size-[26px] items-center justify-center rounded-full border border-dashed border-[var(--chat-border)] text-[var(--chat-text-tertiary)] opacity-0 transition-all hover:border-[var(--chat-accent)] hover:text-[var(--chat-accent)] group-hover/message:opacity-100"
        aria-label="Add reaction"
      >
        <SmilePlus className="size-3" />
      </button>
    </div>
  )
}

// ─── ChatReadReceipts (group chat — stacked mini avatars) ─────────────────────

function ChatReadReceipts({
  readBy,
  isOutgoing,
}: {
  readBy: NonNullable<ChatMessageData["readBy"]>
  isOutgoing: boolean
}) {
  const maxVisible = 3
  const visible = readBy.slice(0, maxVisible)
  const overflow = readBy.length - maxVisible

  return (
    <div
      className={cn(
        "mt-1 flex items-center",
        isOutgoing ? "justify-end" : "justify-start"
      )}
    >
      <div className="flex -space-x-1.5">
        {visible.map((user) => (
          <div
            key={user.userId}
            className="flex size-4 items-center justify-center rounded-full border border-[var(--chat-bg-main)] bg-[var(--chat-bubble-incoming)] text-[7px] font-bold text-[var(--chat-text-secondary)]"
            title={user.name}
          >
            {user.avatar ? (
              <img
                src={user.avatar}
                alt={user.name}
                className="size-full rounded-full object-cover"
              />
            ) : (
              user.name.charAt(0).toUpperCase()
            )}
          </div>
        ))}
      </div>
      {overflow > 0 && (
        <span className="ml-1 text-[10px] text-[var(--chat-text-tertiary)]">
          +{overflow}
        </span>
      )}
    </div>
  )
}

// ─── ChatMessageGroup ─────────────────────────────────────────────────────────

interface ChatMessageGroupProps {
  group: MessageGroup
  className?: string
}

function ChatMessageGroup({ group, className }: ChatMessageGroupProps) {
  const len = group.messages.length

  return (
    <div
      className={cn(
        "chat-message-group",
        group.isOutgoing ? "items-end" : "items-start",
        className
      )}
    >
      {group.messages.map((msg, i) => {
        const position: "solo" | "first" | "middle" | "last" =
          len === 1
            ? "solo"
            : i === 0
              ? "first"
              : i === len - 1
                ? "last"
                : "middle"

        return (
          <ChatMessage
            key={msg.id}
            message={msg}
            isOutgoing={group.isOutgoing}
            position={position}
            showSender={i === 0}
            showAvatar={position === "solo" || position === "last"}
          />
        )
      })}
    </div>
  )
}

// ─── ChatDateSeparator ────────────────────────────────────────────────────────

interface ChatDateSeparatorProps {
  label: string
  className?: string
}

function ChatDateSeparator({ label, className }: ChatDateSeparatorProps) {
  return (
    <div
      className={cn(
        "chat-date-separator my-6 flex items-center gap-4",
        className
      )}
    >
      <div className="h-px flex-1 bg-[var(--chat-border)]" />
      <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--chat-text-tertiary)]">
        {label}
      </span>
      <div className="h-px flex-1 bg-[var(--chat-border)]" />
    </div>
  )
}

// ─── ChatSystemMessage ────────────────────────────────────────────────────────

interface ChatSystemMessageProps {
  message: ChatMessageData
  className?: string
}

function ChatSystemMessage({ message, className }: ChatSystemMessageProps) {
  return (
    <div
      className={cn(
        "chat-system-message my-4 flex justify-center",
        className
      )}
    >
      <span className="text-[13px] font-medium tracking-[0.01em] text-[var(--chat-text-secondary)]">
        {message.text || message.systemEvent}
      </span>
    </div>
  )
}

// ─── ChatTypingIndicator ──────────────────────────────────────────────────────

interface ChatTypingIndicatorProps {
  users: TypingUser[]
  className?: string
}

function ChatTypingIndicator({ users, className }: ChatTypingIndicatorProps) {
  if (users.length === 0) return null

  const label =
    users.length === 1
      ? `${users[0].name} is typing`
      : users.length === 2
        ? `${users[0].name} and ${users[1].name} are typing`
        : "Several people are typing"

  return (
    <div
      className={cn(
        "chat-message mt-4 flex items-end gap-2",
        className
      )}
    >
      {/* Avatar */}
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--chat-bubble-incoming)] text-[11px] font-semibold text-[var(--chat-text-secondary)]">
        {users[0].avatar ? (
          <img
            src={users[0].avatar}
            alt={users[0].name}
            className="size-full rounded-full object-cover"
          />
        ) : (
          users[0].name.charAt(0).toUpperCase()
        )}
      </div>

      <div className="flex flex-col">
        {/* Label */}
        <span className="mb-0.5 ml-3 text-[12px] text-[var(--chat-text-tertiary)]">
          {label}
        </span>

        {/* Dots bubble */}
        <div className="flex w-16 items-center justify-center gap-1 rounded-[18px_18px_18px_4px] bg-[var(--chat-bubble-incoming)] px-4 py-3">
          <span
            className="chat-typing-dot size-[7px] rounded-full bg-[var(--chat-text-secondary)]"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="chat-typing-dot size-[7px] rounded-full bg-[var(--chat-text-secondary)]"
            style={{ animationDelay: "160ms" }}
          />
          <span
            className="chat-typing-dot size-[7px] rounded-full bg-[var(--chat-text-secondary)]"
            style={{ animationDelay: "320ms" }}
          />
        </div>
      </div>
    </div>
  )
}

// ─── ChatReplyPreview (bar above composer) ────────────────────────────────────

interface ChatReplyPreviewProps {
  replyingTo: ChatMessageData
  onCancel: () => void
  className?: string
}

function ChatReplyPreview({
  replyingTo,
  onCancel,
  className,
}: ChatReplyPreviewProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 border-t border-[var(--chat-border)] bg-[var(--chat-bg-sidebar)] px-4 py-2",
        className
      )}
    >
      <div className="h-8 w-0.5 shrink-0 rounded-full bg-[var(--chat-accent)]" />
      <div className="min-w-0 flex-1">
        <span className="block text-[12px] font-semibold text-[var(--chat-accent)]">
          {replyingTo.senderName}
        </span>
        <span className="block truncate text-[13px] text-[var(--chat-text-secondary)]">
          {replyingTo.text}
        </span>
      </div>
      <button
        onClick={onCancel}
        className="flex size-6 shrink-0 items-center justify-center rounded-full text-[var(--chat-text-tertiary)] transition-colors hover:bg-[var(--chat-accent-soft)] hover:text-[var(--chat-text-primary)]"
        aria-label="Cancel reply"
      >
        <X className="size-3.5" />
      </button>
    </div>
  )
}

// ─── ChatMessages (scroll container) ──────────────────────────────────────────

interface ChatMessagesProps {
  messages: ChatMessageData[]
  typingUsers?: TypingUser[]
  className?: string
  onLoadMore?: () => Promise<void>
  hasMore?: boolean
}

function ChatMessages({
  messages,
  typingUsers = [],
  className,
}: ChatMessagesProps) {
  const { currentUser, messageGroupingInterval } = useChatContext()
  const { containerRef, scrollToBottom, isAtBottom, unseenCount } =
    useAutoScroll(messages)

  const items = React.useMemo(
    () => groupMessages(messages, currentUser.id, messageGroupingInterval),
    [messages, currentUser.id, messageGroupingInterval]
  )

  return (
    <div
      className={cn(
        "chat-messages relative flex flex-1 flex-col overflow-hidden",
        className
      )}
    >
      {/* Scrollable area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto px-4 py-4"
        role="log"
        aria-live="polite"
      >
        <div className="mx-auto w-full max-w-3xl">
          {items.map((item, i) => {
            switch (item.type) {
              case "date":
                return (
                  <ChatDateSeparator
                    key={`date-${item.label}-${i}`}
                    label={item.label}
                  />
                )
              case "system":
                return (
                  <ChatSystemMessage
                    key={item.message.id}
                    message={item.message}
                  />
                )
              case "group":
                return (
                  <ChatMessageGroup
                    key={`group-${item.group.messages[0].id}`}
                    group={item.group}
                  />
                )
            }
          })}

          {/* Typing indicator at the bottom */}
          {typingUsers.length > 0 && (
            <ChatTypingIndicator users={typingUsers} />
          )}
        </div>
      </div>

      {/* Scroll-to-bottom FAB with unread badge */}
      <button
        onClick={() => scrollToBottom("smooth")}
        className={cn(
          "absolute bottom-4 right-4 z-5 flex size-10 items-center justify-center rounded-full border border-[var(--chat-border-strong)] bg-[var(--chat-bg-main)] shadow-[var(--chat-shadow-md)] transition-all duration-200",
          isAtBottom
            ? "pointer-events-none translate-y-2 opacity-0"
            : "translate-y-0 opacity-100"
        )}
        aria-label={
          unseenCount > 0
            ? `${unseenCount} new messages, scroll to bottom`
            : "Scroll to bottom"
        }
      >
        <ChevronDown className="size-[18px] text-[var(--chat-text-secondary)]" />
        {/* Unread badge */}
        {unseenCount > 0 && (
          <span className="absolute -top-1 -right-1 flex size-[18px] items-center justify-center rounded-full bg-[var(--chat-accent)] text-[11px] font-bold text-white tabular-nums">
            {unseenCount > 99 ? "99+" : unseenCount}
          </span>
        )}
      </button>
    </div>
  )
}

// ─── File preview item ────────────────────────────────────────────────────────

interface FilePreviewItem {
  file: File
  id: string
  preview?: string // data URL for images
  progress?: number // 0-100
}

function ChatFilePreview({
  item,
  onRemove,
}: {
  item: FilePreviewItem
  onRemove: () => void
}) {
  const isImage = item.file.type.startsWith("image/")

  return (
    <div className="relative shrink-0 rounded-lg border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)]">
      {isImage && item.preview ? (
        <div className="relative size-14 overflow-hidden rounded-lg">
          <img src={item.preview} alt={item.file.name} className="size-full object-cover" />
        </div>
      ) : (
        <div className="flex items-center gap-2 px-3 py-2">
          <div className="flex size-8 items-center justify-center rounded-md bg-[var(--chat-accent-soft)]">
            <Paperclip className="size-3.5 text-[var(--chat-accent)]" />
          </div>
          <div className="min-w-0">
            <p className="max-w-[120px] truncate text-[12px] font-medium text-[var(--chat-text-primary)]">{item.file.name}</p>
            <p className="text-[10px] text-[var(--chat-text-tertiary)]">{(item.file.size / 1024).toFixed(0)} KB</p>
          </div>
        </div>
      )}
      {/* Progress bar */}
      {item.progress !== undefined && item.progress < 100 && (
        <div className="absolute bottom-0 left-0 h-[3px] w-full bg-[var(--chat-border)]">
          <div className="h-full bg-[var(--chat-accent)] transition-all" style={{ width: `${item.progress}%` }} />
        </div>
      )}
      {/* Remove button */}
      <button
        onClick={onRemove}
        className="absolute -top-1.5 -right-1.5 flex size-5 items-center justify-center rounded-full border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] text-[var(--chat-text-secondary)] shadow-sm hover:bg-[var(--chat-bg-hover)] hover:text-[var(--chat-text-primary)]"
        aria-label="Remove file"
      >
        <X className="size-3" />
      </button>
    </div>
  )
}

// ─── ChatComposer ─────────────────────────────────────────────────────────────

interface ChatComposerProps {
  onSend?: (text: string) => void
  onTyping?: (isTyping: boolean) => void
  onFileUpload?: (files: File[]) => void
  onVoiceRecord?: () => void
  placeholder?: string
  disabled?: boolean
  replyingTo?: ChatMessageData | null
  onCancelReply?: () => void
  className?: string
}

function ChatComposer({
  onSend,
  onTyping,
  onFileUpload,
  onVoiceRecord,
  placeholder = "Message",
  disabled = false,
  replyingTo,
  onCancelReply,
  className,
}: ChatComposerProps) {
  const [value, setValue] = React.useState("")
  const [files, setFiles] = React.useState<FilePreviewItem[]>([])
  const [isDragging, setIsDragging] = React.useState(false)
  const [showAttachMenu, setShowAttachMenu] = React.useState(false)
  const { textareaRef, resize } = useAutoResize({ maxRows: 6 })
  const { handleKeyDown: handleTypingKeyDown, stopTyping } =
    useTypingIndicator({ onTypingChange: onTyping })
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const imageInputRef = React.useRef<HTMLInputElement>(null)
  const hasContent = value.trim().length > 0 || files.length > 0

  const addFiles = React.useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles)
    const items: FilePreviewItem[] = arr.map((f) => ({
      file: f,
      id: `${f.name}-${Date.now()}-${Math.random()}`,
      progress: undefined,
    }))

    // Generate image previews
    items.forEach((item) => {
      if (item.file.type.startsWith("image/")) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setFiles((prev) =>
            prev.map((f) => f.id === item.id ? { ...f, preview: e.target?.result as string } : f)
          )
        }
        reader.readAsDataURL(item.file)
      }
    })

    setFiles((prev) => [...prev, ...items])
    onFileUpload?.(arr)
  }, [onFileUpload])

  const removeFile = React.useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }, [])

  const handleSend = React.useCallback(() => {
    const trimmed = value.trim()
    if ((!trimmed && files.length === 0) || disabled) return
    if (trimmed) onSend?.(trimmed)
    setValue("")
    setFiles([])
    stopTyping()
    if (textareaRef.current) textareaRef.current.style.height = "auto"
  }, [value, files, disabled, onSend, textareaRef, stopTyping])

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      handleTypingKeyDown()
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }
      if (e.key === "Escape" && replyingTo) onCancelReply?.()
    },
    [handleSend, handleTypingKeyDown, replyingTo, onCancelReply]
  )

  // Paste upload
  const handlePaste = React.useCallback(
    (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      const imageFiles: File[] = []
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile()
          if (file) imageFiles.push(file)
        }
      }
      if (imageFiles.length > 0) {
        addFiles(imageFiles)
        setShowAttachMenu(false)
      }
    },
    [addFiles]
  )

  // Drag-and-drop handlers (on the composer container)
  const handleDragOver = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])
  const handleDragLeave = React.useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])
  const handleDrop = React.useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files)
        setShowAttachMenu(false)
      }
    },
    [addFiles]
  )

  return (
    <div
      className={cn("chat-composer sticky bottom-0 z-10 relative", className)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop overlay */}
      {isDragging && (
        <div className="chat-drop-overlay">
          <div className="flex flex-col items-center gap-2">
            <Upload className="size-8 text-[var(--chat-accent)]" />
            <span className="text-[14px] font-medium text-[var(--chat-accent)]">Drop files to upload</span>
          </div>
        </div>
      )}

      {/* Reply preview bar */}
      {replyingTo && (
        <ChatReplyPreview replyingTo={replyingTo} onCancel={() => onCancelReply?.()} />
      )}

      {/* File preview strip */}
      {files.length > 0 && (
        <div className="flex gap-3 overflow-x-auto border-t border-[var(--chat-border)] bg-background px-4 pt-3 pb-2 backdrop-blur-[20px]">
          {files.map((f) => (
            <ChatFilePreview key={f.id} item={f} onRemove={() => removeFile(f.id)} />
          ))}
        </div>
      )}

      {/* Composer body — professional style */}
      <div className="bg-background px-4 py-4">
        <div className="mx-auto max-w-3xl">
          <div className="relative bg-card border border-border rounded-2xl p-3 shadow-sm focus-within:border-ring transition-colors">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => { setValue(e.target.value); resize() }}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="max-h-36 min-h-[44px] w-full resize-none overflow-y-auto border-none bg-transparent py-1 px-1 text-sm text-foreground shadow-none outline-none focus:outline-none focus:ring-0 placeholder:text-muted-foreground"
            />
            
            <div className="flex items-center justify-between mt-2 pt-2">
              <div className="flex items-center gap-1">
                {onVoiceRecord && (
                  <button 
                    type="button" 
                    onClick={onVoiceRecord} 
                    disabled={disabled} 
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground disabled:opacity-50"
                    aria-label="Record voice message"
                  >
                    <Mic className="h-4 w-4" />
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={handleSend}
                  disabled={!hasContent || disabled}
                  className={cn(
                    "inline-flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 active:scale-95",
                    hasContent
                      ? "bg-primary text-primary-foreground hover:bg-primary/90"
                      : "bg-transparent text-muted-foreground cursor-not-allowed"
                  )}
                  aria-label="Send message"
                >
                  <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
                </button>
              </div>
            </div>

            {/* Hidden file inputs */}
            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = "" }} />
            <input ref={imageInputRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = "" }} />
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Exports ──────────────────────────────────────────────────────────────────

export {
  ChatProvider,
  ChatMessage,
  ChatMessageGroup,
  ChatDateSeparator,
  ChatSystemMessage,
  ChatMessages,
  ChatComposer,
  ChatMessageStatus,
  ChatMessageReactions,
  ChatMessageActions,
  ChatMessageReply,
  ChatTypingIndicator,
  ChatReplyPreview,
  ChatReadReceipts,
}
export type {
  ChatProviderProps,
  ChatMessageProps,
  ChatMessageGroupProps,
  ChatDateSeparatorProps,
  ChatSystemMessageProps,
  ChatMessagesProps,
  ChatComposerProps,
  ChatMessageActionsProps,
  ChatTypingIndicatorProps,
  ChatReplyPreviewProps,
}
