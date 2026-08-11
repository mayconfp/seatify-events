# Eventify — Plataforma de Bilheteria e Gestão de Sessões de Cinema

Aplicação fullstack desenvolvida para o **Desafio Elite Dev 2026 (Verzel)**. O projeto simula um ecossistema completo de bilheteria de cinema, cobrindo desde a busca de filmes via API externa (TMDb) e cadastro de sessões pelo organizador, até a seleção de assentos em tempo real com mapas em perspectiva, checkout integrado ao Stripe, emissão de ingressos com QR Code criptografado (JWT) e validação segura na portaria (*Gatekeeper*).

---

## Decisões de Arquitetura e Engenharia de Software

### 1. Arquitetura Modular e Separação de Responsabilidades (Back-End)
O back-end foi construído em **Python com FastAPI**, adotando uma estrutura modular inspirada nas diretrizes oficiais para aplicações escaláveis.
- **Organização por Domínios (`src/module/`)**: O código é isolado em módulos independentes (`auth`, `events`, `tickets`, `checkout`, `gatekeeper`), garantindo baixo acoplamento e alta coesão.
- **Camada de Serviço Dedicada (`service.py`)**: Toda a regra de negócio reside exclusivamente nos serviços. Os *routers* atuam estritamente como *thin controllers* (recebem a requisição, validam via Pydantic e delegam ao serviço).
- **Injeção de Dependências Tipada (`deps.py`)**: O controle de acesso baseado em papéis (RBAC) para perfis (`CLIENT`, `ORGANIZER`, `GATEKEEPER`) é injetado de forma declarativa nas rotas.

### 2. Persistência Assíncrona e Concorrência Segura (SQLAlchemy 2.0 Async)
- **AsyncIO + AsyncPG**: Toda a camada de banco de dados opera de forma assíncrona para maximizar o throughput da API sob alta carga.
- **Prevenção de Venda Duplicada (*Double-Booking*)**: Nas rotas críticas de reserva e fechamento de carrinho, utilizamos bloqueios atômicos de linha no PostgreSQL (`SELECT ... FOR UPDATE`). Se múltiplos usuários tentarem comprar o mesmo assento no mesmo milissegundo, a concorrência é enfileirada de forma segura pelo banco.
- **Cache Local de Metadados do TMDb**: Para otimizar a performance e eliminar latências externas em tempo de execução, os metadados complementares do filme (elenco, diretor, nota e data de estreia) são buscados na API do TMDb e persistidos de forma estruturada (`JSONB`) diretamente na tabela `events` no momento da criação da sessão.

### 3. Resiliência e Idempotência em Pagamentos (Stripe & Webhooks)
- **Idempotência em Dupla Camada**: O processador de webhooks do Stripe protege contra entregas duplicadas (*at-least-once delivery*) utilizando um *fast-path* de leitura na tabela `processed_webhook_events` combinado com restrições de unicidade (`UNIQUE INDEX`) no PostgreSQL.
- **Tratamento de Edge Cases**: Pagamentos efetuados após a expiração do prazo de 15 minutos de reserva são interceptados graciosamente, registrando logs de auditoria e respondendo com HTTP 200 ao Stripe para cessar retentativas em loop, sem quebrar o servidor.

---

## Evolução do Produto: Do Escopo Geral ao Nicho de Cinema

Iniciamos o desenvolvimento com uma estrutura genérica de gestão de eventos (nos moldes de plataformas como a *Sympla*). No entanto, avaliando as sugestões de referência do edital (*Ingresso.com*), reposicionamos estrategicamente o produto para o nicho especializado de **Cinema**:
- **Foco em Poltronas Marcadas (`SEATED`)**: Substituição de modelos genéricos de pista por mapas de sala interativos e numerados em perspectiva.
- **Integração Enriquecida com TMDb**: Implementação de carrossel de filmes em alta (*trending*), filtros dinâmicos por gênero cinematográfico, badges de classificação indicativa (idade) e exibição detalhada de elenco e equipe.

---

## Segurança e Regras de Negócio

