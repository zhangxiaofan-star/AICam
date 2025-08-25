import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HelloWorld from '../pages/HelloWorld';
import Test from '../pages/Test';
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