# TESTES.md — Cronograma de Testes Completo

> Campanha de testes de 11/06/2026. Modelos sob teste: **claude-sonnet-4-6** (principal)
> e **gpt-5.4** (auditor), conforme pedido do usuário.
> Status: ✅ passou · ⚠️ passou com ressalva · ❌ falhou
> **Resultado geral: 24/24 itens ✅ (1 com observação de melhoria já aplicada)**

## Fase 1 — Infraestrutura
| # | Teste | Resultado | Status |
|---|---|---|---|
| 1.1 | Containers saudáveis | api/redis/web healthy | ✅ |
| 1.2 | /api/health e frontend | 200 / 200 | ✅ |
| 1.3 | gpt-5.4 e sonnet-4-6 nas listas | presentes | ✅ |
| 1.4 | gpt-5.4 como auditor (JSON) | audit OK, via=gpt-5.4, usage 371/25 tokens | ✅ |

## Fase 2 — Debate real com pergunta complexa (sonnet-4-6 × gpt-5.4)
| # | Teste | Resultado | Status |
|---|---|---|---|
| 2.1 | Tabela Price em 4x | **DEBATE GENUÍNO**: gpt-5.4 achou erro real de arredondamento (parcela exata 2.121,58394), sonnet refinou, veredito final ainda REVIEW discutindo a convenção de arredondamento — discussão técnica legítima entre os dois | ✅ |
| 2.2 | Lógica capciosa (taco+bola / 100 máquinas) em 6x | sonnet acertou ambas de primeira (R$0,05 / 5 min), gpt-5.4 aprovou → parada antecipada r2/6 | ✅ |
| 2.3 | Modelos reais confirmados | used=claude-sonnet-4-6; críticas via gpt-5.4 | ✅ |
| 2.4 | Métricas somadas | 3.892 in / 1.868 out (2 rodadas Claude), rodadas 4/4, ~$0,0397 | ✅ |
| 2.5 | Debate persistido no Redis | campo debate com rodada [2] + metrics na mensagem | ✅ |

## Fase 3 — Booster no debate
| # | Teste | Resultado | Status |
|---|---|---|---|
| 3.1 | 4x + booster (paradoxo do aniversário) | resposta aprovada r2; booster: claude-opus-4-8 OK ("50,7%, 253 pares, dados precisos") + gpt-5.5 OK | ✅ |

## Fase 4 — Geração de arquivos complexos (sonnet-4-6)
| # | Teste | Resultado | Status |
|---|---|---|---|
| 4.1 | XLSX 3 abas c/ fórmulas | controle_financeiro.xlsx gerado sem auto-fix; auditor pegou detalhe (4 indicadores vs 3 pedidos — crítica justa) | ✅ |
| 4.2 | PDF relatório multi-seção | relatorio_energia_solar_brasil.pdf, 4 págs; código com platypus+KeepTogether, zero drawString | ✅ |
| 4.3 | CSV + PNG no mesmo pedido | vendas_2024.csv + grafico (110KB) | ✅ |
| 4.4 | TXT estruturado | resumo_analise_2024.txt íntegro | ✅ |

## Fase 5 — Revisão profunda dos arquivos gerados
| # | Teste | Resultado | Status |
|---|---|---|---|
| 5.1 | PDF página a página | 4 páginas, **zero tofu ■/�**, todas as seções presentes (Sumário Executivo, Vantagens, Desafios, Conclusão), nada cortado | ✅ |
| 5.2 | PDF tabelas extraíveis | tabela de estados com cabeçalho íntegro (Estado/Região/Cap./Particip./Destaque), 6 linhas | ✅ |
| 5.3 | XLSX célula a célula | 3 abas, zero células vazias nos dados, fórmulas cross-aba (=SUM(Receitas!D2:D9)...), cabeçalho colorido, freeze A2 | ✅ |
| 5.4 | CSV parse | 13 linhas, colunas consistentes, UTF-8 | ✅ |
| 5.5 | TXT encoding | UTF-8 válido com acentos corretos | ✅ |
| obs | PDF do modelo veio SEM acentos (overcaução do sonnet — não é corte) | prompt corrigido: "acentuação é suportada, escreva normalmente" | ⚠️→✅ |

