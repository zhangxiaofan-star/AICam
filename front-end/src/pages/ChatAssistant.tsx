import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { SendHorizonal, Home, RotateCcw, History, Download, Settings, X, Search, FileText, Trash2, Star, StarOff, BarChart3 } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { ConversationStats } from '../components/ConversationStats';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

interface Message {
  id: number;
  text: string;
  isUser: boolean;
  timestamp: string;
}

interface ConversationHistory {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  isFavorite: boolean;
}

export const ChatAssistant: React.FC = () => {
  const [message, setMessage] = useState('');
  const [conversation, setConversation] = useState<Message[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationHistory[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [settings, setSettings] = useState({
    autoSave: true,
    maxHistoryItems: 50,
    theme: 'light' as 'light' | 'dark',
    fontSize: 'medium' as 'small' | 'medium' | 'large'
  });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // 头像URL
  const assistantAvatar = "https://s3plus.sankuai.com/nocode-external/nocode_image/default/image-kdwoi8qdx21d3kzn1zgkxhci23rzn0.png";
  const userAvatar = "https://s3plus.sankuai.com/nocode-external/nocode_image/default/image-b7i9z7yszcj15las7ndnozt9iwjl7j.png";

  // Moonshot API配置
  const API_KEY = "sk-WeilCDHWP9Qdj9PBBgjOFv3PZESfVc8FTGDIGz0T2IxgN3I7";
  const BASE_URL = "https://api.moonshot.cn/v1";
  const MODEL = "moonshot-v1-8k";

  // 从localStorage加载历史对话
  useEffect(() => {
    const savedHistory = localStorage.getItem('conversationHistory');
    const savedSettings = localStorage.getItem('chatSettings');
    
    if (savedHistory) {
      setConversationHistory(JSON.parse(savedHistory));
    }
    
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  // 保存历史对话到localStorage
  useEffect(() => {
    localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory));
  }, [conversationHistory]);

  // 保存设置到localStorage
  useEffect(() => {
    localStorage.setItem('chatSettings', JSON.stringify(settings));
  }, [settings]);

  // 自动保存对话
  useEffect(() => {
    if (settings.autoSave && conversation.length > 0 && !currentConversationId) {
      const conversationId = Date.now().toString();
      const title = conversation[0]?.text.slice(0, 30) + (conversation[0]?.text.length > 30 ? '...' : '');
      
      const newHistoryItem: ConversationHistory = {
        id: conversationId,
        title,
        messages: [...conversation],
        createdAt: new Date().toISOString(),
        isFavorite: false
      };
      
      setConversationHistory(prev => {
        const updated = [newHistoryItem, ...prev.slice(0, settings.maxHistoryItems - 1)];
        return updated;
      });
      
      setCurrentConversationId(conversationId);
    }
  }, [conversation, settings.autoSave, currentConversationId, settings.maxHistoryItems]);

  // 使用Moonshot API发送消息
  const sendMessageMutation = useMutation({
    mutationFn: async (userMessage: string) => {
      try {
        // 构建完整的消息历史
        const messagesHistory = [
          ...conversation.filter(msg => !msg.isUser).map(msg => ({
            role: "assistant",
            content: msg.text
          })),
          ...conversation.filter(msg => msg.isUser).map(msg => ({
            role: "user",
            content: msg.text
          })),
          { role: "user", content: userMessage }
        ];

        const response = await axios.post(
          `${BASE_URL}/chat/completions`,
          {
            model: MODEL,
            messages: messagesHistory,
            temperature: 0.3,
            max_tokens: 2048
          },
          {
            headers: {
              'Authorization': `Bearer ${API_KEY}`,
              'Content-Type': 'application/json'
            }
          }
        );

        return {
          id: Date.now(),
          text: response.data.choices[0].message.content,
          isUser: false,
          timestamp: new Date().toLocaleTimeString()
        };
      } catch (error) {
        toast.error('API请求失败');
        console.error('API请求错误:', error);
        return {
          id: Date.now(),
          text: '抱歉，请求失败，请稍后再试',
          isUser: false,
          timestamp: new Date().toLocaleTimeString()
        };
      }
    },
    onSuccess: (aiResponse) => {
      setConversation(prev => [...prev, aiResponse]);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: message,
      isUser: true,
      timestamp: new Date().toLocaleTimeString()
    };

    setConversation(prev => [...prev, userMessage]);
    sendMessageMutation.mutate(message);
    setMessage('');
  };

  // 处理推荐问题点击
  const handleRecommendedQuestion = (question: string) => {
    setMessage(question);
  };

  // 重置对话
  const resetConversation = () => {
    setConversation([]);
    setCurrentConversationId(null);
    toast.success('对话已重置');
  };

  // 回到首页
  const goToHome = () => {
    navigate('/');
    resetConversation();
  };

  // 加载历史对话
  const loadConversation = (historyItem: ConversationHistory) => {
    setConversation(historyItem.messages);
    setCurrentConversationId(historyItem.id);
    setShowHistory(false);
    toast.success('对话已加载');
  };

  // 删除历史对话
  const deleteConversation = (id: string) => {
    setConversationHistory(prev => prev.filter(item => item.id !== id));
    if (currentConversationId === id) {
      resetConversation();
    }
    toast.success('对话已删除');
  };

  // 切换收藏状态
  const toggleFavorite = (id: string) => {
    setConversationHistory(prev => 
      prev.map(item => 
        item.id === id ? { ...item, isFavorite: !item.isFavorite } : item
      )
    );
  };

  // 导出对话
  const exportConversation = (historyItem?: ConversationHistory) => {
    const dataToExport = historyItem || {
      id: currentConversationId || 'current',
      title: '当前对话',
      messages: conversation,
      createdAt: new Date().toISOString(),
      isFavorite: false
    };

    const exportData = {
      title: dataToExport.title,
      createdAt: dataToExport.createdAt,
      messages: dataToExport.messages
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${dataToExport.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('对话已导出');
  };

  // 导出所有对话
  const exportAllConversations = () => {
    const exportData = {
      exportedAt: new Date().toISOString(),
      conversations: conversationHistory
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `all-conversations-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('所有对话已导出');
  };

  // 清空所有历史
  const clearAllHistory = () => {
    if (window.confirm('确定要清空所有历史对话吗？此操作不可恢复。')) {
      setConversationHistory([]);
      resetConversation();
      toast.success('所有历史对话已清空');
    }
  };

  // 过滤历史对话
  const filteredHistory = conversationHistory.filter(item =>
    item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.messages.some(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // 计算统计数据
  const stats = {
    totalConversations: conversationHistory.length,
    totalMessages: conversationHistory.reduce((sum, conv) => sum + conv.messages.length, 0),
    favoriteConversations: conversationHistory.filter(conv => conv.isFavorite).length,
    lastActivity: conversationHistory.length > 0 ? conversationHistory[0].createdAt : null
  };

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        if (message.trim() && !sendMessageMutation.isPending) {
          handleSubmit(e as any);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [message, sendMessageMutation.isPending]);

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      {/* 顶部操作栏 */}
      <div className="flex justify-between items-center mb-4 pb-2 border-b">
        <h1 className="text-xl font-bold">对话助手</h1>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowHistory(!showHistory)}
            title="历史对话"
          >
            <History className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowStats(!showStats)}
            title="统计信息"
          >
            <BarChart3 className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
            title="设置"
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={resetConversation}
            title="重置对话"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={goToHome}
            title="回到首页"
          >
            <Home className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-1 gap-4">
        {/* 历史对话侧边栏 */}
        {showHistory && (
          <div className="w-80 border-r p-4 space-y-4 fade-in">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">历史对话</h2>
              <Button variant="outline" size="sm" onClick={() => setShowHistory(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="space-y-2">
              <Input
                placeholder="搜索对话..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mb-2"
              />
              
              <div className="flex gap-2 mb-2">
                <Button variant="outline" size="sm" onClick={exportAllConversations}>
                  <Download className="h-4 w-4" />
                  导出全部
                </Button>
                <Button variant="outline" size="sm" onClick={clearAllHistory}>
                  <Trash2 className="h-4 w-4" />
                  清空
                </Button>
              </div>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredHistory.length === 0 ? (
                <p className="text-gray-500 text-center py-4">暂无历史对话</p>
              ) : (
                filteredHistory.map((item) => (
                  <div 
                    key={item.id} 
                    className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                      currentConversationId === item.id ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-medium text-sm truncate flex-1">{item.title}</h3>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFavorite(item.id);
                          }}
                        >
                          {item.isFavorite ? (
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          ) : (
                            <StarOff className="h-3 w-3" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            exportConversation(item);
                          }}
                        >
                          <Download className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteConversation(item.id);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mb-2">
                      {new Date(item.createdAt).toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-600 line-clamp-2">
                      {item.messages[0]?.text || '空对话'}
                    </p>
                    <div className="mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => loadConversation(item)}
                      >
                        加载对话
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* 统计信息侧边栏 */}
        {showStats && (
          <div className="w-80 border-r p-4 space-y-4 fade-in">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">统计信息</h2>
              <Button variant="outline" size="sm" onClick={() => setShowStats(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <ConversationStats {...stats} />
            
            <div className="space-y-4">
              <h3 className="font-medium">最近对话</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {conversationHistory.slice(0, 5).map((item) => (
                  <div key={item.id} className="p-2 border rounded text-sm">
                    <p className="font-medium truncate">{item.title}</p>
                    <p className="text-gray-500 text-xs">
                      {new Date(item.createdAt).toLocaleDateString()} - {item.messages.length} 条消息
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 设置侧边栏 */}
        {showSettings && (
          <div className="w-80 border-r p-4 space-y-4 fade-in">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">设置</h2>
              <Button variant="outline" size="sm" onClick={() => setShowSettings(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">自动保存对话</label>
                <input
                  type="checkbox"
                  checked={settings.autoSave}
                  onChange={(e) => setSettings(prev => ({ ...prev, autoSave: e.target.checked }))}
                  className="mr-2"
                />
                <span className="text-sm text-gray-600">启用自动保存</span>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">最大历史记录数</label>
                <select
                  value={settings.maxHistoryItems}
                  onChange={(e) => setSettings(prev => ({ ...prev, maxHistoryItems: parseInt(e.target.value) }))}
                  className="w-full p-2 border rounded"
                >
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">主题</label>
                <select
                  value={settings.theme}
                  onChange={(e) => setSettings(prev => ({ ...prev, theme: e.target.value as 'light' | 'dark' }))}
                  className="w-full p-2 border rounded"
                >
                  <option value="light">浅色</option>
                  <option value="dark">深色</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">字体大小</label>
                <select
                  value={settings.fontSize}
                  onChange={(e) => setSettings(prev => ({ ...prev, fontSize: e.target.value as 'small' | 'medium' | 'large' }))}
                  className="w-full p-2 border rounded"
                >
                  <option value="small">小</option>
                  <option value="medium">中</option>
                  <option value="large">大</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* 主聊天区域 */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {conversation.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <h1 className="text-2xl font-bold mb-2">咯咯咯</h1>
                <p>输入您的问题开始与专属助手对话</p>
                {conversationHistory.length > 0 && (
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => setShowHistory(true)}
                  >
                    <History className="h-4 w-4 mr-2" />
                    查看历史对话
                  </Button>
                )}
              </div>
            ) : (
              conversation.map((msg) => (
                <div 
                  key={msg.id} 
                  className={`flex items-start gap-3 message-bubble ${msg.isUser ? 'flex-row-reverse' : ''}`}
                >
                  <img 
                    src={msg.isUser ? userAvatar : assistantAvatar} 
                    alt={msg.isUser ? "用户头像" : "助手头像"}
                    className="w-10 h-10 rounded-full object-cover" 
                  />
                  <div 
                    className={`max-w-xs md:max-w-md px-4 py-2 rounded-lg ${
                      msg.isUser 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-gray-100 dark:bg-gray-800'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                    <p className="text-xs opacity-70 mt-1">{msg.timestamp}</p>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 推荐问题区域 */}
          <div className="mb-3 space-y-2">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-medium text-gray-600">推荐问题</h3>
              {conversation.length > 0 && (
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => exportConversation()}
                    title="导出当前对话"
                  >
                    <Download className="h-3 w-3 mr-1" />
                    导出
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      if (currentConversationId) {
                        toggleFavorite(currentConversationId);
                      }
                    }}
                    title="收藏当前对话"
                  >
                    {currentConversationId && conversationHistory.find(c => c.id === currentConversationId)?.isFavorite ? (
                      <Star className="h-3 w-3 mr-1 fill-yellow-400 text-yellow-400" />
                    ) : (
                      <StarOff className="h-3 w-3 mr-1" />
                    )}
                    收藏
                  </Button>
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleRecommendedQuestion("我今天该吃些什么？")}
              >
                我今天该吃些什么？
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleRecommendedQuestion("你为谁服务？")}
              >
                你为谁服务？
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleRecommendedQuestion("你是谁？")}
              >
                你是谁？
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleRecommendedQuestion("帮我写一个简单的Python程序")}
              >
                帮我写一个简单的Python程序
              </Button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
            <Input
              value={message}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMessage(e.target.value)}
              placeholder="输入您的问题... (Ctrl+Enter 发送)"
              className="flex-1"
              disabled={sendMessageMutation.isPending}
            />
            <Button 
              type="submit" 
              disabled={sendMessageMutation.isPending || !message.trim()}
            >
              {sendMessageMutation.isPending ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <SendHorizonal className="h-4 w-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatAssistant;