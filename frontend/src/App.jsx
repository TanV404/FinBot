import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Bot, User, Activity, MessageSquare, Plus, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const generateSessionId = () => `session_${Math.random().toString(36).substring(2, 11)}`;

const INTRO_MESSAGE = `## Hello! I'm **FinBot** 🚀

I've analysed the **NIFTY 50** knowledge graph — covering financials, leadership, sectors, and shareholding for all 50 index companies.

Try asking me:
• **"What was Reliance's revenue last quarter?"**
• **"Who is the CEO of HDFC Bank?"**
• **"Compare TCS and Infosys revenue"**
• **"Which companies are in the Financial Services sector?"**`;

// ── Typewriter effect ──────────────────────────────────────────────────────────
const TypewriterText = ({ text, delay = 8, onComplete }) => {
  const [displayed, setDisplayed] = useState('');
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      setDisplayed(text.substring(0, i + 1));
      i++;
      if (i >= text.length) { clearInterval(id); onComplete?.(); }
    }, delay);
    return () => clearInterval(id);
  }, [text, delay, onComplete]);
  return <ReactMarkdown>{displayed}</ReactMarkdown>;
};

// ── Message bubble ─────────────────────────────────────────────────────────────
const MessageBubble = ({ msg, markDone }) => {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-3 max-w-[88%] animate-in slide-in-from-bottom-2 duration-300 ${isUser ? 'ml-auto flex-row-reverse' : ''}`}>
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${isUser ? 'bg-slate-800 border border-white/10' : 'bg-blue-600 shadow-blue-500/20 shadow-lg'}`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`p-4 rounded-2xl text-[14px] leading-relaxed shadow-lg ${
        isUser
          ? 'bg-gradient-to-br from-blue-600 to-blue-700 rounded-tr-none text-white'
          : 'bg-[#1E293B]/80 border border-white/10 rounded-tl-none text-slate-200'
      }`}>
        <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-headings:mb-2 prose-ul:my-1 prose-li:my-0.5">
          {!isUser && msg.isNew
            ? <TypewriterText text={msg.text} onComplete={markDone} />
            : <ReactMarkdown>{msg.text}</ReactMarkdown>
          }
        </div>
      </div>
    </div>
  );
};

