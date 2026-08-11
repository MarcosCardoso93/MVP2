# Rodada de decisões de 2026-08-05 — 16 pendências respondidas

> ⚠️ **Este é um plano, não o estado do repositório.** As decisões abaixo foram
> tomadas em 2026-08-05, mas **nenhuma das fases A–I foi executada ainda**. O
> `duvidas-pendentes.md` continua sendo a fonte do status; ele só refletirá estas
> decisões quando a Fase I rodar.

## Contexto

O GP/dev (Btime) revisou as 26 pendências abertas e decidiu o destino de cada uma.
**Quatro viraram trabalho de código**, seis fecharam, e as demais vão para um
documento de encaminhamento ao cliente.

O saldo previsto: as pendências abertas caem de **26 para 10**, e todas as 10
restantes passam a depender exclusivamente de terceiros.

---

## As decisões

### Fecham agora (6)

| # | Decisão | Efeito |
|---|---|---|
| **Q7** | A HU-20 **fica no escopo** | Fecha a pergunta que a V2 (¶706) mandava confirmar. O kill-switch deixa de ser dúvida de escopo e passa a ser só proteção de ambiente |
| **Q1** | **Dia 5, configurável no `.env`** | O `DETRAF_DIA_LIBERACAO` deixa de ser "placeholder" e vira decisão nossa, registrada como tal — a V2 removeu a regra, a V1 a tinha |
| **N9** | Os códigos internos bastam | A V2 (¶340) pede erro *"sem detalhamento, apenas com alerta em vermelho"* — um de-para oficial não é requisito de produto |
| **N11** | **0,01 configurável** | `TOLERANCIA_VERIFICACAO` já existe; fica registrado como escolha nossa, ajustável sem tocar no código |
| **N5** | A pasta `AI/`/`TODO/` do P4 já não faz falta | Os inventários cobrem o que ela traria |
| **N6** | Idem, declaração de dependências | O `requirements.txt` unificado está consolidado e testado |

### Ficam como estão (4)

**N3** — manter a rejeição da expectativa sem `R$_Bruto`: falhar alto é melhor que
comparar coluna errada em silêncio. **Q22** — o código funciona com o schema
presumido. **Q14** — o `DE_EBT_..._MODELO` segue fora de escopo, agora
reconfirmado sabendo que é acréscimo da V2. **N12** — a HU-21 será entregue
depois; o `rpa4_retificacao/` fica preparado e a ficha do AGI mantém o gatilho.

---

# Fase A — Q25: duas cartas, dois números CT

Hoje `_gerar_env_e_carta` emite **uma** carta, com `_cenario_da_carta` escolhendo
um cenário para o documento inteiro ("prevalece COM retenção"). Passa a
emitir **uma carta por cenário**, cada uma com o seu número CT.

**Onde:** `rpa3/src/services/geracao_env_carta.py` e o
`_gerar_env_e_carta` do controller.

- separar as linhas contestadas por cenário (`geracao_ext.eh_com_retencao` já
  classifica);
- para cada cenário presente, resolver um número CT e renderizar uma carta com
  **as tabelas daquele cenário**;
- `ResultadoOperadora.carta` vira lista.

⚠️ **Uma decisão de desenho vem junto, e é do desenvolvedor, não do cliente:** o `_ENV`
**continua único**. O nome dele (`Base Contestação_{op}_{mes}_ENV`) não tem
cenário, e ele é o anexo de dados da contestação inteira. Duas cartas + um `_ENV`,
e a HU-15 anexa os três. Dois `_ENV` seriam mudança de nomenclatura, e ficam
como alternativa registrada.

⚠️ **Consome dois números da sequência CT no mesmo mês** para a mesma operadora —
que é exatamente o que a Q18 abaixo protege.

---

# Fase B — Q18: trava na numeração CT

A seção crítica não é só a leitura: é **ler o último número → gravar a carta com
ele**. Dois processos entre esses dois passos emitiriam o mesmo número.

