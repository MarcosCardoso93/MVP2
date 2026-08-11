# Inventário — Projeto 7: Épico 5 (Carga no AGI)

- **Pasta:** `projetos-origem/projeto-7-epico-5-carga-agi/`
- **HUs:** HU-17 (upload `_EXT`/`_INT`) e HU-18 (upload `CONT_PROC`)
- **RPA de destino:** RPA 3
- **Recebido em:** 2026-08-04

---

## 1. O Épico 5 existe — pendência Q3 resolvida

A pasta `projeto-7-epico-5-carga-agi/` estava **reservada** desde a etapa
documental, criada porque o Épico 5 não aparecia em nenhum dos seis projetos
informados. Confirmou-se depois que ele **não estava no Projeto 4** — que não tem
nenhuma automação de interface.

Restavam duas hipóteses: existir um sétimo projeto, ou as HUs nunca terem sido
implementadas. **Era a do sétimo projeto** — a **hipótese 2** na numeração original
da Q3 (1 = está no P4, 2 = sétimo projeto, 3 = não implementada). A pendência
**Q3** está resolvida.

---

## 2. Estrutura e execução

```
main.py                                     4 linhas
src/
├── config/     config.py (78) · conexao.py (160)
├── main/       process_handle.py (22)
├── services/AGI/
│   ├── AGI_config.py              (269)   login e navegação no AGI
│   ├── Upload_Detraf_EXT_INT.py   (200)   HU-17
│   └── Upload_Contestacao.py      (148)   HU-18
├── utils/      utils.py (24)
└── view/imagens/                          27 PNGs
data/           AGI/EXT · AGI/INT · Contestacoes · exports_erros · Temp
```

| Item | Valor |
|---|---|
| Ponto de entrada | `main.py` → `process_handle.run()` |
| Testes | **nenhum** |
| Kill-switch | ✅ `PERMITIR_UPLOAD_AGI`, default seguro |
| Python | **3.12+ obrigatório** — `AGI_config.py` usa f-strings aninhadas (PEP 701) |

Mesma origem do P5: o `RPA_DETRAF_RECEITA` (MVP1). Ver o inventário do P5 §2 para
a tabela de divergências de arquitetura, que é idêntica.

---

## 3. 🔴 Credencial do AGI exposta

O `.env` deste projeto traz **preenchidos**:

| Variável | Tamanho |
|---|---|
| `RPA_DETRAF_DESPESA_AGI_USER` | 8 caracteres |
| `RPA_DETRAF_DESPESA_AGI_PASSWORD` | 28 caracteres |

Não é vazamento de repositório — `/projetos-origem` está no `.gitignore` —, mas é
credencial de acesso ao AGI num arquivo que circulou fora do controle de versão.
**Escalado; vale avaliar rotação com quem administra o acesso.**

O código unificado não herda o padrão: credencial só por variável de ambiente,
com `.env.example` sem valores.

---

## 4. Mapeamento HU → código

### HU-17 — `Upload_Detraf_EXT_INT.py` (200 linhas, 8 TODO)

| Parte | Status |
|---|---|
| Navegação `Detraf > Importar Dados` | ✅ reaproveitada do exemplo |
| Upload de um arquivo por vez | ✅ `_upload_um_arquivo` |
| Detecção de erro pós-upload (linha vermelha) | ⚠️ copiada, **não validada** na tela de Despesa |
| **Regra de cenário** — EXT sempre, INT só COM retenção | ❌ **não implementada** |
| Ordem "um de cada vez, por operadora" | ❌ não implementada |
| Evidência de sucesso (screenshot) | ❌ só o TODO |
| Gravar `carga_agi` após o upload | ✅ **implementado em 2026-08-04** — `repositorio_tabelas.atualizar_carga_agi`, chamado pela HU-18 |

`_montar_lista_upload` **está implementado**, mas errado para a V2: varre as
pastas `EXT` e `INT` e devolve tudo, sem olhar cenário nem agrupar por operadora.
No cenário "sem contestação" e "sem retenção" o `_INT` nem deveria existir — mas
se existir na pasta, ele sobe.

⚠️ **O dado para a regra já existe:** `tipo_contestacao` em
`tbl_rpa_log_detraf_despesa_contestacao`, lido por
`comum/dados/repositorio_tabelas.py::obter_tipo_contestacao`. E o RPA 3 já tem
`geracao_ext.py::eh_com_retencao`, que faz exatamente essa classificação. Falta
ligar — o que é desenvolvimento, fora desta rodada.

### HU-18 — `Upload_Contestacao.py` (148 linhas, 8 TODO)

O próprio arquivo declara: *"TUDO abaixo é ESQUELETO/TODO"*.

> ⚠️ **Desatualizado (2026-08-04).** A HU-18 foi escrita na migração — as 4
> imagens existiam, e a navegação segue o padrão validado da HU-17. Ela é
> orquestrada e grava `carga_agi`. O que **continua** verdadeiro: nunca executou
> contra o AGI, porque não há ambiente de teste (Q20).

`_navegar_contestacao_gerenciar` e `_upload_um_arquivo_contestacao` são corpos
comentados. Não existia nada equivalente no exemplo de Receita — a tela
"Contestação > Gerenciar" nunca foi automatizada lá.

