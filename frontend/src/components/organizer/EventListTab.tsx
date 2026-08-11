import { useState, useEffect } from 'react';
import { api } from '../../api/axios';
import { Button } from '../../components/ui/Button';
import { Clapperboard, Calendar, Clock, MapPin, Users, DollarSign, Film, Plus, List, Trash2, BarChart3, ImageOff } from 'lucide-react';
import { toast } from 'sonner';
import type { Event, PaginatedEvents } from '../../types';
import { EventAnalyticsModal } from './EventAnalyticsModal';
import { format } from 'date-fns';

interface EventListTabProps {
  onEdit: (event: Event) => void;
  onDuplicate: (event: Event) => void;
  onStartCreate: () => void;
}

export const EventListTab = ({ onEdit, onDuplicate, onStartCreate }: EventListTabProps) => {
  const [myEvents, setMyEvents] = useState<Event[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [analyticsEventId, setAnalyticsEventId] = useState<string | null>(null);
  const [expandedMovieTitle, setExpandedMovieTitle] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchMyEvents = async (page = currentPage) => {
    setLoadingEvents(true);
    try {
      const res = await api.get<PaginatedEvents>('/events/organizer/me', { params: { page, page_size: 100 } });
      setMyEvents(res.data.events);
      setTotalPages(Math.ceil(res.data.total / res.data.page_size) || 1);
      setCurrentPage(res.data.page);
    } catch (error) {
      toast.error('Erro ao carregar suas sessões.');
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    fetchMyEvents(currentPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage]);

  const handleDelete = async (eventId: string) => {
    try {
      await api.delete(`/events/${eventId}`);
      toast.success("Sessão excluída com sucesso!");
      fetchMyEvents(currentPage);
    } catch (error: any) {
      if (error.response?.status === 409) {
        toast.error("Não é possível excluir: já existem ingressos vendidos para esta sessão.");
      } else if (error.response?.status === 403) {
        toast.error("Você não tem permissão para gerenciar este evento.");
      } else {
        toast.error("Erro ao excluir sessão.");
      }
    }
  };

  const confirmDelete = (eventId: string, title: string) => {
    toast('Confirmar Exclusão', {
      description: `Tem certeza que deseja excluir "${title}"?`,
      action: {
        label: 'Sim, excluir',
        onClick: () => handleDelete(eventId)
      },
      cancel: {
        label: 'Cancelar',
        onClick: () => {}
      },
      duration: 8000,
      className: 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-900',
    });
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {analyticsEventId && (
        <EventAnalyticsModal
          eventId={analyticsEventId}
          onClose={() => setAnalyticsEventId(null)}
        />
      )}

      {loadingEvents ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 bg-zinc-100 dark:bg-zinc-900/80 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : myEvents.length === 0 ? (
        <div className="text-center py-20 bg-zinc-50 dark:bg-zinc-900/30 rounded-3xl border border-zinc-200 dark:border-zinc-800 border-dashed">
          <Film className="w-12 h-12 text-zinc-400 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-zinc-900 dark:text-white mb-2">Nenhuma sessão encontrada</h3>
          <p className="text-sm text-zinc-500 mb-6 max-w-md mx-auto">Você ainda não publicou nenhuma sessão. Vá para a aba "Publicar Sessão" para começar a vender ingressos.</p>
          <Button onClick={onStartCreate} variant="outline">
            Publicar Primeira Sessão
          </Button>
        </div>
      ) : (
        expandedMovieTitle ? (
          <div className="animate-in fade-in zoom-in-95 duration-300">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <Button onClick={() => setExpandedMovieTitle(null)} variant="outline" className="h-10 px-3">
                  Voltar
                </Button>
                <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                  <Clapperboard className="w-5 h-5 text-primary" />
                  {expandedMovieTitle}
                </h2>
              </div>
              <Button 
                variant="primary" 
                onClick={() => {
                  const template = myEvents.find(e => e.title === expandedMovieTitle);
                  if(template) onDuplicate(template);
                }}
              >
                <Plus className="w-4 h-4 mr-2" /> Adicionar Sessões
              </Button>
            </div>
            
            <div className="grid grid-cols-1 gap-4">
              {myEvents.filter(e => e.title === expandedMovieTitle).map(session => (
                <div key={session.id} className="glass-card bg-white dark:bg-zinc-950 p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center gap-6">
                    <div className="bg-primary/10 text-primary w-14 h-14 rounded-xl flex flex-col items-center justify-center font-bold">
                      <span className="text-sm">{format(new Date(session.event_date), 'dd')}</span>
                      <span className="text-xs uppercase">{format(new Date(session.event_date), 'MMM')}</span>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                        <Clock className="w-4 h-4 text-zinc-400" />
                        {format(new Date(session.event_date), 'HH:mm')}
                      </div>
                      <div className="text-sm text-zinc-500 flex items-center gap-4 mt-1">
                        <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {session.venue_name}</span>
                        <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {session.capacity} vagas</span>
                        <span className="flex items-center gap-1"><DollarSign className="w-3.5 h-3.5" /> R$ {Number(session.price).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button variant="outline" size="sm" onClick={() => setAnalyticsEventId(session.id)}>
                      <BarChart3 className="w-4 h-4 mr-1.5" /> Relatório
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => onEdit(session)}>
                      Editar
                    </Button>
                    <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => confirmDelete(session.id, session.title)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from(new Map(myEvents.map(e => [e.title, e])).values()).map((event: any) => (
              <div key={event.id} className="group glass-card bg-white dark:bg-zinc-950 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden flex flex-col">
                <div className="h-40 relative overflow-hidden bg-zinc-900">
                  {event.poster_url ? (
                    <>
                      <div 
                        className="absolute inset-0 bg-cover bg-center blur-md opacity-50 scale-110" 
                        style={{ backgroundImage: `url(https://image.tmdb.org/t/p/w500${event.poster_url})` }} 
                      />
                      <img 
                        src={`https://image.tmdb.org/t/p/w500${event.poster_url}`} 
                        alt={event.title}
                        className="w-full h-full object-contain relative z-10"
                      />
                    </>
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-zinc-700">
                      <ImageOff className="w-10 h-10 opacity-50" />
                    </div>
                  )}
                </div>
                
                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="font-bold text-lg text-zinc-900 dark:text-white mb-2 line-clamp-1">{event.title}</h3>
                  
                  <div className="space-y-1.5 mb-6 text-sm text-zinc-500 dark:text-zinc-400 font-medium">
                    <div className="flex items-center gap-2 text-primary">
                      <Calendar className="w-4 h-4" />
                      {myEvents.filter(e => e.title === event.title).length} sessões cadastradas
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      <span className="truncate">{event.venue_name}</span>
                    </div>
                  </div>

                  <div className="mt-auto flex flex-col gap-2">
                    <div className="grid grid-cols-2 gap-2">
                      <Button 
                        variant="primary" 
                        className="w-full text-xs h-10 gap-1 px-1"
                        onClick={() => setExpandedMovieTitle(event.title)}
                      >
                        <List className="w-3.5 h-3.5 mr-1" />
                        Ver Sessões
                      </Button>
                      <Button 
                        variant="secondary" 
                        className="w-full text-xs h-10 gap-1 px-1 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 border border-emerald-200 dark:border-emerald-800"
                        onClick={() => onDuplicate(event)}
                      >
                        <Plus className="w-3.5 h-3.5 mr-1" />
                        Adicionar Sessões
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      )}
      
      {!loadingEvents && myEvents.length > 0 && !expandedMovieTitle && totalPages > 1 && (
        <div className="flex justify-center items-center gap-4 mt-10">
          <Button 
            variant="outline" 
            disabled={currentPage === 1} 
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm font-medium text-zinc-500">Página {currentPage} de {totalPages}</span>
          <Button 
            variant="outline" 
            disabled={currentPage === totalPages} 
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  );
};
