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
import { manrope, GOLD, WHITE, MUTED, NEAR_BLACK, BORDER, RED, GREEN } from "@/lib/theme";

// ── Typing cursor ─────────────────────────────────────────────────────────────
function Cursor() {
  return (
    <span className="inline-block w-[7px] h-[13px] ml-0.5 animate-pulse align-middle" style={{ background: GOLD }} />
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
    <div className="flex flex-wrap gap-1 mb-2 pb-2" style={{ borderBottom: `1px solid ${BORDER}` }}>
      {tools.map((t, i) => (
        <span
          key={i}
          className="text-[8px] font-bold tracking-wide px-2 py-0.5 rounded-full"
          style={{ color: GOLD, border: `1px solid ${BORDER}`, background: "rgba(250,189,73,0.06)" }}
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
          <div className="text-black text-[12px] px-4 py-2.5 leading-5 font-medium rounded-2xl rounded-tr-md" style={{ background: GOLD }}>
            {msg.content}
          </div>
          <p className="text-[9px] text-right mt-1 tracking-wide" style={{ color: MUTED }}>YOU</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[80%]">
        <p className="text-[9px] font-bold tracking-wide mb-1" style={{ color: GOLD }}>
          FINSIGHT AI
        </p>
        <div className="text-[12px] px-4 py-3 leading-6 rounded-2xl rounded-tl-md" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, color: WHITE }}>
          <ToolChips tools={toolCalls ?? []} />
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <p className="font-bold tracking-wide mt-3 mb-1" style={{ color: GOLD }}>{children}</p>,
              h2: ({ children }) => <p className="font-bold tracking-wide mt-3 mb-1" style={{ color: GOLD }}>{children}</p>,
              h3: ({ children }) => <p className="font-bold tracking-wide mt-3 mb-1" style={{ color: GOLD }}>{children}</p>,
              strong: ({ children }) => <span className="font-bold" style={{ color: WHITE }}>{children}</span>,
              em: ({ children }) => <span className="italic" style={{ color: MUTED }}>{children}</span>,
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 mb-2">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-0.5 mb-2">{children}</ol>,
              li: ({ children }) => <li style={{ color: WHITE }}>{children}</li>,
              code: ({ children }) => <code className="px-1 rounded text-[10px]" style={{ background: "rgba(255,255,255,0.06)", color: GOLD }}>{children}</code>,
              pre: ({ children }) => <pre className="p-2 rounded text-[10px] overflow-x-auto mb-2" style={{ background: "rgba(255,255,255,0.06)" }}>{children}</pre>,
              hr: () => <hr className="my-2" style={{ borderColor: BORDER }} />,
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
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="text-left text-[11px] px-3.5 py-2.5 rounded-xl transition-colors tracking-wide"
      style={{ color: hover ? GOLD : MUTED, border: `1px solid ${hover ? "rgba(250,189,73,0.4)" : BORDER}` }}
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
    <div className={`max-w-5xl mx-auto flex flex-col h-[calc(100vh-72px)] ${manrope.className}`}>

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <div className="rounded-t-2xl flex items-center justify-between px-4 py-3 shrink-0" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
        <div className="flex items-center gap-3">
          <MessageSquare size={14} style={{ color: GOLD }} />
          <span className="text-[11px] font-bold tracking-wide" style={{ color: GOLD }}>
            AI Chat
          </span>
          <span style={{ color: BORDER }}>│</span>
          <span className="text-[10px] tracking-wide" style={{ color: MUTED }}>
            Portfolio Q&amp;A · streaming GPT-4o
          </span>
        </div>
        <div className="flex items-center gap-3">
          {hasMessages && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-[10px] tracking-wide transition-colors"
              style={{ color: MUTED }}
              onMouseEnter={e => (e.currentTarget.style.color = WHITE)}
              onMouseLeave={e => (e.currentTarget.style.color = MUTED)}
            >
              <RotateCcw size={11} />
              Clear
            </button>
          )}
          <span style={{ color: BORDER }}>│</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: GREEN }} />
            <span className="text-[10px] font-bold tracking-wide" style={{ color: GREEN }}>LIVE</span>
          </div>
        </div>
      </div>

      {/* ── Portfolio selector bar ────────────────────────────────────────── */}
      <div className="px-4 py-3 flex items-center gap-4 shrink-0" style={{ background: "#000", borderLeft: `1px solid ${BORDER}`, borderRight: `1px solid ${BORDER}` }}>
        <span className="text-[10px] font-bold tracking-wide" style={{ color: GOLD }}>PORTFOLIO</span>
        <div className="relative">
          <button
            onClick={() => setShowPortfolioMenu(m => !m)}
            className="flex items-center gap-2 text-[11px] rounded-lg px-3.5 py-2 transition-colors"
            style={{ color: WHITE, border: `1px solid ${BORDER}` }}
          >
            {selectedPortfolio
              ? `#${selectedPortfolio.portfolio_id} — ${selectedPortfolio.portfolio_name} · ${selectedPortfolio.strategy_type ?? "N/A"}`
              : "Select portfolio"
            }
            <ChevronDown size={11} style={{ color: MUTED }} />
          </button>
          {showPortfolioMenu && (
            <div className="absolute top-full left-0 z-50 mt-1 w-80 rounded-xl overflow-hidden max-h-56 overflow-y-auto" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}` }}>
              {portfolios.map(p => (
                <button
                  key={p.portfolio_id}
                  onClick={() => {
                    setSelectedId(p.portfolio_id);
                    setShowPortfolioMenu(false);
                    clearChat();
                  }}
                  className="w-full text-left px-3.5 py-2.5 text-[11px] transition-colors"
                  style={{
                    borderBottom: `1px solid ${BORDER}`,
                    color: p.portfolio_id === selectedId ? GOLD : MUTED,
                    background: p.portfolio_id === selectedId ? "rgba(250,189,73,0.06)" : "transparent",
                  }}
                >
                  #{String(p.portfolio_id).padStart(3, "0")} — {p.portfolio_name} · {p.strategy_type ?? "N/A"}
                  <span className="ml-2" style={{ color: MUTED }}>
                    (Customer #{p.customer_id})
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
        {selectedPortfolio && (
          <div className="flex items-center gap-4 ml-2">
            <span className="text-[10px] tracking-wide" style={{ color: MUTED }}>
              STRATEGY: <span style={{ color: WHITE }}>{selectedPortfolio.strategy_type?.toUpperCase() ?? "—"}</span>
            </span>
            <span className="text-[10px] tracking-wide" style={{ color: MUTED }}>
              CCY: <span style={{ color: WHITE }}>{selectedPortfolio.currency}</span>
            </span>
          </div>
        )}
      </div>

      {/* ── Message area ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-4" style={{ background: "#000", borderLeft: `1px solid ${BORDER}`, borderRight: `1px solid ${BORDER}` }}>

        {/* Empty state with suggested questions */}
        {!hasMessages && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="text-center">
              <MessageSquare size={28} className="mx-auto mb-3" style={{ color: BORDER }} />
              <p className="text-xs tracking-wide" style={{ color: WHITE }}>
                Ask anything about this portfolio
              </p>
              <p className="text-[10px] mt-1 tracking-wide" style={{ color: MUTED }}>
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
          <div className="rounded-lg text-[11px] px-3 py-2 mt-3 tracking-wide" style={{ border: `1px solid ${RED}4d`, background: `${RED}0d`, color: RED }}>
            Error: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ────────────────────────────────────────────────────── */}
      <div className="rounded-b-2xl shrink-0" style={{ background: NEAR_BLACK, border: `1px solid ${BORDER}`, borderTop: "none" }}>
        {/* Hint strip */}
        <div className="px-4 py-1.5 flex items-center gap-3" style={{ borderBottom: `1px solid ${BORDER}` }}>
          <span className="text-[9px] tracking-wide" style={{ color: MUTED }}>
            ENTER to send · SHIFT+ENTER for new line
          </span>
          {streaming && (
            <>
              <span style={{ color: BORDER }}>│</span>
              {streamingToolCalls.length > 0 && streamBuf.current === "" ? (
                <span className="text-[9px] tracking-wide animate-pulse" style={{ color: GOLD }}>
                  ● Calling: {streamingToolCalls[streamingToolCalls.length - 1].replace(/_/g, " ").toUpperCase()}
                </span>
              ) : (
                <span className="text-[9px] tracking-wide animate-pulse" style={{ color: GOLD }}>
                  ● Generating...
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex items-end gap-0">
          {/* Prompt prefix */}
          <span className="text-[12px] font-bold px-3 pb-3 pt-2.5 shrink-0 self-end" style={{ color: GOLD }}>
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
            className="flex-1 bg-transparent text-[12px] resize-none py-2.5 pr-2 focus:outline-none leading-5 tracking-wide"
            style={{ minHeight: "40px", maxHeight: "120px", color: WHITE }}
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
            className="shrink-0 px-4 py-2.5 self-end mb-0 rounded-br-2xl transition-colors disabled:cursor-not-allowed"
            style={{
              background: streaming || !input.trim() || !selectedId ? "rgba(255,255,255,0.06)" : GOLD,
              color: streaming || !input.trim() || !selectedId ? MUTED : "#000",
            }}
          >
            <Send size={14} />
          </button>
        </div>
      </div>

    </div>
  );
}
