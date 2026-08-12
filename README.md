# Eventify — Plataforma de Bilheteria e Gestão de Sessões de Cinema

Aplicação fullstack desenvolvida para o **Desafio Elite Dev 2026 (Verzel)**. O projeto simula um ecossistema completo de bilheteria de cinema, cobrindo desde a busca de filmes via API externa (TMDb) e cadastro de sessões pelo organizador, até a seleção de assentos em tempo real com mapas em perspectiva, checkout integrado ao Stripe, emissão de ingressos com QR Code criptografado (JWT) e validação segura na portaria (*Gatekeeper*).

> 📖 **[Clique aqui para ler o Guia de Uso Completo (Manual da Plataforma)](./GUIA_DE_USO.md)**

> 🚀 **Acesso ao Projeto Online:** [https://seatify-events.vercel.app/](https://seatify-events.vercel.app/)
> *(Front-End hospedado na Vercel, Back-End e Banco de Dados hospedados no Render)*

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
- **Limpeza Assíncrona em Memória (Background Task)**: Liberação assíncrona de carrinhos abandonados através de task nativa (`asyncio.sleep`) vinculada ao ciclo de vida da aplicação, evitando dependências pesadas de infraestrutura como Redis ou Celery para rotinas periódicas simples.
- **Integração e Cache do TMDb**: Para otimizar a performance e contornar limites de taxa (Rate Limit) da API externa em uma infraestrutura enxuta, os metadados de filmes e a lista de "Filmes em Alta" (Trending) são protegidos. O Trending utiliza um Cache em Memória nativo (variável global) com TTL de 6 horas, para consumir pouca memória RAM, enquanto os metadados das sessões criadas são persistidos de forma estruturada (`JSONB`) diretamente na tabela `events`.

### 3. Resiliência e Idempotência em Pagamentos (Stripe & Webhooks)
- **Idempotência em Dupla Camada**: O processador de webhooks do Stripe protege contra entregas duplicadas (*at-least-once delivery*) utilizando leitura prévia combinada com restrições de unicidade (`UNIQUE INDEX`) no PostgreSQL. Em caso de colisão simultânea de requisições concorrentes idênticas, a delegação para o banco garante que o erro de integridade (`IntegrityError`) atue como trava de segurança definitiva.
- **Tratamento de Edge Cases**: Pagamentos efetuados após a expiração do prazo de 15 minutos de reserva são interceptados graciosamente, registrando logs de auditoria e respondendo com HTTP 200 ao Stripe para cessar retentativas em loop, sem quebrar o servidor.

### 4. Ciclo de Vida do Assento e Resgate de Contexto (UX)
Anteriormente, ao abandonar a tela de pagamento (Stripe Checkout), o usuário perdia totalmente o contexto da compra e as cadeiras ficavam "fantasmas". Evoluímos esse fluxo para um modelo robusto de retenção e edição:
- **Reserva Temporária (`PENDING`)**: A cadeira é reservada em nome do usuário por 15 minutos, protegida por lock de banco.
- **Interatividade no Front-End**: Ao voltar no mapa da sessão, o usuário visualiza seus próprios assentos "Pendentes" destacados na cor amarela. Ele possui liberdade total para clicar nos assentos pendentes e **retirá-los** do carrinho ou adicionar novos antes de prosseguir novamente para o pagamento, sem precisar iniciar o fluxo do zero.
- **Liberação Automática**: Sem intervenção humana, assentos `PENDING` não pagos no prazo voltam silenciosamente para `AVAILABLE`, impedindo assentos bloqueados para sempre.

### 5. Estorno Seguro e Automatizado (Regra de 2 Horas)
A arquitetura de reembolsos segue protocolos restritivos para blindar tanto o produtor do evento (contra prejuízos de assentos vazios) quanto a segurança financeira da API:
- **Barreira Temporal Dupla**: No Front-End (botão "Solicitar Reembolso") e no Back-End (`POST /tickets/{id}/refund`), o estorno só é permitido se o cancelamento ocorrer até **2 horas antes** do início do filme. Pedidos tardios são bloqueados com erro `400 Bad Request`.
- **Desacoplamento Assíncrono**: Ao solicitar o estorno, a API comunica-se com a SDK do Stripe (`stripe.Refund.create`), mas **NÃO altera** o banco de dados no momento do clique. Isso evita que falhas de rede no gateway de pagamento deixem o ingresso cancelado, mas o dinheiro retido.
- **Reversão Orientada a Webhook**: Apenas quando a operadora de cartão confirma a devolução do dinheiro, o Stripe envia um webhook (`charge.refunded`). Nosso servidor captura o evento, processa-o via idempotência, usa `SELECT FOR UPDATE` para travar o registro, marca o `Ticket` como `CANCELLED` e devolve a cadeira para o mapa como `AVAILABLE`.
- **Anti-Fraude na Portaria**: Se um usuário agir de má fé, realizar o estorno e levar um "print" do QR Code para o cinema, o tablet do porteiro fará a interceptação com a tela `CANCELLED` e registrará um alerta `WARNING` no log do servidor.

---

## Evolução do Produto: Do Escopo Geral ao Nicho de Cinema

Iniciamos o desenvolvimento com uma estrutura genérica de gestão de eventos (nos moldes de plataformas como a *Sympla*). No entanto, avaliando as sugestões de referência do edital (*Ingresso.com*), reposicionamos estrategicamente o produto para o nicho especializado de **Cinema**:
- **Foco em Poltronas Marcadas (`SEATED`)**: Substituição de modelos genéricos de pista por mapas de sala interativos e numerados em perspectiva.
- **Integração Enriquecida com TMDb**: Implementação de carrossel de filmes em alta (*trending*), filtros dinâmicos por gênero cinematográfico, badges de classificação indicativa (idade) e exibição detalhada de elenco e equipe.

---

## Segurança e Regras de Negócio

- **Ocultação Automática de Sessões Expiradas (Catálogo Dinâmico)**: A listagem pública de eventos atua de forma estritamente temporal. No Back-End (`GET /events`), a query no PostgreSQL possui um filtro nativo (`Event.event_date >= aware_utcnow()`). Isso garante que, se uma sessão de cinema começar às 14h00, às 14h01 ela desaparece imediatamente do catálogo para os usuários. Isso elimina o risco de clientes comprarem ingressos para sessões que já começaram ou que já acabaram.
- **Proteção contra IDOR**: As rotas de gerenciamento e relatórios do organizador validam rigorosamente a propriedade do recurso (`Event.organizer_id == current_user.id`), impedindo acessos cruzados.
- **QR Codes Infalsificáveis**: Os ingressos geram um token JWT assinado digitalmente (`create_qr_token`) contendo apenas metadados opacos (`ticket_id` e `event_id`). 
- **Validação Segura na Portaria (*Gatekeeper*)**: O aplicativo da portaria decodifica o token, valida a assinatura criptográfica, rejeita tokens de eventos errados (`WRONG_EVENT`) e barra reutilizações (`ALREADY_USED`) através de travas transacionais.
  - *Evolução de Regra de Negócio (Janela de Tempo)*: Inicialmente, o sistema permitia a validação baseada apenas na correspondência de IDs. Evoluímos o modelo para implementar uma **Janela de Tempo Estrita** (`WRONG_TIME`). Agora, o ingresso só é considerado válido se o check-in ocorrer entre **2 horas antes e 4 horas depois** do horário exato da sessão. Isso blinda o cinema contra erros humanos do porteiro (ao selecionar o evento da data errada no aplicativo) e fraudes de clientes comparecendo em dias futuros/passados.
- **Rate Limiting**: Proteção contra ataques de negação de serviço (DoS) e scraping nas rotas públicas e de autenticação utilizando o middleware `SlowAPI`.
- **Prevenção de Supply Chain Attacks (Front-End)**: O ambiente de desenvolvimento isola dependências maliciosas forçando o uso de instalação limpa travada no Lockfile (`npm ci`) associado ao bloqueio de injeção de scripts arbitrários (`--ignore-scripts`).

---

## Tecnologias Utilizadas

- **Front-End**: React 18, Vite, TypeScript, Tailwind CSS, Zustand (estado global com persistência no `localStorage`), React Router DOM, Lucide Icons, Sonner (notificações), Axios (interceptadores globais blindados e sensíveis ao contexto), Html5-qrcode (leitura de câmera em stream continuo).
- **Back-End**: Python 3.10+, FastAPI, SQLAlchemy (Async/AsyncPG), Pydantic v2, Alembic (migrações de banco), SlowAPI, PyJWT, Cryptography (Fernet).
- **Banco de Dados**: PostgreSQL.

---

## Processo de Desenvolvimento e Uso de Inteligência Artificial

Em atendimento direto à diretriz do edital sobre o uso transparente de Inteligência Artificial:
- **Auxílio da IA**: A ferramenta foi utilizada como um par de programação (*co-pilot e Antigravity*) para agilizar a criação de estruturas repetitivas de código (como schemas Pydantic, rotas auxiliares em routers e estruturação inicial de componentes de interface).
- **Autoria Humana**: As decisões críticas de engenharia foram inteiramente conduzidas pelo desenvolvedor:
  - Concepção do modelo de concorrência atômica com `SELECT ... FOR UPDATE` para zerar falhas de *double-booking*.
  - Tratamento de resiliência e idempotência em dupla camada para webhooks do Stripe.
  - Arquitetura de segurança para validação de ingressos na portaria via tokens JWT criptografados.
  - **Auditoria de Regras de Negócio**: Identificação proativa da falha lógica na portaria (que inicialmente validava ingressos ignorando a distância das datas) e direcionamento da IA para estruturar e codificar a barreira temporal estrita da Janela de Tempo (`WRONG_TIME`).

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

### 1. Configurando e Rodando o Banco de Dados e o Back-End
1. Na **raiz do projeto**, crie o arquivo de variáveis de ambiente principal:
   - Duplique o arquivo `.env.example` (que está na raiz) e renomeie para `.env`.
   - Preencha as chaves da API do TMDb e as chaves JWT/Fernet (há instruções no arquivo).
2. Ainda na **raiz do projeto**, suba o container do PostgreSQL utilizando o Docker:
   ```bash
   docker compose up -d
   ```
3. Pelo terminal, entre na pasta do servidor (back-end):
   ```bash
   cd backend
   ```
4. Sincronize as dependências e crie o ambiente virtual utilizando o `uv`:
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
2. Crie o arquivo de variáveis de ambiente:
   - Duplique o arquivo `.env.example` e renomeie para `.env`.
3. Instale as dependências de forma segura, bloqueando scripts maliciosos de terceiros:
   ```bash
   npm ci --ignore-scripts ou npm install
   ```
3. Inicie o servidor de desenvolvimento do Vite:
   ```bash
   npm run dev
   ```
4. Acesse o Front-End pelo navegador através das URLs geradas no terminal (ex: `https://localhost:5173/`).
