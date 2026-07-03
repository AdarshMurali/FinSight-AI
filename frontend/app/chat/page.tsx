"use client";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getPortfolios,
  getSuggestedQuestions,
  aiChatStream,
  Portfolio,
  ChatMessage,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Send, MessageSquare, RotateCcw, ChevronDown } from "lucide-react";

// ── Typing cursor ─────────────────────────────────────────────────────────────
function Cursor() {
  return (
    <span className="inline-block w-[7px] h-[13px] bg-[#F5821F] ml-0.5 animate-pulse align-middle" />
  );
}

// ── Tool call chips shown inside the assistant bubble ─────────────────────────
function ToolChips({ tools }: { tools: string[] }) {
  if (!tools.length) return null;
  const labels: Record<string, string> = {
    get_portfolio_data:   "PORTFOLIO DATA",
    get_position_history: "POSITION HISTORY",
    search_market_context:"MARKET CONTEXT",
    get_market_events:    "MARKET EVENTS",
    run_risk_analysis:    "RISK ANALYSIS",
  };
  return (
    <div className="flex flex-wrap gap-1 mb-2 pb-2 border-b border-[#1A1A1A]">
      {tools.map((t, i) => (
        <span
          key={i}
          className="text-[8px] font-bold tracking-wider px-2 py-0.5 border"
          style={{ color: "#F5821F", borderColor: "rgba(245,130,31,0.25)", background: "rgba(245,130,31,0.06)" }}
        >
          ▸ {labels[t] ?? t.replace(/_/g, " ").toUpperCase()}
        </span>
      ))}
    </div>
  );
}

// ── Single chat bubble ────────────────────────────────────────────────────────
function Bubble({
  msg,
  isStreaming,
  toolCalls,
}: {
  msg: ChatMessage;
  isStreaming?: boolean;
  toolCalls?: string[];
}) {
  const isUser = msg.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[72%]">
          <div className="bg-[#F5821F] text-black text-[11px] px-4 py-2.5 leading-5 font-medium">
            {msg.content}
          </div>
          <p className="text-[#555] text-[9px] text-right mt-1 tracking-wider">YOU</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[80%]">
        <p className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em] mb-1">
          FINSIGHT AI
        </p>
        <div className="bg-[#0D0D0D] border border-[#2A2A2A] text-[#E0E0E0] text-[11px] px-4 py-3 leading-6">
          <ToolChips tools={toolCalls ?? []} />
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <p className="text-[#F5821F] font-bold tracking-wider mt-3 mb-1">{children}</p>,
              h2: ({ children }) => <p className="text-[#F5821F] font-bold tracking-wider mt-3 mb-1">{children}</p>,
              h3: ({ children }) => <p className="text-[#F5821F] font-bold tracking-wider mt-3 mb-1">{children}</p>,
              strong: ({ children }) => <span className="text-white font-bold">{children}</span>,
              em: ({ children }) => <span className="text-[#AAA] italic">{children}</span>,
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 mb-2">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-0.5 mb-2">{children}</ol>,
              li: ({ children }) => <li className="text-[#E0E0E0]">{children}</li>,
              code: ({ children }) => <code className="bg-[#1A1A1A] text-[#F5821F] px-1 rounded text-[10px]">{children}</code>,
              pre: ({ children }) => <pre className="bg-[#1A1A1A] p-2 rounded text-[10px] overflow-x-auto mb-2">{children}</pre>,
              hr: () => <hr className="border-[#2A2A2A] my-2" />,
            }}
          >
            {msg.content}
          </ReactMarkdown>
          {isStreaming && <Cursor />}
        </div>
      </div>
    </div>
  );
}

// ── Suggested question chip ───────────────────────────────────────────────────
function QuestionChip({
  text,
  onClick,
}: {
  text: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="text-left text-[10px] text-[#AAA] border border-[#2A2A2A] px-3 py-2 hover:border-[#F5821F] hover:text-[#F5821F] transition-colors tracking-wide"
    >
      {text}
    </button>
  );
}

