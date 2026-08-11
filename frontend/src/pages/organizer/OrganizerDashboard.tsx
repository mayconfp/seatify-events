import { useState } from 'react';
import { LayoutDashboard, Sparkles, Plus, List } from 'lucide-react';
import type { Event } from '../../types';
import { EventCreateTab } from '../../components/organizer/EventCreateTab';
import { EventListTab } from '../../components/organizer/EventListTab';

export const OrganizerDashboard = () => {
  const [activeTab, setActiveTab] = useState<'create' | 'list'>('list');
  const [editingEvent, setEditingEvent] = useState<Event | null>(null);
  const [tabMode, setTabMode] = useState<'create' | 'edit' | 'duplicate'>('create');

  const handleEdit = (event: Event) => {
    setEditingEvent(event);
    setTabMode('edit');
    setActiveTab('create');
  };

  const handleDuplicate = (event: Event) => {
    setEditingEvent(event);
    setTabMode('duplicate');
    setActiveTab('create');
  };

  const handleStartCreate = () => {
    setEditingEvent(null);
    setTabMode('create');
    setActiveTab('create');
  };

  const handleSuccess = () => {
    setEditingEvent(null);
    setTabMode('create');
    setActiveTab('list');
  };

  const handleCancel = () => {
    setEditingEvent(null);
    setTabMode('create');
    setActiveTab('list');
  };

  return (
    <div className="container mx-auto px-4 py-12 max-w-6xl transition-colors duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 pb-6 border-b border-zinc-200 dark:border-zinc-800/80">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center text-primary border border-primary/20 shadow-inner">
            <LayoutDashboard className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-zinc-900 dark:text-white tracking-tight">Painel do Organizador</h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 font-medium">Gerencie sessões de cinema e publique novos filmes na plataforma.</p>
          </div>
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-600 dark:text-zinc-300">
          <Sparkles className="w-4 h-4 text-primary" /> Integração TMDb Ativa
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-8 bg-zinc-100 dark:bg-zinc-900/50 p-1.5 rounded-2xl w-fit border border-zinc-200 dark:border-zinc-800/80">
        <button
          onClick={() => setActiveTab('list')}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === 'list' 
              ? 'bg-white dark:bg-zinc-800 text-primary shadow-sm' 
              : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-300'
          }`}
        >
          <List className="w-4 h-4" />
          Minhas Sessões
        </button>
        <button
          onClick={handleStartCreate}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === 'create' 
              ? 'bg-white dark:bg-zinc-800 text-primary shadow-sm' 
              : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-300'
          }`}
        >
          <Plus className="w-4 h-4" />
          {tabMode === 'edit' ? 'Editar Sessão' : 'Publicar Sessão'}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'create' && (
        <EventCreateTab 
          mode={tabMode}
          initialEvent={editingEvent}
          onSuccess={handleSuccess}
          onCancel={handleCancel}
        />
      )}

      {activeTab === 'list' && (
        <EventListTab 
          onEdit={handleEdit}
          onDuplicate={handleDuplicate}
          onStartCreate={handleStartCreate}
        />
      )}
    </div>
  );
};