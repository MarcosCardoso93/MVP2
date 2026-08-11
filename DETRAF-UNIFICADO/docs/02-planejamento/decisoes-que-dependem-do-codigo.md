# Decisões que Dependem da Análise do Código

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Registro explícito do que **não** foi decidido nesta etapa, e por quê.

> Sem o código, qualquer decisão aqui seria suposição apresentada como projeto. Este documento existe para que a próxima etapa saiba exatamente o que precisa decidir — e para que ninguém confunda o silêncio desta etapa com omissão.

Cada item traz: a decisão pendente, **o que precisa ser observado no código** para tomá-la, e em que fase do [`plano-geral-da-unificacao.md`](plano-geral-da-unificacao.md) ela cabe.

---

## 1. Estrutura de pacotes e organização do repositório

**Pendente.** Como `unificado/` se organiza internamente; onde vive a base comum; como cada RPA referencia o que é comum; se é um pacote instalável, um caminho relativo ou outra coisa.

**Observar no código.** Como cada projeto de origem se organiza hoje; se já existe alguma forma de compartilhamento entre eles; qual gerenciador de dependências e qual forma de empacotamento estão em uso; se os projetos rodam do diretório ou instalados.

**Fase.** F4.

---

## 2. Fronteiras de módulo dentro de cada RPA

**Pendente.** Como o fluxo de cada RPA se divide internamente.

**Observar.** Onde o código já quebra naturalmente; quais funções são chamadas de mais de um ponto; onde estão os limites de transação e os pontos de leitura/escrita externa.

**Fase.** F4.

---

## 3. Interfaces, classes, modelos e abstrações

**Pendente.** Toda e qualquer definição de contrato: assinaturas, hierarquias, representação de uma linha de Detraf, de uma operadora, de uma contestação.

**Observar.** Se os projetos usam classes, dicionários, DataFrames ou tuplas; se há alguma representação comum de "linha de Detraf" ou cada um reinventou a sua; que biblioteca de manipulação tabular está em uso.

**Fase.** F4.

⚠️ Esta é a decisão mais tentadora de antecipar e a mais cara de errar. A representação da linha de Detraf atravessa os quatro RPAs — escolhê-la sem ver como cada projeto já a trata é apostar.

---

## 4. Estratégia de configuração e credenciais

**Pendente.** Onde vivem caminhos de rede, strings de conexão, endereços, credenciais do usuário robótico, e como se separa configuração por RPA de configuração comum.

**Observar.** Se há `.env`, `.ini`, `.json`, constantes no código ou variáveis de ambiente; **se há credencial commitada** (achado de segurança, reportar imediatamente); como o "usuário robótico" da tabela GSA é resolvido.

**Fase.** F4, mas **credencial exposta se reporta em F1**.

---

## 5. Tratamento de erro e política de retomada

**Pendente.** O que acontece quando um passo falha; onde estão os pontos de retomada; como não repetir passos irreversíveis.

**Observar.** Como cada projeto trata exceção hoje; se há estado persistido que permita retomar; se a V2 ("o robô seguirá para o próximo processamento") está implementada assim de fato.

**Fase.** F4.

⚠️ **Ponto crítico do RPA 3.** A cadeia mistura passos irreversíveis (e-mail à operadora, consumo de numeração CT, carga no AGI) com passos reexecutáveis. O relatório de separação já sugere isolar a carga no AGI para permitir reprocessar sem reenviar a carta. Onde colocar o ponto de retomada depende de como o código estrutura esses passos hoje.

---

## 6. Logging e observabilidade

**Pendente.** Formato, destino, nível, correlação entre execuções, e como isso convive com o requisito da V2 de mostrar o erro no WebFat "sem detalhamento, apenas com alerta em vermelho".

**Observar.** O que cada projeto registra hoje e onde; se há correlação por operadora/mês; se o log alimenta o WebFat ou é separado.

**Fase.** F4.

---

## 7. Orquestração e gatilhos

**Pendente.** Como cada RPA é disparado; como o RPA 3 detecta a sinalização do analista; como o RPA 4 é acionado; se rodam na mesma máquina; como se evita concorrência sobre Outlook, AGI e pastas de rede.

**Observar.** Se há agendador, serviço, polling ou execução manual; se há trava de execução; se algum projeto assume exclusividade de recurso.

**Fase.** F4. ⚠️ Parcialmente bloqueado por pendências da área cliente (data de corte, mecanismo de sinalização).

---

## 8. Granularidade de execução

**Pendente.** Se um RPA processa por operadora, por lote mensal ou por arquivo; e o que isso implica para paralelismo e reprocessamento.

