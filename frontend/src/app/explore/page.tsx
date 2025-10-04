'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'error' | 'prompt' | 'reasoning' | 'data_table' | 'action_status';
  content: string;
  timestamp: Date;
  data?: any[]; // For data table messages
  filename?: string; // For data table messages
  action?: string; // For action status messages
  workflowId?: number;
}

interface Cluster {
  id: string;
  name: string;
  size: number;
  description?: string;
  filename?: string;
  data?: any[];
}


enum ServerState {
  IDLE = 'idle',
  PROCESSING = 'processing',
  STREAMING = 'streaming',
  WAITING_INPUT = 'waiting_input'
}

const availableClusters: Cluster[] = [
  { id: '1', name: 'High-Volume Rheumatologists', size: 342, description: 'Rheumatologists treating 200+ autoimmune patients with recent JAK inhibitor prescriptions' },
  { id: '2', name: 'Academic Immunology Centers', size: 87, description: 'Immunologists at major academic medical centers specializing in complex autoimmune disorders' }
];

export default function ExplorePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [visibleMessages, setVisibleMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedClusters, setSelectedClusters] = useState<string[]>([]);
  const [isClusterDropdownOpen, setIsClusterDropdownOpen] = useState(false);
  const [serverState, setServerState] = useState<ServerState>(ServerState.IDLE);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');

  const dropdownRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMessageRef = useRef<string>('');
  const lastNonOutputTextRef = useRef<string>('');
  const recentNonOutputTextsRef = useRef<string[]>([]);
  const workflowIdRef = useRef<number>(0);
  const [thinkingOpen, setThinkingOpen] = useState<boolean>(true);
  const [thinkingActive, setThinkingActive] = useState<boolean>(false);
  const lastReasoningRef = useRef<string>('');
  const lastActionRef = useRef<string>('');
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const messageRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const [currentActiveActionId, setCurrentActiveActionId] = useState<string | null>(null);
  const [hasEverSentQuery, setHasEverSentQuery] = useState<boolean>(false);
  const [isSessionComplete, setIsSessionComplete] = useState<boolean>(true);
  const [savedClusters, setSavedClusters] = useState<Cluster[]>([]);
  const [showClusterPopup, setShowClusterPopup] = useState<boolean>(false);
  const [clusterToSave, setClusterToSave] = useState<{data: any[], filename: string} | null>(null);
  const [clusterName, setClusterName] = useState<string>('');
  const [clusterDescription, setClusterDescription] = useState<string>('');

  // Load saved clusters from sessionStorage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem('savedClusters');
    if (saved) {
      try {
        setSavedClusters(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load saved clusters:', e);
      }
    }
  }, []);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  const scrollToBottom = useCallback((smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: smooth ? 'smooth' : 'auto',
        block: 'end'
      });
    }
  }, []);

  // Scroll to bottom when messages change or streaming content updates
  useEffect(() => {
    // Use requestAnimationFrame to ensure DOM is updated before scrolling
    requestAnimationFrame(() => {
      scrollToBottom();
    });
  }, [messages, currentStreamingMessage, scrollToBottom]);

  // Force scroll when visible messages change
  useEffect(() => {
    if (visibleMessages.length > 0) {
      requestAnimationFrame(() => {
        scrollToBottom(true);
      });
    }
  }, [visibleMessages, scrollToBottom]);

  // Initialize Intersection Observer for lazy loading
  useEffect(() => {
    if (!observerRef.current) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const messageId = entry.target.getAttribute('data-message-id');
              if (messageId) {
                setVisibleMessages((prev) => {
                  const message = messages.find((m) => m.id === messageId);
                  if (message && !prev.some((m) => m.id === messageId)) {
                    return [...prev, message].sort((a, b) =>
                      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                    );
                  }
                  return prev;
                });
              }
            }
          });
        },
        {
          root: chatContainerRef.current,
          rootMargin: '100px',
          threshold: 0.01
        }
      );
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [messages]);

  // Update visible messages when messages change
  useEffect(() => {
    // Start with showing recent messages (last 20) to ensure user messages are always visible
    const recentMessages = messages.slice(-20);
    setVisibleMessages(recentMessages);

    // Observe all message placeholders
    messages.forEach((message) => {
      const element = messageRefsMap.current.get(message.id);
      if (element && observerRef.current) {
        observerRef.current.observe(element);
      }
    });

    return () => {
      // Clean up observers
      messageRefsMap.current.forEach((element) => {
        if (observerRef.current) {
          observerRef.current.unobserve(element);
        }
      });
    };
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to WebSocket server');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleWebSocketMessage = (data: any) => {
    console.log('📨 WS Message:', data.type, data);

    switch (data.type) {
      case 'status':
        console.log('📊 Status message:', data.state);
        if (data.state === 'connected') {
          setConnected(true);
          setSessionId(data.session_id);
        } else if (data.state === 'complete') {
          console.log('✅ Complete status received');
        }
        break;

      case 'state':
        const newState = data.value as ServerState;
        console.log(`🔄 State change: ${serverState} -> ${newState}`);
        console.log('📝 Current streaming message ref:', streamingMessageRef.current.length);
        setServerState(newState);

        if (newState === ServerState.PROCESSING) {
          workflowIdRef.current += 1;
          setThinkingActive(true);
          setThinkingOpen(true);
          streamingMessageRef.current = '';
          setCurrentStreamingMessage('');
          console.log('🔄 Session started - hiding intermediate tables');
          setIsSessionComplete(false);
        }

        // Only finalize streaming message when moving to IDLE or WAITING_INPUT
        if (newState === ServerState.IDLE || newState === ServerState.WAITING_INPUT) {
          console.log('📌 Finalizing message on state:', newState, 'Message:', streamingMessageRef.current);
          if (streamingMessageRef.current) {
            addMessage('assistant', streamingMessageRef.current);
            streamingMessageRef.current = '';
            setCurrentStreamingMessage('');
          }
          // Clear active action when session is complete
          setCurrentActiveActionId(null);
          console.log('✅ Session complete - showing final tables');
          setIsSessionComplete(true);
        }
        break;

      case 'output':
        console.log('💬 Output received:', data.text);
        // Remove "You: " or "Assistant: " prefixes from the text
        let cleanText: string = data.text;
        cleanText = cleanText.trim();
        const assistantPrefix = '💬';
        const youPrefix = '👤';
        if (cleanText.startsWith(youPrefix)) {
          console.log('👤 Ignoring user echo');
          cleanText = cleanText.substring("👤 You: ".length);
          // Ignore user echoes from server
        } else if (cleanText.startsWith(assistantPrefix)) {
          console.log('🤖 Cleaning assistant prefix');
          cleanText = cleanText.substring("💬 Assistant: ".length);
        }

        // Always accumulate during non-idle states
        if (cleanText && cleanText.trim() !== '') {
          console.log('📝 Accumulating text:', cleanText);
          console.log('📊 Current server state:', serverState);

          streamingMessageRef.current += (streamingMessageRef.current ? '\n' : '') + cleanText;
          setCurrentStreamingMessage(streamingMessageRef.current);
          console.log('📄 New streaming message ref length:', streamingMessageRef.current.length);
        }
        break;

      case 'prompt':
        //addMessage('prompt', data.text);
        break;

      case 'error':
        addMessage('error', `Error: ${data.text}`);
        break;

      case 'log':
        console.log('Debug:', data.text);
        break;

      case 'reasoning':
        console.log('🧠 Reasoning trace received:', data.text);
        if (data.text !== lastReasoningRef.current) {
          addMessage('reasoning', data.text);
          lastReasoningRef.current = data.text;
          // Clear active action when reasoning comes in (action is complete)
          setCurrentActiveActionId(null);
        }
        break;

      case 'data_table':
        console.log('📊 Data table received:', data.filename, data.data?.length, 'rows');
        addMessage('data_table', '', data.data, data.filename);
        break;

      case 'action_status':
        console.log('⚡ Action status received:', data.action, data.description);
        const actionKey = `${data.action}:${data.description}`;
        if (actionKey !== lastActionRef.current) {
          // Generate unique ID for this specific action message
          const newMessageId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          
          // Add message with custom ID
          setMessages(prev => [...prev, {
            id: newMessageId,
            type: 'action_status',
            content: data.description,
            timestamp: new Date(),
            action: data.action,
            workflowId: workflowIdRef.current
          }]);
          
          lastActionRef.current = actionKey;
          // Set this specific message ID as the currently active one
          setCurrentActiveActionId(newMessageId);
        }
        break;
    }
  };

  const addMessage = (type: Message['type'], content: string, data?: any[], filename?: string, action?: string) => {
    setMessages(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      content,
      timestamp: new Date(),
      data,
      filename,
      action,
      workflowId: workflowIdRef.current
    }]);
  };


  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    // Check if we can send
    const canSend = serverState === ServerState.IDLE ||
                    serverState === ServerState.WAITING_INPUT;

    if (!canSend) {
      addMessage('system', `⚠️ Cannot send - server is ${serverState}`);
      return;
    }

    // Mark that a query has been sent (for hiding Quick Actions)
    setHasEverSentQuery(true);

    // Add user message to display
    addMessage('user', inputMessage);

    // Include cluster context if any selected
    let messageToSend = inputMessage;
    if (selectedClusters.length > 0) {
      const allClusters = [...availableClusters, ...savedClusters];
      const clusterNames = selectedClusters.map(id => {
        const cluster = allClusters.find(c => c.id === id);
        return cluster?.name;
      }).filter(Boolean).join(', ');

      messageToSend = `${inputMessage} [Context: Analyzing clusters: ${clusterNames}]`;
    }

    // Send to server
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      text: messageToSend
    }));

    setInputMessage('');
  };

  const toggleClusterSelection = (clusterId: string) => {
    setSelectedClusters(prev => 
      prev.includes(clusterId) 
        ? prev.filter(id => id !== clusterId)
        : [...prev, clusterId]
    );
  };

  const handleQuickAction = (action: string) => {
    if (!connected || (serverState !== ServerState.IDLE && serverState !== ServerState.WAITING_INPUT)) {
      addMessage('system', '⚠️ Cannot send - server is not ready');
      return;
    }
    setHasEverSentQuery(true);
    setInputMessage(action);
  };

  const handleClusterSuggestion = (clusterId: string) => {
    if (!selectedClusters.includes(clusterId)) {
      setSelectedClusters(prev => [...prev, clusterId]);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsClusterDropdownOpen(false);
      }
    };

    if (isClusterDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isClusterDropdownOpen]);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header connected={connected} />
        <main className="flex-1 flex flex-col overflow-hidden">
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6" ref={chatContainerRef}>
              <div className="max-w-4xl mx-auto space-y-4">
                
                {/* Show all messages in chronological order, but insert Thinking header strategically */}
                {(() => {
                  const result = [];
                  let thinkingInserted = false;
                  
                  // Find the last user message index
                  let lastUserMessageIndex = -1;
                  for (let i = messages.length - 1; i >= 0; i--) {
                    if (messages[i].type === 'user') {
                      lastUserMessageIndex = i;
                      break;
                    }
                  }

                  messages.forEach((message, index) => {
                    const isVisible = visibleMessages.some((m) => m.id === message.id);
                    
                    // Skip reasoning and action_status messages for now - we'll handle them later
                    if (message.type === 'reasoning' || message.type === 'action_status') {
                      return;
                    }

                    // Skip data tables if session is not complete (hide intermediate tables)
                    if (message.type === 'data_table' && !isSessionComplete) {
                      console.log('🚫 Hiding intermediate table:', message.filename);
                      return;
                    }

                    // Render regular message  
                    // Always show user messages, use intersection observer for others
                    if (!isVisible && message.type !== 'user') {
                      result.push(
                        <div
                          key={message.id}
                          data-message-id={message.id}
                          ref={(el) => {
                            if (el) messageRefsMap.current.set(message.id, el);
                          }}
                          className="h-20 flex items-center justify-center opacity-0 animate-fadeIn"
                          style={{
                            animationDelay: `${index * 50}ms`,
                            animationFillMode: 'forwards'
                          }}
                        >
                          <div className="animate-pulse bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 rounded-lg h-12 w-3/4 shadow-sm"></div>
                        </div>
                      );
                    } else {
                      result.push(
                        <div
                          key={message.id}
                          className={`flex ${
                            message.type === 'user' ? 'justify-end' :
                            message.type === 'system' || message.type === 'error' ? 'justify-center' :
                            'justify-start'
                          } opacity-0 animate-slideInUp`}
                          style={{
                            animationDelay: `${Math.min(index * 30, 300)}ms`,
                            animationFillMode: 'forwards'
                          }}
                        >
                          <div className={(() => {
                            switch (message.type) {
                              case 'user':
                                return 'max-w-3xl px-4 py-3 rounded-lg bg-black text-white';
                              case 'assistant':
                                return 'max-w-3xl px-4 py-3 text-gray-700';
                              case 'error':
                                return 'max-w-3xl px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-800';
                              case 'prompt':
                                return 'max-w-3xl px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900';
                              case 'data_table':
                                return 'max-w-3xl rounded-lg bg-gray-50 border border-gray-200 p-0';
                              case 'system':
                                return 'max-w-3xl px-4 py-3 rounded-lg bg-gray-100 text-gray-600 text-sm';
                              default:
                                return 'max-w-3xl px-4 py-3 rounded-lg bg-white border border-gray-200 text-gray-900';
                            }
                          })()}>
                            {message.type === 'data_table' && message.data ? (
                              <div className="w-full">
                                <div className="mb-3 px-4 py-2 bg-gray-100 border-b border-gray-200 flex items-center justify-between">
                                  <div>
                                    <span className="text-xs font-medium text-gray-600">📊 {message.filename?.replace('.csv', '')}</span>
                                    <span className="ml-2 text-xs text-gray-500">{message.data.length} rows</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => {
                                        setClusterToSave({data: message.data, filename: message.filename || 'cluster'});
                                        setShowClusterPopup(true);
                                      }}
                                      className="flex items-center justify-center w-6 h-6 bg-blue-500 text-white rounded text-xs font-bold hover:bg-blue-600 transition-colors"
                                      title="Save to Clusters"
                                    >
                                      +
                                    </button>
                                    <button
                                      onClick={() => {
                                        if (sessionId && message.filename) {
                                          const url = `http://localhost:8766/download/${sessionId}/${message.filename}`;
                                          const link = document.createElement('a');
                                          link.href = url;
                                          link.download = message.filename;
                                          document.body.appendChild(link);
                                          link.click();
                                          document.body.removeChild(link);
                                        }
                                      }}
                                      className="flex items-center justify-center w-6 h-6 bg-green-500 text-white rounded text-xs font-bold hover:bg-green-600 transition-colors"
                                      title="Download CSV"
                                    >
                                      ↓
                                    </button>
                                  </div>
                                </div>
                                <div className="overflow-x-auto">
                                  <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                      <tr>
                                        {Object.keys(message.data[0] || {}).map((header, idx) => (
                                          <th
                                            key={idx}
                                            className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                          >
                                            {header}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                      {message.data.slice(0, 20).map((row, rowIdx) => (
                                        <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                          {Object.keys(row).map((header, colIdx) => (
                                            <td
                                              key={colIdx}
                                              className="px-3 py-2 text-sm text-gray-900 whitespace-nowrap"
                                            >
                                              {row[header]}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                  {message.data.length > 20 && (
                                    <div className="px-3 py-2 bg-gray-50 text-xs text-gray-500 border-t border-gray-200">
                                      Showing first 20 of {message.data.length} rows
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                            )}
                          </div>
                        </div>
                      );
                    }

                    // Insert Thinking header right after the last user message (if thinking is active)
                    if (index === lastUserMessageIndex && thinkingActive && !thinkingInserted) {
                      const thinkingMessages = messages.filter(m => m.type === 'reasoning' || m.type === 'action_status');
                      
                      if (thinkingMessages.length > 0) {
                        // Insert Thinking header
                        result.push(
                          <div key="thinking-header" className="flex justify-start">
                            <button
                              type="button"
                              onClick={() => setThinkingOpen(!thinkingOpen)}
                              className="text-sm text-gray-700 flex items-center space-x-2 hover:text-gray-900 transition-colors"
                            >
                              <span>Thinking…</span>
                              <svg className={`h-4 w-4 transform transition-transform ${thinkingOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z" clipRule="evenodd" />
                              </svg>
                            </button>
                          </div>
                        );

                        // Insert thinking messages in chronological order (if expanded)
                        if (thinkingOpen) {
                          thinkingMessages.forEach((thinkingMessage, thinkingIndex) => {
                            result.push(
                              <div
                                key={thinkingMessage.id}
                                className="flex justify-start opacity-0 animate-slideInUp"
                                style={{
                                  animationDelay: `${Math.min(thinkingIndex * 20, 200)}ms`,
                                  animationFillMode: 'forwards'
                                }}
                              >
                                <div>
                                  {thinkingMessage.type === 'action_status' && (
                                    <span className={`inline-block text-[11px] px-2 py-0.5 rounded-full border text-gray-700 transition-all duration-500 ${
                                      currentActiveActionId === thinkingMessage.id 
                                        ? 'border-blue-400 bg-blue-50 shadow-blue-200 shadow-md animate-pulse ring-2 ring-blue-200' 
                                        : 'border-gray-300 bg-gray-50'
                                    }`}>
                                      {thinkingMessage.content}
                                    </span>
                                  )}

                                  {thinkingMessage.type === 'reasoning' && (
                                    <p className="text-sm text-gray-900 whitespace-pre-wrap">{thinkingMessage.content}</p>
                                  )}
                                </div>
                              </div>
                            );
                          });
                        }
                        
                        thinkingInserted = true;
                      }
                    }
                  });

                  // Show thinking messages inline when thinking is not active
                  if (!thinkingActive) {
                    messages
                      .filter(m => m.type === 'reasoning' || m.type === 'action_status')
                      .forEach((message, index) => {
                        result.push(
                          <div
                            key={message.id}
                            className="flex justify-start opacity-0 animate-slideInUp"
                            style={{
                              animationDelay: `${Math.min(index * 20, 200)}ms`,
                              animationFillMode: 'forwards'
                            }}
                          >
                            <div>
                              {message.type === 'action_status' && (
                                <span className={`inline-block text-[11px] px-2 py-0.5 rounded-full border text-gray-700 transition-all duration-500 ${
                                  currentActiveActionId === message.id 
                                    ? 'border-blue-400 bg-blue-50 shadow-blue-200 shadow-md animate-pulse ring-2 ring-blue-200' 
                                    : 'border-gray-300 bg-gray-50'
                                }`}>
                                  {message.content}
                                </span>
                              )}

                              {message.type === 'reasoning' && (
                                <p className="text-sm text-gray-900 whitespace-pre-wrap">{message.content}</p>
                              )}
                            </div>
                          </div>
                        );
                      });
                  }

                  return result;
                })()}


                {/* Show streaming message in progress with fade-in */}
                {serverState === ServerState.STREAMING && currentStreamingMessage && (
                  <div className="flex justify-start opacity-0 animate-fadeIn" style={{ animationDelay: '50ms', animationFillMode: 'forwards' }}>
                    <div className="max-w-3xl px-4 py-3 rounded-lg bg-white border border-gray-200 text-gray-900 shadow-sm transition-all duration-200">
                      <p className="text-sm whitespace-pre-wrap">{currentStreamingMessage}</p>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>



            {/* Enhanced Chat Input */}
            <div className="border-t border-gray-200 bg-white p-6">
              <div className="max-w-4xl mx-auto">

                {/* Quick Actions - only show at the very beginning before any queries */}
                {!hasEverSentQuery && (serverState === ServerState.IDLE || serverState === ServerState.WAITING_INPUT) && (
                  <div className="mb-4">
                    <span className="text-sm font-medium text-gray-700 mb-2 block">Quick Actions</span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleQuickAction('Find HCPs that are in all of my selected clusters')}
                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                      >
                        Find the intersection of my selected clusters 
                      </button>
                      <button
                        onClick={() => handleQuickAction('Rank the top 20 high decile HCPs by payments from competitors')}
                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                      >
                        Rank the top 20 high decile HCPs by payments from competitors
                      </button>
                      <button
                        onClick={() => handleQuickAction('Create a new cluster of doctors in CA who have not prescribed an Abbvie drug in the last 3 months')}
                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                      >
                        Create a cluster of doctors in CA who have not prescribed an Abbvie drug in the last 3 months
                      </button>
                      <button
                        onClick={() => handleQuickAction('Rank HCPs in these clusters by number of publications')}
                        className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                      >
                        Rank HCPs in these clusters by number of publications
                      </button>
                    </div>
                  </div>
                )}

                {/* Selected Clusters */}
                {selectedClusters.length > 0 && (
                  <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-900">Selected for Analysis</span>
                      <button
                        onClick={() => setSelectedClusters([])}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        Clear all
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedClusters.map(clusterId => {
                        const allClusters = [...availableClusters, ...savedClusters];
                        const cluster = allClusters.find(c => c.id === clusterId);
                        return cluster ? (
                          <span
                            key={clusterId}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 border border-blue-300"
                          >
                            {cluster.name}
                            <button
                              onClick={() => toggleClusterSelection(clusterId)}
                              className="ml-1 hover:text-blue-600"
                            >
                              ×
                            </button>
                          </span>
                        ) : null;
                      })}
                    </div>
                  </div>
                )}
                
                {/* Chat Input */}
                <form onSubmit={handleSendMessage} className="flex space-x-4">
                  {/* Cluster Dropdown */}
                  <div className="relative" ref={dropdownRef}>
                    <button
                      type="button"
                      onClick={() => setIsClusterDropdownOpen(!isClusterDropdownOpen)}
                      className="flex items-center justify-center px-4 py-3 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                    >
                      <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      {selectedClusters.length === 0 ? 'Clusters' : selectedClusters.length.toString()}
                      <svg
                        className={`h-4 w-4 ml-1 transition-transform ${isClusterDropdownOpen ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                      </svg>
                    </button>
                    
                    {isClusterDropdownOpen && (
                      <div className="absolute bottom-full left-0 w-80 mb-2 bg-white border border-gray-300 rounded-lg shadow-lg z-10">
                        <div className="p-3 border-b border-gray-200">
                          <span className="text-sm font-medium text-gray-900">Select Clusters</span>
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                          {[...availableClusters, ...savedClusters].map((cluster) => (
                            <button
                              key={cluster.id}
                              type="button"
                              onClick={() => {
                                handleClusterSuggestion(cluster.id);
                              }}
                              className={`w-full px-4 py-3 text-left text-sm hover:bg-gray-50 flex items-center justify-between border-b border-gray-100 last:border-b-0 ${
                                selectedClusters.includes(cluster.id) ? 'bg-blue-50 text-blue-800' : 'text-gray-700'
                              }`}
                            >
                              <div className="flex-1">
                                <div className="font-medium">{cluster.name}</div>
                                <div className="text-xs text-gray-500 mt-1">{cluster.size} HCPs</div>
                              </div>
                              {selectedClusters.includes(cluster.id) && (
                                <svg className="h-4 w-4 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </button>
                          ))}
                        </div>
                        {selectedClusters.length > 0 && (
                          <div className="p-3 border-t border-gray-200 bg-gray-50">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedClusters([]);
                                setIsClusterDropdownOpen(false);
                              }}
                              className="text-xs text-gray-600 hover:text-gray-800"
                            >
                              Clear all ({selectedClusters.length})
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder={connected ? "Ask me anything about healthcare data..." : "Not connected..."}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    disabled={!connected || (serverState !== ServerState.IDLE && serverState !== ServerState.WAITING_INPUT)}
                  />
                  <button
                    type="submit"
                    disabled={!connected || !inputMessage.trim() || (serverState !== ServerState.IDLE && serverState !== ServerState.WAITING_INPUT)}
                    className="px-6 py-3 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {!connected ? 'Offline' : 'Send'}
                  </button>
                </form>
              </div>
            </div>
        </main>

        {/* Cluster Save Popup */}
        {showClusterPopup && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-96 max-w-90vw">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Save to Clusters</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cluster Name
                  </label>
                  <input
                    type="text"
                    value={clusterName}
                    onChange={(e) => setClusterName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter cluster name..."
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={clusterDescription}
                    onChange={(e) => setClusterDescription(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                    placeholder="Enter cluster description..."
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => {
                    setShowClusterPopup(false);
                    setClusterName('');
                    setClusterDescription('');
                    setClusterToSave(null);
                  }}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (clusterName.trim() && clusterToSave) {
                      const newCluster: Cluster = {
                        id: `saved-${Date.now()}`,
                        name: clusterName.trim(),
                        size: clusterToSave.data.length,
                        description: clusterDescription.trim() || undefined,
                        filename: clusterToSave.filename,
                        data: clusterToSave.data
                      };
                      
                      setSavedClusters(prev => {
                        const updated = [...prev, newCluster];
                        // Store in sessionStorage for cross-tab communication
                        sessionStorage.setItem('savedClusters', JSON.stringify(updated));
                        return updated;
                      });
                      
                      setShowClusterPopup(false);
                      setClusterName('');
                      setClusterDescription('');
                      setClusterToSave(null);
                    }
                  }}
                  disabled={!clusterName.trim()}
                  className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Save Cluster
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
