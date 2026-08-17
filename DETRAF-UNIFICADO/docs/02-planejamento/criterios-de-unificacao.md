# Critérios de Unificação

Quando dois trechos de projetos diferentes são "a mesma coisa" — e o que fazer em cada caso.

> Este documento resolve a pergunta operacional mais frequente da próxima etapa: *"esses dois blocos de código fazem o mesmo? Devo juntar?"*

---

## O teste central

Dois trechos são **o mesmo comportamento** quando:

> Para toda entrada válida do domínio, ambos produzem o mesmo efeito observável — mesmo valor de retorno, mesmo artefato gravado, mesmo registro em banco, mesma ação externa.

Note o que o teste **não** exige: mesmo nome, mesma linguagem interna, mesma estrutura, mesma performance. E note o que ele exige: **para toda entrada válida** — não para o caso feliz.

---

## Os quatro veredictos

Todo par candidato recebe um destes:

| Veredicto | Significado | Ação |
|---|---|---|
| **IDÊNTICO** | Mesmo comportamento, mesmas entradas, mesmas saídas | Unificar |
| **EQUIVALENTE-PARAMETRIZÁVEL** | Mesmo comportamento; a diferença é dado | Unificar com parâmetro |
| **DIVERGENTE** | Comportamentos diferentes para a mesma responsabilidade | **Não unificar sem decisão** — escalar |
| **FALSO PAR** | Mesmo nome ou aparência, propósitos diferentes | Não unificar; renomear para evitar confusão futura |

---

## IDÊNTICO — unificar

**Reconhecimento.** Mesma responsabilidade, mesmas entradas, mesmas saídas, mesmo tratamento de borda.

**Cuidado obrigatório antes de declarar idêntico:** comparar os **casos de borda**, não o caminho feliz. Dois parsers de arquivo Detraf podem ser idênticos em arquivo bem formado e divergirem completamente em:
- arquivo **sem cabeçalho** (a V2 exige aceitar)
- presença de **aba de resumo** (a V2 exige ignorar)
- linhas com `Rel = 1` (excluídas nas consolidações)
- coluna `Rel` **vazia** (a V2 permite)
- coluna `POI` vazia (permitido)
- campos numéricos com separador decimal diferente

Se as bordas divergem, é DIVERGENTE, não IDÊNTICO.

**Ação.** Unificar numa única implementação. Escolher a origem pelo critério da seção "qual implementação vence".

---

## EQUIVALENTE-PARAMETRIZÁVEL — unificar com parâmetro

**Reconhecimento.** A diferença entre os dois é **dado**, não decisão.

**Exemplos plausíveis neste projeto** (⚠️ hipóteses — a confirmar no código):
- Construção de caminho de rede que difere apenas na subpasta final (`Detrafs Recebidos` vs `AGI` vs `Contestações`)
- Escrita em banco que difere apenas na tabela ou no valor de `tipo_registro`
- Geração de arquivo de carga que difere apenas nos valores fixos de ORIGEM/EXPECTATIVA/INSERÇÃO (`_EXT` vs `_INT`)
- Envio de e-mail que difere apenas em assunto, corpo e anexos

**O teste que separa isto de DIVERGENTE:**

> Se eu extrair a diferença para um parâmetro, o corpo restante fica **igual** — sem `if` sobre o parâmetro?

Se o corpo unificado precisar ramificar sobre o parâmetro, a diferença não era dado. É comportamento. Vá para DIVERGENTE.

**⚠️ Limite de parâmetros.** Um componente com muitos parâmetros que só existem para satisfazer um chamador específico não foi unificado — foi disfarçado. Quando isso acontecer, prefira manter separado.

**Ação.** Unificar, com a diferença explícita na assinatura. Nunca com uma flag booleana que liga/desliga comportamento — isso é ramificação, não parametrização.

---

## DIVERGENTE — não unificar sem decisão

**Reconhecimento.** Duas implementações da mesma responsabilidade que se comportam diferente em pelo menos uma entrada válida.

**Este é o veredicto mais importante do projeto**, porque a documentação praticamente garante que ele vai aparecer. As HUs marcadas 🔴 mudaram estruturalmente entre V1 e V2:

| HU | Divergência esperada |
|---|---|
| HU-02 | Identificação por domínio do remetente (V1) × por EOT/Anexo 5 (V2) |
| HU-07 | Fluxo de erro L-L dedicado (V1) × regra geral `_ERRO` (V2) |
| HU-09 | Saída em planilha `Base_Contestação` (V1) × gravação em banco (V2) |
| HU-10 | Aba `Contest` (V1) × banco (V2) |
| HU-19 | Planilha de Encontro de Contas (V1) × campos do banco (V2) |

