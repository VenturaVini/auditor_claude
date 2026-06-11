# CONTEXT.md — Contexto do Projeto (para continuar em outra sessão de Claude)

> **Propósito deste arquivo:** se esta sessão for perdida, qualquer outra instância de Claude
> deve conseguir continuar o trabalho lendo APENAS este arquivo. Mantenha-o atualizado.

---

## O que é o projeto

App web estilo Claude.ai com **duplo modelo**:
1. Usuário conversa com **Claude Haiku** (`claude-haiku-4-5`) — resposta em streaming SSE no painel principal (esquerda).
2. Após o Claude terminar, **GPT-4o-mini** audita a resposta (painel direita):
   - Concordou → badge verde "✓ Concordou com o Claude" + comentário breve.
   - Discordou/complementou → resposta completa do GPT em markdown.

Suporta upload de arquivos (imagens, PDF, TXT, MD, DOCX, XLSX), download da resposta (TXT/MD/PDF), tema escuro, responsivo (auditor vira aba em < 768px). **Sem auth.**

> **MUDANÇA DE SPEC (pedida pelo usuário durante o build):** a spec original dizia "sem banco / histórico só no browser", mas o usuário pediu persistência do histórico — escolhemos **Redis** (serviço no compose, AOF ligado). Há sidebar estilo Claude.ai para listar/retomar/apagar conversas.

## Stack

- **Backend:** FastAPI (Python 3.12), SDK `anthropic` (AsyncAnthropic) + SDK `openai` (AsyncOpenAI), `redis.asyncio`
- **Frontend:** React 18 + Vite, `react-markdown` + `remark-gfm`, `react-syntax-highlighter`, build servido por Nginx
- **Persistência:** Redis 7 (histórico de conversas) + `/tmp/uploads` em disco (arquivos com TTL)
- **Deploy:** `docker compose up` → web em **http://localhost:8100**, api em **http://localhost:8101**, redis interno (sem porta no host)
  - Portas configuráveis via `.env`: `WEB_PORT` (8100), `API_PORT` (8101), `VITE_API_URL` (precisa apontar p/ API_PORT; embutida no build → `docker compose build web` ao mudar). Faixa 8100+ escolhida a pedido do usuário p/ não conflitar com outros projetos.

## Status do build (atualizar conforme avança)

- [x] docker-compose.yml (api + web + redis), .env.example
- [x] backend/ completo (Dockerfile, requirements, main.py, routers/, services/ incl. storage.py Redis)
- [x] frontend: package.json, vite.config.js, Dockerfile, nginx.conf, index.html
- [x] frontend/src: main.jsx, index.css, App.jsx
- [x] frontend/src/components: ChatPanel, AuditorPanel, MessageBubble, FileUpload, DownloadMenu, Sidebar
- [x] frontend/src/services/api.js (upload, streamChat SSE, download, conversas)
- [x] README.md
- [x] Sintaxe Python validada (py_compile)
- [x] **Testado de ponta a ponta com `docker compose up` e chaves reais (2026-06-10):**
  - build das 3 imagens OK; health, frontend e bundle com URL correta
  - upload dos 6 tipos (txt/md/png/pdf/docx/xlsx) com extração correta; erros 415/413/400 OK
  - download txt/md/pdf (PDF válido) + formato inválido 400
  - SSE completo: meta → chunks → [AUDIT] → [DONE]; caminho de erro (401) limpo
  - chat real com streaming do Claude + auditoria do GPT funcionando
  - visão: imagem vermelha 64x64 → Claude respondeu "Vermelho"
  - Redis: criar/listar/GET/DELETE, turno persistido (msgs+audits), multi-turno com memória
  - portas novas 8100/8101 ativas e configuráveis
- [x] **Rodada de portabilidade (10/06/2026, tarde):**
  - simulação de máquina nova: `down -v --rmi local` + `up --build -d` → 3 containers healthy num comando
  - healthchecks nos 3 serviços + `restart: unless-stopped` + `depends_on` com condition
  - ATENÇÃO: healthcheck do web usa `http://127.0.0.1:80/` (NÃO `localhost` — resolve p/ ::1 e o nginx só escuta IPv4)
  - `package-lock.json` gerado (via container node) + Dockerfile mudado p/ `npm ci` → build reproduzível
  - fixes: guard 400 p/ messages vazio em chat.py; App.jsx marca auditoria como ERROR se o stream falhar antes dela
  - uploads movidos p/ volume nomeado `uploads-data` (nada toca o host)
  - persistência confirmada: conversa sobrevive a `docker compose restart`
  - PDD.md criado + PDD.pdf gerado pelo PRÓPRIO endpoint /api/download/pdf (3 páginas, dogfooding)