// ── Main chat page ────────────────────────────────────────────────────────────
export default function ChatPage() {
  const [portfolios, setPortfolios]         = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId]         = useState<number>(0);
  const [suggested, setSuggested]           = useState<string[]>([]);
  const [messages, setMessages]             = useState<ChatMessage[]>([]);
  const [input, setInput]                   = useState("");
  const [streaming, setStreaming]           = useState(false);
  const [error, setError]                   = useState("");
  const [streamingToolCalls, setStreamingToolCalls] = useState<string[]>([]);
  const [loadingInit, setLoadingInit]       = useState(true);
  const [showPortfolioMenu, setShowPortfolioMenu] = useState(false);

  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  const streamBuf  = useRef("");       // accumulates tokens during streaming

  // ── Init ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    Promise.all([getPortfolios(), getSuggestedQuestions()]).then(([p, s]) => {
      setPortfolios(p);
      setSuggested(s.questions);
      if (p.length) setSelectedId(p[0].portfolio_id);
    }).finally(() => setLoadingInit(false));
  }, []);

  // ── Auto-scroll ────────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Selected portfolio info ────────────────────────────────────────────────
  const selectedPortfolio = portfolios.find(p => p.portfolio_id === selectedId);

  // ── Send message ───────────────────────────────────────────────────────────
  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || streaming || !selectedId) return;

    setInput("");
    setError("");
    setStreamingToolCalls([]);

    const userMsg: ChatMessage = { role: "user", content: trimmed };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);

    // Add empty assistant bubble to stream into
    const assistantMsg: ChatMessage = { role: "assistant", content: "" };
    setMessages([...newMessages, assistantMsg]);
    setStreaming(true);
    streamBuf.current = "";

    // Build history (exclude the empty assistant bubble we just added)
    const history = newMessages.slice(-16); // last 8 turns

    await aiChatStream(
      selectedId,
      trimmed,
      history,
      // onToken — update the last (streaming) bubble
      (token) => {
        streamBuf.current += token;
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role:    "assistant",
            content: streamBuf.current,
          };
          return updated;
        });
      },
      // onError
      (err) => setError(err),
      // onDone
      () => setStreaming(false),
      // onToolCall — accumulate tool names for display in the bubble
      (toolName) => setStreamingToolCalls(prev => [...prev, toolName]),
    );
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function clearChat() {
    setMessages([]);
    setError("");
    streamBuf.current = "";
  }

  if (loadingInit) return <LoadingSpinner label="Loading terminal..." />;

  const hasMessages = messages.length > 0;

  return (
    <div className="max-w-5xl mx-auto flex flex-col h-[calc(100vh-52px)] font-mono">

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <div className="border border-[#2A2A2A] bg-[#0D0D0D] flex items-center justify-between px-4 py-2 shrink-0">
        <div className="flex items-center gap-3">
          <MessageSquare size={13} className="text-[#F5821F]" />
          <span className="text-[#F5821F] text-[10px] font-bold tracking-[0.18em]">
            AI CHAT INTERFACE
          </span>
          <span className="text-[#3A3A3A]">│</span>
          <span className="text-[#888] text-[9px] tracking-wider">
            PORTFOLIO Q&amp;A · STREAMING GPT-4o
          </span>
        </div>
        <div className="flex items-center gap-3">
          {hasMessages && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-[#666] text-[9px] hover:text-[#AAA] tracking-wider transition-colors"
            >
              <RotateCcw size={10} />
              CLEAR
            </button>
          )}
          <span className="text-[#3A3A3A]">│</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00CC44] animate-pulse" />
            <span className="text-[#00CC44] text-[9px] font-bold tracking-wider">LIVE</span>
          </div>
        </div>
      </div>

      {/* ── Portfolio selector bar ────────────────────────────────────────── */}
      <div className="border-x border-b border-[#2A2A2A] bg-black px-4 py-2.5 flex items-center gap-4 shrink-0">
        <span className="text-[#F5821F] text-[9px] font-bold tracking-[0.15em]">PORTFOLIO</span>
        <div className="relative">
          <button
            onClick={() => setShowPortfolioMenu(m => !m)}
            className="flex items-center gap-2 text-[#E0E0E0] text-[10px] border border-[#2A2A2A] px-3 py-1.5 hover:border-[#F5821F] transition-colors"
          >
            {selectedPortfolio
              ? `#${selectedPortfolio.portfolio_id} — ${selectedPortfolio.portfolio_name} · ${selectedPortfolio.strategy_type ?? "N/A"}`
              : "Select portfolio"
            }
            <ChevronDown size={10} className="text-[#888]" />
          </button>
          {showPortfolioMenu && (
            <div className="absolute top-full left-0 z-50 mt-px w-80 bg-[#0D0D0D] border border-[#2A2A2A] max-h-56 overflow-y-auto">
              {portfolios.map(p => (
                <button
                  key={p.portfolio_id}
                  onClick={() => {
                    setSelectedId(p.portfolio_id);
                    setShowPortfolioMenu(false);
                    clearChat();
                  }}
                  className={`w-full text-left px-3 py-2 text-[10px] border-b border-[#1A1A1A] transition-colors ${
                    p.portfolio_id === selectedId
                      ? "text-[#F5821F] bg-[#F5821F]/5"
                      : "text-[#AAA] hover:text-[#E0E0E0] hover:bg-[#1A1A1A]"
                  }`}
                >
                  #{String(p.portfolio_id).padStart(3, "0")} — {p.portfolio_name} · {p.strategy_type ?? "N/A"}
                  <span className="text-[#555] ml-2">
                    (Customer #{p.customer_id})
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
        {selectedPortfolio && (
          <div className="flex items-center gap-4 ml-2">
            <span className="text-[#555] text-[9px] tracking-wider">
              STRATEGY: <span className="text-[#888]">{selectedPortfolio.strategy_type?.toUpperCase() ?? "—"}</span>
            </span>
            <span className="text-[#555] text-[9px] tracking-wider">
              CCY: <span className="text-[#888]">{selectedPortfolio.currency}</span>
            </span>
          </div>
        )}
      </div>

      {/* ── Message area ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto border-x border-[#2A2A2A] bg-black px-5 py-4">

        {/* Empty state with suggested questions */}
        {!hasMessages && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="text-center">
              <MessageSquare size={28} className="text-[#2A2A2A] mx-auto mb-3" />
              <p className="text-[#E0E0E0] text-xs tracking-wider">
                Ask anything about this portfolio
              </p>
              <p className="text-[#555] text-[10px] mt-1 tracking-wider">
                Agentic GPT-4o · calls live tools on demand · ChromaDB RAG
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 w-full max-w-xl">
              {suggested.map((q, i) => (
                <QuestionChip
                  key={i}
                  text={q}
                  onClick={() => sendMessage(q)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {hasMessages && (
          <div className="space-y-1">
            {messages.map((msg, i) => (
              <Bubble
                key={i}
                msg={msg}
                isStreaming={streaming && i === messages.length - 1 && msg.role === "assistant"}
                toolCalls={i === messages.length - 1 && msg.role === "assistant" ? streamingToolCalls : undefined}
              />
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="border border-[#FF4040]/30 bg-[#FF4040]/5 text-[#FF4040] text-[10px] px-3 py-2 mt-3 tracking-wide">
            ERROR: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ────────────────────────────────────────────────────── */}
      <div className="border border-[#2A2A2A] border-t-0 bg-[#0D0D0D] shrink-0">
        {/* Hint strip */}
        <div className="px-4 py-1 border-b border-[#1A1A1A] flex items-center gap-3">
          <span className="text-[#555] text-[9px] tracking-wider">
            ENTER to send · SHIFT+ENTER for new line
          </span>
          {streaming && (
            <>
              <span className="text-[#3A3A3A]">│</span>
              {streamingToolCalls.length > 0 && streamBuf.current === "" ? (
                <span className="text-[#F5821F] text-[9px] tracking-wider animate-pulse">
                  ● CALLING: {streamingToolCalls[streamingToolCalls.length - 1].replace(/_/g, "_").toUpperCase()}
                </span>
              ) : (
                <span className="text-[#F5821F] text-[9px] tracking-wider animate-pulse">
                  ● GENERATING...
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex items-end gap-0">
          {/* Prompt prefix */}
          <span className="text-[#F5821F] text-[11px] font-bold px-3 pb-3 pt-2.5 shrink-0 self-end">
            &gt;
          </span>

          {/* Textarea */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={streaming || !selectedId}
            placeholder={
              streaming
                ? "Waiting for response..."
                : selectedId
                ? "Type your question..."
                : "Select a portfolio first"
            }
            rows={1}
            className="flex-1 bg-transparent text-[#E0E0E0] text-[11px] placeholder-[#444] resize-none py-2.5 pr-2 focus:outline-none leading-5 tracking-wide"
            style={{ minHeight: "40px", maxHeight: "120px" }}
            onInput={e => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 120) + "px";
            }}
          />

          {/* Send button */}
          <button
            onClick={() => sendMessage(input)}
            disabled={streaming || !input.trim() || !selectedId}
            className="shrink-0 px-4 py-2.5 self-end mb-0 bg-[#F5821F] text-black hover:bg-[#FFB300] disabled:bg-[#2A2A2A] disabled:text-[#555] transition-colors"
          >
            <Send size={13} />
          </button>
        </div>
      </div>

    </div>
  );
}
