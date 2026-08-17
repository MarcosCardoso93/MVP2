# Épico 5 - Carga no AGI (Detraf Despesa - MVP2)

Pacote de trabalho para o **Épico 5** do cronograma (HU-17 e HU-18), montado seguindo a
mesma estrutura de pastas do exemplo de referência `RPA_DETRAF_RECEITA` (MVP1 de Receita,
já em produção/homologação). Este README documenta o que já veio pronto reaproveitado do
exemplo, o que foi adaptado, e o que ainda precisa ser criado do zero.

Legenda: ✅ Pronto (reaproveitado)  |  🔄 Adaptado (existe, mas com lógica alterada/nova)  |  🆕 A criar (não existe no exemplo)

## Escopo

| História | Descrição | Status geral |
|---|---|---|
| HU-17 | Upload dos arquivos EXT/INT no AGI (Detraf > Importar Dados) | 🔄 Maior parte pronta, falta a regra de cenário e a evidência |
| HU-18 | Upload do arquivo de contestação no AGI (Contestação > Gerenciar) | 🆕 Esqueleto criado, mas telas/imagens/lógica ainda por fazer |

## Estrutura da pasta

```
EPICO_5_Carga_AGI_Despesa/
├── main.py                                    -> ponto de entrada (python main.py)
├── .env.example                                -> variáveis necessárias (copiar p/ .env e ajustar)
├── requirements.txt                            -> copiado do exemplo (mesmas libs)
├── src/
│   ├── config/
│   │   ├── config.py                           🔄 adaptado (novos nomes de pasta/env da Despesa)
│   │   └── conexao.py                          ✅ copiado sem alteração
│   ├── main/
│   │   └── process_handle.py                   🔄 adaptado (orquestra só HU-17 + HU-18)
│   ├── services/AGI/
│   │   ├── AGI_config.py                       ✅ copiado sem alteração
│   │   ├── Upload_Detraf_EXT_INT.py             🔄 adaptado do Upload_DI_DE.py (HU-17)
│   │   └── Upload_Contestacao.py                🆕 esqueleto novo (HU-18)
│   ├── utils/
│   │   └── utils.py                            ✅ copiado sem alteração
│   └── view/imagens/
│       ├── AGI_CONFIG/                         ✅ copiado sem alteração (login/produção do AGI)
│       ├── AGI_Upload_Detraf/                   🔄 copiado do exemplo, precisa VALIDAR na VM (ver LEIA-ME_VALIDACAO.md)
│       └── AGI_Upload_Contestacao/              🆕 pasta vazia (ver MANIFESTO_IMAGENS.md)
└── data/
    ├── AGI/EXT/  AGI/INT/                       -> arquivos que o Épico 4 entrega para o Épico 5 consumir
    ├── Contestacoes/                            -> arquivos CONT_PROC_MASCARA_<operadora>_<aaaamm>
    ├── exports_erros/
    └── Temp/
```

## ✅ O que está pronto (reaproveitado 1:1 do exemplo)

- **`AGI_config.py`** inteiro: login, abertura/fechamento do AGI, navegação por imagem
  (`_click`, `_wait_appear`), tratamento do diálogo nativo do Windows (`_Janela_salvar`). Não
  tem nada específico de Receita, serve para Despesa sem alteração.
- **`conexao.py`** (classe `Banco`): camada genérica de acesso a banco (insert/update/log).
  Reaproveitada de forma direta; só falta apontar para as tabelas novas (ver seção "A criar").
- **`utils.py`**: funções de normalização de texto, sem relação com Receita/Despesa.
- **Imagens de login/produção do AGI** (pasta `AGI_CONFIG/`): tela de login é a mesma para
  qualquer fluxo dentro do AGI.
- **`requirements.txt`**: mesmas dependências (pyautogui, pywinauto, pandas, mysql-connector etc.).
- **Padrão de kill-switch** `PERMITIR_UPLOAD_AGI`: permite rodar tudo em modo seguro (sem subir
  nada em produção) até o fluxo estar validado.

## 🔄 O que foi adaptado (existe no exemplo, mas precisa de ajuste)

### HU-17 — `Upload_Detraf_EXT_INT.py`
- Estrutura de navegação (Detraf > Importar Dados) e upload de arquivo (`_upload_um_arquivo`)
  vieram praticamente copiados do `Upload_DI_DE.py`.
- **Falta implementar de verdade** (hoje é só esqueleto/TODO no código):
  1. `_montar_lista_upload`: regra de cenário — EXT sempre sobe, INT só quando o cenário for
     "contestação com retenção". No exemplo, o upload sobe cegamente tudo que está na pasta;
     aqui precisa checar o cenário vindo do Épico 4.
  2. Ordem "um de cada vez, por operadora" (To Be MVP2 §313) — ainda não implementada.
  3. Avaliar se a lógica de consolidação em lotes de 17.900 linhas do exemplo
     (`_consolidar_arquivos`) é necessária aqui — provavelmente **não**, já que o Épico 4 deve
     entregar 1 arquivo pronto por operadora. **Confirmar com quem está fazendo o Épico 4.**