E as ambiguidades da própria V2 podem gerar divergência entre dois projetos que a leram de formas diferentes:

| Ambiguidade | Divergência possível |
|---|---|
| Borda de 1% | `> 1%` vs `>= 1%` vs `> +1%` |
| Base do percentual | sobre a operadora vs sobre a expectativa |
| Recálculo do total no `_BK` | com vs sem |
| Tarifas não reguladas | valida vs só classifica |

**Sub-classificação obrigatória:**

**DIVERGENTE-VERSÃO** — uma implementação segue a V1, outra a V2.
→ Registrar; a **V2 é normativa**; a implementação V1 é retrabalho, não migração. Encaminhar ao PO como confirmação, não como pergunta aberta.

**DIVERGENTE-INTERPRETAÇÃO** — ambas leram a mesma V2 e chegaram a comportamentos diferentes, porque o texto é ambíguo.
→ **Não decidir tecnicamente.** Apresentar as duas leituras e o impacto financeiro de cada uma ao PO.

**DIVERGENTE-DEFEITO** — uma das duas está objetivamente errada em relação à V2.
→ Registrar como bug. **Migrar a correta**, registrar a incorreta no backlog. Não corrigir a incorreta durante a migração.

**Ação em todos os casos.** Nunca unificar "escolhendo a que parecer melhor". A regra de negócio é do cliente.

---

## FALSO PAR — não unificar

**Reconhecimento.** Nome, assinatura ou aparência parecidos; propósitos diferentes.

**Armadilhas prováveis neste projeto:**
- **"validar arquivo"** no P1 (é divergente? é `.csv`/Excel? abre?) ≠ **"validar arquivo"** no P2 (as 15 colunas e as tarifas)
- **"enviar e-mail"** no P2 (crítica à operadora sobre erro) ≠ **"enviar e-mail"** no P5 (contestação formal com carta anexa)
- **"contestação"** como decisão de negócio ≠ **"contestação"** como tela do AGI ≠ **"contestação"** como arquivo `CONT_PROC`
- **"expectativa"** como arquivo do ICT ≠ campo `EXPECTATIVA` do `_EXT`/`_INT` (que vale `"S"`/`"N"`)
- **"operadora"** como entidade ≠ nome fantasia ≠ EOT

**Ação.** Não unificar. Renomear no destino para que o falso par não se repita.

---

## Qual implementação vence

Quando o veredicto permite unificar, a origem se escolhe nesta ordem:

1. **Aderência à V2.** Sempre primeiro. Uma implementação mais elegante da regra errada perde para uma feia da regra certa.
2. **Cobertura de bordas.** A que trata mais casos válidos do domínio.
3. **Menor acoplamento.** A que depende de menos coisas do seu projeto de origem.
4. **Testabilidade.** A que tem teste, ou é mais fácil de testar.
5. **Legibilidade.** Critério de desempate, não de decisão.

⚠️ **"É a do projeto maior" e "é a mais recente" não são critérios.** Data de commit não diz nada sobre aderência à V2 — um projeto pode ter sido escrito depois e mesmo assim sobre a especificação antiga.

---

## Quando NÃO unificar, mesmo sendo idêntico

Três casos em que a duplicação é a escolha certa:

**1. A regra está em pendência aberta.**
Data de corte, borda de 1%, CBS/IBS, envio automático da HU-15 — unificar antes da decisão significa que a decisão vai exigir mexer na base comum, com impacto em todos os RPAs. Deixe duplicado até a regra fechar.

**2. A unificação criaria acoplamento entre RPAs que devem ser independentes.**
O requisito é que cada RPA execute isolado. Se compartilhar um componente significasse que o RPA 4 não roda sem parte do RPA 3, a duplicação é preferível.

**3. Uma das ocorrências está prestes a desaparecer.**
Se a HU-20 for descartada do escopo, unificar código dela é trabalho jogado fora. Confirme o escopo antes.

---

## Registro obrigatório

Todo par avaliado gera um registro — inclusive os que **não** foram unificados. Template em [`../05-proxima-etapa/templates/registro-de-duplicacao.md`](../05-proxima-etapa/templates/registro-de-duplicacao.md).

O registro de um **não-par** vale tanto quanto o de um par: sem ele, a próxima pessoa reavalia o mesmo trecho e chega a outra conclusão.
