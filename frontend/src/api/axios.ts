import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { toast } from 'sonner';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Tratamento global de erros
    if (error.response) {
      if (error.response.status === 401) {
        useAuthStore.getState().logout();
        toast.error('Sessão expirada. Faça login novamente.');
        // SPA-friendly: nao recarrega a pagina, apenas limpa o estado.
        // O componente App.tsx ou um guard de rota deve redirecionar
        // automaticamente para /login ao detectar que user === null.
      } else if (error.response.status === 403) {
        toast.error('Acesso negado. Você não tem permissão.');
      } else if (error.response.status >= 500) {
        toast.error('Erro interno do servidor.');
      }
    } else if (error.request) {
      toast.error('Não foi possível conectar ao servidor.');
    }
    return Promise.reject(error);
  }
);
