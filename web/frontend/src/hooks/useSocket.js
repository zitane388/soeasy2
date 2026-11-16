// src/hooks/useSocket.js
import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = 'http://localhost:5000';

let socket = null;
let connectHandlers = new Set();
let disconnectHandlers = new Set();
let statusHandlers = new Set();
let errorHandlers = new Set();

// Initialize socket once globally
const getSocket = () => {
  if (!socket) {
    console.log('🔌 Initializing Socket.IO connection...');
    socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    });

    socket.on('connect', () => {
      console.log('✅ Connected to server');
      connectHandlers.forEach(handler => handler(true));
    });

    socket.on('disconnect', () => {
      console.log('❌ Disconnected from server');
      disconnectHandlers.forEach(handler => handler(false));
    });

    socket.on('status', (data) => {
      console.log('[STATUS]', data.message);
      statusHandlers.forEach(handler => handler(data.message));
    });

    socket.on('error', (data) => {
      console.error('[ERROR]', data.message);
      errorHandlers.forEach(handler => handler(data.message));
    });
  }
  return socket;
};

export const useSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    const socket = getSocket();

    // Add handlers to sets
    connectHandlers.add(setIsConnected);
    disconnectHandlers.add(setIsConnected);
    statusHandlers.add(setStatusMessage);
    errorHandlers.add((msg) => alert(msg));

    // Set initial connection state
    setIsConnected(socket.connected);

    return () => {
      // Remove handlers on unmount
      connectHandlers.delete(setIsConnected);
      disconnectHandlers.delete(setIsConnected);
      statusHandlers.delete(setStatusMessage);
      // Note: error handler is anonymous, so it won't be removed
    };
  }, []);

  const on = (event, callback) => {
    const socket = getSocket();
    if (socket) {
      socket.on(event, callback);
    }
  };

  const off = (event, callback) => {
    const socket = getSocket();
    if (socket) {
      socket.off(event, callback);
    }
  };

  const emit = (event, data) => {
    const socket = getSocket();
    if (socket) {
      socket.emit(event, data);
    }
  };

  return {
    isConnected,
    statusMessage,
    on,
    off,
    emit,
  };
};
