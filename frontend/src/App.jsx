import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Bot, User, Activity, MessageSquare, Plus, Trash2, LogOut, ShieldAlert } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://lpjcmbjjtqktzptosvvi.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_t7TT7TL40gvYAKFJl5Yw8g_qPZPRXkj';
const supabaseClient = createClient(supabaseUrl, supabaseAnonKey);

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

// ── Auth Screen ───────────────────────────────────────────────────────────────
function AuthScreen({ onAuthSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [infoMsg, setInfoMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setInfoMsg('');
    setLoading(true);

    try {
      if (isSignUp) {
        const { error } = await supabaseClient.auth.signUp({ email, password });
        if (error) throw error;
        setInfoMsg('Verification email sent! Check your inbox to confirm.');
      } else {
        const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
        if (error) throw error;
        if (data.session) onAuthSuccess(data.session);
      }
    } catch (err) {
      setErrorMsg(err.message || 'An error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#0B0F19] text-slate-100 relative p-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[20%] left-[20%] w-[60%] h-[60%] rounded-full bg-blue-500/[0.08] blur-[130px]" />
        <div className="absolute bottom-[20%] right-[20%] w-[50%] h-[50%] rounded-full bg-purple-500/[0.08] blur-[130px]" />
      </div>

      <div className="w-full max-w-md bg-[#12192B]/60 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-2xl relative z-10 animate-in fade-in zoom-in-95 duration-300">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Activity className="text-white w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            {isSignUp ? 'Create your Account' : 'Welcome to FinBot'}
          </h2>
          <p className="text-xs text-slate-500 text-center">
            {isSignUp ? 'Sign up to start analyzing NIFTY 50 metrics' : 'Sign in to access your financial research workspace'}
          </p>
        </div>

        {errorMsg && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs p-3.5 rounded-xl mb-5 animate-in fade-in">
            {errorMsg}
          </div>
        )}

        {infoMsg && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs p-3.5 rounded-xl mb-5 animate-in fade-in">
            {infoMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              className="w-full bg-[#1E293B]/70 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full bg-[#1E293B]/70 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-medium text-sm py-3 rounded-xl transition-all shadow-lg shadow-blue-500/20 hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
          >
            {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setErrorMsg('');
              setInfoMsg('');
            }}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
          >
            {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function App() {
  const [session, setSession]         = useState(null);
  const [sessions, setSessions]       = useState([]);
  const [sessionId, setSessionId]     = useState(null);
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [isLoading, setIsLoading]     = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [adminOverlay, setAdminOverlay] = useState(false);
  const [resetConfirm, setResetConfirm] = useState('');
  const chatRef     = useRef(null);
  const textareaRef = useRef(null);

  // ── Listen for Supabase Auth state changes ───────────────────────────────
  useEffect(() => {
    supabaseClient.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const { data: { subscription } } = supabaseClient.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabaseClient.auth.signOut();
    setSession(null);
    setSessions([]);
    setMessages([]);
  };

  // ── Load sessions from backend (JWT Protected) ──────────────────────────────
  const fetchSessions = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
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
  }, [session]);

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

  // ── Load history when session changes (JWT Protected) ──────────────────────
  useEffect(() => {
    if (!sessionId || !session?.access_token) return;
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/history/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${session.access_token}` }
        });
        if (cancelled) return;
        if (res.ok) {
          const data = await res.json();
          if (data.messages?.length > 0) {
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
  }, [sessionId, session]);

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

  // ── Delete session (JWT Protected) ──────────────────────────────────────────
  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!session?.access_token) return;
    try {
      await fetch(`${API_BASE}/history/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
    } catch (_) {}
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      if (sessionId === id) {
        if (next.length > 0) setTimeout(() => setSessionId(next[0].id), 0);
        else setTimeout(handleNewChat, 0);
      }
      return next;
    });
  };

  // ── Send message (JWT Protected) ────────────────────────────────────────────
  const handleSend = async (overrideText) => {
    const msg = (overrideText ?? input).trim();
    if (!msg || isLoading || !session?.access_token) return;
    setInput('');

    setSessions(prev => prev.map(s => {
      if (s.id === sessionId) {
        const isDefault = s.name === 'New Chat';
        return {
          ...s,
          name: isDefault
            ? msg.substring(0, 38) + (msg.length > 38 ? '…' : '')
            : s.name,
          messageCount: (s.messageCount || 0) + 1,
        };
      }
      return s;
    }));

    setMessages(prev => [...prev, { role: 'user', text: msg }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ message: msg, session_id: sessionId }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', text: data.answer, isNew: true }]);
      fetchSessions(); // refresh sidebar previews
    } catch (_) {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `⚠️ Could not reach the backend. Make sure the server is running on \`${API_BASE}\`.`,
        isNew: false,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Admin Reset All Database (JWT Admin Protected) ──────────────────────────
  const handleAdminReset = async () => {
    if (resetConfirm !== 'RESET' || !session?.access_token) return;
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      if (res.ok) {
        setSessions([]);
        setMessages([{ role: 'ai', text: INTRO_MESSAGE, isNew: true }]);
        setAdminOverlay(false);
        setResetConfirm('');
        handleNewChat();
      } else {
        alert('Verification failed or unauthorized action.');
      }
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  const markMessageDone = (idx) =>
    setMessages(prev => prev.map((m, i) => i === idx ? { ...m, isNew: false } : m));

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // Render Auth Screen if not logged in
  if (!session) {
    return <AuthScreen onAuthSuccess={setSession} />;
  }

  // Parse claims for admin role check
  const isAdmin = session?.user?.app_metadata?.role === 'admin' || session?.user?.role === 'admin';

  // ── Render Dashboard ──────────────────────────────────────────────────────────
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

          {/* Logo & Logout */}
          <div className="flex items-center justify-between mb-6 shrink-0">
            <div className="flex items-center gap-3">
              <Activity className="text-blue-400 w-7 h-7 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]" />
              <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">FinBot</h2>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-400 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all cursor-pointer"
              title="Sign Out"
            >
              <LogOut size={16} />
            </button>
          </div>

          {/* New Chat button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 p-2.5 mb-5 rounded-xl
              bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium
              transition-all shadow-lg shadow-blue-500/20 hover:scale-[1.02] active:scale-[0.98] shrink-0 cursor-pointer"
          >
            <Plus size={16} /> New Chat
          </button>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin scrollbar-thumb-slate-700 custom-scrollbar">
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
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all text-left group cursor-pointer
                  ${s.id === sessionId
                    ? 'bg-slate-800/90 border border-white/10 text-white'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-white'}`}
              >
                <MessageSquare size={13} className={`shrink-0 ${s.id === sessionId ? 'text-blue-400' : 'group-hover:text-blue-400'}`} />
                <span className="truncate text-xs flex-1">{s.name}</span>
                <span
                  onClick={(e) => handleDelete(e, s.id)}
                  className="opacity-0 group-hover:opacity-50 hover:!opacity-100 shrink-0 p-0.5 rounded hover:text-red-400 transition-all cursor-pointer"
                  title="Delete chat"
                  role="button"
                >
                  <Trash2 size={12} />
                </span>
              </button>
            ))}
          </div>

          {/* Admin Panel Button */}
          {isAdmin && (
            <button
              onClick={() => setAdminOverlay(true)}
              className="w-full flex items-center justify-center gap-2 p-2 rounded-xl mb-4
                border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-400 text-xs font-semibold
                transition-all cursor-pointer"
            >
              Admin: Reset Database
            </button>
          )}

          {/* User profile */}
          <div className="border-t border-white/10 pt-4 flex flex-col gap-1.5 shrink-0">
            <p className="text-[10px] text-slate-500 truncate px-1">Signed in as:</p>
            <p className="text-xs text-slate-300 truncate font-medium px-1">{session.user.email}</p>
            <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500 px-1">
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_6px_#10B981]" />
              NIFTY 50 · Connected
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main panel ───────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col relative z-10 min-w-0">

        {/* Header */}
        <header className="px-5 py-3.5 border-b border-white/10 bg-[#0B0F19]/80 backdrop-blur-md flex items-center gap-3 shrink-0">
          <button
            onClick={() => setSidebarOpen(p => !p)}
            className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800 cursor-pointer"
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
          className="flex-1 overflow-y-auto px-5 py-6 space-y-5 scrollbar-thin scrollbar-thumb-slate-700 custom-scrollbar"
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
                hover:scale-105 active:scale-95 shrink-0 shadow-lg shadow-blue-500/20 cursor-pointer"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="text-[9px] text-center text-slate-600 mt-2 uppercase tracking-[0.15em]">
            AI-generated analysis · Verify with NSE official filings
          </p>
        </div>
      </main>

      {/* ── Admin Reset Overlay Modal ─────────────────────────────────────────── */}
      {adminOverlay && (
        <div className="absolute inset-0 bg-[#0B0F19]/80 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in">
          <div className="w-full max-w-md bg-[#12192B] border border-red-500/20 rounded-3xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 text-red-400 mb-4">
              <ShieldAlert size={28} />
              <h3 className="text-lg font-bold">Administrative Reset</h3>
            </div>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              This action is protected by strict role policies. Executing this will permanently wipe all conversation transcripts and session summaries for <strong>ALL</strong> users in the database.
            </p>
            <p className="text-xs text-slate-300 font-semibold mb-4">
              To proceed, please type <code className="text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded">RESET</code> below:
            </p>
            <input
              type="text"
              value={resetConfirm}
              onChange={e => setResetConfirm(e.target.value)}
              placeholder="RESET"
              className="w-full bg-[#1E293B] border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-red-500/50 focus:ring-1 focus:ring-red-500/20 outline-none transition-all text-center tracking-widest font-mono mb-5"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setAdminOverlay(false); setResetConfirm(''); }}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-xs font-semibold py-2.5 rounded-xl transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAdminReset}
                disabled={resetConfirm !== 'RESET'}
                className="flex-1 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:opacity-40 text-xs font-semibold py-2.5 rounded-xl transition-all shadow-lg shadow-red-500/20 cursor-pointer"
              >
                Execute Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}