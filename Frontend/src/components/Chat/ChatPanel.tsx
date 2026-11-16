import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Bot, User, MessageCircle } from 'lucide-react'
import { v4 as uuidv4 } from 'uuid'
import { sendChatMessage } from '../../services/api'
import type { ChatMessage } from '../../types'

const SUGGESTED_QUESTIONS = [
  'Hôm nay biển có an toàn để đi tắm không?',
  'Từ 2019 đến 2024 bờ biển thay đổi bao nhiêu mét?',
  'Tuần này sóng cao nhất ngày nào?',
  'Tốc độ xói lở trung bình mỗi năm là bao nhiêu?',
]

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

interface MessageBubbleProps {
  message: ChatMessage
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-cyan-500/30 border border-cyan-500/40' : 'bg-slate-700 border border-slate-600'
        }`}
      >
        {isUser ? (
          <User size={13} className="text-cyan-400" />
        ) : (
          <Bot size={13} className="text-slate-300" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-cyan-500/20 border border-cyan-500/30 text-cyan-50 rounded-tr-sm'
            : 'bg-slate-700/70 border border-slate-600 text-slate-200 rounded-tl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <p
          className={`text-xs mt-1.5 ${
            isUser ? 'text-cyan-400/60 text-right' : 'text-slate-500'
          }`}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uuidv4(),
      role: 'assistant',
      content:
        'Xin chào! Tôi là trợ lý AI của hệ thống CoastWatch. Tôi có thể giúp bạn phân tích dữ liệu biến động bờ biển Cửa Tùng, Quảng Trị. Bạn có thể hỏi tôi về xu hướng xói lở, bồi tụ, dự báo tương lai, hoặc so sánh các phương pháp phân tích.',
      timestamp: new Date().toISOString(),
    },
  ])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(() => uuidv4())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSend = useCallback(async (text?: string) => {
    const messageText = (text ?? inputText).trim()
    if (!messageText || isLoading) return

    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      const response = await sendChatMessage(messageText, sessionId)

      const assistantMessage: ChatMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: response.reply,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorContent =
        err instanceof Error ? err.message : 'Xin lỗi, tôi không thể xử lý câu hỏi này lúc này.'

      const errorMessage: ChatMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: `⚠ ${errorContent}`,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }, [inputText, isLoading, sessionId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="flex-shrink-0 bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center gap-3">
        <div className="w-8 h-8 bg-cyan-500/20 rounded-full flex items-center justify-center border border-cyan-500/30">
          <MessageCircle size={16} className="text-cyan-400" />
        </div>
        <div>
          <p className="text-white font-medium text-sm">Trợ lý CoastWatch AI</p>
          <p className="text-slate-400 text-xs">Phân tích biến động bờ biển Cửa Tùng</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          <span className="text-slate-400 text-xs">Trực tuyến</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex gap-2.5">
            <div className="w-7 h-7 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center flex-shrink-0">
              <Bot size={13} className="text-slate-300" />
            </div>
            <div className="bg-slate-700/70 border border-slate-600 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-1.5">
                <Loader2 size={13} className="animate-spin text-cyan-400" />
                <span className="text-slate-400 text-xs">Đang phân tích...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested questions */}
      <div className="flex-shrink-0 px-4 py-2 border-t border-slate-800">
        <p className="text-slate-500 text-xs mb-2">Câu hỏi gợi ý:</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {SUGGESTED_QUESTIONS.map((question, i) => (
            <button
              key={i}
              onClick={() => void handleSend(question)}
              disabled={isLoading}
              className="flex-shrink-0 text-xs bg-slate-700/60 hover:bg-slate-700 border border-slate-600 hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 rounded-full px-3 py-1.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {question}
            </button>
          ))}
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 bg-slate-800 border-t border-slate-700 px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi về biến động bờ biển... (Enter để gửi)"
            className="flex-1 bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors min-h-10 max-h-32"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={() => void handleSend()}
            disabled={isLoading || !inputText.trim()}
            className="w-10 h-10 bg-cyan-500 hover:bg-cyan-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-colors flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
        <p className="text-slate-600 text-xs mt-1.5">
          Session: {sessionId.slice(0, 8)}... • Shift+Enter để xuống dòng
        </p>
      </div>
    </div>
  )
}
