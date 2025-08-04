import React, { useState } from 'react';

export const ChatAssistant: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || loading) return;

    // 添加用户消息
    const userMessage = { role: 'user', content: inputValue };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setLoading(true);

    try {
      // 这里应该是调用后端 API 的逻辑
      // 模拟 API 调用
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: newMessages }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // 添加助手消息
      setMessages([...newMessages, { role: 'assistant', content: data.content }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages([...newMessages, { role: 'assistant', content: '抱歉，我遇到了一些问题。请稍后再试。' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '20px',
      maxWidth: '800px',
      margin: '0 auto'
    }}>
      <h1>大模型对话助手</h1>
      
      <div style={{
        width: '100%',
        maxHeight: '60vh',
        overflowY: 'auto',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '10px',
        marginBottom: '20px'
      }}>
        {messages.map((msg, index) => (
          <div 
            key={index}
            style={{
              textAlign: msg.role === 'user' ? 'right' : 'left',
              marginBottom: '10px'
            }}
          >
            <strong>{msg.role === 'user' ? '你' : '助手'}:</strong> {msg.content}
          </div>
        ))}
        {loading && <div>助手正在思考...</div>}
      </div>
      
      <form 
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          display: 'flex',
          gap: '10px'
        }}
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="请输入您的问题..."
          style={{
            flex: 1,
            padding: '10px',
            borderRadius: '4px',
            border: '1px solid #ccc'
          }}
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading}
          style={{
            padding: '10px 20px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: '#007bff',
            color: 'white',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '发送中...' : '发送'}
        </button>
      </form>
    </div>
  );
};

export default ChatAssistant;