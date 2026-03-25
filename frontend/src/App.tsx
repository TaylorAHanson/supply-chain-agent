import { useState, useRef, useEffect } from 'react'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ToolCall {
  tool_name: string;
  status: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: ToolCall[];
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I am your Supply Chain AI Agent. How can I help you today?' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(() => 'sess-' + Math.random().toString(36).substring(2, 9))
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: userMessage,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      // Check if it's an event stream (LOCAL_MODE)
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("text/event-stream")) {
        const reader = response.body?.getReader();
        const decoder = new TextDecoder("utf-8");
        
        if (reader) {
          // Keep isLoading true until the stream finishes so the send button stays disabled
          
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
                  if (data.type === 'chunk') {
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
                  } else if (data.type === 'tool_calls') {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      const lastMessageIndex = newMessages.length - 1;
                      const lastMessage = { ...newMessages[lastMessageIndex] };
                      if (lastMessage.role === 'assistant') {
                        lastMessage.tool_calls = data.content;
                      }
                      newMessages[lastMessageIndex] = lastMessage;
                      return newMessages;
                    });
                  }
                } catch (e) {
                  // Ignore parse errors for incomplete JSON chunks
                }
              }
            }
          }
        }
      } else {
        // Standard JSON response
        const data = await response.json()
        setMessages(prev => {
          const newMessages = [...prev];
          // Replace the placeholder with the actual response
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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setMessages(prev => [...prev, { role: 'user', content: `[Uploading file: ${file.name}]` }])
    setIsLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()
      
      // Notify the agent generically that a file was uploaded so it can respond
      try {
        const autoResponse = await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId,
            query: `[System Event] I have successfully uploaded a file named "${data.filename}" to the volume path "${data.volume_path}". Please acknowledge this upload and ask me what I would like to do with it.`,
          }),
        })
        
        if (autoResponse.ok) {
          const autoData = await autoResponse.json()
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: autoData.message,
            tool_calls: autoData.tool_calls 
          }])
        } else {
          throw new Error("Agent failed to respond to upload notification")
        }
      } catch (autoErr) {
        console.error('Error communicating upload to agent:', autoErr)
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `File ${data.filename} uploaded successfully to ${data.volume_path}, but I encountered an error responding.` 
        }])
      }
      
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Failed to upload file ${file.name}.` 
      }])
    } finally {
      setIsLoading(false)
      // Reset input
      e.target.value = ''
    }
  }

  const handleClearChat = async () => {
    try {
      await fetch('http://localhost:8000/clear_chat', {
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

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-sm">
      <header className="bg-white shadow-sm px-4 py-2 flex justify-between items-center">
        <div>
          <h1 className="text-base font-semibold text-gray-800">Supply Chain Agent</h1>
          <p className="text-[10px] text-gray-500">Databricks Agent Framework + FastMCP</p>
        </div>        
      </header>

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
                  <div className="agent-message-content leading-relaxed prose prose-sm max-w-none">
                    {msg.content ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      <div className="flex items-center space-x-1.5 h-6 px-1">
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    )}
                  </div>
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