## Fase 6 — Uploads complexos + análise cruzada
| # | Teste | Resultado | Status |
|---|---|---|---|
| 6.1 | Upload do PDF 4 págs gerado | extração correta (round-trip completo: app gerou → app leu) | ✅ |
| 6.2 | PDF+XLSX+CSV juntos, perguntas por @nome | 3/3 respostas corretas (Minas Gerais 8.450MW / 8 receitas / 12 meses), cada uma citando o arquivo; gpt-5.4 validou com contexto | ✅ |

## Fase 7 — Downloads (conversor próprio)
| # | Teste | Resultado | Status |
|---|---|---|---|
| 7.1 | PDF c/ tabela + código 200 colunas + acentos | tabela real extraível, código completo quebrado (não cortado), acentos preservados (coração/açaí), rodapé Página 1, zero tofu | ✅ |
| 7.2 | TXT e MD | bytes idênticos ao conteúdo original | ✅ |

## Fase 8 — Encerramento
| # | Teste | Resultado | Status |
|---|---|---|---|
| 8.1 | Logs da API (60 min de campanha) | 0 exceções | ✅ |
| 8.2 | Limpeza | 8 conversas de teste removidas; conversa do usuário preservada | ✅ |

## Melhorias aplicadas durante a campanha
1. **Prompt de acentos**: o sonnet evitava acentos em PDFs por precaução; os prompts agora instruem que acentuação do português é suportada (apenas emoji é proibido). Conversor próprio já preservava acentos (validado na F7).
2. **Nomes amigáveis de modelos na UI** (pedido do usuário): `frontend/src/services/models.js::modelLabel()` — "claude-sonnet-4-6"→"Claude Sonnet 4.6", "gpt-4o-mini"→"GPT-4o mini", "o3-mini"→"OpenAI o3-mini". Aplicado nos 2 seletores, no badge da mensagem e no "auditado por" — testado contra 12 IDs reais.

## Fase 9 — Testes financeiros complexos com verificação matemática exata (11/06/2026)
> Sonnet 4.6 × GPT-5.4, rounds 4x, gabaritos calculados com `decimal.Decimal` e comparados número a número.

| # | Teste | Resultado da análise | Status |
|---|---|---|---|
| 9.1 | Etanol×gasolina (custo/km, equilíbrio, viagem 850km) | 6/8 números EXATOS; erro de R$ 0,18 na viagem a gasolina (403,93 vs 403,75) que o gpt-5.4 APROVOU sem pegar — deslizes aritméticos pequenos passam pelo auditor | ⚠️ |
| 9.2 | SAC × Price R$ 300k/360m (4x + booster) | SAC PERFEITO (433.200/733.200/mês 105 ✓ exatos); PMT Price com desvio de R$ 0,31 (0,012%) — **auditor e os 2 boosters apontaram exatamente o fator (1,008)^360** | ✅ |
| 9.2b | **Auditor pode errar — PROVADO**: gpt-5.4 alegou que juros SAC seria N(N-1)/2; soma exata mês a mês confirma N(N+1)/2=433.200 (fórmula do Claude). O prompt de refino ("a crítica PODE estar errada") existe por isso | ✅ |
| 9.3a | XLSX amortização (Price/SAC/Comparativo c/ fórmulas) | gerado com =PMT real; **BUG ACHADO**: fórmulas =SE() em português → #NAME? no Excel (xlsx armazena nomes em inglês) → prompt corrigido; reteste com 55 fórmulas 100% inglês ✅ | ✅ |
| 9.3b | PDF financeiro 6 págs (capa+4 seções+3 tabelas) | **BUG ACHADO**: código truncava em MAX_TOKENS=8192 → corrigido p/ 32000; reteste: 6 págs, 3 tabelas, 0 tofu, **0 palavras estourando margem** (checagem por bounding-box) | ✅ |
| 9.4 | Aposentadoria 25 anos c/ inflação (Fisher) em 4x | debate funcionou (gpt-5.4 pegou fator superestimado); análise fina: exato=14,7011, Claude=14,7304, crítica gpt=14,6916 — **ambos derrapam ~0,1-0,3% em potências grandes de cabeça**; resposta final a 0,2% do exato | ⚠️ |

