// src/services/api.js
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const collectAPI = {
  scrape: (url) => api.post('/collect/scrape', { url }),
  getPending: () => api.get('/collect/pending'),
};

export const naverBestAPI = {
  loadStore: () => api.post('/naver-best/load-store'),
  collectList: () => api.post('/naver-best/collect-list'),
  collectDetails: () => api.post('/naver-best/collect-details'),
  collectOrigin: () => api.post('/naver-best/collect-origin'),
  getItems: () => api.get('/naver-best/items'),
};

export const productsAPI = {
  getPending: () => api.get('/products/pending'),
  getCollected: () => api.get('/products/collected'),
  deletePending: (index) => api.delete(`/products/pending/${index}`),
  deleteCollected: (index) => api.delete(`/products/collected/${index}`),
};

export const healthAPI = {
  check: () => api.get('/health'),
  getState: () => api.get('/state'),
};

export default api;
