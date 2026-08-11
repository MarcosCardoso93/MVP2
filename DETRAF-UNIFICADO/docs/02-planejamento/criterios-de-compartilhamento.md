# Critérios de Compartilhamento de Componentes

Quando um componente vai para a base comum e quando fica no RPA.

> A base comum é o principal ativo da unificação — e o principal risco. Uma base comum errada acopla quatro robôs que deveriam ser independentes, e cada mudança nela passa a exigir revalidar tudo.

---

## Os quatro critérios — todos obrigatórios

Um componente entra na base comum **somente se atender aos quatro**. Falhar em um já basta para ficar no RPA.

### C1 — Recorrência comprovada

> Aparece em **pelo menos dois** RPAs, com o **mesmo propósito**.

"Mesmo propósito" no sentido de [`criterios-de-unificacao.md`](criterios-de-unificacao.md): IDÊNTICO ou EQUIVALENTE-PARAMETRIZÁVEL. FALSO PAR não conta.

**Comprovada** significa: duas ocorrências reais, localizadas em código, com arquivo e linha registrados. **Não** conta como recorrência:
- "provavelmente vai ser usado pelo RPA 3 também"
- "é genérico por natureza"
- "seria bom ter isso disponível"

⚠️ **Este é o critério mais fácil de violar de boa-fé.** A tentação de promover algo "obviamente reutilizável" antes da segunda ocorrência é a principal causa de abstração errada. Se a segunda ocorrência não existe hoje, o componente fica no RPA e é promovido quando ela aparecer — o que é barato, porque o código já foi lido e inventariado.

### C2 — Independência de RPA

> Não depende de estado, contexto ou fase exclusivos de um RPA.

Um componente da base comum não pode:
- assumir que existe uma decisão de analista já tomada (só o RPA 3 tem)
- assumir que a data de corte já passou (só o RPA 2 tem)
- ler configuração específica de um RPA
- chamar de volta o fluxo de um RPA específico

**Teste:** o componente funciona se for chamado pelo RPA 4, que é o mais isolado de todos? Se a resposta exigir "depende de onde ele é chamado", falha em C2.

### C3 — Regra fechada

> A regra que ele implementa **não** está em pendência aberta.

Enquanto uma regra está indefinida, ela vai mudar. Uma mudança na base comum obriga a revalidar os quatro RPAs; a mesma mudança dentro de um RPA afeta só ele.

**Componentes bloqueados por C3 hoje:**

| Componente candidato | Pendência que o bloqueia |
|---|---|
| Cálculo da variação e decisão S/N | Borda de 1%: valor, sinal e base indefinidos |
| Janela de captura / regra de reprocessamento | Data de corte não definida |
| Layout de arquivo com CBS/IBS | Posição e obrigatoriedade das colunas indefinidas |
| Envio do e-mail de contestação | Envio automático sem aprovação não confirmado |
| Correção automática de erro em expectativa | "Avalia possível correção automática" sem regra |
| Validação de descritores de transporte | V2: "aguardando informação do solicitante" |

Isso não impede a migração — impede a **promoção**. O componente vive no RPA até a regra fechar.

### C4 — Variação parametrizável

> A diferença entre as ocorrências cabe em **parâmetro**, não em ramificação de comportamento.

O teste é o mesmo de EQUIVALENTE-PARAMETRIZÁVEL: extraindo a diferença para um parâmetro, o corpo restante fica igual, sem `if` sobre esse parâmetro?

Se o componente precisa saber **quem** o chamou para decidir o que fazer, ele não é compartilhado — são dois componentes com um nome só.

---

## Candidatos, e como cada um se sai nos critérios

⚠️ **Tudo abaixo é hipótese derivada da recorrência na documentação.** A confirmação — e a contagem real de ocorrências — depende da análise do código. A coluna "C1" indica em quantos RPAs a documentação sugere uso.