- [x] **Rodada de features (10/06/2026, noite) — tudo testado com chaves reais:**
  - **Execução de código + artefatos:** Claude gera código Python p/ arquivos (xlsx etc.); botão "▶ Executar código" no frontend roda via POST /api/execute (subprocess isolado, timeout 30s, python -I, tempdir); arquivos gerados viram artefatos baixáveis em GET /api/files/{id}. Libs no container: openpyxl, python-docx, reportlab, pdfplumber, pandas, matplotlib. System prompt do Claude instrui a escrever código autossuficiente e avisar do botão.
  - **Troca de modelos:** GET /api/models lista opções; selects nos headers dos dois painéis (persistem em localStorage); ChatRequest aceita main_model/auditor_model. Claude: haiku-4-5 (default), sonnet-4-6, opus-4-8. OpenAI: gpt-4o-mini (default), gpt-4o, gpt-4.1-mini.
  - **Failover bidirecional:** Anthropic falha → evento SSE "failover" (provider+mensagem) + GPT assume a resposta em streaming (imagens são descartadas na conversão; texto de docs vai junto) + banner vermelho na mensagem. OpenAI falha na auditoria → Claude audita (audit_with_claude) e o card mostra "auditado por: ... (failover)". Ambas falham → evento "error" com as duas mensagens. Campo "via" no JSON da auditoria.
  - **Confirmação ao apagar conversa:** clicou 🗑 → item vira "Apagar esta conversa? Sim/Não" inline (sem window.confirm). Ícone agora sempre visível (opacity 0.55).
  - Testes: /api/models OK; fluxo normal com via OK; failover Anthropic→GPT OK (forçado com modelo inexistente); failover auditoria OpenAI→Claude OK; sonnet como principal OK; falha dupla com erro claro OK; execute: xlsx real validado, pandas/matplotlib png, SyntaxError, timeout 30s, 400 vazio, 404 artefato.
- [x] **Rodada de refinamentos (10/06/2026, madrugada) — testes T1-T10 todos PASS:**
  - **Modelos dinâmicos:** /api/models agora consulta as Models APIs dos provedores (lista o que a CHAVE tem acesso; fallback p/ lista fixa). Chave do usuário tem GPT-5/5.1/5.2/5.3/5.4 e claude-fable-5/opus-4-8 etc. Filtro OpenAI por prefixo (gpt-, o1/o3/o4...) excluindo tts/embedding/audio/realtime etc.
  - **Auditor com contexto de arquivos:** audit_question agora inclui o conteúdo extraído dos docs (antes auditava às cegas e chutava). Auditores também instruídos: (a) código Python executável É entrega válida de arquivo (botão Executar) — matou o falso REVIEW; (b) não penalizar afirmações sobre imagens que só o modelo principal vê.
  - **Cards visuais (FileCard.jsx):** estilo Claude.ai — ícone colorido por extensão, nome, tamanho; usados em: previews do input, anexos da mensagem, artefatos p/ download (com hover verde + ⬇). ImageCard com thumbnail arredondado e ✕ flutuante.
  - **System prompt Claude:** seção ARQUIVOS ANEXADOS (menções @nome funcionam; identificar cada arquivo pelo nome).
  - **Layout:** scrollbars finas customizadas (webkit + Firefox), scroll suave, input radius 18 + sombra, ✕ de apagar aparece no hover da LINHA inteira (com confirmação Sim/Não inline mantida).
  - **Testes (T1-T10):** pedido de PDF via chat real → código → execução → %PDF válido; XLSX idem (auditor agora dá OK); imagem real 64x64 + 2 docs numa msg com @menções (cor + fatos corretos; OBS: imagem de 1px o Claude não "vê" — usar imagens reais nos testes); gpt-5-mini como auditor OK (json_object funciona); failover com gpt-5-mini assumindo OK; arquivo com acentos/espaços no nome OK; 2 chats concorrentes OK; multi-turno lembra contexto OK.
  - Conversas sintéticas de teste removidas do Redis ao final.
