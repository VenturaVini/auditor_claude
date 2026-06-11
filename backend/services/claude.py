"""Integração com Claude via SDK oficial da Anthropic.

- stream_claude(): resposta principal em streaming (modelo selecionável).
- audit_with_claude(): auditoria de fallback quando a OpenAI está indisponível.
"""

import json

from anthropic import AsyncAnthropic

DEFAULT_MODEL = "claude-haiku-4-5"
# Aliases oficiais (sem sufixo de data). Ordem: custo crescente.
AVAILABLE_MODELS = ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8"]
MAX_TOKENS = 32000  # scripts longos de geração de documentos estouravam 8K e truncavam o código

SYSTEM_PROMPT = (
    "Você é um assistente de IA avançado. Responda com clareza, precisão e profundidade.\n"
    "Use markdown quando enriquecer a resposta (código, listas, tabelas).\n"
    "Seja direto e objetivo.\n"
    "\n"
    "GERAÇÃO DE ARQUIVOS: quando o usuário pedir um arquivo (XLSX, DOCX, PDF, CSV, gráfico etc.), "
    "escreva um bloco ```python completo e autossuficiente cuja PRIMEIRA LINHA seja exatamente "
    "`# gerar-arquivo` e que salve o(s) arquivo(s) no diretório de trabalho atual. Esse código é "
    "EXECUTADO AUTOMATICAMENTE pelo sistema e o usuário recebe os arquivos prontos na resposta — "
    "o código fica oculto. Por isso: NÃO explique o código, NÃO mencione execução/botões, NÃO diga "
    "que não pode criar arquivos. Apenas escreva 1-2 frases sobre o que o arquivo contém, seguidas "
    "do bloco de código. Se o usuário pedir vários arquivos, gere todos no mesmo bloco.\n"
    "Só mostre código SEM o marcador (e com explicações) quando o usuário pedir explicitamente "
    "código/script como conteúdo da resposta.\n"
    "Bibliotecas disponíveis no ambiente de execução: openpyxl, python-docx, reportlab, pdfplumber, "
    "pandas, matplotlib (use matplotlib.use('Agg') antes de plotar). Não use bibliotecas fora dessa "
    "lista nem acesso à internet.\n"
    "\n"
    "QUALIDADE DOS DOCUMENTOS (sempre entregue documentos bonitos e estruturados):\n"
    "- PDF: use SEMPRE reportlab.platypus (SimpleDocTemplate, Paragraph, Table, Spacer, "
    "KeepTogether) com pagesize=A4 e margens de 2cm. NUNCA use canvas.drawString para texto "
    "corrido — ele NÃO quebra linha e corta o texto na borda da página. Todo texto vai dentro de "
    "Paragraph (quebra automática); títulos com os estilos Heading1/2/3 de getSampleStyleSheet(); "
    "crie um ParagraphStyle de título com cor (ex.: HexColor('#1F4788')) e espaçamento. Tabelas "
    "com Table + TableStyle: cabeçalho com BACKGROUND escuro e texto branco, GRID fino cinza, "
    "ROWBACKGROUNDS alternados (zebra), colWidths somando ~17cm.\n"
    "- PDF — quebra de página: envolva cada seção (título + sua tabela/conteúdo) em "
    "KeepTogether([...]) para a seção não ser cortada no meio entre páginas; em tabelas longas use "
    "Table(dados, repeatRows=1) para o cabeçalho repetir na página seguinte. Separe seções com "
    "Spacer(1, 12).\n"
    "- PDF — PROIBIDO usar emoji ou símbolos especiais (🏆 ✓ ▪ 🇧🇷 etc.): as fontes do PDF não têm "
    "esses glifos e eles viram quadrados pretos ■. Use apenas texto (letras, números, pontuação). "
    "Para destacar, use cor e negrito, não emoji. Em qualquer célula/título de PDF, escreva por "
    "extenso (ex.: '1o lugar' em vez de troféu). A ACENTUAÇÃO do português é totalmente suportada "
    "(ação, coração, à, é) — escreva com acentos normais em TODO o documento, INCLUSIVE títulos e "
    "maiúsculas (escreva 'RELATÓRIO', 'Análise', 'Orçamento' — NUNCA 'RELATORIO', 'Analise', "
    "'Orcamento'). Remover acentos é considerado erro.\n"
    "- DOCX: use os headings nativos (document.add_heading), tabelas com style='Light Grid Accent 1' "
    "ou similar, negrito nos cabeçalhos.\n"
    "- XLSX: cabeçalhos com PatternFill colorido + Font branca em negrito, larguras de coluna "
    "ajustadas (column_dimensions), number_format com separador de milhar, freeze_panes='A2'. "
    "FÓRMULAS escritas via openpyxl DEVEM usar nomes de função em INGLÊS (=IF, =SUM, =PMT, "
    "=VLOOKUP) — o arquivo xlsx armazena nomes canônicos em inglês e o Excel traduz na exibição; "
    "'=SE(...)' quebraria com #NAME?.\n"
    "- Gráficos: matplotlib com título, rótulos nos eixos, grid leve e tight_layout().\n"
    "\n"
    "ARQUIVOS ANEXADOS: o conteúdo de documentos anexados chega no início da mensagem em seções "
    "'--- Conteúdo do arquivo: <nome> ---'. O usuário pode se referir a eles pelo nome, com ou sem "
    "'@' (ex.: '@vendas.xlsx'). Quando houver vários arquivos, identifique cada um pelo nome e diga "
    "de qual arquivo veio cada informação."
)

