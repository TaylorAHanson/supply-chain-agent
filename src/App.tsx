import { useState, useRef, useEffect } from 'react'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ArchitecturePresentation from './ArchitecturePresentation'
import ToolsAndSkillsModal from './ToolsAndSkillsModal'

// Feature flag for architecture presentation
const ENABLE_ARCHITECTURE_UI = import.meta.env.VITE_ENABLE_ARCHITECTURE_UI !== 'false';
const ENABLE_TOOLS_UI = import.meta.env.VITE_ENABLE_TOOLS_UI !== 'false';

interface ToolCall {
  tool_name: string;
  status: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string;
  tool_calls?: ToolCall[];
  trace_id?: string;
  feedback?: 'up' | 'down';
}

interface AvailableTool {
  name: string;
  type: string;
  always_on?: boolean;
}

function ThinkingDisclosure({ text, label, defaultOpen }: { text: string; label: string; defaultOpen: boolean }) {
  // null = follow the auto/default behavior (open while thinking, collapse once the
  // answer arrives); once the user clicks, their choice sticks.
  const [openOverride, setOpenOverride] = useState<boolean | null>(null);
  const open = openOverride === null ? defaultOpen : openOverride;
  const trimmed = text.replace(/\n{3,}/g, '\n\n').trim();

  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setOpenOverride(!open)}
        className="flex items-center gap-1.5 text-[11px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform duration-150 ${open ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
        </svg>
        <span>{label}</span>
      </button>
      {open && (
        <div className="mt-1.5 rounded-md bg-gray-50 border border-gray-100 px-3 py-2 text-[12px] text-gray-500 whitespace-pre-wrap leading-relaxed">
          {trimmed}
        </div>
      )}
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am the EDH Agent. How can I help you today?' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(() => 'sess-' + Math.random().toString(36).substring(2, 9))
  const [showArchitecture, setShowArchitecture] = useState(false)
  const [showTools, setShowTools] = useState(false)
  
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([])
  const [availableSkills, setAvailableSkills] = useState<string[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [userPrompt, setUserPrompt] = useState<string>(() => {
    try { return localStorage.getItem('edh_user_prompt') || '' } catch { return '' }
  })
  const [isToolsLoaded, setIsToolsLoaded] = useState(false)

  useEffect(() => {
    try { localStorage.setItem('edh_user_prompt', userPrompt) } catch { /* ignore */ }
  }, [userPrompt])

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const fetchToolsAndSkills = async () => {
      try {
        const response = await fetch('/tools-and-skills');
        if (response.ok) {
          const data = await response.json();
          setAvailableTools(data.tools || []);
          setAvailableSkills(data.skills || []);
          setSelectedTools(data.default_tools || []);
          setSelectedSkills(data.default_skills || []);
          setIsToolsLoaded(true);
        }
      } catch (err) {
        console.error("Failed to fetch tools", err);
        setIsToolsLoaded(true);
      }
    };
    fetchToolsAndSkills();
  }, []);

  const handleClearChat = async () => {
    try {
      await fetch('/clear_chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      })
      setMessages([{ role: 'assistant', content: 'Chat history cleared. How can I help you today?' }])
    } catch (error) {
      console.error('Error clearing chat:', error)
    }
  }

  const handleFeedback = async (messageIndex: number, rating: 'up' | 'down') => {
    const msg = messages[messageIndex];
    if (msg.role !== 'assistant') return;
    
    // Optimistically update UI
    setMessages(prev => {
      const newMessages = [...prev];
      newMessages[messageIndex] = { ...newMessages[messageIndex], feedback: rating };
      return newMessages;
    });

    try {
      await fetch('/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          session_id: sessionId,
          trace_id: msg.trace_id || 'unknown',
          rating: rating === 'up' ? 1 : -1
        }),
      });
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  // Mutate just the trailing assistant message (the in-flight turn).
  const updateLastMessage = (mutate: (m: Message) => void) => setMessages(prev => {
    const next = [...prev];
    const i = next.length - 1;
    if (next[i]?.role !== 'assistant') return prev;
    const last = { ...next[i] };
    mutate(last);
    next[i] = last;
    return next;
  });

  // Drains an async Genie turn after the agent halted with a pending_poll handle. Each poll is
  // a short request, so no single request is held open past the platform's ~5-min cap — this is
  // what makes long Genie answers reliable instead of leaving the UI stuck on the typing dots.
  const drainGeniePoll = async (handle: { conversation_id: string; response_id: string; space_id?: string; question?: string }) => {
    const startedAt = Date.now();
    const TIMEOUT_MS = 270_000;
    while (Date.now() - startedAt < TIMEOUT_MS) {
      let res: any;
      try {
        const r = await fetch('/genie/poll', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversation_id: handle.conversation_id,
            response_id: handle.response_id,
            space_id: handle.space_id || '',
            question: handle.question || '',
          }),
        });
        res = await r.json();
      } catch {
        updateLastMessage(m => { m.content = 'Sorry, I lost the connection while waiting on Genie.'; });
        return;
      }

      if (res.status === 'complete') {
        const answer = res.answer || '_Genie returned no answer._';
        const link = res.deep_link ? `\n\n[Open in Databricks Genie ↗](${res.deep_link})` : '';
        const full = answer + link;
        updateLastMessage(m => { m.content = full; });
        // Record the answer in the agent's server-side history so follow-ups have context.
        try {
          await fetch('/genie/resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, answer: full }),
          });
        } catch { /* best-effort */ }
        return;
      }
      if (res.status === 'failed') {
        updateLastMessage(m => { m.content = `Genie could not answer: ${res.error || 'unknown error'}`; });
        return;
      }
      // Still running: render Genie's partial answer live (REPLACE — it can change
      // non-additively). Empty partial keeps the typing indicator.
      if (res.answer) updateLastMessage(m => { m.content = res.answer; });
      await new Promise(r => setTimeout(r, res.attempt_after_ms || 3000));
    }
    updateLastMessage(m => { m.content = 'Genie did not respond in time. Please try again or narrow the question.'; });
  };

  const sendQueryAndStream = async (query: string) => {
    let pendingPoll: { conversation_id: string; response_id: string; space_id?: string; question?: string } | null = null;
    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: query,
          selected_tools: selectedTools,
          selected_skills: selectedSkills,
          user_prompt: userPrompt,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      // Check if it's an event stream
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("text/event-stream")) {
        const reader = response.body?.getReader();
        const decoder = new TextDecoder("utf-8");
        
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.substring(6);
                if (dataStr === '[DONE]') break;
                
                try {
                  const data = JSON.parse(dataStr);
                  if (data.type === 'pending_poll') {
                    // The agent started Genie and halted; remember the handle and drive the
                    // poll loop once this (short) stream closes.
                    pendingPoll = data;
                  } else if (data.type === 'chunk') {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        lastMessage.content += data.content;
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  } else if (data.type === 'reasoning') {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        lastMessage.reasoning = (lastMessage.reasoning || '') + data.content;
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  } else if (data.type === 'reclassify') {
                    // A streamed snippet was actually reasoning, not the answer: move it
                    // from the visible message content into the thinking panel.
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        const moved: string = data.content;
                        if (lastMessage.content.endsWith(moved)) {
                          lastMessage.content = lastMessage.content.slice(0, -moved.length);
                        }
                        lastMessage.reasoning = (lastMessage.reasoning || '') + moved;
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  } else if (data.type === 'final') {
                    // Authoritative cleaned answer from the backend — replace the streamed
                    // content so no raw tool scaffolding can remain visible.
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        lastMessage.content = data.content;
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  } else if (data.type === 'tool_calls') {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        lastMessage.tool_calls = data.content;
                        if (lastMessage.content && !lastMessage.content.endsWith('\n\n')) {
                          lastMessage.content += '\n\n';
                        }
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  } else if (data.type === 'trace_id') {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      newMessages[lastMessageIndex] = { ...newMessages[lastMessageIndex], trace_id: data.content };
                      return newMessages;
                    });
                  }
                } catch (e) {
                  // Ignore parse errors for incomplete JSON chunks
                }
              }
            }
          }

          // The agent halted on an async Genie call: drain it via short poll requests so the
          // answer streams in reliably instead of leaving the UI stuck on the typing dots.
          if (pendingPoll) {
            await drainGeniePoll(pendingPoll);
          }
        }
      } else {
        // Standard JSON response
        const data = await response.json()
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            role: 'assistant',
            content: data.message,
            tool_calls: data.tool_calls
          };
          return newMessages;
        });
      }
      
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          role: 'assistant',
          content: 'Sorry, I encountered an error communicating with the server.'
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message and a placeholder for the assistant's response
    setMessages(prev => [
      ...prev, 
      { role: 'user', content: userMessage },
      { role: 'assistant', content: '', tool_calls: [] } // Placeholder
    ])
    setIsLoading(true)

    await sendQueryAndStream(userMessage)
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setMessages(prev => [...prev, { role: 'user', content: `[Uploading file: ${file.name}]` }])
    setIsLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()
      
      // Notify the agent generically that a file was uploaded so it can respond
      setMessages(prev => [
        ...prev, 
        { role: 'assistant', content: '', tool_calls: [] } // Placeholder
      ])
      
      const query = `[System Event] I have successfully uploaded a file named "${data.filename}" to the volume path "${data.volume_path}". Please acknowledge this upload and ask me what I would like to do with it.`
      await sendQueryAndStream(query)
      
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Failed to upload file ${file.name}.` 
      }])
      setIsLoading(false)
    } finally {
      // Reset input
      e.target.value = ''
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-sm">
      <header className="bg-white shadow-sm px-4 py-2 flex justify-between items-center">
        <div>
          <h1 className="text-base font-semibold text-gray-800">EDH Agent</h1>
          <p className="text-[10px] text-gray-500">Databricks Agent Framework + FastMCP</p>
        </div>
        <div className="flex items-center space-x-2">
          {ENABLE_TOOLS_UI && (
            <button
              onClick={() => setShowTools(true)}
              className="text-xs bg-[#3253DC] text-white hover:bg-[#2842b0] px-3 py-1.5 rounded-md font-medium transition-colors flex items-center"
            >
              <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
              </svg>
              My Tools & Skills
            </button>
          )}
          {ENABLE_ARCHITECTURE_UI && (
            <button
              onClick={() => setShowArchitecture(true)}
              className="text-xs bg-[#3253DC] text-white hover:bg-[#2842b0] px-3 py-1.5 rounded-md font-medium transition-colors flex items-center"
            >
              <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
              </svg>
              Architecture
            </button>
          )}
        </div>
      </header>

      {showArchitecture && (
        <ArchitecturePresentation onClose={() => setShowArchitecture(false)} />
      )}

      {showTools && (
        <ToolsAndSkillsModal 
          onClose={() => setShowTools(false)} 
          availableTools={availableTools}
          availableSkills={availableSkills}
          selectedTools={selectedTools}
          selectedSkills={selectedSkills}
          onToolsChange={setSelectedTools}
          onSkillsChange={setSelectedSkills}
          userPrompt={userPrompt}
          onUserPromptChange={setUserPrompt}
          isLoading={!isToolsLoaded}
        />
      )}

      <main className="flex-1 overflow-y-auto p-3">
        <div className="w-full mx-auto space-y-3">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[90%] rounded-lg p-3 ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white border border-gray-200 text-gray-800'
              }`}>
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                ) : (
                  <>
                  {msg.reasoning && (
                    <ThinkingDisclosure
                      text={msg.reasoning}
                      label={isLoading && idx === messages.length - 1 && !msg.content ? 'Thinking…' : 'Thoughts'}
                      defaultOpen={isLoading && idx === messages.length - 1 && !msg.content}
                    />
                  )}
                  <div className="agent-message-content leading-relaxed prose prose-sm max-w-none">
                    {msg.content ? (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                        {isLoading && idx === messages.length - 1 && (
                          <div className="flex items-center space-x-1.5 h-6 px-1 mt-2">
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex items-center space-x-1.5 h-6 px-1">
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    )}
                  </div>
                  </>
                )}
                
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100">
                    <p className="text-[10px] font-semibold text-gray-400 mb-1">TOOLS USED</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.tool_calls.map((tc, tIdx) => (
                        <span key={tIdx} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500">
                          <svg className="w-2.5 h-2.5 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                          {tc.tool_name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {msg.role === 'assistant' && !isLoading && idx > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100 flex justify-end space-x-2">
                    <button 
                      onClick={() => handleFeedback(idx, 'up')}
                      className={`p-1 rounded hover:bg-gray-100 transition-colors ${msg.feedback === 'up' ? 'text-green-600' : 'text-gray-400'}`}
                      title="Helpful response"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path></svg>
                    </button>
                    <button 
                      onClick={() => handleFeedback(idx, 'down')}
                      className={`p-1 rounded hover:bg-gray-100 transition-colors ${msg.feedback === 'down' ? 'text-red-600' : 'text-gray-400'}`}
                      title="Not helpful"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"></path></svg>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && !messages[messages.length - 1]?.content && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-lg p-3 flex items-center space-x-1.5">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 p-3">
        <div className="w-full mx-auto">
          <form onSubmit={handleSubmit} className="flex space-x-2 items-center">
            <label className="cursor-pointer bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded text-xs font-medium transition-colors border border-gray-300 flex-shrink-0">
              Upload
              <input 
                type="file" 
                className="hidden" 
                accept=".csv,.xlsx" 
                onChange={handleFileUpload} 
                disabled={isLoading} 
              />
            </label>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent text-gray-800"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 text-white px-4 py-1.5 rounded text-xs font-medium hover:bg-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              Send
            </button>
            <button
              type="button"
              onClick={handleClearChat}
              disabled={isLoading}
              className="bg-gray-100 text-gray-700 border border-gray-300 px-3 py-1.5 rounded text-xs font-medium hover:bg-gray-200 focus:outline-none focus:ring-1 focus:ring-gray-400 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              Clear
            </button>
          </form>
        </div>
      </footer>
    </div>
  )
}

export default App
