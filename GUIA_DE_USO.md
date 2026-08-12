# Guia Definitivo de Uso e Operação da Plataforma Eventify

Este manual detalha o fluxo de ponta a ponta da plataforma Eventify, guiando o avaliador ou usuário em todas as jornadas: **Cliente** (navegação e compra), **Organizador** (publicação, gestão de sessões e analytics) e **Portaria** (validação segura de ingressos via câmera).

---

## 1. Jornada do Cliente (Usuário Comum)
Qualquer visitante pode explorar os filmes em cartaz e o catálogo livremente. Para adquirir ingressos, o usuário atua com o perfil padrão de `CLIENT`.

### Cadastro e Acesso Simplificado (Auto-Login)
A criação da conta é focada em conversão: o cliente informa apenas Nome, E-mail e Senha. Imediatamente após criar a conta, o sistema realiza o **Auto-Login** transparente, autenticando o usuário sem exigir que ele passe pela tela de login, devolvendo-o diretamente para o fluxo de compra. O Login tradicional (para retornos futuros) exige apenas E-mail e Senha.

### Acesso e Catálogo
Ao abrir a aplicação, o usuário visualiza um carrossel 3D imersivo (Coverflow) destacando os filmes em alta (*trending*) da semana consumidos via TMDb.
É possível navegar pelo grid de programação ou utilizar os filtros rápidos por gênero cinematográfico (Ação, Comédia, Drama, Ficção Científica, Terror, Romance, Animação).
A plataforma também conta com suporte nativo a Tema Claro e Tema Escuro (Dark Mode), que pode ser alternado a qualquer momento no cabeçalho.

### Seleção de Sessão
Ao clicar em um filme, o sistema exibe os detalhes completos (pôster, sinopse, classificação indicativa brasileira, diretor e elenco) e agrupa as sessões disponíveis por local (*Cinemark-style*), permitindo escolher a data e o horário desejados.

### Mapa de Assentos 3D
O usuário escolhe sua poltrona numerada interativa (ex: A1, A2...) em uma interface com perspectiva de sala de cinema.
* **Trava Anti-Double-Booking**: Ao selecionar os lugares, o sistema trava os assentos temporariamente por 15 minutos (status `PENDING`), exibindo um timer regressivo sincronizado com o back-end.

### Checkout e Pagamento
O resumo do pedido exibe os assentos e o valor total.
* **Flexibilidade de Pagamento**: O usuário pode optar por prosseguir para o ambiente oficial do Stripe Checkout ou utilizar o Modo Desenvolvedor (Simular Sucesso ou Simular Falha) para testes locais instantâneos sem dependência externa.

### Carteira "Meus Ingressos" e Reembolsos
Após a aprovação do pagamento, os ingressos são emitidos com um QR Code seguro (gerado via JWT criptografado) e um link de compartilhamento opaco exclusivo.
* **Auto-Gestão de Estorno**: O cliente possui total autonomia para gerenciar solicitações de reembolso (cancelamento) diretamente na aba do ingresso. 
* O botão de "Solicitar Reembolso" atua integrado à API do Stripe e respeita a **Janela de Segurança**: o cliente só consegue estornar o valor e devolver a cadeira para o mapa se faltarem **mais de 2 horas** para o início da sessão. Pedidos de última hora são bloqueados pelo sistema.

---

## 2. Jornada do Organizador
O organizador possui um painel administrativo exclusivo (`/organizer`) protegido por regras estritas de controle de acesso (RBAC).

### Publicação de Sessões
Na aba "Publicar Sessão", o organizador pesquisa um filme diretamente na base do TMDb. Ao selecionar o título, o sistema preenche automaticamente os metadados (sinopse, pôster, gênero e diretor).
O organizador define a data, a sala/local, a capacidade de assentos e o preço, gerando instantaneamente o mapa de poltronas da sessão.

### Gestão e Edição de Sessões
Na aba "Minhas Sessões", o organizador visualiza todos os filmes cadastrados e pode gerenciar horários específicos, editar detalhes da sessão ou excluí-la de forma segura (o back-end protege contra exclusão caso já existam ingressos vendidos, garantindo integridade financeira).

### Relatórios de Vendas e Analytics
Ao clicar no botão "Relatório" em uma sessão específica, o organizador acessa métricas em tempo real calculadas pelo back-end:
* Faturamento total em R$.
* Total de ingressos vendidos vs. assentos livres.
* Lista detalhada das poltronas ocupadas.

---

## 🛡️ 3. Jornada da Portaria (Gatekeeper)
A portaria (Gatekeeper) é o ponto focal de validação de entrada no evento.

### Acesso à Tela de Validação
Operadores autenticados com o perfil `GATEKEEPER` acessam a interface de leitura.

### Leitura via Câmera do Celular
O sistema aciona a câmera do dispositivo móvel através da engine `html5-qrcode`.
Inclui um botão prático para alternar entre a câmera frontal e traseira do celular, facilitando a leitura ágil do QR Code impresso no celular do cliente na catraca.

### Alternativa Manual (Fallback)
Caso a câmera tenha dificuldade de leitura por iluminação, o porteiro pode copiar e colar (ou digitar) o código alfanumérico do hash do ingresso no campo de input manual.

### Engine de Validação Criptográfica
O back-end decodifica o token JWT do QR Code, valida a assinatura criptográfica, cruza o ID do evento com a sessão da portaria e retorna instantaneamente um dos status visuais em tela cheia:
* **VÁLIDO (VALID)**: Acesso liberado à sala de cinema (o ingresso é marcado automaticamente como `USED` para impedir reutilizações).
* **JÁ UTILIZADO (ALREADY_USED)**: Alerta de tentativa de fraude por reutilização de bilhete.
* **EVENTO ERRADO (WRONG_EVENT)**: Ingresso pertencente a outra sessão ou data.
* **FORA DO HORÁRIO (WRONG_TIME)**: O usuário chegou muito cedo ou em um dia totalmente incorreto (a janela de validação aceita entrada entre 2h antes e 4h depois do início do filme).
* **INVÁLIDO (INVALID)**: Código corrompido, falso ou ingresso cancelado/reembolsado.
