# Checklist — Padronização

Aplicar durante a migração (F5) e na validação (F6), a cada RPA e à base comum.

**Objetivo:** que os quatro RPAs pareçam ter sido escritos pela mesma equipe, e que a base comum não seja um mosaico das convenções de seis projetos diferentes.

⚠️ **Padronizar não é refatorar.** Uniformizar nomes, estrutura e configuração faz parte da unificação. Reescrever lógica que funciona não faz — ver [`../02-planejamento/estrategia-de-migracao.md`](../02-planejamento/estrategia-de-migracao.md).

> A definição concreta de cada padrão (qual convenção, qual formato, qual biblioteca) é da fase **F4** e depende do que o código revelar. Este checklist garante que a decisão seja **tomada e aplicada de forma consistente** — não prescreve qual será.

---

## 1. Estrutura

- [ ] Os quatro RPAs seguem a mesma organização interna
- [ ] Cada RPA tem seu ponto de entrada, no mesmo lugar e com o mesmo nome (`main.py`)
- [ ] A base comum é referenciada da mesma forma pelos quatro
- [ ] Não há RPA acessando arquivo de outro RPA diretamente
- [ ] `projetos-origem/` continua intocada

---

## 2. Nomenclatura no código

- [ ] Uma única convenção de nomes (módulos, funções, variáveis, constantes), aplicada em tudo
- [ ] Um único idioma para identificadores — decidido em F4, aplicado sem exceção
- [ ] Termos do domínio grafados de forma consistente: **EOT**, **descritor**, **remuneração**, **expectativa**, **contestação**, **retenção**, **credora**, **devedora**
- [ ] Nenhum nome ambíguo dos listados no [checklist de duplicações](checklist-duplicacoes.md#parte-c--armadilhas-de-falso-par) sobreviveu sem qualificação
- [ ] Nenhum módulo chamado `utils`, `helpers`, `common` ou `misc`

---

## 3. Nomenclatura de artefatos externos

Estes **não** são escolha da equipe — são contrato com sistemas externos e com o usuário. Devem ser produzidos por um único ponto do código.

- [ ] `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_EXT`
- [ ] `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_INT`
- [ ] `Base_Contestação_{operadora}_{mesdodetraf}` / `_M` / `_ENV`
- [ ] `CONT_PROC_MASCARA_{nomeoperadora}_{aaaamm}` (`.xls`)
- [ ] Sufixos `_BK` e `_ERRO`
- [ ] Filtro `_D_` nos arquivos de expectativa
- [ ] Numeração `CT`
- [ ] Assunto do e-mail: `CONTESTAÇÃO_TBRA|{NOMEDAOPERADORA}_{MESDODETRAF}`

- [ ] **Cada padrão acima é gerado por um único ponto do código** — nenhuma concatenação inline espalhada

---

## 4. Caminhos de rede

- [ ] Toda construção de caminho passa por um único ponto
- [ ] Nenhum caminho absoluto constante no código
- [ ] A estrutura `Operadoras\{operadora}\{ano}\{aaaamm}\{subpasta}` é expressa uma vez só
- [ ] As subpastas (`Detrafs Recebidos`, `Detrafs Enviados`, `Contestações`, `AGI`, `Encontro de Contas`) são valores, não literais espalhados
- [ ] O caminho de `Correspondências Enviadas\CT\{ano}` idem
- [ ] O caminho do servidor do WebFat idem

⚠️ Esta é a padronização de maior valor prático: os caminhos são o **contrato implícito entre os RPAs**. Divergência aqui é bug latente que só aparece em produção.

---

## 5. Configuração

- [ ] Um único mecanismo de configuração para os quatro RPAs
- [ ] Separação clara entre configuração comum e específica de cada RPA
- [ ] Nenhuma credencial no código ou no repositório
- [ ] Existe arquivo de exemplo, sem valores reais
- [ ] Configuração de ambiente (teste × produção) é explícita e óbvia

### 5.1 🔴 Premissas 10.3 e 10.4 da V2

A V2 exige que regras de negócio e tabelas de consulta sejam **editáveis e gerenciáveis pelo usuário**:

- [ ] Nenhum **valor de tarifa** constante no código — vem de `tbl_detraf_tarifas`
- [ ] Nenhum **mapeamento descritor → remuneração** constante — vem de `tbl_detraf_mapeamento_descritores`
- [ ] Nenhum **limiar** constante (1%, `0,9635`)
- [ ] Nenhum **índice de coluna fixo** na leitura de arquivos — requisito do risco de novo imposto em 2028
- [ ] EOTs da Vivo (011, 200, 9\*\*) são configuração, não literal

⚠️ Se algum destes já estava fixo nos projetos de origem, corrigir aqui **muda comportamento**. Registre e trate como item explícito, não como efeito colateral da padronização.

---

## 6. Acesso a dados

- [ ] Um único mecanismo de conexão ao banco WebFat
- [ ] Nenhuma string de conexão duplicada
- [ ] Consultas parametrizadas — nenhuma concatenação de SQL com dado externo
- [ ] Política de transação consistente entre os quatro RPAs
- [ ] Nomes de tabela e campo escritos uma única vez

---

## 7. Logging

- [ ] Um único mecanismo de logging
- [ ] Formato uniforme
- [ ] Níveis usados com o mesmo significado nos quatro RPAs
- [ ] É possível correlacionar uma execução ponta a ponta (operadora, mês, RPA)
- [ ] Nenhuma credencial ou dado sensível em log
- [ ] O caminho até o alerta do WebFat (vermelho, sem detalhamento) é o mesmo em todos

---

## 8. Tratamento de erro

- [ ] Uma única política, aplicada de forma consistente
- [ ] O comportamento da V2 ("o robô seguirá para o próximo processamento") está implementado de uma só forma
- [ ] A distinção entre erro do arquivo **da operadora** (aciona a operadora) e erro do arquivo **de expectativa** (WebFat) é feita num único ponto
- [ ] Passos irreversíveis (envio de e-mail, numeração CT, carga no AGI, evento de recuperação) estão explicitamente marcados no código
- [ ] Os pontos de retomada estão documentados

---

## 9. Integrações

- [ ] Toda automação do Outlook passa pela mesma camada
- [ ] Toda automação do AGI passa pela mesma camada
- [ ] Autenticação no AGI é resolvida num único ponto
- [ ] Confirmação de sucesso das operações de UI é verificada da mesma forma

---

## 10. Dependências

- [ ] Uma única declaração de dependências, ou um esquema consistente entre os RPAs
- [ ] Versões fixadas
- [ ] Nenhuma biblioteca duplicada resolvendo o mesmo problema (duas de Excel, duas de banco, duas de automação de UI)
- [ ] Nenhuma dependência que veio de um projeto de origem e não é mais usada

---

## 11. Documentação do código

- [ ] Cada RPA tem README: o que faz, gatilho, como executar, o que precisa de ambiente
- [ ] A base comum tem README: o que contém e por que cada componente está lá
- [ ] Regras de negócio não óbvias apontam para a HU e para o item da V2
- [ ] Pontos com **pendência aberta** estão marcados no código, com a pendência nomeada

---

## 12. Testes

- [ ] Mesma estrutura e mesma forma de executar nos quatro RPAs
- [ ] Mesmo framework
- [ ] Massa de dados de teste organizada de forma consistente
- [ ] Nenhum teste toca produção
- [ ] Testes de passos irreversíveis usam ambiente isolado (e-mail de teste, AGI de teste, contador CT isolado)

---

## 13. Fechamento

- [ ] Nenhum RPA destoa dos demais em estrutura, nomes ou configuração
- [ ] A base comum não é um mosaico de convenções
- [ ] Toda alteração de comportamento causada pela padronização foi registrada e justificada
- [ ] `projetos-origem/` continua intocada
