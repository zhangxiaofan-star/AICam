import React from 'react';

const HelloWorld: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      fontSize: '2rem'
    }}>
      <h1>Hello, World!</h1>
    </div>
  );
};

export default HelloWorld;