import { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '../../api/axios';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Search, Clapperboard, Calendar, Clock, MapPin, Users, DollarSign, Film, CheckCircle2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { useDebounce } from '../../hooks/useDebounce';
import type { Event } from '../../types';
import { format } from 'date-fns';

const eventSchema = z.object({
  title: z.string().min(3, 'Título muito curto'),
  description: z.string().optional(),
  sessions: z.array(z.object({
    event_date: z.string().min(1, 'Data obrigatória'),
    event_time: z.string().min(1, 'Horário obrigatório'),
  })).min(1, 'Adicione pelo menos uma sessão'),
  venue_name: z.string().min(2, 'Local obrigatório'),
  capacity: z.coerce.number().min(1, 'Capacidade mínima 1'),
  price: z.coerce.number().min(0, 'Preço inválido'),
  external_tmdb_id: z.string().optional(),
  poster_url: z.string().optional(),
});

type EventFormData = z.infer<typeof eventSchema>;

interface TmdbMovie {
  id: number;
  title: string;
  overview: string | null;
  poster_path: string | null;
  release_date: string | null;
}

interface EventCreateTabProps {
  mode: 'create' | 'edit' | 'duplicate';
  initialEvent: Event | null;
  onSuccess: () => void;
  onCancel: () => void;
}

export const EventCreateTab = ({ mode, initialEvent, onSuccess, onCancel }: EventCreateTabProps) => {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 500);
  const [movies, setMovies] = useState<TmdbMovie[]>([]);
  const [searching, setSearching] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState<TmdbMovie | null>(null);

  const { register, control, handleSubmit, setValue, reset, formState: { errors } } = useForm<EventFormData>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      capacity: 120,
      price: 35.00,
      sessions: [{ event_date: '', event_time: '' }]
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'sessions'
  });

  useEffect(() => {
    if (initialEvent) {
      setValue('title', initialEvent.title);
      setValue('description', initialEvent.description || '');
      setValue('venue_name', initialEvent.venue_name);
      setValue('capacity', initialEvent.capacity);
      setValue('price', Number(initialEvent.price));
      
      if (initialEvent.external_tmdb_id) {
        setValue('external_tmdb_id', initialEvent.external_tmdb_id);
        setSelectedMovie({
          id: Number(initialEvent.external_tmdb_id),
          title: initialEvent.title,
          overview: initialEvent.description || null,
          poster_path: initialEvent.poster_url || null,
          release_date: null
        });
      }
      if (initialEvent.poster_url) setValue('poster_url', initialEvent.poster_url);

      if (mode === 'edit') {
        const dateObj = new Date(initialEvent.event_date);
        setValue('sessions', [{ 
          event_date: format(dateObj, 'yyyy-MM-dd'), 
          event_time: format(dateObj, 'HH:mm') 
        }]);
      } else if (mode === 'duplicate') {
        setValue('sessions', [{ event_date: '', event_time: '' }]);
      }
    } else {
      reset();
      setSelectedMovie(null);
    }
  }, [initialEvent, mode, setValue, reset]);

  useEffect(() => {
    const searchTmdb = async () => {
      if (!debouncedSearch) {
        setMovies([]);
        return;
      }
      setSearching(true);
      try {
        const res = await api.get('/events/tmdb/search', { params: { query: debouncedSearch } });
        setMovies(res.data.results);
      } catch (error) {
        toast.error('Erro ao buscar filmes no TMDb.');
      } finally {
        setSearching(false);
      }
    };
    searchTmdb();
  }, [debouncedSearch]);

  const selectMovie = (movie: TmdbMovie) => {
    setSelectedMovie(movie);
    setValue('title', movie.title);
    if (movie.overview) setValue('description', movie.overview);
    setValue('external_tmdb_id', String(movie.id));
    if (movie.poster_path) setValue('poster_url', movie.poster_path);
    toast.success(`Filme "${movie.title}" selecionado com sucesso!`);
    setSearch('');
    setMovies([]);
  };

  const onSubmit = async (data: EventFormData) => {
    setCreating(true);
    try {
      if (mode === 'edit' && initialEvent) {
        const session = data.sessions[0];
        const combinedDateTime = new Date(`${session.event_date}T${session.event_time}:00`);
        const payload = {
          title: data.title,
          description: data.description,
          event_date: combinedDateTime.toISOString(),
          venue_name: data.venue_name,
          capacity: data.capacity,
          price: data.price,
          type: 'SEATED',
          external_tmdb_id: data.external_tmdb_id,
          poster_url: data.poster_url,
        };
        await api.put(`/events/${initialEvent.id}`, payload);
        toast.success('Sessão atualizada com sucesso!');
      } else {
        const payloads = data.sessions.map((session) => {
          const combinedDateTime = new Date(`${session.event_date}T${session.event_time}:00`);
          return {
            title: data.title,
            description: data.description,
            event_date: combinedDateTime.toISOString(),
            venue_name: data.venue_name,
            capacity: data.capacity,
            price: data.price,
            type: 'SEATED',
            external_tmdb_id: data.external_tmdb_id,
            poster_url: data.poster_url,
          };
        });
        await Promise.all(payloads.map(payload => api.post('/events', payload)));
        toast.success(`${payloads.length} ${payloads.length > 1 ? 'sessões publicadas' : 'sessão publicada'} com sucesso!`);
      }
      reset();
      setSelectedMovie(null);
      onSuccess();
    } catch (error: any) {
      if (error.response?.status === 409) {
        toast.error(error.response?.data?.detail || "Não é possível alterar uma sessão com ingressos vendidos.");
      } else {
        toast.error(error.response?.data?.detail || 'Erro ao publicar sessão.');
      }
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="lg:col-span-5 space-y-6">
        <div className="glass-card p-6 md:p-8 rounded-3xl border border-zinc-200 dark:border-zinc-800/80 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

          <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-2 flex items-center gap-2">
            <Clapperboard className="text-primary w-5 h-5" />
            1. Selecionar Filme
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-6 font-medium leading-relaxed">
            Pesquise no catálogo oficial para carregar a capa e a sinopse automaticamente.
          </p>

          <Input
            placeholder="Digite o título do filme..."
            icon={<Search className="w-4 h-4" />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12"
          />

          {selectedMovie && (
            <div className="mt-6 p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-primary/30 flex items-center gap-4 relative animate-in fade-in duration-300">
              {selectedMovie.poster_path ? (
                <img src={`https://image.tmdb.org/t/p/w200${selectedMovie.poster_path}`} className="w-16 h-24 object-cover rounded-xl shadow-md flex-shrink-0" alt="" />
              ) : (
                <div className="w-16 h-24 bg-zinc-800 rounded-xl flex items-center justify-center text-[10px] text-zinc-500 flex-shrink-0">Sem Foto</div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 text-emerald-500 text-xs font-bold mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Vinculado
                </div>
                <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100 truncate">{selectedMovie.title}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-2">{selectedMovie.overview}</p>
              </div>
              <button
                type="button"
                onClick={() => { setSelectedMovie(null); reset(); }}
                className="absolute top-2 right-2 text-xs text-zinc-400 hover:text-red-500 transition-colors p-1"
                title="Trocar filme"
              >
                ✕
              </button>
            </div>
          )}

          {searching && <p className="text-xs text-zinc-400 mt-4 animate-pulse text-center font-medium">Buscando no TMDb...</p>}

          {movies.length > 0 && !selectedMovie && (
            <div className="mt-4 space-y-3 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
              {movies.map(movie => (
                <div
                  key={movie.id}
                  className="flex gap-3 p-3 rounded-2xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 hover:border-primary/50 cursor-pointer transition-all hover:scale-[1.01]"
                  onClick={() => selectMovie(movie)}
                >
                  {movie.poster_path ? (
                    <img src={`https://image.tmdb.org/t/p/w200${movie.poster_path}`} className="w-12 h-16 object-cover rounded-lg flex-shrink-0 shadow-sm" alt="" />
                  ) : (
                    <div className="w-12 h-16 bg-zinc-800 rounded-lg flex items-center justify-center text-[10px] text-zinc-500 flex-shrink-0">Sem Foto</div>
                  )}
                  <div className="min-w-0 flex-1">
                    <h4 className="font-bold text-xs text-zinc-900 dark:text-zinc-200 truncate">{movie.title}</h4>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-2">{movie.overview || 'Sem descrição.'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="lg:col-span-7">
        <form onSubmit={handleSubmit(onSubmit)} className="glass-card p-6 md:p-8 rounded-3xl border border-zinc-200 dark:border-zinc-800/80 shadow-sm space-y-6">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <Film className="text-primary w-5 h-5" />
            {mode === 'edit' ? '2. Editar Detalhes da Sessão' : '2. Configuração da Sessão'}
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5 block">Título do Evento / Filme *</label>
              <Input {...register('title')} error={errors.title?.message} placeholder="Ex: Avatar: O Caminho da Água" className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12" />
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5 block">Sinopse / Descrição</label>
              <textarea
                {...register('description')}
                className="w-full rounded-xl border border-zinc-200 dark:border-zinc-700/60 bg-zinc-50 dark:bg-zinc-900/80 px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-all font-medium"
                rows={3}
                placeholder="Insira a sinopse detalhada..."
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400">Datas e Horários *</label>
                {mode !== 'edit' && (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => append({ event_date: '', event_time: '' })}
                    className="text-[10px] h-7 px-2"
                  >
                    <Plus className="w-3 h-3 mr-1" /> Adicionar Horário
                  </Button>
                )}
              </div>
              
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-start gap-3">
                  <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input type="date" icon={<Calendar className="w-4 h-4" />} {...register(`sessions.${index}.event_date` as const)} error={errors.sessions?.[index]?.event_date?.message} className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12 dark:[color-scheme:dark]" />
                    <Input type="time" icon={<Clock className="w-4 h-4" />} {...register(`sessions.${index}.event_time` as const)} error={errors.sessions?.[index]?.event_time?.message} className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12 dark:[color-scheme:dark]" />
                  </div>
                  {mode !== 'edit' && fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      className="mt-1 w-10 h-10 flex items-center justify-center rounded-xl text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Remover Horário"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              {errors.sessions?.root && <p className="text-xs text-red-500 font-medium">{errors.sessions.root.message}</p>}
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5 block">Sala / Local (Venue) *</label>
              <Input icon={<MapPin className="w-4 h-4" />} {...register('venue_name')} placeholder="Ex: Sala IMAX - Cineplex" error={errors.venue_name?.message} className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5 block">Preço por Ingresso (R$) *</label>
                <Input type="number" step="0.01" icon={<DollarSign className="w-4 h-4" />} {...register('price')} error={errors.price?.message} className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12" />
              </div>
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5 block">Capacidade da Sala *</label>
                <Input type="number" icon={<Users className="w-4 h-4" />} {...register('capacity')} error={errors.capacity?.message} className="bg-zinc-50 dark:bg-zinc-900/80 border-zinc-200 dark:border-zinc-700/60 h-12" />
              </div>
            </div>

            <div className="pt-4 space-y-3">
              <Button type="submit" className="w-full h-14 text-base font-bold shadow-lg shadow-primary/25" isLoading={creating} size="lg">
                {mode === 'edit' ? 'Salvar Alterações' : 'Publicar Sessão no Catálogo'}
              </Button>
              {mode === 'edit' && (
                <Button type="button" variant="outline" className="w-full h-12" onClick={onCancel}>
                  Cancelar Edição
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
