import React from 'react';
import { MessageSquare, Clock, Star, Download } from 'lucide-react';

interface ConversationStatsProps {
  totalConversations: number;
  totalMessages: number;
  favoriteConversations: number;
  lastActivity: string | null;
}

export const ConversationStats: React.FC<ConversationStatsProps> = ({
  totalConversations,
  totalMessages,
  favoriteConversations,
  lastActivity
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <div className="flex items-center space-x-2">
        <MessageSquare className="h-5 w-5 text-blue-500" />
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">总对话</p>
          <p className="text-lg font-semibold">{totalConversations}</p>
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        <MessageSquare className="h-5 w-5 text-green-500" />
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">总消息</p>
          <p className="text-lg font-semibold">{totalMessages}</p>
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        <Star className="h-5 w-5 text-yellow-500" />
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">收藏</p>
          <p className="text-lg font-semibold">{favoriteConversations}</p>
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        <Clock className="h-5 w-5 text-purple-500" />
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">最后活动</p>
          <p className="text-sm font-semibold">
            {lastActivity ? new Date(lastActivity).toLocaleDateString() : '无'}
          </p>
        </div>
      </div>
    </div>
  );
}; 