AUDITOR_SYSTEM = """Você é um auditor de respostas de IA. Analise a resposta à pergunta do usuário.

CONTEXTO DA INTERFACE: quando o usuário pede um arquivo (XLSX, DOCX, PDF, gráfico etc.), o sistema
EXECUTA AUTOMATICAMENTE os blocos de código Python da resposta e entrega os arquivos gerados ao
usuário — o código fica oculto na interface. Portanto, responder com código Python que salva o
arquivo É a entrega correta do arquivo — NÃO marque isso como falha. Avalie, em vez disso, se o
código está correto e se os dados usados são precisos.

IMAGENS: você não tem acesso a imagens anexadas (apenas o modelo principal as vê). NÃO marque como
erro afirmações sobre imagens só porque não pode verificá-las — avalie o restante da resposta.

Se a resposta estiver correta e completa, responda APENAS com:
{"status": "OK", "comment": "frase breve confirmando"}

Se houver erro, imprecisão ou algo relevante a acrescentar, responda com:
{"status": "REVIEW", "comment": "o que está errado ou faltando", "response": "sua resposta completa"}

Quando a resposta auditada contiver CÓDIGO com erros (dados errados, bug, arquivo que não atende ao
pedido), seu "response" deve: explicar a correção em TEXTO primeiro e incluir o código Python
COMPLETO e CORRIGIDO num ÚNICO bloco ```python ao final — a interface executa o SEU código e
entrega os arquivos ao usuário (o código fica recolhido na tela; o texto é o que o usuário lê).
Salve arquivos no diretório de trabalho ATUAL com caminho relativo (ex.: wb.save("arquivo.xlsx"))
— NUNCA use /mnt/data ou caminhos absolutos. Corrija os dados, não apenas aponte o erro.

Responda APENAS com JSON válido, sem cercas de código."""

_client = AsyncAnthropic()  # lê ANTHROPIC_API_KEY do ambiente


async def list_anthropic_models() -> list[str]:
    """Lista os modelos Claude disponíveis para a chave (Models API).

    Exceções propagam — o chamador usa AVAILABLE_MODELS como fallback.
    """
    models = []
    async for m in _client.models.list():
        models.append(m.id)
    return models


async def stream_claude(messages: list[dict], model: str | None = None, info: dict | None = None):
    """Gera os chunks de texto da resposta do Claude (async generator).

    Se `info` for passado, recebe o modelo REAL reportado pela API no response
    (prova de qual modelo processou) e o uso de tokens.
    """
    async with _client.messages.stream(
        model=model or DEFAULT_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
        if info is not None:
            final = await stream.get_final_message()
            info["model"] = final.model
            info["input_tokens"] = final.usage.input_tokens
            info["output_tokens"] = final.usage.output_tokens


REFINE_INSTRUCTION = """Um auditor de IA (GPT) analisou sua resposta acima e fez esta crítica:

---
{critique}
---

Julgue a crítica com rigor: aceite os pontos corretos e ignore os incorretos (a crítica PODE estar errada — não aceite cegamente). Reescreva sua resposta COMPLETA e final incorporando apenas as correções válidas. Responda apenas com a resposta refinada, sem comentar o processo de revisão."""


async def refine_claude(
    question_content,
    prev_answer: str,
    critique_text: str,
    model: str | None = None,
    info: dict | None = None,
):
    """Rodada de refinamento: Claude julga a crítica do auditor e reescreve a resposta.

    `question_content` é o content da pergunta original (string ou blocos com
    imagens/contexto de arquivos). Async generator de chunks, como stream_claude.
    """
    messages = [
        {"role": "user", "content": question_content},
        {"role": "assistant", "content": prev_answer},
        {"role": "user", "content": REFINE_INSTRUCTION.format(critique=critique_text)},
    ]
    async with _client.messages.stream(
        model=model or DEFAULT_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
        if info is not None:
            final = await stream.get_final_message()
            info["model"] = final.model
            info["input_tokens"] = final.usage.input_tokens
            info["output_tokens"] = final.usage.output_tokens


async def fix_code(code: str, error: str, model: str | None = None) -> str:
    """Corrige um código Python que falhou na execução. Retorna só o código."""
    response = await _client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=4096,
        system=(
            "Você corrige código Python. Receberá um código e o erro que ele produziu. "
            "Responda APENAS com o código corrigido completo, sem explicações e sem cercas de código."
        ),
        messages=[{
            "role": "user",
            "content": f"## Código\n{code}\n\n## Erro na execução\n{error}",
        }],
    )
    fixed = next((b.text for b in response.content if b.type == "text"), "").strip()
    if fixed.startswith("```"):
        fixed = fixed.strip("`")
        if fixed.startswith("python"):
            fixed = fixed[6:]
        fixed = fixed.strip()
    return fixed


async def audit_with_claude(question: str, answer: str, model: str | None = None) -> dict:
    """Auditoria via Claude (fallback quando a OpenAI falha). Exceções propagam."""
    response = await _client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=2048,
        system=AUDITOR_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"## Pergunta do usuário\n{question}\n\n## Resposta a auditar\n{answer}",
        }],
    )
    raw = next((b.text for b in response.content if b.type == "text"), "{}").strip()
    if raw.startswith("```"):  # remove cerca de código se vier
        raw = raw.strip("`").lstrip("json").strip()
    try:
        data = json.loads(raw)
        if "status" not in data:
            data = {"status": "REVIEW", "comment": raw}
    except json.JSONDecodeError:
        data = {"status": "REVIEW", "comment": raw}
    data["usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return data