- [x] **Rodada auditor-corretor + segurança (10/06/2026) — tudo testado:**
  - **Auditor entrega arquivos:** prompts dos 2 auditores instruem: se a resposta auditada tiver código com erro (dados/bug), o "response" deve trazer o código Python COMPLETO CORRIGIDO em bloco ```python. AuditorPanel agora também tem CodeRunner → botão "Executar código" no painel do GPT entrega os arquivos corrigidos.
  - **Auto-correção na execução:** POST /api/execute com auto_fix=true (default): se o código falhar, chama claude.fix_code(código, stderr) e re-executa 1x; resposta ganha auto_fixed=true e a UI mostra "⚙️ corrigido automaticamente". (Caso real que motivou: o gpt-4o-mini corrigiu a tabuada mas escreveu bb.save em vez de wb.save.)
  - **Segurança de upload (magic bytes):** _validate_content() em file_processor confere assinatura real do conteúdo vs extensão — PNG/JPG/GIF/WEBP/PDF/DOCX/XLSX (zip PK) — e rejeita binário com NUL disfarçado de texto. Whitelist ampliada com .csv e .json (texto). Testes: exe→.png 415, binário→.txt 415, lixo→.docx 415, pdf falso 415, csv/json/png legítimos OK.
  - **SIMULAÇÕES de erro do Claude (pedido do usuário):** SIM1 xlsx com tabuada errada (7x8=58) → auditor REVIEW + código corrigido (56/63) → executado → arquivo certo validado via openpyxl. SIM2 pdf com fatos errados (ebulição 50°C) → REVIEW + código corrigido (100°C/0°C) → executado → %PDF válido.
  - **Layout (pedido do usuário, ref. claude.ai):** scrollbars finas customizadas, scroll suave, input radius 18+sombra, ✕ vermelho aparece no hover da linha inteira da conversa (confirmação Sim/Não inline mantida; 🗑 revertido p/ ✕ a pedido).
- [x] **Curadoria de modelos (10/06/2026):**
  - Lista OpenAI enxugada de ~50 p/ ~27: filtra snapshots datados (regex -YYYY-MM-DD e -NNNN), 'codex' e 'chat-latest' — fica 1 por família, do gpt-3.5-turbo ao gpt-5.5-pro + o1/o3/o4. Claude mantém os 11 (fable-5 → sonnet-4 antigo).
  - audit_response: se o modelo não suporta response_format json_object (gpt-4/3.5 antigos), refaz sem o parâmetro e parseia manualmente (strip de cercas). Testado: gpt-4 e gpt-3.5-turbo auditando OK sem failover.
- [x] **AUTO-EXECUÇÃO de arquivos (10/06/2026) — feedback do usuário ("só quero o arquivo, não o código"):**
  - Fluxo novo: usuário pede arquivo → Claude gera código com 1ª linha `# gerar-arquivo` → backend EXECUTA AUTOMATICAMENTE (chat.py, após resposta completa, antes da auditoria) → evento SSE `{"type":"artifacts","files":[...],"ok","auto_fixed","error"}` → frontend mostra os CARDS dos arquivos prontos; o código fica RECOLHIDO num <details> "Ver código usado para gerar o arquivo".
  - Decisão de execução (services/executor.py::should_auto_run): blocos com marcador rodam sempre; sem marcador, roda se a pergunta tem keyword de arquivo (xlsx/pdf/planilha/etc.) E o usuário NÃO pediu código explicitamente. Pedido explícito de código → código aberto, sem execução.
  - executor.py centraliza run_code/run_with_autofix (usados pelo chat e pelo endpoint /api/execute, que ficou como fallback + painel do auditor).
  - Artifacts persistidos no Redis (campo "artifacts" na msg do assistant) — recarregar a conversa mostra os cards.
  - Prompts atualizados: Claude e GPT-failover usam o marcador e NÃO mencionam botão/execução (matou o 'sempre clicar em executar' que o usuário reclamou); auditores sabem que a execução é automática.
  - Testes (todos PASS): pdf de acordes de guitarra (caso do usuário) → arquivo direto, sem menção a botão; xlsx+pdf JUNTOS no mesmo pedido → 2 arquivos; pedido explícito de código → código aberto sem auto-exec; pergunta normal → nada; conversa recarregada mantém cards + %PDF válido; failover (GPT) também gera arquivo (csv); 0 exceções nos logs.
- [x] **Layout dos PDFs (11/06/2026) — usuário recebeu PDF com texto cortado e quadrados ■:**
  - Causas: (1) modelo usava canvas.drawString (não quebra linha → corta na borda); (2) emojis nas células (fontes padrão do PDF não têm os glifos → tofu ■); (3) tabelas cortadas na quebra de página.
  - **Guia de qualidade de documentos nos prompts** (claude SYSTEM_PROMPT + gpt MAIN_SYSTEM): PDFs SEMPRE com reportlab.platypus (SimpleDocTemplate/Paragraph/Table/Spacer/KeepTogether, A4, margens 2cm), NUNCA drawString p/ texto corrido; tabelas com cabeçalho escuro+GRID+zebra+repeatRows=1; seções em KeepTogether; PROIBIDO emoji em PDF (usar cor/negrito). Guia também cobre DOCX (add_heading, estilos de tabela), XLSX (PatternFill, larguras, number_format, freeze_panes) e gráficos matplotlib — "documentos bonitos e estruturados" nos DOIS modelos (pedido do usuário).
  - **_markdown_to_pdf reescrito** (download.py): tabelas markdown → platypus Table (cabeçalho repetido, zebra, KeepTogether se ≤12 linhas), blocos de código com textwrap a 95 colunas (linha longa NÃO corta mais), listas ordenadas, blockquote, título destacado, rodapé "Página N", e _sanitize() que mapeia símbolos comuns (✓→v etc.) e remove chars fora do cp1252 (emoji não vira ■).
  - Testes PASS: chat real "pdf bonito de acordes" → código com platypus+KeepTogether, 0 emoji, 2 páginas, texto íntegro via pdfplumber; conversor download → tabela extraível como tabela, linha de código de 200 colunas completa (quebrada), rodapé presente, 0 tofu; PDD.pdf regenerado (5 págs, tabelas de verdade agora).
