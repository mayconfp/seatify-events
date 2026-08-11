import { useEffect, useState, useRef } from 'react';
import { useSearchStore } from '../../store/searchStore';
import { api } from '../../api/axios';
import type { PaginatedEvents } from '../../types';
import { useDebounce } from '../../hooks/useDebounce';
import { X, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';

export const SearchOverlay = () => {
  const { isOpen, setIsOpen, searchQuery, setSearchQuery } = useSearchStore();
  const [data, setData] = useState<PaginatedEvents | null>(null);
  const [loading, setLoading] = useState(false);
  const debouncedSearch = useDebounce(searchQuery, 500);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      // Small delay to allow the slide animation to start before focusing
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    const fetchResults = async () => {
      setLoading(true);
      try {
        const response = await api.get<PaginatedEvents>('/events', {
          params: debouncedSearch ? { search: debouncedSearch } : {}
        });
        setData(response.data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    
    if (isOpen) {
      fetchResults();
    }
  }, [debouncedSearch, isOpen]);

  const handleClose = () => {
    setIsOpen(false);
    setSearchQuery('');
    setData(null);
  };

  return (
    <div 
      className={`fixed inset-y-0 right-0 w-full bg-zinc-950 z-[100] transform transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] flex flex-col overflow-y-auto ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header / Search Bar */}
      <div className="sticky top-0 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-800 z-10 px-4 py-6 md:px-12 flex items-center gap-4 md:gap-8">
        <button 
          onClick={handleClose}
          className="w-10 h-10 flex items-center justify-center rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors border border-zinc-700 flex-shrink-0"
          aria-label="Fechar busca"
        >
          <X className="w-5 h-5" />
        </button>
        
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Busque seu filme ou evento aqui..."
            className="w-full bg-transparent border-none text-sm md:text-base font-medium text-white placeholder:text-zinc-600 focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      {/* Results Area */}
      <div className="flex-1 container mx-auto px-4 md:px-12 py-8">
        <h2 className="text-xl md:text-2xl font-bold text-white mb-8 uppercase tracking-wider">
          {loading ? 'Carregando...' : 'Programação'}
        </h2>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
             {[1, 2, 3, 4].map(i => (
              <div key={i} className="rounded-2xl h-[400px] animate-pulse bg-zinc-900 border border-zinc-800" />
            ))}
          </div>
        ) : data?.events && data.events.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from(new Map(data.events.map(e => [e.title, e])).values()).map((event: any) => (
              <Link
                to={`/events/${event.id}`}
                key={event.id}
                onClick={handleClose}
                className="group event-card rounded-2xl overflow-hidden flex flex-col"
              >
                <div className="aspect-[3/4] w-full relative overflow-hidden bg-zinc-900">
                  {event.poster_url ? (
                    <img
                      src={`https://image.tmdb.org/t/p/w500${event.poster_url}`}
                      alt={event.title}
                      className="object-cover w-full h-full transition-transform duration-700 group-hover:scale-110"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-600">Sem Imagem</div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

                  <div className="absolute top-4 left-4">
                    <div className="inline-flex items-center px-3 py-1 text-xs font-bold bg-white text-zinc-900 shadow-sm uppercase">
                      ASSISTA AGORA
                    </div>
                  </div>
                  
                  <div className="absolute bottom-0 left-0 w-full p-5">
                    <h3 className="text-2xl font-bold text-white leading-tight mb-1 line-clamp-2">
                      {event.title}
                    </h3>
                  </div>
                </div>

                <div className="p-4 bg-zinc-900 flex-1 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-sm text-zinc-400 font-medium mb-3">
                    <div className="flex items-center gap-2">
                      <span className="truncate">{event.venue_name}</span>
                    </div>
                    <div className="flex items-center gap-2 text-primary font-bold">
                       R$ {Number(event.price).toFixed(2).replace('.', ',')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-zinc-500">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{data.events.filter(e => e.title === event.title).length} sessões disponíveis</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 bg-zinc-900/50 rounded-3xl border border-zinc-800">
            <p className="text-xl text-zinc-400">Nenhum evento encontrado para "{searchQuery}".</p>
          </div>
        )}
      </div>
    </div>
  );
};