- **Imagens copiadas, mas não validadas**: ver `src/view/imagens/AGI_Upload_Detraf/LEIA-ME_VALIDACAO.md`
  — mesma tela do AGI, mas resolução/tema da VM de Despesa pode exigir recaptura.
- Tratamento de erro pós-upload (linha vermelha na grid) foi copiado como referência, mas
  **não validado** para a tela de Despesa.

## 🆕 O que precisa ser criado do zero (não existe no exemplo)

### HU-18 — `Upload_Contestacao.py`
Não existe **nenhum** código equivalente no exemplo de Receita (a tela "Contestação >
Gerenciar" nunca foi automatizada lá). O esqueleto criado segue o padrão de código mais
parecido do projeto (`Tratativa_Erro.py`: navega 1x, depois faz upload em loop), mas:

1. **Capturar 4 imagens novas** — checklist completo em
   `src/view/imagens/AGI_Upload_Contestacao/MANIFESTO_IMAGENS.md`:
   - `bnt_contestacao.png` (menu)
   - `bnt_submenu_gerenciar.png` (submenu)
   - `bnt_upload_contestacao.png` (botão upload da tela)
   - `bnt_salvar_contestacao.png` (botão Salvar, passo que só existe nesta tela)
2. Confirmar o título do diálogo nativo de upload nessa tela (pode ser igual ao já mapeado
   `"Select file for upload by {host}"`, ou diferente).
3. Implementar a lógica real dos métodos `_navegar_contestacao_gerenciar` e
   `_upload_um_arquivo_contestacao` (hoje são esqueletos comentados).
4. Definir se essa etapa só roda em cenário de contestação (com/sem retenção) — no cenário
   "sem contestação" ela não deve executar.

### Evidência de sucesso (print automático)
Requisito explícito do To Be (item 4.7.3), **não existe rotina equivalente no exemplo** — lá
só há captura de tela para *erro* (linha vermelha), nunca para confirmar sucesso. Os métodos
`_capturar_evidencia_sucesso` já estão no esqueleto (em ambos `Upload_Detraf_EXT_INT.py` e
`Upload_Contestacao.py`), mas o `pyautogui.screenshot().save(...)` real ainda não foi
implementado — só o TODO.

### Tabelas de log da Despesa
O To Be MVP2 cita `tbl_rpa_log_detraf_despesa_arquivos` e `tbl_rpa_log_detraf_despesa_contestacao`
como destino dos registros de upload. O exemplo de Receita usa `marcar_enviado_agi` apontando
para `tbl_encontro_contas` — o padrão de código (`Banco._atualizar_banco`/`_inserir_banco`) é
reaproveitável, mas:
- As tabelas/colunas da Despesa ainda precisam ser confirmadas com o time de banco.
- Não existe hoje nenhum método em `conexao.py` apontando para essas duas tabelas — precisa
  ser adicionado.

## Pré-requisito herdado do exemplo

- **Python 3.12+ obrigatório.** `AGI_config.py` foi copiado 1:1 do exemplo e usa f-strings com
  aspas aninhadas (PEP 701, só suportado a partir do 3.12) — testado aqui e confirma o mesmo
  requisito já documentado no README do `RPA_DETRAF_RECEITA`. Todos os outros arquivos deste
  pacote foram validados (`py_compile`) sem erro em Python 3.10, mas a VM final precisa ter
  3.12+ por causa deste arquivo reaproveitado.

## Checklist antes de rodar na VM

1. Copiar `.env.example` para `.env` e ajustar os caminhos (marcados com TODO no arquivo).
2. Criar as variáveis de ambiente do Windows (`RPA_DETRAF_DESPESA_AGI_USER/PASSWORD`,
   `RPA_DETRAF_DESPESA_DB_USER/PASSWORD`) — confirmar antes se é credencial própria ou a
   mesma já usada na Receita.
3. Validar as imagens copiadas em `AGI_Upload_Detraf/` (rodar um teste de reconhecimento).
4. Capturar as 4 imagens que faltam em `AGI_Upload_Contestacao/`.
5. Confirmar com o Épico 4 o formato/nome exato dos arquivos EXT/INT/CONT_PROC_MASCARA que
   serão entregues como entrada para este Épico 5.
6. Rodar primeiro com `PERMITIR_UPLOAD_AGI=False` (modo seguro) para validar toda a
   navegação sem subir nada em produção.
7. Só então mudar para `PERMITIR_UPLOAD_AGI=True` e testar o upload real em homologação.