**Observar.** Como o laço principal de cada projeto está estruturado; se há paralelismo; se o estado é acumulado em memória ao longo de todas as operadoras (o que impede processar uma isoladamente).

**Fase.** F4.

⚠️ Consequência direta: com ~1.600 arquivos/mês, processar tudo em memória num único passe pode ser inviável — mas isso depende do tamanho dos arquivos, que não está documentado.

---

## 9. Estratégia de testes

**Pendente.** O que testar, em que nível, com que dados, e como testar o que toca sistemas externos.

**Observar.** Se existe algum teste hoje; se há massa de dados de exemplo; se existe ambiente de teste do AGI e caixa de e-mail de teste.

**Fase.** F4. ⚠️ **A ausência de ambiente de teste do AGI é impedimento para a validação do RPA 3 e do RPA 4** — levantar em F1.

---

## 10. Onde vive a lógica de decisão do analista

**Pendente.** O RPA 2 termina esperando o analista e o RPA 3 começa depois dele. Como essa espera é implementada, e de quem é a responsabilidade de ler a decisão.

**Observar.** Se o P3 tem código de polling ou de espera; se o P4 lê a decisão do banco; se existe uma coluna de estado que hoje cumpre esse papel.

**Fase.** F3/F4.

---

## 11. Composição real do RPA 3

**Pendente.** O RPA 3 recebe código de P4, P5, P6(HU-20) e possivelmente P7. Como esses quatro viram um `main.py` coerente.

**Observar.** Se P4 e P5 já compartilham algo; se P5 é autossuficiente ou depende de artefatos do P4 por caminho de arquivo; se o Épico 5 está dentro do P4.

**Fase.** F3/F4.

---

## 12. Cisão do Projeto 6

**Pendente.** Como separar HU-20 (RPA 3) de HU-21 (RPA 4) dentro do mesmo projeto.

**Observar.** Se as duas HUs compartilham a camada de automação do AGI; se compartilham estado; se a separação é limpa ou entrelaçada.

**Fase.** F3/F4.

⚠️ **Pode desaparecer.** Se a HU-20 for descartada do escopo — a própria V2 questiona se "vale a pena ser mantida" — o P6 fica reduzido à HU-21 e não há cisão. **Confirmar o escopo antes de planejar a cisão.**

---

## 13. Destino do arquivo `Base_Contestação`

**Pendente.** A HU-09 (V2) diz que a `Base_Contestação` não é mais gerada como arquivo. Mas a HU-14 define o `_ENV` como cópia dela. Se ela não existe, de onde sai o `_ENV`?

**Observar.** Se o P3 gera o arquivo, o banco, ou ambos; se o P4 lê o arquivo ou o banco para montar o `_ENV`.

**Fase.** F2 — provavelmente respondida pela simples leitura do código, mas **a decisão sobre qual comportamento manter é do PO**.

---

## 14. Aderência às premissas de configurabilidade

**Pendente.** As premissas 10.3/10.4 da V2 exigem que regras de negócio e tabelas de consulta sejam editáveis pelo usuário. O risco declarado do imposto de 2028 exige que o layout dos arquivos não seja posicional-fixo.

**Observar.** Se há tarifas, mapeamentos descritor→remuneração, limiares (1%, 0,9635) ou índices de coluna **constantes no código**.

**Fase.** F2 para o achado, F4 para a solução.

⚠️ Cada violação encontrada é **dívida técnica a tratar**, não comportamento a replicar. Mas corrigi-la durante a migração viola a regra de "equivalência funcional antes de melhoria" — registre e trate depois.

---

## 15. Escopo real de cada projeto

**Pendente.** Se a fronteira do código coincide com a fronteira das HUs informada.

**Observar.** Se algum projeto contém código de outro épico; se contém código do fluxo de **Receita** (escopo das demandas irmãs ATA0000571/567/572, explicitamente fora deste MVP); se contém código morto.

**Fase.** F2.

---

## Resumo — o que esta etapa deliberadamente não produziu

- ❌ Estrutura definitiva de pacotes
- ❌ Arquitetura final do código
- ❌ Componentes compartilhados específicos (só **candidatos**, marcados como hipótese)
- ❌ Interfaces, classes, módulos, serviços, modelos, abstrações
- ❌ Estratégia de configuração, logging, erro ou teste
- ❌ Estimativa de prazo ou esforço

O que ela produziu: o **entendimento do domínio**, o **mapa de destino**, os **critérios de decisão** e o **roteiro** para tomar cada uma das decisões acima com o código na mão.
