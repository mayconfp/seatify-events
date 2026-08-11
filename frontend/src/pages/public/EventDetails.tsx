import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../../api/axios';
import type { Event, Seat, TmdbMovie } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { SeatMap } from '../../components/event/SeatMap';
import { Button } from '../../components/ui/Button';
import { Calendar, MapPin, Loader2, Star, User, Clapperboard } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { toast } from 'sonner';

export const EventDetails = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, hasRole } = useAuthStore();

  const [event, setEvent] = useState<Event | null>(null);
  const [sessions, setSessions] = useState<Event[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>(id || '');
  const [seats, setSeats] = useState<Seat[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeats, setSelectedSeats] = useState<string[]>([]);
  const [isReserving, setIsReserving] = useState(false);

  useEffect(() => {
    const fetchEventData = async () => {
      try {
        const eventRes = await api.get<Event>(`/events/${id}`);
        setEvent(eventRes.data);
        setSelectedSessionId(eventRes.data.id);

        // Fetch all sessions for this movie
        const sessionsRes = await api.get<{events: Event[]}>('/events', {
          params: { search: eventRes.data.title }
        });
        
        // Filter strictly by title to avoid fuzzy matches and sort by date
        const exactSessions = sessionsRes.data.events
          .filter(e => e.title === eventRes.data.title)
          .sort((a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime());
          
        setSessions(exactSessions);
      } catch (error) {
        toast.error('Não foi possível carregar os detalhes do evento.');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    if (id) fetchEventData();
  }, [id, navigate]);

  useEffect(() => {
    if (selectedSessionId && event) {
      const fetchSeats = async () => {
        try {
          const seatsRes = await api.get<Seat[]>(`/events/${selectedSessionId}/seats`);
          setSeats(seatsRes.data);
          setSelectedSeats([]);
        } catch (error) {
          toast.error('Erro ao carregar assentos da sessão.');
        }
      };
      fetchSeats();
    }
  }, [selectedSessionId, id, event]);

  const handleSeatToggle = (seatNumber: string) => {
    setSelectedSeats((prev) =>
      prev.includes(seatNumber)
        ? prev.filter((s) => s !== seatNumber)
        : [...prev, seatNumber]
    );
  };

  const handleReserve = async () => {
    if (!isAuthenticated()) {
      toast.error('Você precisa estar logado para reservar assentos.');
      navigate('/login');
      return;
    }

    if (!hasRole(['CLIENT'])) {
      toast.error('Apenas clientes podem reservar ingressos.');
      return;
    }

    if (selectedSeats.length === 0) return;

    setIsReserving(true);
    try {
      await api.post(`/events/${selectedSessionId}/reserve`, {
        seat_numbers: selectedSeats
      });
      toast.success('Assentos reservados com sucesso!');
      navigate(`/checkout/${selectedSessionId}`, { state: { selectedSeats } });
    } catch (error: any) {
      if (error.response?.status === 409) {
        toast.error('Um ou mais assentos já foram reservados por outra pessoa.');
        const seatsRes = await api.get<Seat[]>(`/events/${id}/seats`);
        setSeats(seatsRes.data);
        setSelectedSeats([]);
      } else {
        toast.error('Erro ao reservar assentos.');
      }
    } finally {
      setIsReserving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  if (!event) return null;

  const subtotal = selectedSeats.length * event.price;

  // Resolve badge color for age rating
  const getBadgeColor = (rating: string) => {
    const r = rating.toLowerCase();
    if (r === 'l' || r === 'livre') return 'bg-green-500 text-white';
    if (r.includes('10') || r.includes('12')) return 'bg-yellow-500 text-zinc-900';
    if (r.includes('14')) return 'bg-orange-500 text-white';
    return 'bg-red-600 text-white';
  };

  // Use stored event data which now includes TMDb cache
  const displayGenre = event.genre;
  const displayDirector = event.director;
  const displayAgeRating = event.age_rating;
  const displayReleaseDate = event.release_date;
  const displayCast = event.cast || [];
  const displayVoteAverage = event.vote_average;

  return (
    <div className="flex-1 pb-32">
      {/* Event Header */}
      <div className="w-full bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 transition-colors duration-300">
        <div className="container mx-auto px-4 py-8 lg:py-12 flex flex-col lg:flex-row gap-8 items-start">
          {event.poster_url ? (
            <img
              src={`https://image.tmdb.org/t/p/w500${event.poster_url}`}
              alt={event.title}
              className="w-full lg:w-64 rounded-xl shadow-2xl object-cover aspect-[3/4] flex-shrink-0"
            />
          ) : (
            <div className="w-full lg:w-64 aspect-[3/4] bg-zinc-800 rounded-xl flex items-center justify-center border border-zinc-700 flex-shrink-0">
              <span className="text-zinc-500">Sem Imagem</span>
            </div>
          )}

          <div className="flex-1 min-w-0">
            {/* Badges row */}
            <div className="flex flex-wrap items-center gap-2 mb-4">
              {displayAgeRating && (
                <span className={`px-2 py-0.5 text-xs font-black rounded-sm ${getBadgeColor(displayAgeRating)}`}>
                  {displayAgeRating.toUpperCase()}
                </span>
              )}
              {displayGenre && (
                <span className="px-3 py-1 text-xs font-semibold bg-primary/15 text-primary rounded-full border border-primary/30">
                  {displayGenre.split('Â·')[0].trim()}
                </span>
              )}
              <span className="px-3 py-1 text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 rounded-full">
                {event.type}
              </span>
            </div>

            <h1 className="text-3xl lg:text-5xl font-bold text-zinc-900 dark:text-white mb-4 leading-tight">{event.title}</h1>

            {/* Rating + Year row */}
            <div className="flex flex-wrap items-center gap-5 mb-6 text-sm">
              {displayVoteAverage && (
                <div className="flex items-center gap-1.5 text-yellow-500 font-bold">
                  <Star className="w-4 h-4 fill-yellow-500" />
                  <span className="text-lg font-black">{displayVoteAverage.toFixed(1)}</span>
                  <span className="text-zinc-400 font-normal text-xs">/10 TMDb</span>
                </div>
              )}
              {displayReleaseDate && (
                <div className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
                  <Calendar className="w-4 h-4" />
                  <span>Estreia: {format(new Date(displayReleaseDate), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}</span>
                </div>
              )}
            </div>

            {/* Sessions date */}
            <div className="flex items-center gap-3 mb-6 text-zinc-600 dark:text-zinc-300">
              <div className="w-9 h-9 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-primary">
                <Calendar className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs text-zinc-500">Próxima Sessão</p>
                <p className="font-semibold text-zinc-800 dark:text-zinc-200">{format(new Date(event.event_date), "dd 'de' MMMM", { locale: ptBR })}</p>
              </div>
            </div>

            {event.description && (
              <div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-2 uppercase tracking-wider">Sobre o filme</h3>
                <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed max-w-3xl text-sm">
                  {event.description}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Elenco e Equipe */}
      {(displayDirector || displayCast.length > 0) && (
        <div className="container mx-auto px-4 py-8 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-6 flex items-center gap-2">
            <Clapperboard className="w-5 h-5 text-primary" />
            Elenco e Equipe
          </h2>

          {/* Director */}
          {displayDirector && (
            <div className="flex items-center gap-4 mb-6 pb-6 border-b border-zinc-100 dark:border-zinc-800">
              <div className="w-10 h-10 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-zinc-500" />
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-semibold">Diretor</p>
                <p className="font-semibold text-zinc-900 dark:text-white">{displayDirector}</p>
              </div>
            </div>
          )}

          {/* Cast grid */}
          {displayCast.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-semibold mb-4">Elenco Principal</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8 gap-4">
                {displayCast.map((actor, i) => (
                  <div key={i} className="flex flex-col items-center text-center gap-2">
                    {actor.profile_path ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w185${actor.profile_path}`}
                        alt={actor.name}
                        className="w-16 h-16 rounded-full object-cover shadow-md border-2 border-zinc-200 dark:border-zinc-700"
                      />
                    ) : (
                      <div className="w-16 h-16 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center border-2 border-zinc-300 dark:border-zinc-700">
                        <span className="text-lg font-bold text-zinc-400">{actor.name[0]}</span>
                      </div>
                    )}
                    <div>
                      <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">{actor.name}</p>
                      {actor.character && (
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 leading-tight mt-0.5">{actor.character}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cinemark-style Session Groups */}
      {sessions.length > 0 && (
        <div className="container mx-auto px-4 py-8">
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-white mb-6 transition-colors">Horários Disponíveis</h2>
          <div className="space-y-8">
            {Object.entries(
              sessions.reduce((acc, session) => {
                if (!acc[session.venue_name]) acc[session.venue_name] = [];
                acc[session.venue_name].push(session);
                return acc;
              }, {} as Record<string, Event[]>)
            ).map(([venue, venueSessions]) => (
              <div key={venue} className="bg-zinc-50 dark:bg-zinc-900/50 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800">
                <div className="flex items-center gap-2 mb-4">
                  <MapPin className="w-5 h-5 text-primary" />
                  <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{venue}</h3>
                </div>
                <div className="flex flex-wrap gap-3">
                  {venueSessions.map(session => {
                    const isSelected = selectedSessionId === session.id;
                    const dateObj = new Date(session.event_date);
                    return (
                      <button
                        key={session.id}
                        onClick={() => setSelectedSessionId(session.id)}
                        className={`px-4 py-3 rounded-xl flex flex-col items-center justify-center transition-all duration-300 ${
                          isSelected 
                            ? 'bg-primary text-white shadow-md scale-105' 
                            : 'bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 hover:border-primary/50'
                        }`}
                      >
                        <span className="text-xs font-semibold mb-1 opacity-80 uppercase tracking-wider">{format(dateObj, 'EEEE, dd MMM', { locale: ptBR })}</span>
                        <span className="text-xl font-bold">{format(dateObj, 'HH:mm')}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Seat Selection */}
      {event.type === 'SEATED' && selectedSessionId && (
        <div className="container mx-auto px-4 pt-8 pb-4">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-white mb-2 transition-colors">Escolha seus assentos</h2>
            <p className="text-zinc-600 dark:text-zinc-400 text-sm">Selecione os lugares desejados para a sessão escolhida.</p>
          </div>

          <SeatMap
            seats={seats}
            selectedSeats={selectedSeats}
            onSeatToggle={handleSeatToggle}
          />
        </div>
      )}

      {/* Sticky Drawer for Selected Seats */}
      {selectedSeats.length > 0 && (
        <div className="fixed bottom-0 left-0 w-full bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border-t border-zinc-200 dark:border-zinc-700 p-4 shadow-[0_-10px_40px_rgba(0,0,0,0.1)] dark:shadow-[0_-10px_40px_rgba(0,0,0,0.5)] z-40 animate-in slide-in-from-bottom-full duration-500 ease-out transition-colors">
          <div className="container mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-1">
                {selectedSeats.length} {selectedSeats.length === 1 ? 'assento selecionado' : 'assentos selecionados'}:
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedSeats.map(seat => (
                  <span key={seat} className="px-2 py-1 bg-primary/20 text-primary-300 border border-primary/30 rounded text-sm font-semibold">
                    {seat}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">Total</p>
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">R$ {Number(subtotal).toFixed(2).replace('.', ',')}</p>
              </div>
              <Button size="lg" className="w-full sm:w-auto" onClick={handleReserve} isLoading={isReserving}>
                Reservar Ingressos
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