| Candidato | C1 (RPAs) | C2 | C3 | Avaliação preliminar |
|---|---|---|---|---|
| **Consulta ao Anexo 5** (EOT → nome fantasia, tipo de serviço, região, concessão) | 1, 2, 3, 4 | ✅ | ✅ | **Candidato mais forte.** Usado em HU-02, 04, 05, 06, 10, 21 |
| **Acesso ao banco WebFat** (conexão, transação) | 1, 2, 3, 4 | ✅ | ✅ | Forte. Todos os RPAs gravam |
| **Consulta a `tbl_detraf_tarifas`** | 2 | ⚠️ 1 RPA | ✅ | ❌ falha C1 pela documentação — a menos que apareça em outro lugar no código |
| **Mapeamento descritor → remuneração** | 2, 3 | ✅ | ⚠️ transporte indefinido | Forte para os descritores fechados |
| **Leitura de arquivo Detraf** (csv/xlsx, sem cabeçalho, ignora aba de resumo) | 1?, 2, 3 | ✅ | ⚠️ CBS/IBS | Forte, mas o layout precisa ser configurável |
| **Construção de caminhos de rede** | 1, 2, 3 | ✅ | ✅ | Forte. É o contrato implícito entre RPAs |
| **Convenções de nome de arquivo** (`_D_`, `_BK`, `_ERRO`, `_ENV`, `_EXT`, `_INT`) | 1, 2, 3 | ✅ | ✅ | Forte, e de alto valor: divergência aqui é bug latente |
| **Automação do Outlook** (ler/mover/enviar) | 1, 2, 3 | ✅ | ⚠️ HU-15 | Leitura e movimentação: ok. **Envio de contestação: bloqueado por C3** |
| **Automação de UI do AGI** (login, navegação, upload) | 3, 4 | ✅ | ✅ | Forte. Provar no RPA 4 antes do RPA 3 |
| **Logging e observabilidade** | 1, 2, 3, 4 | ✅ | ✅ | Forte |
| **Configuração e credenciais** | 1, 2, 3, 4 | ✅ | ✅ | Forte |
| **Escrita em `tbl_..._contestacao`** | 2, 3 | ⚠️ | ✅ | ⚠️ **Cuidado:** quatro responsabilidades diferentes escrevem nessa tabela em momentos distintos. Pode ser FALSO PAR |
| **Cálculo de variação e decisão S/N** | 2 | ✅ | ❌ | **Bloqueado por C3** — e por C1 |
| **Detecção de tráfego recuperado** | 3, 4 | ⚠️ | ✅ | A detecção está no RPA 3, a execução no RPA 4. Depende de como o código resolveu isso |

---

## Onde fica o que não é compartilhado

| Situação | Destino |
|---|---|
| Passa nos quatro critérios | Base comum |
| Falha C1 (uma ocorrência) | RPA que o usa. Reavaliar quando surgir a segunda |
| Falha C2 (depende de um RPA) | RPA. Não force |
| Falha C3 (regra aberta) | RPA. **Marcar como candidato bloqueado**, com a pendência nomeada |
| Falha C4 (variação é comportamento) | Manter separado nos RPAs, com nomes distintos |

⚠️ Um componente que falha **apenas** C3 é diferente de um que falha C1 ou C2: ele é um compartilhamento **adiado**, não rejeitado. Registre-o como tal, para que a promoção seja automática quando a pendência fechar.

---

## Antipadrões a evitar

| Antipadrão | Por que é ruim |
|---|---|
| **Base comum "utils"** | Vira depósito. Se não há nome melhor que "utils", a responsabilidade não foi entendida |
| **Promover por antecipação** | Viola C1. Abstração inventada acopla sem benefício |
| **Flag booleana de comportamento** | Viola C4. É ramificação disfarçada de parâmetro |
| **Componente que conhece o chamador** | Viola C2. Inverte a dependência |
| **Compartilhar regra em aberto** | Viola C3. Garante retrabalho nos quatro RPAs |
| **Compartilhar por semelhança de nome** | FALSO PAR. "validar arquivo" e "enviar e-mail" significam coisas diferentes em RPAs diferentes |

---

## Registro obrigatório

Todo candidato avaliado gera uma ficha, **inclusive os rejeitados**. Template em [`../05-proxima-etapa/templates/ficha-de-componente-candidato.md`](../05-proxima-etapa/templates/ficha-de-componente-candidato.md).

A ficha de um rejeitado precisa dizer **qual critério falhou** e **o que mudaria o veredicto**. É isso que permite reavaliar depois sem refazer a análise.
