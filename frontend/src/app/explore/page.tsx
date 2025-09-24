'use client';

import { useState, useEffect, useRef } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'error' | 'prompt';
  content: string;
  timestamp: Date;
}

interface Cluster {
  id: string;
  name: string;
  size: number;
}

enum ServerState {
  IDLE = 'idle',
  PROCESSING = 'processing',
  STREAMING = 'streaming',
  WAITING_INPUT = 'waiting_input'
}

const availableClusters: Cluster[] = [
  { id: '1', name: 'High-Volume Endocrinologists', size: 45 },
  { id: '2', name: 'Tier 1 Non-Prescribers', size: 23 },
  { id: '3', name: 'Urban Family Medicine', size: 67 },
  { id: '4', name: 'Recent Cardiology Adopters', size: 32 },
  { id: '5', name: 'High-Value Internal Medicine', size: 89 },
  { id: '6', name: 'West Coast Specialists', size: 156 }
];

export default function ExplorePage() {
  const [messages, setMessages] = useState<Message[]>([]);
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

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
      addMessage('system', '❌ Connection error. Please refresh the page.');
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setConnected(false);
      addMessage('system', '🔌 Disconnected from server');
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
          addMessage('system', '✅ Connected to Healthcare Data Agent');
        } else if (data.state === 'complete') {
          // Finalize any pending streaming message when complete
          console.log('✅ Complete status - current streaming msg:', streamingMessageRef.current);
          if (streamingMessageRef.current) {
            addMessage('assistant', streamingMessageRef.current);
            streamingMessageRef.current = '';
            setCurrentStreamingMessage('');
          }
          addMessage('system', '✅ Analysis complete');
        }
        break;

      case 'state':
        const newState = data.value as ServerState;
        console.log(`🔄 State change: ${serverState} -> ${newState}`);
        console.log('📝 Current streaming message ref:', streamingMessageRef.current.length);
        setServerState(newState);

        // Only finalize streaming message when moving to IDLE or WAITING_INPUT
        if (newState === ServerState.IDLE || newState === ServerState.WAITING_INPUT) {
          console.log('📌 Finalizing message on state:', newState, 'Message:', streamingMessageRef.current);
          if (streamingMessageRef.current) {
            addMessage('assistant', streamingMessageRef.current);
            streamingMessageRef.current = '';
            setCurrentStreamingMessage('');
          }
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
        if (cleanText) {
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
    }
  };

  const addMessage = (type: Message['type'], content: string) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date()
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

    // Add user message to display
    addMessage('user', inputMessage);

    // Include cluster context if any selected
    let messageToSend = inputMessage;
    if (selectedClusters.length > 0) {
      const clusterNames = selectedClusters.map(id => {
        const cluster = availableClusters.find(c => c.id === id);
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
        <Header />
        <main className="flex-1 flex flex-col overflow-hidden">
            {/* Connection Status Bar */}
            <div className="bg-white border-b border-gray-200 px-6 py-3">
              <div className="flex items-center justify-between max-w-4xl mx-auto">
                <div className="flex items-center space-x-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    <span className={`w-2 h-2 mr-1 rounded-full ${
                      connected ? 'bg-green-400' : 'bg-red-400'
                    }`} />
                    {connected ? 'Connected' : 'Disconnected'}
                  </span>
                  {sessionId && (
                    <span className="text-xs text-gray-500">Session: {sessionId.slice(0, 8)}</span>
                  )}
                </div>
                {connected && (
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      serverState === ServerState.IDLE ? 'bg-green-100 text-green-700' :
                      serverState === ServerState.PROCESSING ? 'bg-yellow-100 text-yellow-700' :
                      serverState === ServerState.STREAMING ? 'bg-blue-100 text-blue-700' :
                      'bg-purple-100 text-purple-700'
                    }`}>
                      {serverState === ServerState.PROCESSING ? '⚡ Processing...' :
                       serverState === ServerState.STREAMING ? '📝 Receiving...' :
                       serverState === ServerState.WAITING_INPUT ? '❓ Waiting for input...' :
                       '✅ Ready'}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto space-y-4">
                {messages.length === 0 && connected && (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Connected to Healthcare Data Agent. Start by asking a question or selecting clusters to analyze.</p>
                  </div>
                )}
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.type === 'user' ? 'justify-end' :
                      message.type === 'system' || message.type === 'error' ? 'justify-center' :
                      'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-3xl px-4 py-3 rounded-lg ${
                        message.type === 'user' ? 'bg-black text-white' :
                        message.type === 'assistant' ? 'bg-white border border-gray-200 text-gray-900' :
                        message.type === 'error' ? 'bg-red-50 border border-red-200 text-red-800' :
                        message.type === 'prompt' ? 'bg-amber-50 border border-amber-200 text-amber-900' :
                        message.type === 'system' ? 'bg-gray-100 text-gray-600 text-sm' :
                        'bg-white border border-gray-200 text-gray-900'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      {message.type !== 'system' && (
                        <p className={`text-xs mt-2 ${
                          message.type === 'user' ? 'text-gray-300' : 'text-gray-500'
                        }`}>
                          {message.timestamp.toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {/* Show processing bubbles */}
                {serverState === ServerState.PROCESSING && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 px-4 py-3 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Show streaming message in progress */}
                {serverState === ServerState.STREAMING && currentStreamingMessage && (
                  <div className="flex justify-start">
                    <div className="max-w-3xl px-4 py-3 rounded-lg bg-white border border-gray-200 text-gray-900">
                      <p className="text-sm whitespace-pre-wrap">{currentStreamingMessage}</p>
                      <p className="text-xs mt-2 text-gray-500">
                        {new Date().toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Enhanced Chat Input */}
            <div className="border-t border-gray-200 bg-white p-6">
              <div className="max-w-4xl mx-auto">

                {/* Quick Actions */}
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
                        const cluster = availableClusters.find(c => c.id === clusterId);
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
                          {availableClusters.map((cluster) => (
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
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(e);
                      }
                    }}
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
      </div>
    </div>
  );
}