// ── Main App ───────────────────────────────────────────────────────────────────
export default function App() {
  const [sessions, setSessions]       = useState([]);
  const [sessionId, setSessionId]     = useState(null);
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [isLoading, setIsLoading]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatRef     = useRef(null);
  const textareaRef = useRef(null);

  // ── Load sessions from backend ──────────────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/sessions');
      if (!res.ok) return;
      const data = await res.json();
      const remote = (data.sessions || []).map(s => ({
        id: s.id,
        name: s.preview
          ? s.preview.substring(0, 38) + (s.preview.length > 38 ? '…' : '')
          : 'New Chat',
        messageCount: s.message_count,
      }));
      setSessions(prev => {
        const remoteIds = new Set(remote.map(s => s.id));
        const localOnly = prev.filter(s => !remoteIds.has(s.id));
        return [...localOnly, ...remote];
      });
    } catch (_) { /* server not up yet */ }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  // Create first session if none exist
  useEffect(() => {
    if (sessions.length === 0) {
      const first = { id: generateSessionId(), name: 'New Chat', messageCount: 0 };
      setSessions([first]);
      setSessionId(first.id);
    } else if (!sessionId) {
      setSessionId(sessions[0].id);
    }
  }, [sessions, sessionId]);

  // ── Load history when session changes ──────────────────────────────────────
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/history/${sessionId}`);
        if (cancelled) return;
        if (res.ok) {
          const data = await res.json();
          if (data.messages?.length > 0) {
            // Role from backend: 'user' or 'ai' (fixed in main.py)
            setMessages(data.messages.map(m => ({
              role: m.role,
              text: m.content,
              isNew: false,
            })));
          } else {
            setMessages([{ role: 'ai', text: INTRO_MESSAGE, isNew: true }]);
          }
        } else {
          setMessages([{ role: 'ai', text: INTRO_MESSAGE, isNew: true }]);
        }
      } catch (_) {
        if (!cancelled) setMessages([{ role: 'ai', text: INTRO_MESSAGE, isNew: true }]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [sessionId]);

  // ── Auto-scroll ─────────────────────────────────────────────────────────────
  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Auto-resize textarea ────────────────────────────────────────────────────
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }, [input]);

  // ── New chat ────────────────────────────────────────────────────────────────
  const handleNewChat = () => {
    const s = { id: generateSessionId(), name: 'New Chat', messageCount: 0 };
    setSessions(prev => [s, ...prev]);
    setSessionId(s.id);
  };

  // ── Delete session ──────────────────────────────────────────────────────────
  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try { await fetch(`http://localhost:8000/history/${id}`, { method: 'DELETE' }); } catch (_) {}
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      if (sessionId === id) {
        if (next.length > 0) setTimeout(() => setSessionId(next[0].id), 0);
        else setTimeout(handleNewChat, 0);
      }
      return next;
    });
  };

  // ── Send message ────────────────────────────────────────────────────────────
  const handleSend = async (overrideText) => {
    const msg = (overrideText ?? input).trim();
    if (!msg || isLoading) return;
    setInput('');

    setSessions(prev => prev.map(s =>
      s.id === sessionId && s.messageCount === 0
        ? { ...s, name: msg.substring(0, 38) + (msg.length > 38 ? '…' : ''), messageCount: 1 }
        : s
    ));

    setMessages(prev => [...prev, { role: 'user', text: msg }]);
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: sessionId }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', text: data.answer, isNew: true }]);
      fetchSessions(); // refresh sidebar previews
    } catch (_) {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: '⚠️ Could not reach the backend. Make sure the server is running on `http://localhost:8000`.',
        isNew: false,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const markMessageDone = (idx) =>
    setMessages(prev => prev.map((m, i) => i === idx ? { ...m, isNew: false } : m));

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen w-full bg-[#0B0F19] text-slate-100 overflow-hidden relative">

      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[40%] left-[10%] w-[55%] h-[55%] rounded-full bg-blue-500/[0.07] blur-[130px]" />
        <div className="absolute top-[20%] right-[5%] w-[45%] h-[45%] rounded-full bg-purple-500/[0.07] blur-[130px]" />
      </div>

      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <aside
        className={`${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'}
          transition-[width] duration-300 flex flex-col bg-[#12192B]/70 backdrop-blur-xl
          border-r border-white/10 z-10 shrink-0`}
      >
        <div className="flex flex-col h-full p-5 min-w-[17rem]">

          {/* Logo */}
          <div className="flex items-center gap-3 mb-6 shrink-0">
            <Activity className="text-blue-400 w-7 h-7 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]" />
            <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">FinBot</h2>
          </div>

          {/* New Chat button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 p-2.5 mb-5 rounded-xl
              bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium
              transition-all shadow-lg shadow-blue-500/20 hover:scale-[1.02] active:scale-[0.98] shrink-0"
          >
            <Plus size={16} /> New Chat
          </button>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin scrollbar-thumb-slate-700">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 px-1">
              Conversations
            </p>
            {sessions.length === 0 && (
              <p className="text-xs text-slate-600 px-2 italic">No conversations yet</p>
            )}
            {sessions.map(s => (
              <button
                key={s.id}
                onClick={() => setSessionId(s.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all text-left group
                  ${s.id === sessionId
                    ? 'bg-slate-800/90 border border-white/10 text-white'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-white'}`}
              >
                <MessageSquare size={13} className={`shrink-0 ${s.id === sessionId ? 'text-blue-400' : 'group-hover:text-blue-400'}`} />
                <span className="truncate text-xs flex-1">{s.name}</span>
                <span
                  onClick={(e) => handleDelete(e, s.id)}
                  className="opacity-0 group-hover:opacity-50 hover:!opacity-100 shrink-0 p-0.5 rounded hover:text-red-400 transition-all"
                  title="Delete chat"
                  role="button"
                >
                  <Trash2 size={12} />
                </span>
              </button>
            ))}
          </div>

          {/* Status */}
          <div className="pt-4 mt-4 border-t border-white/10 flex items-center gap-2 text-[11px] text-slate-500 shrink-0">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_6px_#10B981]" />
            NIFTY 50 · Knowledge Graph Active
          </div>
        </div>
      </aside>

      {/* ── Main panel ───────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col relative z-10 min-w-0">

        {/* Header */}
        <header className="px-5 py-3.5 border-b border-white/10 bg-[#0B0F19]/80 backdrop-blur-md flex items-center gap-3 shrink-0">
          <button
            onClick={() => setSidebarOpen(p => !p)}
            className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800"
            title="Toggle sidebar"
          >
            <MessageSquare size={17} />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold tracking-tight truncate">Financial Research Assistant</h1>
            <p className="text-[10px] text-slate-500">NIFTY 50 · GraphRAG · {sessions.find(s => s.id === sessionId)?.name || '—'}</p>
          </div>
        </header>

        {/* Messages */}
        <div
          ref={chatRef}
          className="flex-1 overflow-y-auto px-5 py-6 space-y-5 scrollbar-thin scrollbar-thumb-slate-700"
        >
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              msg={msg}
              markDone={() => markMessageDone(i)}
            />
          ))}

          {isLoading && (
            <div className="flex gap-3 max-w-[88%]">
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-blue-500/20 shadow-lg shrink-0">
                <Bot size={16} />
              </div>
              <div className="bg-[#1E293B]/80 px-5 py-4 rounded-2xl rounded-tl-none border border-white/10 flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" />
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-5 pb-4 pt-2 bg-gradient-to-t from-[#0B0F19] via-[#0B0F19]/95 to-transparent shrink-0">
          <div className="max-w-3xl mx-auto flex gap-2 bg-[#1E293B]/70 border border-white/10 rounded-2xl px-4 py-3
            focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/20
            transition-all shadow-2xl items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about financials, leadership, sectors…  (Enter to send)"
              className="flex-1 bg-transparent border-none outline-none resize-none text-sm placeholder:text-slate-500 min-h-[38px] max-h-[150px] py-1"
              rows={1}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:opacity-40 text-white
                w-9 h-9 rounded-xl flex items-center justify-center transition-all
                hover:scale-105 active:scale-95 shrink-0 shadow-lg shadow-blue-500/20"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="text-[9px] text-center text-slate-600 mt-2 uppercase tracking-[0.15em]">
            AI-generated analysis · Verify with NSE official filings
          </p>
        </div>
      </main>
    </div>
  );
}