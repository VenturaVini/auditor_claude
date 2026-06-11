# Claude + Auditor GPT

Chat estilo Claude.ai onde o **Claude** responde (com streaming) e o **GPT** audita cada resposta — concordando com um badge verde ou apresentando correções/complementos. No **modo de rodadas (4x–10x)**, os dois debatem: a crítica do GPT volta ao Claude, que refina a resposta, até o veredito final.

## Como rodar

```sh
cp .env.example .env
# edite .env e preencha ANTHROPIC_API_KEY e OPENAI_API_KEY

docker compose up --build
```

Abra **http://localhost:8100** (a API fica em http://localhost:8101).

> As portas ficam na faixa 8100+ para não conflitar com outros projetos (3000/8000/5173 etc.).
> Para mudar: edite `WEB_PORT` / `API_PORT` / `VITE_API_URL` no `.env` e rode `docker compose build web && docker compose up -d`.

## Funcionalidades

- Chat com streaming em tempo real (SSE) — Claude (modelos listados dinamicamente da sua chave, selecionável)
- Auditoria automática de cada resposta — GPT (do 3.5 ao 5.x, selecionável)
- **Modo de rodadas (2x/4x/6x/8x/10x)**: debate Claude ↔ GPT com refinamento da resposta a cada ciclo; para antecipadamente se o auditor aprovar; timeline do debate no painel
- **⭐ Booster (opcional)**: os melhores modelos de cada provedor dão a opinião final sobre a resposta
- **Failover automático**: se a API de um provedor falhar, o app avisa qual foi o problema e o outro modelo assume a função
- **Execução de código**: quando o Claude gera código Python (ex.: para criar um XLSX), o botão "▶ Executar código" roda o script no container e entrega os arquivos para download — com auto-correção se o código falhar
- **Auditor que corrige**: se o Claude errar num arquivo, o GPT entrega o código corrigido no painel de auditoria, também executável com 1 clique
- Upload de arquivos: imagens (visão), PDF, TXT, MD, DOCX, XLSX, CSV, JSON — com validação de conteúdo real (magic bytes) contra arquivos disfarçados
- Download de respostas como TXT, MD ou PDF
- Histórico de conversas persistido em **Redis** (sidebar com confirmação ao apagar)
- **Métricas por resposta**: modelo real usado (reportado pela API), tokens in/out, tempo, velocidade (tok/s) e custo estimado
- Tema escuro, responsivo (auditor vira aba em telas < 768px)

## Variáveis de ambiente (`.env`)

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API da Anthropic |
| `OPENAI_API_KEY` | Chave da API da OpenAI |
| `MAX_FILE_SIZE_MB` | Limite de upload (padrão 10) |
| `UPLOAD_TTL_MINUTES` | TTL dos arquivos enviados (padrão 60) |
| `WEB_PORT` | Porta do frontend no host (padrão 8100) |
| `API_PORT` | Porta da API no host (padrão 8101) |
| `VITE_API_URL` | URL da API vista pelo browser (padrão http://localhost:8101) — **embutida no build**; mudou? rode `docker compose build web` |

## Desenvolvimento sem Docker

```sh
# Redis
docker run -p 6379:6379 redis:7-alpine

# Backend
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... REDIS_URL=redis://localhost:6379/0
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:3000
```

> Documentação completa de arquitetura, contratos de API e decisões técnicas: ver **CONTEXT.md**.
