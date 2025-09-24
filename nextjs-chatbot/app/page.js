'use client';

import { useState, useEffect, useRef } from 'react';

const ServerState = {
  IDLE: 'idle',
  PROCESSING: 'processing',
  STREAMING: 'streaming',
  WAITING_INPUT: 'waiting_input'
};

export default function ChatBot() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [serverState, setServerState] = useState(ServerState.IDLE);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

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
      handleMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
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

  const handleMessage = (data) => {
    switch (data.type) {
      case 'status':
        if (data.state === 'connected') {
          setConnected(true);
          setSessionId(data.session_id);
        } else if (data.state === 'complete') {
          addMessage('system', '✅ Complete!');
        }
        break;

      case 'state':
        setServerState(data.value);
        break;

      case 'output':
        addMessage('assistant', data.text);
        break;

      case 'prompt':
        addMessage('prompt', data.text);
        break;

      case 'error':
        addMessage('error', `Error: ${data.text}`);
        break;

      case 'log':
        console.log('Debug:', data.text);
        break;
    }
  };

  const addMessage = (role, text) => {
    setMessages(prev => [...prev, { role, text, timestamp: Date.now() }]);
  };

  const sendMessage = () => {
    if (!inputValue.trim()) return;

    // Check if we can send
    const canSend = serverState === ServerState.IDLE ||
                    serverState === ServerState.WAITING_INPUT;

    if (!canSend) {
      addMessage('system', `Cannot send - server is ${serverState}`);
      return;
    }

    // Add user message to display
    addMessage('user', inputValue);

    // Send to server
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      text: inputValue
    }));

    // Clear input
    setInputValue('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getStateIndicator = () => {
    switch (serverState) {
      case ServerState.PROCESSING:
        return '⚡ Processing...';
      case ServerState.STREAMING:
        return '📝 Receiving...';
      case ServerState.WAITING_INPUT:
        return '❓ Waiting for input...';
      case ServerState.IDLE:
        return '✅ Ready';
      default:
        return '';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Healthcare Data Chatbot</h1>

      <div style={{ marginBottom: '10px' }}>
        Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}
        {sessionId && ` | Session: ${sessionId}`}
        {connected && ` | ${getStateIndicator()}`}
      </div>

      <div style={{
        border: '1px solid #ccc',
        height: '500px',
        overflowY: 'auto',
        padding: '10px',
        marginBottom: '10px',
        backgroundColor: '#f9f9f9'
      }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{
            marginBottom: '10px',
            padding: '8px',
            backgroundColor: msg.role === 'user' ? '#e3f2fd' :
                           msg.role === 'assistant' ? '#f5f5f5' :
                           msg.role === 'error' ? '#ffebee' :
                           msg.role === 'prompt' ? '#fff3e0' : '#ffffff',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            <strong>
              {msg.role === 'user' ? '👤 You: ' :
               msg.role === 'assistant' ? '🤖 Assistant: ' :
               msg.role === 'error' ? '❌ ' :
               msg.role === 'prompt' ? '❓ ' :
               msg.role === 'system' ? 'ℹ️ ' : ''}
            </strong>
            {msg.text}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={!connected || (serverState !== ServerState.IDLE && serverState !== ServerState.WAITING_INPUT)}
          placeholder={connected ? "Type your message..." : "Not connected..."}
          style={{
            flex: 1,
            padding: '10px',
            fontSize: '16px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
        <button
          onClick={sendMessage}
          disabled={!connected || (serverState !== ServerState.IDLE && serverState !== ServerState.WAITING_INPUT)}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: connected ? 'pointer' : 'not-allowed',
            opacity: connected ? 1 : 0.5
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}