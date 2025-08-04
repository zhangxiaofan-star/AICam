import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HelloWorld from '../pages/HelloWorld';
import Test from '../pages/Test';
// 此错误通常表示文件路径不正确或文件不存在，需要确认 '../pages/ChatAssistant' 文件是否存在。
// 假设文件扩展名是 .tsx，尝试添加扩展名
import ChatAssistant from '../pages/ChatAssistant';

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HelloWorld />} />
      <Route path="/test" element={<Test />} />
      <Route path="/chat" element={<ChatAssistant />} />
    </Routes>
  );
};

export default AppRoutes;