**Onde:** `geracao_env_carta.obter_proximo_numero_carta` e `gerar_arquivo_carta`.

→ Trava por arquivo na pasta de controle CT (`.numeracao.lock`, criado com
`O_CREAT|O_EXCL`), com timeout e liberação garantida. A trava cobre o par
leitura+gravação, não cada um isolado.

Fica mais necessária agora: a Fase A faz a **mesma execução** consumir dois
números seguidos.

---

# Fase C — Q21: pasta de expectativa vazia acusa

Hoje uma pasta de `PASTAS_EXPECTATIVAS` que não existe, ou existe sem arquivo
válido, é ignorada em silêncio — e o efeito é grave: sem expectativa, a variação dá
100% e **toda a operadora é contestada indevidamente**.

**Onde:** `rpa2/src/services/validacao_detrafs.py::_preparar_arquivos_expectativa`
e o equivalente em `batimento_detraf.py`.

→ `logger.error` nomeando a pasta, e a contagem por pasta no resumo final. Não
aborta — uma pasta vazia pode ser legítima —, mas para de passar batido.

---

# Fase D — Q24: a regra do ¶942

> *"Quando acontece a contestação com retenção, o robô também preenche a coluna de
> contestação da remuneração no EC para a EOT da Vivo atrelada à contestação com o
> valor bruto da Diferença apresentada aba Contest."*

