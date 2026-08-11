import { create } from 'zustand';

interface SearchState {
  searchQuery: string;
  isOpen: boolean;
  setSearchQuery: (query: string) => void;
  setIsOpen: (isOpen: boolean) => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  searchQuery: '',
  isOpen: false,
  setSearchQuery: (query) => set({ searchQuery: query }),
  setIsOpen: (isOpen) => set({ isOpen }),
}));