✅ **As 4 imagens que faltavam já foram capturadas** (`bnt_contestacao.png`,
`bnt_submenu_gerenciar.png`, `bnt_upload_contestacao.png`,
`bnt_salvar_contestacao.png`). O `MANIFESTO_IMAGENS.md` que pedia a captura veio
junto e já está atendido.

Falta confirmar o título do diálogo nativo de upload nessa tela — pode ser igual
ao já mapeado (`"Select file for upload by {host}"`) ou não.

---

## 5. `AGI_config.py` — o ativo reaproveitável

269 linhas, copiadas sem alteração do exemplo. API pública:

`Inicializando_AGI` · `Fechar_AGI` · `Verificando_janela_aberta` ·
`Acessando_producao_AGI` · `Login_AGI_producao` · `Baixar_Remessa`

E os utilitários de automação por imagem: `_click(img, tentativa, confidence)`,
`_wait_appear(img, timeout, confidence)`, `_Janela_salvar(diretorio, nome_janela)`
— este último trata o diálogo nativo do Windows.

Não tem nada específico de Receita; serve à Despesa sem alteração.

**Fica no RPA 3, não sobe para `comum/`.** É uma ocorrência única — o RPA 4 (HU-21)
também usaria o AGI, mas o **P6 não foi entregue**. Falha o critério C1. Vira
candidata à base comum quando o P6 chegar; a ficha fica registrada como rejeitada
por C1, com o gatilho de reavaliação anotado.

---

## 6. ⚠️ Caminho de arquivo plano

`DIRETORIO_PASTA_EXT` e `DIRETORIO_PASTA_INT` apontam para pastas planas
(`data/AGI/EXT`, `data/AGI/INT`). A estrutura real é
`{operadora}/{ano}/{aaaamm}/AGI/`, e `comum/arquivos/estrutura_pastas.py` já tem
`caminho_agi()`.

Mesmo problema do P5 (§6 daquele inventário) e do contrato RPA 1 → RPA 2. É a
**segunda** ocorrência nesta leva. Reconciliar pelo helper comum.

Isso também é o que permite a regra "por operadora": com a estrutura correta, a
operadora vem do caminho.

---

## 7. Camada de banco

`conexao.py` é quase idêntico ao do P5 — diferem em **duas linhas**: o rótulo do
RPA no log e o nome da tabela (`tbl_rpa_log_detraf_despesa_arquivos` aqui,
`..._contestacao` no P5).

Está **desligado** no código: o import de `Banco` e a atribuição `self.db` estão
comentados no `Upload_Detraf_EXT_INT.py`.

**Decisão:** migrar para `comum/dados/`. Os dois nomes de tabela já estão em
`comum/dados/tabelas.py` com os mesmos valores.

---

## 8. Dependências

`requirements.txt` idêntico ao do P5, com 28 pacotes. Os que a automação por
imagem exige: `pyautogui`, `pywinauto`, `opencv-python`, `pillow`, `pyperclip`,
`psutil`, `comtypes`.

⚠️ **Dois problemas a não herdar:**
- `mysql-connector-python` — desnecessário; a camada unificada usa
  SQLAlchemy + PyMySQL;
- `dotenv==0.9.9` **e** `python-dotenv==1.2.1` juntos. O `dotenv` 0.9.9 é um
  pacote **diferente**, um stub no PyPI que conflita com o `python-dotenv`. Fica
  só o segundo.

---

## 9. Achados

### 🔴 Críticos
1. **Credencial do AGI preenchida no `.env`** (§3)
2. **HU-18 é esqueleto declarado** — não executa
3. **HU-17 sem a regra de cenário** — sobe o `_INT` mesmo quando não deveria

### 🟡 Relevantes
4. Caminho de arquivo plano, ignorando a estrutura de pastas (§6)
5. Imagens de `AGI_Upload_Detraf/` **não validadas** na VM de Despesa — vieram da
   Receita, e resolução/tema podem exigir recaptura (`LEIA-ME_VALIDACAO.md`)
6. `REGION = (20, 241, 1880, 740)` — área de tela fixa, herdada do exemplo
7. Detecção de erro por linha vermelha **não validada** na tela de Despesa
8. Camada de banco paralela e **desligada**
9. `print()` em vez de logger
10. **Sem nenhum teste**
11. `dotenv` 0.9.9 no requirements (§8)

### 🟢 Observações
- `AGI_config.py` é sólido e reaproveitável sem alteração
- As 4 imagens da HU-18 **já foram capturadas** — o manifesto está atendido
- Kill-switch `PERMITIR_UPLOAD_AGI` no padrão certo. **É especialmente importante
  aqui:** não há ambiente de teste do AGI (pendência Q20), então sem ele a única
  forma de exercitar o fluxo seria contra produção

---

## 10. Conclusão

**Escopo real:** a HU-17 tem a mecânica pronta e a regra de negócio faltando; a
HU-18 tem as imagens e o esqueleto, sem lógica.

**Complexidade de migração:** **baixa** — reorganizar 3 services e 27 imagens,
trocar a camada de banco e o logger. O que é caro é *completar* as duas HUs, e
isso depende de validação na VM, que não temos.