- [x] **Verificação de modelos + bateria multi-modelo (11/06/2026, pedido "o sonnet é o sonnet msm?"):**
  - **Evento SSE `model_info`** {requested, used}: stream_claude captura via get_final_message().model (+tokens) e stream_gpt_answer via chunk.model — o modelo REAL reportado pela API no response. Frontend mostra badge ao lado de "Claude" na mensagem (campo message.model_used).
  - PROVA: haiku/sonnet-4-6/opus-4-8/opus-4-6 → API reportou exatamente o pedido (CONFERE em todos). Failover GPT: alias resolve p/ snapshot datado (gpt-4o-mini→gpt-4o-mini-2024-07-18, gpt-5-mini→gpt-5-mini-2025-08-07) — comportamento esperado da OpenAI.
  - Bateria multi-modelo de documentos (tudo PASS): SONNET pdf estruturado (platypus+KeepTogether, 0 emoji, tabela real extraída, 0 ■); OPUS-4-8 xlsx (título linha 1 + cabeçalho com fill #1F4788 linha 2, freeze A3, FÓRMULA na coluna diferença); HAIKU docx+png JUNTOS (ata + gráfico) com auditoria gpt-5-mini OK. 0 exceções nos logs.
- [x] **Métricas por resposta + re-teste de PC novo (11/06/2026):**
  - **services/pricing.py**: tabela USD/1M tokens (Claude: haiku 1/5, sonnet 3/15, opus 5/25, fable 10/50; OpenAI: famílias com preço público estável; gpt-5+ fora do mapa → custo None, UI mostra só tokens). Match por prefixo mais longo (cobre snapshots datados).
  - **Evento `model_info` virou métricas completas**: {requested, used, input_tokens, output_tokens, duration_s, ttft_s, tokens_per_s, cost_usd}. Claude: get_final_message().usage; GPT streaming: stream_options include_usage. Timing medido no chat.py (monotonic; reset no failover).
  - **Auditoria com usage**: audit_response (OpenAI) e audit_with_claude retornam usage {input,output} → card do auditor mostra "auditado por X · N in / M out tokens".
  - **UI**: linha de métricas sob cada resposta (⇅ tokens · ⏱ tempo · ⚡ tok/s · ~$custo) + badge do modelo real. Persistidas no Redis (campo metrics na msg do assistant) — recarregar conversa mantém.
  - **Portabilidade re-validada (pedido "como se fosse um pc novo")**: `docker compose config` válido; ZERO bind mounts de host (só volumes nomeados); env_file agora OPCIONAL (path+required:false — sem .env os containers sobem e o erro de chave aparece limpo no chat); wipe total (down -v --rmi local) + `docker compose up --build -d` → 3 containers healthy; smoke test completo com métricas reais (haiku: 113 tokens out, 1.94s, 58 tok/s, ~$0.0016; auditor 469/16 tokens) e persistência confirmada.
  - ATENÇÃO portabilidade: `env_file` com `required:false` exige Docker Compose ≥ 2.24 (lançado 2024) — em máquinas com compose muito antigo, criar o .env resolve.
- [x] **Cópia de segurança (11/06/2026):** projeto copiado p/ `/Users/viniciusventura/Projetos/projeto_base` (rsync, 42 arquivos, com .env) com portas 8200/8201 p/ rodar em paralelo. O usuário vai subir p/ git. NÃO mexer no projeto_base — as features novas vão NESTE projeto (decisão do usuário).
- [x] **MODO DE RODADAS 2x/4x/6x/8x/10x + BOOSTER (11/06/2026) — debate Claude ↔ GPT, tudo testado:**
  - **Conceito:** 2x = fluxo atual (Claude→GPT julga). 4x+ = a crítica do GPT volta ao Claude (refine_claude em claude.py, prompt manda julgar a crítica com rigor — ela PODE estar errada — e reescrever a resposta completa), GPT julga de novo; sempre termina no GPT. **Parada antecipada** se o GPT der OK numa rodada intermediária (audit.early_stop=true).
  - **Request:** ChatRequest.rounds (clamp par 2..10) e ChatRequest.booster (bool).
  - **SSE novos:** `debate {round,total,audit}` (crítica intermediária), `revision_start {round,total}` (frontend ZERA o conteúdo da msg e re-streama a versão refinada), `booster {claude:{...via}, gpt:{...via}}`. [AUDIT] final ganha round/total/early_stop. model_info ganha rounds_executed/rounds_total e SOMA tokens/custo de todas as rodadas Claude.
  - **Artifacts**: rodam 1x sobre a resposta FINAL (movido p/ depois do loop). Failover Anthropic→GPT colapsa o debate (sem rodadas).
  - **BOOSTER (opcional, toggle ⭐ no header):** após o veredito final, os MELHORES modelos dão opinião independente em paralelo (asyncio.gather, best-effort). Seleção: Claude opus-4-8 (pref. sobre fable-5 por custo) e o melhor gpt-5.x "puro" via regex `gpt-5(\.\d+)?` (excl. pro/codex/mini) → na chave do usuário deu **gpt-5.5**. Cards "⭐ Booster — opinião final" no painel.
  - **UI:** seletor "Nx rodadas" + toggle ⭐ no header do chat (localStorage); indicador "✍️ Refinando (rodada k/N)"; "🔁 k/N rodadas" nas métricas; timeline no AuditorPanel (cards "Rodada k/N — crítica intermediária"/"veredito final" + grupo por turno com divisor). Persistência: campos debate e booster na msg do assistant (storage.append_exchange).
  - **Testes (todos PASS):** rounds=2 regressão idêntica; rounds=4 ordem exata `chunk* → debate(r2,REVIEW) → revision_start(r3) → chunk* → metrics(4/4, tokens somados 2410in/91out) → AUDIT(r4/4)` com resposta final ≠ inicial; parada antecipada r2/6 EARLY; xlsx em rounds=4 com artifacts 1x; booster ON → claude-opus-4-8 OK + gpt-5.5 OK; booster OFF sem evento; failover colapsa o debate; debate persistido no Redis; 0 exceções.
  - DICA prompts de teste: p/ forçar REVIEW do auditor, peça resposta propositalmente incompleta ("explique X em no máximo 5 palavras, será julgado por auditor rigoroso").
- [x] **Contexto do auditor + poda de histórico (11/06/2026, autorizado pelo usuário "corrija o que achar melhor"):**
  - **Auditor/booster com contexto multi-turno:** audit_question agora inclui os últimos 6 turnos (cada um truncado a 800 chars) em "## Contexto da conversa (turnos anteriores)" antes da pergunta atual. Corrige REVIEW injusto quando a pergunta depende de turno antigo (ex.: orçamento dito 2 turnos antes). Constantes: AUDIT_HISTORY_TURNS/AUDIT_HISTORY_CHARS em chat.py.
  - **Poda do histórico ENVIADO à API:** MAX_HISTORY_MESSAGES=40 (Redis guarda tudo; só a chamada à Anthropic é podada; garante 1ª msg = user após o corte). Protege custo e janela de 200K do haiku em conversas longas.
  - Testes PASS: auditor aprovou resposta que dependia de orçamento dito 2 turnos antes (sem reclamar de contexto); histórico sintético de 51 msgs podado sem 400 de alternância; regressão OK; 0 exceções.
  - **Semântica das rodadas CONFIRMADA pelo usuário:** Claude normal → ChatGPT audita o anterior → Claude audita o anterior (julga a crítica e refina) → ... sucessivamente, sempre fechando no GPT. É exatamente o que o loop implementa (rodada ímpar=Claude, par=GPT).
- [x] **CAMPANHA DE TESTES COMPLETA + UI de modelos (11/06/2026) — ver TESTES.md (24/24 PASS):**
  - Cronograma formal em **TESTES.md** (8 fases): infra, debate complexo sonnet-4-6×gpt-5.4 (Tabela Price gerou DEBATE GENUÍNO sobre arredondamento — gpt-5.4 achou erro real, sonnet refinou), booster, geração de arquivos complexos (xlsx 3 abas c/ fórmulas cross-aba, pdf 4 págs, csv+png+txt), revisão profunda (pdfplumber página a página: 0 tofu/0 cortes; openpyxl célula a célula), round-trip upload dos arquivos gerados c/ análise cruzada por @nome, downloads, logs 0 exceções.
  - **Fix de acentos nos prompts:** sonnet evitava acentos em PDF por precaução → prompts agora dizem que acentuação pt-BR é suportada (só emoji proibido). Conversor próprio já preservava (validado: coração/açaí no PDF).
  - **UI de modelos (pedidos do usuário):** frontend/src/services/models.js — modelLabel() ("claude-sonnet-4-6"→"Claude Sonnet 4.6", "gpt-4o-mini"→"GPT-4o mini", "o3-mini"→"OpenAI o3-mini"; testado c/ 12 IDs reais) + modelRank()/organizeModels() (forte/caro→barato). Novo components/ModelSelect.jsx: mostra os PRINCIPAIS (Claude: Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5; GPT: 5.5, 5.4, 5, 4o, 4o-mini — match exato p/ não pegar variantes pro/mini) + opção "▾ mostrar todos (N modelos)" que expande. Usado nos 2 painéis; badge e "auditado por" também usam modelLabel.
- [x] **FASE 9 — testes financeiros c/ verificação exata + 5 fixes (11/06/2026) — ver TESTES.md Fase 9:**
  - Metodologia: gabaritos com decimal.Decimal comparados número a número com as respostas (sonnet-4-6 × gpt-5.4, 4x).
  - Achados: deslize de R$0,18 que o auditor APROVOU (erros pequenos passam); auditor ERROU fórmula de juros SAC (alegou N(N-1)/2; exato é N(N+1)/2 — prova por soma mês a mês; o prompt de refino "a crítica PODE estar errada" salvou); ambos os modelos derrapam ~0,1-0,3% em potências grandes de cabeça (ex.: 1,009^300: exato 14,7011, claude 14,7304, gpt 14,6916) — debate reduz mas não zera; PARA PRECISÃO REAL → pedir ARQUIVO (fórmulas Excel calculam exato).
  - **FIXES:** (1) claude.py MAX_TOKENS 8192→32000 — scripts de PDF complexo truncavam (fence aberta → nem executava); (2) prompt: fórmulas Excel via openpyxl OBRIGATORIAMENTE em inglês (=IF/=SUM/=PMT) — "=SE()" dá #NAME? (xlsx armazena nomes canônicos em inglês); reteste: 55/55 fórmulas inglês; (3) executor.run_with_autofix(code, model) — auto-fix usa o MESMO modelo da conversa (antes haiku tentava consertar código do sonnet e falhava); stderr da retentativa exposto; (4) prompt de acentos reforçado c/ exemplos em MAIÚSCULAS ('RELATÓRIO' nunca 'RELATORIO') — sonnet ainda pode escapar às vezes; auditor flagra quando acontece (comportamento conhecido); (5) validador de PDF ganhou checagem de estouro de margem por bounding-box (planejamento.pdf: 6 págs, 0 overflow, 0 tofu).
  - **UI (pedidos do usuário):** booster corporativo — cards "Parecer final independente · <Modelo>" c/ borda dourada sóbria (#c9a227) e gradiente sutil; toggle dourado; seletor de rodadas mostra "2x rodadas (Padrão)".
- [x] **HANDOFF / TROCA DE CONTA — o essencial para continuar:** app 100% funcional em http://localhost:8100 (web) / 8101 (api), 3 containers healthy. Funciona em qualquer máquina: copiar pasta + .env (chaves reais NESTA máquina; .gitignore protege) + `docker compose up --build -d`. Cópia-backup intocada em ../projeto_base (portas 8200/8201, usuário vai subir p/ git). Fluxo principal: chat.py orquestra rodadas de debate → auto-execução de arquivos → auditoria → booster → persistência Redis. Tudo que existe está descrito nas seções acima (estrutura, contratos SSE, decisões); TESTES.md tem a metodologia de validação; PDD.md/pdf é o doc de produto. Pendências conhecidas: sonnet às vezes sem acentos em títulos de PDF (auditor flagra); drift de cálculo mental ~0,1-0,3% em potências (recomendar arquivo p/ precisão); gpt-5.x "pro"/"codex" não testados como auditor (excluídos da lista).

## Estrutura de pastas

```
projeto_auditor/
├── docker-compose.yml        # api (8000) + web (3000); VITE_API_URL via build arg
├── .env.example              # ANTHROPIC_API_KEY, OPENAI_API_KEY, MAX_FILE_SIZE_MB, UPLOAD_TTL_MINUTES, VITE_API_URL
├── CONTEXT.md                # este arquivo
├── README.md                 # instruções de uso
├── PDD.md / PDD.pdf          # Documento de Projeto (PDF gerado pelo próprio endpoint do app)
├── .gitignore                # exclui .env (tem chaves reais!)
├── backend/
│   ├── Dockerfile            # python:3.12-slim, uvicorn main:app --host 0.0.0.0 --port 8000
│   ├── requirements.txt      # fastapi, anthropic, openai, pdfplumber, python-docx, openpyxl, reportlab...
│   ├── main.py               # app FastAPI, CORS aberto, lifespan com loop de limpeza de uploads (5 em 5 min)
│   ├── routers/
│   │   ├── chat.py           # POST /api/chat (SSE: rodadas de debate, failover, booster, métricas) + GET /api/models
│   │   ├── upload.py         # POST /api/upload (multipart, validação magic bytes)
│   │   ├── download.py       # POST /api/download/{txt|md|pdf} — conversor platypus c/ tabelas
│   │   ├── execute.py        # POST /api/execute (fallback manual + painel auditor) + GET /api/files/{id}
│   │   └── conversations.py  # GET/DELETE /api/conversations[/{id}] — histórico Redis
│   └── services/
│       ├── claude.py         # stream_claude/refine_claude/audit_with_claude/fix_code/list_anthropic_models
│       ├── gpt.py            # audit_response/stream_gpt_answer (failover)/list_openai_models
│       ├── executor.py       # run_code/run_with_autofix/should_auto_run — auto-execução de arquivos
│       ├── pricing.py        # estimate_cost_usd — custo por resposta (USD/1M tokens)
│       ├── storage.py        # Redis: conv:{id} JSON + zset 'conversations' (score=updated_at)
│       └── file_processor.py # process_upload/load_file_meta/cleanup — /tmp/uploads/{uuid} + {uuid}.json
└── frontend/
    ├── Dockerfile            # node:20-alpine build → nginx:alpine; ARG VITE_API_URL
    ├── nginx.conf            # SPA fallback try_files
    ├── package.json / vite.config.js / index.html
    └── src/
        ├── main.jsx / index.css   # tema escuro (#1a1a1a fundo, #111 painéis), Inter/system-ui
        ├── App.jsx                # estado central: messages, audits, modelos, rounds, booster, aba mobile
        ├── components/
        │   ├── Sidebar.jsx        # lista de conversas (Redis): nova/abrir/apagar (✕ hover + confirmação Sim/Não)
        │   ├── ChatPanel.jsx      # header (modelo + Nx rodadas + ⭐ Booster) + mensagens + input
        │   ├── MessageBubble.jsx  # markdown/highlight, código de arquivo recolhido, artifacts, métricas, badge do modelo
        │   ├── AuditorPanel.jsx   # timeline do debate (cards por rodada) + veredito final + cards ⭐ booster
        │   ├── CodeRunner.jsx     # botão Executar (fallback + código corrigido do auditor)
        │   ├── FileCard.jsx       # cards de arquivo estilo Claude.ai (anexos e downloads)
        │   ├── FileUpload.jsx     # previews + FileUpload.Button (clipe que faz upload)
        │   └── DownloadMenu.jsx   # dropdown TXT/MD/PDF
        └── services/api.js        # uploadFile, streamChat (SSE c/ todos os eventos), execute, downloads, conversas
```

## Contratos de API (importante para o frontend)

### POST /api/chat — SSE
Request:
```json
{ "messages": [...], "files": ["file_id"], "conversation_id": "uuid ou null",
  "main_model": "claude-...", "auditor_model": "gpt-...",
  "rounds": 2, "booster": false }
```
`rounds`: 2 (padrão) a 10, sempre par — debate Claude↔GPT. `booster`: opinião final dos melhores modelos.
Se `conversation_id` for null, o backend cria a conversa no Redis (título = pergunta truncada) e devolve o id no evento `meta`.

Eventos SSE (linhas `data: ...`), na ordem em que podem ocorrer:
- `{"type":"meta","conversation_id":"..."}` — id da conversa (primeiro evento)
- `{"type":"chunk","text":"..."}` — pedaço da resposta (rodada 1 e refinamentos)
- `{"type":"failover","provider":"anthropic","message":"...","took_over":"..."}` — Anthropic caiu, GPT assume
- `{"type":"debate","round":k,"total":N,"audit":{...}}` — crítica intermediária do GPT (4x+)
- `{"type":"revision_start","round":k,"total":N}` — Claude vai re-streamar a resposta refinada (frontend zera o conteúdo)
- `{"type":"model_info",...}` — métricas SOMADAS de todas as rodadas: requested/used/input_tokens/output_tokens/duration_s/ttft_s/tokens_per_s/cost_usd/rounds_executed/rounds_total
- `{"type":"artifacts","ok":bool,"files":[...],"auto_fixed":bool,"error":...}` — arquivos auto-gerados (1x, da resposta final)
- `data: [AUDIT]{"status":"OK|REVIEW|ERROR","comment","response?","via","usage","round","total","early_stop?"}` — veredito final
- `{"type":"booster","claude":{...,"via":"claude-opus-4-8"},"gpt":{...,"via":"gpt-5.5"}}` — se booster ativo
- `{"type":"error","message":"..."}` — erro fatal (ambas APIs falharam)
- `data: [DONE]` — fim

Ao final o backend salva (pergunta, resposta final, auditoria, artifacts, metrics, debate, booster) via `storage.append_exchange`. Redis fora do ar → chat funciona normalmente, só não persiste.

### Conversas (Redis)
- `GET /api/conversations` → `[{id, title, updated_at, message_count}]` (zset ordenado por atividade; retorna [] se Redis cair)
- `GET /api/conversations/{id}` → conversa completa `{id, title, messages, audits, ...}`
- `DELETE /api/conversations/{id}`

Os `files` são anexados apenas à ÚLTIMA mensagem: imagens viram blocos `image` base64 da Messages API; documentos têm o texto extraído injetado no início do texto da mensagem (`--- Conteúdo do arquivo: nome ---`).

### POST /api/upload — multipart, campo `file`
Response: `{ "file_id": "...", "name": "...", "type": "image|document", "preview": "..." }`
- imagem → `preview` é data-URL base64 (usável direto em `<img src>`)
- documento → `preview` são os primeiros 300 chars do texto extraído
- Limites: MAX_FILE_SIZE_MB (413), tipo não suportado (415). TTL: UPLOAD_TTL_MINUTES.
- Persistência: `/tmp/uploads/{uuid}` (bytes) + `/tmp/uploads/{uuid}.json` (metadados c/ texto extraído ou base64).

### POST /api/download/{format} — format ∈ txt|md|pdf
Body: `{ "content": "..." }` → retorna o arquivo com Content-Disposition attachment.
**Desvio da spec:** a spec pedia GET, mas GET com body não é confiável → usamos POST.

## Decisões técnicas (e porquês)

1. **Modelo Claude:** `claude-haiku-4-5` (alias oficial, sem sufixo de data). Streaming via `client.messages.stream()` do SDK `anthropic` (AsyncAnthropic p/ não bloquear o event loop do FastAPI). `max_tokens=8192`.
2. **Auditor:** `gpt-4o-mini` com `response_format={"type":"json_object"}` para garantir JSON parseável. Falha de auditoria NUNCA derruba o chat — retorna `{"status":"ERROR"}`.
3. **PDF de download:** `reportlab` (puro Python) em vez de `weasyprint` (que exige libs de sistema pesadas no Docker). Conversão markdown→PDF é simplificada (headings, listas, bold/italic/code inline, blocos de código).
4. **Extração:** PDF→`pdfplumber`, DOCX→`python-docx`, XLSX→`openpyxl` (200 linhas/planilha), TXT/MD→UTF-8 com `errors="replace"`.
5. **Uploads persistidos em disco** (não só memória) — sobrevivem a restart via volume Docker nomeado `uploads-data` (montado em /tmp/uploads do container; o host NÃO é tocado — mudado a pedido do usuário p/ deixar tudo autocontido). Limpeza por TTL: lazy a cada upload + loop em background a cada 5 min.
6. **VITE_API_URL é build-time** (Vite embute no bundle). Por isso vai como `build.args` no compose, não como `environment` de runtime. Mudou a URL? → `docker compose build web`.
7. **SSE via fetch+ReadableStream** no frontend (não EventSource, que não suporta POST). Parser acumula buffer e divide por `\n\n`.
8. **CORS aberto** (`*`) — app local sem auth, conforme spec.
9. **Redis para histórico** (pedido do usuário, alterando a spec original "sem banco"). Por quê Redis e não SQLite: serviço pronto no compose, zsets dão listagem ordenada de graça, AOF (`--appendonly yes`) garante durabilidade, e o modelo de dados (JSON blob por conversa) dispensa migrations. Volume `redis-data` persiste entre restarts. Toda escrita no Redis é best-effort: falha não derruba o chat.

## Como rodar

```sh
cp .env.example .env   # preencher ANTHROPIC_API_KEY e OPENAI_API_KEY
docker compose up --build
# abrir http://localhost:8100
```

> O `.env` da máquina do usuário JÁ TEM as chaves reais preenchidas (não commitar!). Não existe .gitignore ainda — se o projeto virar repo git, criar .gitignore com `.env` antes do primeiro commit.

Dev local sem Docker:
- backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000` (exportar as chaves antes)
- frontend: `cd frontend && npm install && npm run dev` (porta 3000; usa VITE_API_URL do ambiente ou default http://localhost:8000)

## Pendências / melhorias possíveis

- Testar de ponta a ponta com chaves reais (`docker compose up --build`).
- Histórico multi-turno é enviado inteiro a cada request (sem compaction) — ok para uso local.
- Imagens anexadas em turnos ANTERIORES não são re-enviadas ao Claude (só os da última mensagem, conforme spec do request body).
- PDF de download não renderiza tabelas markdown (vira texto corrido).
- Sem testes automatizados.

## Notas para a próxima sessão de Claude

- O usuário fala português (pt-BR) — responder em português.
- A spec original completa está no primeiro prompt do usuário; este arquivo resume tudo que importa.
- Se for mexer na integração Anthropic, consultar a skill `claude-api` (model IDs atuais, streaming) — NÃO usar IDs com sufixo de data.
- Manter este CONTEXT.md atualizado a cada mudança relevante (o usuário pediu explicitamente).
