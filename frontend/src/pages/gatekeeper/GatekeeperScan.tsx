import { useState, useRef, useEffect, useCallback } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { api } from '../../api/axios';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import type { Event } from '../../types';
import {
  QrCode,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Camera,
  CameraOff,
  FlipHorizontal,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { toast } from 'sonner';

type ValidationStatus = 'IDLE' | 'VALID' | 'ALREADY_USED' | 'WRONG_EVENT' | 'INVALID' | 'WRONG_TIME';

interface ValidationResponse {
  status: ValidationStatus;
  message: string;
  ticket_id?: string;
  event_title?: string;
}

// Chave usada para lembrar o evento selecionado entre leituras/recarregamentos
// da tela do porteiro, evitando reselecao manual a cada ingresso validado.
const SELECTED_EVENT_STORAGE_KEY = 'gatekeeper:selected_event_id';

export const GatekeeperScan = () => {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>(
    () => localStorage.getItem(SELECTED_EVENT_STORAGE_KEY) || ''
  );
  const [loadingEvents, setLoadingEvents] = useState(true);

  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const html5QrCodeRef = useRef<Html5Qrcode | null>(null);
  
  // Ref para contornar o Stale Closure da câmera
  const selectedEventIdRef = useRef<string>(selectedEventId);

  // Carrega a lista de eventos para o porteiro escolher qual sessao esta validando.
  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await api.get<{ events: Event[] }>('/events', {
          params: { page_size: 100 },
        });
        setEvents(response.data.events);
      } catch {
        toast.error('Não foi possível carregar a lista de eventos.');
      } finally {
        setLoadingEvents(false);
      }
    };
    fetchEvents();
  }, []);

  useEffect(() => {
    if (selectedEventId) {
      localStorage.setItem(SELECTED_EVENT_STORAGE_KEY, selectedEventId);
    }
    // Mantém a ref sempre sincronizada com o estado mais atual
    selectedEventIdRef.current = selectedEventId;
  }, [selectedEventId]);

  // Keep focus on input for physical scanners
  useEffect(() => {
    inputRef.current?.focus();
  }, [result]);

  const handleValidate = useCallback(
    async (rawValue: string) => {
      const value = rawValue.trim();
      const currentEventId = selectedEventIdRef.current;
      
      if (!value || !currentEventId) return;

      setLoading(true);
      setResult(null);
      try {
        const response = await api.post<ValidationResponse>('/gatekeeper/validate', {
          qr_token_or_hash: value,
          event_id: currentEventId,
        });
        setResult(response.data);
      } catch (error: any) {
        if (error.response?.data) {
          setResult(error.response.data);
        } else {
          setResult({
            status: 'INVALID',
            message: 'Erro de conexão ou token malformado.',
          });
        }
      } finally {
        setLoading(false);
        setToken('');
      }
    },
    [] // Sem dependências para não recriar a função e quebrar a câmera
  );

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleValidate(token);
  };

  const stopCamera = async () => {
    if (html5QrCodeRef.current) {
      try {
        await html5QrCodeRef.current.stop();
        html5QrCodeRef.current.clear();
        html5QrCodeRef.current = null;
      } catch (err) {
        console.error(err);
      }
    }
    setCameraActive(false);
  };

  const startCamera = async (mode: "environment" | "user" = facingMode) => {
    if (!selectedEventId) return;
    setCameraError(null);
    setCameraActive(true); // Exibe o container da câmera no DOM primeiro

    // Aguarda o React renderizar a div #reader com as dimensões corretas 
    // antes de inicializar o Html5Qrcode, evitando que ele crie um vídeo de 0x0.
    await new Promise(resolve => setTimeout(resolve, 100));

    try {
      if (html5QrCodeRef.current?.isScanning) {
        await html5QrCodeRef.current.stop();
        html5QrCodeRef.current.clear();
      }

      const html5QrCode = new Html5Qrcode("reader");
      html5QrCodeRef.current = html5QrCode;
      
      await html5QrCode.start(
        { facingMode: mode },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          html5QrCode.pause(true);
          handleValidate(decodedText);
        },
        (_error) => {
          // Ignora quadros vazios
        }
      );
    } catch (err) {
      console.error(err);
      const errorMsg = 'Não foi possível acessar a câmera. Verifique as permissões do navegador.';
      setCameraError(errorMsg);
      toast.error(errorMsg);
      setCameraActive(false);
    }
  };

  const toggleCamera = async () => {
    const newMode = facingMode === "environment" ? "user" : "environment";
    setFacingMode(newMode);
    if (cameraActive) {
      await startCamera(newMode);
    }
  };

  // Limpa a câmera ao desmontar
  useEffect(() => {
    return () => {
      if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
        html5QrCodeRef.current.stop().catch(e => console.error(e));
      }
    };
  }, []);

  const handleReset = () => {
    setResult(null);
    setToken('');
    inputRef.current?.focus();
    // Retoma a leitura por camera automaticamente apos o porteiro validar
    if (html5QrCodeRef.current) {
      html5QrCodeRef.current.resume();
    }
  };

  const getStatusColor = (status: ValidationStatus) => {
    switch (status) {
      case 'VALID': return 'bg-green-600 text-white';
      case 'ALREADY_USED': return 'bg-amber-500 text-white';
      case 'WRONG_EVENT': return 'bg-purple-600 text-white';
      case 'WRONG_TIME': return 'bg-orange-600 text-white';
      case 'INVALID': return 'bg-red-600 text-white';
      default: return 'bg-slate-950 text-slate-300';
    }
  };

  const getStatusIcon = (status: ValidationStatus) => {
    switch (status) {
      case 'VALID': return <CheckCircle2 className="w-24 h-24 mb-6" />;
      case 'ALREADY_USED': return <AlertTriangle className="w-24 h-24 mb-6" />;
      case 'WRONG_EVENT': return <AlertTriangle className="w-24 h-24 mb-6" />;
      case 'WRONG_TIME': return <AlertTriangle className="w-24 h-24 mb-6" />;
      case 'INVALID': return <XCircle className="w-24 h-24 mb-6" />;
      default: return null;
    }
  };

  // O overlay de resultado e renderizado como camada sobreposta (nao como
  // early-return) para manter o elemento <video> e a instancia do QrScanner
  // montados continuamente, permitindo retomar a leitura por camera sem
  // precisar reiniciar a permissao/stream a cada ingresso validado.
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 min-h-[calc(100vh-4rem)] bg-zinc-50 dark:bg-slate-950 relative">
      {result && (
        <div className={cn("fixed inset-0 z-50 flex flex-col items-center justify-center p-6 transition-colors duration-300", getStatusColor(result.status))}>
          <div className="flex flex-col items-center text-center max-w-2xl animate-in zoom-in duration-300">
            {getStatusIcon(result.status)}
            <h1 className="text-4xl md:text-6xl font-black mb-4 tracking-tight drop-shadow-lg">
              {result.message}
            </h1>
            {result.event_title && (
              <p className="text-xl opacity-90 font-medium mb-2">Evento: {result.event_title}</p>
            )}
            {result.ticket_id && (
              <p className="text-sm opacity-70 font-mono">ID: {result.ticket_id}</p>
            )}

            <button
              onClick={handleReset}
              className="mt-12 flex items-center gap-2 px-8 py-4 bg-black/20 hover:bg-black/30 rounded-full font-bold transition-all backdrop-blur-sm"
            >
              <RefreshCw className="w-5 h-5" />
              Nova Leitura
            </button>
          </div>
        </div>
      )}

      <div className="w-full max-w-md glass-card p-8 rounded-3xl text-center shadow-[0_0_50px_rgba(79,70,229,0.1)]">
        <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-6 border border-primary/30">
          <QrCode className="w-10 h-10 text-primary" />
        </div>
        <h2 className="text-3xl font-bold text-zinc-900 dark:text-white mb-2">Validação (Gatekeeper)</h2>
        <p className="text-zinc-600 dark:text-slate-400 mb-6">
          Selecione o evento, depois utilize a câmera, um leitor de código de
          barras ou digite o hash manualmente para validar a entrada.
        </p>

        <div className="mb-6 text-left">
          <label className="block text-xs font-semibold uppercase text-zinc-500 dark:text-slate-500 mb-2">
            Evento
          </label>
          <select
            value={selectedEventId}
            onChange={(e) => setSelectedEventId(e.target.value)}
            disabled={loadingEvents}
            className="w-full h-12 rounded-md bg-white dark:bg-slate-900 border border-zinc-300 dark:border-slate-700 text-zinc-900 dark:text-white px-3 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          >
            <option value="">
              {loadingEvents ? 'Carregando eventos...' : 'Selecione um evento'}
            </option>
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.title} — {new Date(event.event_date).toLocaleString('pt-BR')}
              </option>
            ))}
          </select>
          {!selectedEventId && !loadingEvents && (
            <p className="text-amber-400 text-xs mt-2">
              Selecione o evento para habilitar a validação.
            </p>
          )}
        </div>

        <div className="mb-6">
          <div
            id="reader"
            className={cn(
              "w-full rounded-2xl overflow-hidden border border-zinc-300 dark:border-slate-700 bg-black",
              !cameraActive && "hidden"
            )}
            style={{ minHeight: cameraActive ? '300px' : '0' }}
          ></div>

          <div className="flex gap-2 mt-3">
            <Button
              type="button"
              variant={cameraActive ? 'danger' : 'primary'}
              className="flex-1"
              disabled={!selectedEventId || loading}
              onClick={() => cameraActive ? stopCamera() : startCamera(facingMode)}
            >
              {cameraActive ? (
                <>
                  <CameraOff className="w-5 h-5 mr-2" />
                  Desativar Câmera
                </>
              ) : (
                <>
                  <Camera className="w-5 h-5 mr-2" />
                  Ativar Câmera
                </>
              )}
            </Button>

            {cameraActive && (
              <Button
                type="button"
                variant="outline"
                className="px-4 border-zinc-300 dark:border-slate-700 bg-white dark:bg-slate-900"
                onClick={toggleCamera}
                title="Girar Câmera"
              >
                <FlipHorizontal className="w-5 h-5 text-zinc-700 dark:text-zinc-300" />
              </Button>
            )}
          </div>

          {cameraError && (
            <p className="text-red-400 text-xs mt-2">{cameraError}</p>
          )}
        </div>

        <div className="relative py-2 flex items-center mb-4">
          <div className="flex-grow border-t border-zinc-300 dark:border-slate-800" />
          <span className="flex-shrink-0 mx-3 text-zinc-400 dark:text-slate-500 text-xs">
            OU DIGITE / USE LEITOR FÍSICO
          </span>
          <div className="flex-grow border-t border-zinc-300 dark:border-slate-800" />
        </div>

        <form onSubmit={handleFormSubmit} className="space-y-4">
          <Input
            ref={inputRef}
            placeholder="Aguardando leitura..."
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="h-16 text-center text-xl font-mono bg-white dark:bg-slate-900 border-zinc-300 dark:border-slate-700 text-zinc-900 dark:text-white"
            disabled={loading || !selectedEventId}
            autoFocus
          />
          {loading && <p className="text-primary animate-pulse text-sm">Validando ingresso...</p>}
        </form>
      </div>
    </div>
  );
};
