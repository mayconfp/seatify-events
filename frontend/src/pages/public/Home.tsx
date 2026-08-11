import { useState, useEffect } from 'react';
import { api } from '../../api/axios';
import type { PaginatedEvents, TmdbTrendingResponse, TmdbMovie } from '../../types';
import { Button } from '../../components/ui/Button';
import { Calendar, MapPin, User, Tag } from 'lucide-react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useDebounce } from '../../hooks/useDebounce';
import { CoverflowCarousel } from '../../components/event/CoverflowCarousel';
import { useSearchStore } from '../../store/searchStore';

export const Home = () => {
  const { searchQuery } = useSearchStore();
  const [activeCategory, setActiveCategory] = useState('Todos');
  const debouncedSearch = useDebounce(searchQuery, 500);

  const categories = ['Todos', 'Ação', 'Comédia', 'Drama', 'Ficção científica', 'Terror', 'Romance', 'Animação'];
  
  const [data, setData] = useState<PaginatedEvents | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [trending, setTrending] = useState<TmdbMovie[]>([]);
  const [loadingTrending, setLoadingTrending] = useState(true);

  // Fetch trending
  useEffect(() => {
    const fetchTrending = async () => {
      setLoadingTrending(true);
      try {
        const response = await api.get<TmdbTrendingResponse>('/events/tmdb/trending', {
          params: { time_window: 'week' }
        });
        setTrending(response.data.results);
      } catch (error) {
        console.error("Erro ao buscar filmes em alta", error);
      } finally {
        setLoadingTrending(false);
      }
    };
    fetchTrending();
  }, []);

  // Fetch local events
  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      try {
        const params: any = {};
        if (debouncedSearch) params.search = debouncedSearch;
        if (activeCategory !== 'Todos') params.genre = activeCategory;

        const response = await api.get<PaginatedEvents>('/events', { params });
        setData(response.data);
      } catch (error) {
        console.error("Erro ao buscar sessões locais", error);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, [debouncedSearch, activeCategory]);

  return (
    <div className="flex flex-col min-h-full">
      {/* Hero Section */}
      <section className="relative w-full pt-20 flex flex-col items-center justify-center overflow-hidden transition-colors duration-300">
        <div className="absolute inset-0 bg-zinc-50 dark:bg-zinc-950 z-10" />

        <div className="relative z-20 w-full flex flex-col items-center">
          {/* Coverflow Carousel (Trending) */}
          {!loadingTrending && trending.length > 0 ? (
            <CoverflowCarousel events={trending.slice(0, 10)} />
          ) : (
            <div className="w-full max-w-4xl mx-auto h-[450px] bg-slate-200 dark:bg-slate-800 rounded-3xl animate-pulse mb-16" />
          )}

          {/* Categories */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-12 px-4 relative z-30">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${activeCategory === cat
                  ? 'bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 shadow-sm'
                  : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-800'
                  }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Events Grid */}
      <section className="container mx-auto px-4 pb-20 relative z-30">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight transition-colors duration-300">
            Eventos Disponíveis
          </h2>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="glass-card rounded-2xl h-96 animate-pulse flex flex-col overflow-hidden">
                <div className="h-[60%] w-full bg-slate-200 dark:bg-zinc-900" />
                <div className="flex-1 p-5 space-y-4">
                  <div className="h-4 w-1/4 bg-slate-200 dark:bg-zinc-900 rounded" />
                  <div className="h-6 w-3/4 bg-slate-200 dark:bg-zinc-900 rounded" />
                  <div className="h-4 w-1/2 bg-slate-200 dark:bg-zinc-900 rounded mt-4" />
                </div>
              </div>
            ))}
          </div>
        ) : data?.events.length === 0 ? (
          <div className="text-center py-20 glass-card rounded-xl">
            <p className="text-xl text-slate-400">Nenhuma sessão encontrada para esta categoria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from(new Map(data?.events.map(e => [e.title, e])).values()).map((event: any) => {
              // Badge de Classificação Etária 
              // L = verde, 10/12/14 = amarelo/laranja, 16/18 = vermelho
              let badgeColor = "bg-zinc-500 text-white";
              if (event.age_rating) {
                const r = event.age_rating.toLowerCase();
                if (r === 'l' || r === 'livre') badgeColor = "bg-green-500 text-white";
                else if (r.includes('10') || r.includes('12')) badgeColor = "bg-yellow-500 text-white";
                else if (r.includes('14')) badgeColor = "bg-orange-500 text-white";
                else if (r.includes('16') || r.includes('18')) badgeColor = "bg-red-600 text-white";
              }

              return (
                <Link
                  to={`/events/${event.id}`}
                  key={event.id}
                  className="group rounded-2xl overflow-hidden flex flex-col bg-zinc-50 dark:bg-[#1a1a1a] border border-zinc-200 dark:border-[#2a2a2a] hover:border-zinc-300 dark:hover:border-[#3a3a3a] transition-all duration-300 hover:shadow-xl"
                >
                  <div className="aspect-[3/4] w-full relative overflow-hidden bg-zinc-900">
                    {event.poster_url ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w500${event.poster_url}`}
                        alt={event.title}
                        className="object-cover w-full h-full transition-transform duration-700 group-hover:scale-105"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-zinc-600">Sem Imagem</div>
                    )}
                    
                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-900/20 to-transparent opacity-90" />

                    <div className="absolute bottom-0 left-0 w-full p-5">
                      <div className="flex items-center gap-2 mb-2">
                        {event.age_rating && (
                          <div className={`px-2 py-0.5 text-xs font-black rounded-sm ${badgeColor}`}>
                            {event.age_rating.toUpperCase()}
                          </div>
                        )}
                        {event.genre && (
                          <div className="px-2 py-0.5 text-[10px] font-bold bg-white/20 backdrop-blur-md text-white uppercase rounded-sm border border-white/10">
                            {event.genre.split(',')[0]}
                          </div>
                        )}
                      </div>
                      <h3 className="text-xl font-bold text-white leading-tight line-clamp-2 shadow-sm">
                        {event.title}
                      </h3>
                    </div>
                  </div>

                  <div className="p-5 flex-1 flex flex-col justify-between gap-5">
                    <div className="space-y-2 text-xs text-zinc-500 dark:text-zinc-400 font-medium">
                      {event.director && (
                        <div className="flex items-center gap-2">
                          <User className="w-3.5 h-3.5" />
                          <span className="truncate">Diretor: {event.director}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{data?.events.filter(e => e.title === event.title).length} sessões disponíveis</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="truncate">{event.venue_name}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mt-2 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                      <span className="text-base font-bold text-zinc-900 dark:text-white">
                        R$ {Number(event.price).toFixed(2).replace('.', ',')}
                      </span>
                      <Button size="sm" variant="primary" className="text-xs px-4 rounded-lg bg-primary hover:bg-primary/90 text-white border-none">
                        Ingressos
                      </Button>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};
