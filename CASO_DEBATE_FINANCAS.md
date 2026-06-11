# CASO PARA DEBATE — Decisão Financeira da Família Andrade

> **Como usar:** anexe este arquivo no chat (clipe 📎), selecione **8x rodadas** e envie:
> *"Analisem o caso do arquivo com o máximo rigor: calculem cada cenário, apontem erros um do outro e cheguem a uma recomendação final fundamentada."*
> Sugestão de modelos: Claude Sonnet 4.6 + GPT-5.4, com **Booster ligado**.

---

## Situação

A família Andrade tem **R$ 180.000** disponíveis hoje e precisa decidir o que fazer nos próximos **36 meses**. Eles têm simultaneamente uma dívida, uma oportunidade de investimento e um objetivo de compra. Toda a análise deve considerar **inflação constante de 0,42% ao mês**.

## Dados

### Dívida ativa
- Financiamento de veículo: **saldo devedor de R$ 62.000**, taxa de **1,65% a.m.**, restam **30 parcelas fixas (Price)**.
- Quitação antecipada hoje: o banco oferece desconto, cobrando apenas o **valor presente das parcelas descontado a 1,3% a.m.**

### Opções de investimento para o que sobrar (ou para tudo, se não quitarem)
1. **CDB 112% do CDI** — CDI constante de 0,82% a.m.; IR regressivo: 17,5% sobre o rendimento se resgatar entre 12 e 24 meses, **15% acima de 24 meses** (resgate único no mês 36).
2. **LCI 90% do CDI** — isenta de IR, liquidez apenas no vencimento (36 meses).
3. **Fundo multimercado** — expectativa de **1,05% a.m. bruto**, taxa de administração de **1,2% a.a.** (descontada do patrimônio) e **come-cotas semestral de 15%**, mais IR de 15% sobre o ganho restante no resgate.

### Objetivo de compra
- Reforma da casa estimada **hoje em R$ 95.000**, que será feita **no mês 36**. O custo da reforma sobe com a inflação (0,42% a.m.).

## Perguntas que os modelos DEVEM responder (com cálculos explícitos)

1. **Quitar ou não a dívida?** Calcule o valor de quitação hoje (VP das 30 parcelas a 1,3% a.m. — primeiro encontre a parcela do financiamento), e compare matematicamente: quitar e investir o restante × não quitar e investir tudo (pagando as parcelas com o rendimento). Qual a diferença em reais no mês 36?
2. **Qual investimento vence** para o horizonte de 36 meses, no cenário escolhido na pergunta 1? Montante bruto, líquido de IR/taxas (atenção ao come-cotas semestral do fundo) e ganho real acima da inflação, para as 3 opções.
3. **A reforma cabe?** No mês 36, o líquido disponível cobre o custo da reforma corrigido pela inflação? Qual a sobra ou o déficit?
4. **Análise de sensibilidade:** se o CDI cair para 0,70% a.m. a partir do mês 13, a resposta da pergunta 2 muda? E se a inflação subir para 0,55% a.m., o ganho real de alguma opção fica negativo?
5. **Recomendação final** em até 5 linhas, com os números que a sustentam.

## Regras do debate

- Cada modelo deve **refazer os cálculos do outro** antes de concordar — arredondamentos importam (4 casas decimais nas taxas).
- Críticas devem apontar **o número exato errado e o valor correto**, não apenas "há imprecisões".
- A resposta final deve trazer uma **tabela comparativa única** com os 3 investimentos × (bruto, líquido, real).
- Armadilhas conhecidas do caso (verifiquem com atenção): conversão da taxa de administração anual para o desconto mensal; o come-cotas reduz a base que continua rendendo; o IR do CDB aos 36 meses é 15% (não 17,5%); o VP da quitação usa 1,3% e não 1,65%.