Está no bloco antigo da V2 **e na V1** (HU-19: *"Coluna de contestação preenchida
quando houver retenção"*), e **não** no texto vigente.

## ⚠️ Conflito entre duas das decisões desta rodada

O ¶942 pede **uma coluna de contestação**, separada do `vb_diferenca` — que hoje é
gravado para **todas** as linhas, com ou sem retenção. Nossa tabela não tem essa
coluna. Implementar significa **acrescentá-la a um schema presumido** — e a
resposta da Q22 (DDL) foi "deixar como está".

**Precedente que resolve:** a coluna `remuneracao` foi acrescentada exatamente
assim, em 2026-07-28, por decisão do GP/dev, com o DDL pendente — e sem ela o RPA 3 nunca casaria
uma linha escrita pelo RPA 2.

→ Nova coluna `vb_contestacao` em `tbl_rpa_log_detraf_despesa_contestacao`,
preenchida **só nas linhas COM retenção**, com o valor bruto da diferença.
`preparar_atualizacoes_despesa_contestacao` passa a recebê-la; o
`preparar_banco_dev.py` a acrescenta ao SQLite de desenvolvimento.

**Registro como acréscimo da unificação**, na mesma linha do `remuneracao`, e ele
entra no documento de encaminhamento para o DBA confirmar.

---

# Fase E — Q16: contatos por arquivo, como ponte

`buscar_destinatarios` devolve `[]` porque a "tabela de contatos do WebFat" **não
existe na V2**. A ponte: ler de um arquivo de configuração até a tabela aparecer.

**Onde:** `rpa3/src/services/envio_email_contestacao.py`.

→ `CAMINHO_CONTATOS_OPERADORAS` no `.env`, apontando para um CSV
`operadora;emails` (múltiplos separados por vírgula). Sem o arquivo, o
comportamento atual se mantém: recusa o envio com aviso citando a Q16.

A troca pela tabela, quando ela existir, é substituir o corpo de uma função —
por isso a leitura fica isolada nela.

⚠️ Isto **desbloqueia a HU-15**: com o arquivo preenchido e
`PERMITIR_ENVIO_EMAIL=true`, o robô passa a enviar de verdade. O kill-switch
continua sendo a única proteção.

---

# Fase F — Q7 e Q1: fechar as duas no código

- **Q7** — `verificacao_relatorio.py` e o controller deixam de dizer "a V2 pede
  confirmação de escopo". O `PERMITIR_ACESSO_AGI` continua, com a justificativa
  trocada: é proteção de ambiente (Q20), não dúvida de escopo;
- **Q1** — `configuration.py` para de chamar `DETRAF_DIA_LIBERACAO` de
  "placeholder disponível até a regra ser definida". Passa a registrar: a V2
  removeu a periodicidade, a V1 dizia "após o dia 05", e **adotamos o dia 5**,
  configurável. O mesmo nos `main.py` do RPA 1 e do RPA 2.

---

# Fase G — Q20: roteiro de validação em produção

Decisão: validar contra produção, com cuidado. O modo "só leitura" já é
possível com a combinação de kill-switches:

```
PERMITIR_ACESSO_AGI=true      # abre o AGI e baixa o relatório
PERMITIR_UPLOAD_AGI=false     # não sobe nada
PERMITIR_ENVIO_EMAIL=false    # não envia e-mail
```

→ Escrever `docs/03-checklists/checklist-validacao-agi.md`: o que essa combinação
garante, quais imagens são exercitadas em cada passo, o que observar quando o
`locateOnScreen` falha, e a ordem para ligar os outros dois switches depois. Mais
um teste que **prova** que a combinação não escreve — dublê que explode em upload
e em envio.

⚠️ A HU-20 baixa e reescreve o CSV; fora isso, nenhuma escrita. O login em
produção acontece — é inerente.

---

# Fase H — Documento de encaminhamento

`docs/04-relatorios/pendencias-para-o-cliente.md`, agrupado por destinatário, com
a citação literal da V2, o que trava e o que já foi tentado:

| Destinatário | Pendências |
|---|---|
| **PO** | Q6 (layout CBS/IBS no "isnumos"), Q11 (¶643 diz "minutagem" numa coluna `VLR_BRUTO`), Q13, Q16b, N4 |
| **DBA / GP-Vivo** | Q22 (DDL), N1 (nome da tabela de log), N10 (formato de `tarifa`), **e a coluna `vb_contestacao` da Fase D** |
| **Vivo** | Q17 (nome de operadora que muda — a própria V2 declara "Pendência Vivo") |
| **GP-Vivo** | Q23, e o que sobra da Q20 |
| **Solicitante** | Q12 (a V2 diz "aguardando informação do solicitante") |

Mais as duas 🔴 que continuam de fora deste bloco por já terem tratamento: **Q16**
(ponte na Fase E, mas a tabela definitiva continua sendo pergunta) e **N3**
(rejeição mantida, mas a contradição entre a V2 e o arquivo real precisa de
resposta).

---

# Fase I — Atualizar o painel

`duvidas-pendentes.md`: registrar a rodada, fechar as seis, mover as quatro para
"resolvida por decisão nossa" e deixar o painel com **10 pendências abertas**,
todas dependentes de terceiros.

Também: `matriz-de-rastreabilidade.md` (Q7 fechada muda a nota da HU-20),
`riscos-conhecidos.md` (R13 — a numeração CT deixa de ser risco com a trava),
`unificado/README.md` e `.env.example`.

---

# Verificação

1. `unificado\.venv\Scripts\python executar_testes.py` — quatro suítes verdes
2. **Q25** — operadora com linhas COM e SEM retenção produz **duas** cartas, com
   números CT consecutivos, cada uma com as tabelas do seu cenário
3. **Q18** — dois processos concorrentes não emitem o mesmo número (teste com
   trava já adquirida)
4. **Q21** — pasta de expectativa ausente gera `error` nomeando-a
5. **Q24** — linha COM retenção grava `vb_contestacao`; linha SEM retenção não
6. **Q16** — com o CSV de contatos preenchido, `buscar_destinatarios` devolve os
   e-mails; sem o arquivo, o envio continua sendo recusado com aviso
7. **Q20** — com `PERMITIR_ACESSO_AGI=true` e os outros dois `false`, nenhum
   upload e nenhum `Send()` — provado por dublê
8. `git status --short projetos-origem` vazio
9. Nenhuma credencial em código ou `.env.example`
