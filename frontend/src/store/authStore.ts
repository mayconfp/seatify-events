import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, UserRole } from '../types';

interface AuthState {
  token: string | null;
  user: User | null;
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  hasRole: (roles: UserRole[]) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
      isAuthenticated: () => !!get().token && !!get().user,
      hasRole: (roles) => {
        const user = get().user;
        if (!user) return false;
        return roles.includes(user.role);
      },
    }),
    {
      name: 'eventify-auth',
    }
  )
);