- **Proteção contra IDOR**: As rotas de gerenciamento e relatórios do organizador validam rigorosamente a propriedade do recurso (`Event.organizer_id == current_user.id`), impedindo acessos cruzados.
- **QR Codes Infalsificáveis**: Os ingressos geram um token JWT assinado digitalmente (`create_qr_token`) contendo apenas metadados opacos (`ticket_id` e `event_id`). 
- **Validação Segura na Portaria (*Gatekeeper*)**: O aplicativo da portaria decodifica o token, valida a assinatura criptográfica, rejeita tokens de eventos errados (`WRONG_EVENT`) e barra reutilizações (`ALREADY_USED`) através de travas transacionais.
- **Rate Limiting**: Proteção contra ataques de negação de serviço (DoS) e scraping nas rotas públicas e de autenticação utilizando o middleware `SlowAPI`.

---

## Tecnologias Utilizadas

- **Front-End**: React 18, Vite, TypeScript, Tailwind CSS, Zustand (estado global e persistência), React Router DOM, Lucide Icons, Sonner (notificações), Html5-qrcode (leitura de câmera).
- **Back-End**: Python 3.10+, FastAPI, SQLAlchemy (Async/AsyncPG), Pydantic v2, Alembic (migrações de banco), SlowAPI, PyJWT, Cryptography (Fernet).
- **Banco de Dados**: PostgreSQL.

---

## Processo de Desenvolvimento e Uso de Inteligência Artificial

Em atendimento direto à diretriz do edital sobre o uso transparente de Inteligência Artificial:
- **Auxílio da IA**: A ferramenta foi utilizada como um par de programação (*co-pilot*) para agilizar a criação de estruturas repetitivas de código (como schemas Pydantic, rotas auxiliares em routers e estruturação inicial de componentes de interface).
- **Autoria Humana**: As decisões críticas de engenharia foram inteiramente conduzidas pelo desenvolvedor:
  - Concepção do modelo de concorrência atômica com `SELECT ... FOR UPDATE` para zerar falhas de *double-booking*.
  - Tratamento de resiliência e idempotência em dupla camada para webhooks do Stripe.
  - Arquitetura de segurança para validação de ingressos na portaria via tokens JWT criptografados.

---

## Referências de Mercado
- **Ingresso.com**: Inspiração para a experiência de escolha de poltronas de cinema, paginação de horários por sala e visualização de cartazes.
- **Sympla**: Referência para o painel administrativo do organizador e relatórios analíticos de ocupação.

---

## Padrões e Referências Técnicas (Open-Source Standards)

A arquitetura e as escolhas de engenharia do Eventify baseiam-se inteiramente em especificações públicas, documentações oficiais e padrões abertos da indústria:
- **Arquitetura Web**: [FastAPI Bigger Applications Guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- **Persistência Assíncrona**: [SQLAlchemy 2.0 AsyncIO ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- **Segurança de Senhas**: [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) & [NIST SP 800-132](https://csrc.nist.gov/publications/detail/sp/800-132/final)
- **Criptografia de Tokens**: [IETF RFC 7519 (JWT)](https://datatracker.ietf.org/doc/html/rfc7519) & [Cryptography Fernet](https://cryptography.io/en/latest/fernet/)

---

## Instruções de Instalação e Execução

### Pré-requisitos
- Python 3.10+ (Recomendado 3.13+) e gerenciador de pacotes `uv` instalados.
- Node.js 22+ e npm 10+ instalados.
- Docker e Docker Compose instalados (para subir o banco de dados via container).

### 1. Configurando e Rodando o Back-End
1. Pelo terminal, entre na pasta do servidor:
   ```bash
   cd backend
   ```
2. Suba o container do banco de dados PostgreSQL utilizando o Docker:
   ```bash
   docker compose up -d
   ```
3. Sincronize as dependências e crie o ambiente virtual utilizando o `uv`:
   ```bash
   uv sync
   ```
4. Execute as migrações do banco de dados (Alembic) para criar as tabelas:
   ```bash
   uv run alembic upgrade head
   ```
5. Popule o banco de dados com dados iniciais (Seed) para testar com as credenciais padrão:
   ```bash
   uv run python run_seed.py
   ```
6. Inicie o servidor FastAPI:
   ```bash
   uv run uvicorn src.main:app --reload
   ```

### 2. Configurando e Rodando o Front-End
1. Pelo terminal, abra uma nova aba e entre na pasta do frontend:
   ```bash
   cd frontend
   ```
2. Instale as dependências ignorando scripts opcionais (recomendado para maior compatibilidade):
   ```bash
   npm ci --ignore-scripts
   ```
3. Inicie o servidor de desenvolvimento do Vite:
   ```bash
   npm run dev
   ```
4. Acesse o Front-End pelo navegador através das URLs geradas no terminal (ex: `https://localhost:5173/`).