**Conclusões da Fase 9:**
1. O debate **melhora consistentemente** respostas financeiras (toda crítica numérica apontou a classe certa de erro), mas não garante precisão de centavos — cálculo mental de LLM tem drift de ~0,01-0,3% em potências/divisões longas.
2. **Para precisão financeira real, peça o ARQUIVO**: o XLSX gerado usa fórmulas reais do Excel (=PMT etc.) que calculam exato.
3. Correções desta fase: MAX_TOKENS 8K→32K; fórmulas Excel em inglês obrigatórias no prompt; auto-fix de código agora usa o MESMO modelo da conversa; acentos reforçados no prompt (inclusive MAIÚSCULAS); stderr da retentativa de auto-fix agora é exposto.
4. UI: booster com visual corporativo ("Parecer final independente · Claude Opus 4.8", dourado sóbrio) e seletor "2x rodadas (Padrão)".

## Fase 10 — Debate 8x completo (pergunta financeira extrema) + git + máquina nova (11/06/2026)
| # | Teste | Resultado | Status |
|---|---|---|---|
| 10.1 | Máquina nova real (wipe volumes+imagens → `up --build -d`) | 3 healthy; smoke do pipeline inteiro PASS (chat+arquivo+audit+métricas) — só o .env é necessário | ✅ |
| 10.2 | Segurança pré-git: varredura byte a byte | chaves SÓ no .env (gitignored); .claude/ excluído | ✅ |
| 10.3 | Push p/ github.com/VenturaVini/auditor_claude | main publicada (44 arquivos) + commit do caso de debate | ✅ |
| 10.4 | Envio de documentos pós-rebuild | .md e PDF multi-página: upload, extração e leitura no contexto corretos | ✅ |
| 10.5 | **DEBATE 8x** (CDB 110% × LCI 92% × fundo c/ come-cotas, 24m) | **8/8 rodadas, 4 intervenções de cada**; críticas EVOLUÍRAM: r2 conversão de taxas, r4 conceito do come-cotas (maio/nov, não no resgate), r6 sutileza tributária (720 dias exatos = 17,5%, não 15%), r8 sinal da taxa adm; boosters: opus validou o CDB por logaritmo, gpt-5.5 achou bug td() no código do PDF | ✅ |
| 10.6 | Verificação exata do 8x | conclusão CORRETA (CDB vence LCI por ~R$1,4k); números a 0,015-0,03% do exato (drift residual de potência persiste mesmo após 4 refinos) | ⚠️ |
| 10.7 | Custo do 8x | **~$0,76 só no lado Sonnet** (49k in/41k out, 14min) — pergunta pesada em 8x ULTRAPASSA o teto de $0,40/teste; usar 8x só para casos que valem o investimento | ⚠️ |

**Arquivo para debates manuais:** `CASO_DEBATE_FINANCAS.md` (Família Andrade — quitação×investimentos×reforma, 5 perguntas + armadilhas) — anexar no chat com 8x + booster.

## Como repetir a campanha
Os comandos desta campanha estão no histórico da sessão de Claude (CONTEXT.md aponta os destaques).
Atalhos úteis: forçar debate → pergunta de cálculo com arredondamento (Tabela Price); forçar parada
antecipada → pergunta trivial com rounds altos; validar PDF → pdfplumber dentro do container da api;
validar XLSX → openpyxl idem.
