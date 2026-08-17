import csv
import io
import re
import unicodedata
from pathlib import Path
from typing import Optional

import openpyxl

from src.config.logger_config import logger
from src.models.dto.operadora_resultado import OperadoraResultado
from src.models.repository.repositorio_tabelas import bd_tabelas

_CARACTERES_INVALIDOS_PASTA = re.compile(r'[\\/:*?"<>|]')

# Nome da coluna que identifica a operadora credora nos arquivos Detraf.
# Se o layout não tiver essa coluna, usa-se a coluna nesta posição (fallback).
NOME_COLUNA_CREDORA = "credora"
INDICE_COLUNA_FALLBACK = 0

_EXTENSOES_EXCEL = {"xlsx", "xls"}


def extrair_texto_busca_operadora(sender_email: str) -> str:
    """
    Extrai o texto usado para buscar a operadora no WebFat a partir do
    e-mail do remetente.

    Regra atual: parte do domínio antes do primeiro ponto
    (ex.: "contato@vivo.com.br" -> "vivo"). Isolada em função própria
    para ficar fácil de trocar essa regra no futuro.
    """
    dominio = sender_email.split("@")[-1].lower().strip()
    return dominio.split(".")[0]


def _normalizar_eot(valor) -> Optional[str]:
    """Normaliza um valor bruto para o formato EOT (string de 3 dígitos)."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.isdigit():
        return texto.zfill(3)
    return texto


def _indice_coluna_credora(cabecalho: list) -> int:
    """Localiza a coluna 'Credora' pelo nome; se não achar, usa o fallback."""
    for indice, nome_coluna in enumerate(cabecalho):
        if str(nome_coluna).strip().lower() == NOME_COLUNA_CREDORA:
            return indice
    return INDICE_COLUNA_FALLBACK


def _extrair_eot_csv(caminho: Path) -> Optional[str]:
    conteudo_bruto = caminho.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin1"):
        try:
            texto = conteudo_bruto.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None

    try:
        delimitador = csv.Sniffer().sniff(texto.splitlines()[0]).delimiter
    except (csv.Error, IndexError):
        delimitador = ";"

    leitor = csv.reader(io.StringIO(texto), delimiter=delimitador)
    try:
        cabecalho = next(leitor)
        primeira_linha = next(leitor)
    except StopIteration:
        return None

    indice = _indice_coluna_credora(cabecalho)
    if indice >= len(primeira_linha):
        return None
    return _normalizar_eot(primeira_linha[indice])


def _extrair_eot_excel(caminho: Path) -> Optional[str]:
    workbook = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        planilha = workbook.worksheets[0]
        linhas = planilha.iter_rows(max_row=2, values_only=True)
        try:
            cabecalho = next(linhas)
            primeira_linha = next(linhas)
        except StopIteration:
            return None

        indice = _indice_coluna_credora(list(cabecalho))
        if indice >= len(primeira_linha):
            return None
        return _normalizar_eot(primeira_linha[indice])
    finally:
        workbook.close()


def extrair_eot_arquivo(caminho: Path) -> Optional[str]:
    """
    Lê o EOT da operadora credora a partir do próprio arquivo Detraf.

    Procura a coluna "Credora" no cabeçalho (case-insensitive); se não
    encontrar, usa a coluna na posição INDICE_COLUNA_FALLBACK. Nunca lança
    exceção — qualquer falha de leitura/formato retorna None, e quem chama
    decide o que fazer (cair para a regra de domínio).
    """
    try:
        extensao = caminho.suffix.lstrip(".").lower()
        if extensao in _EXTENSOES_EXCEL:
            return _extrair_eot_excel(caminho)
        return _extrair_eot_csv(caminho)
    except Exception as excecao:
        logger.warning(f"Falha ao extrair EOT de '{caminho.name}': {excecao}")
        return None


def normalizar_nome_pasta(nome: str) -> str:
    """Normaliza um nome fantasia para uso seguro como nome de pasta no Windows."""
    sem_acentos = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return _CARACTERES_INVALIDOS_PASTA.sub("_", sem_acentos).strip()


class OperadoraService:
    """Serviço responsável por identificar a operadora de um arquivo Detraf."""

    @staticmethod
    def obter_operadora(caminho_arquivo: Path, sender_email: str) -> OperadoraResultado:
        """
        Identifica a operadora, tentando primeiro pelo EOT lido do próprio
        arquivo Detraf e, se não conseguir, pela regra de domínio do
        remetente (fallback).

        Args:
            caminho_arquivo: Caminho do arquivo Detraf a identificar.
            sender_email: E-mail do remetente do e-mail que trouxe o arquivo.

        Returns:
            OperadoraResultado com o nome fantasia identificado (ou None),
            a flag `identificada` e a `origem` da identificação. Nunca
            lança exceção por operadora não encontrada.
        """
        dominio = sender_email.split("@")[-1].lower().strip() if "@" in sender_email else sender_email.lower().strip()

        eot = extrair_eot_arquivo(caminho_arquivo)
        if eot is not None:
            nome_por_eot = bd_tabelas.buscar_nome_fantasia_por_eot(eot)
            if nome_por_eot is not None:
                return OperadoraResultado(
                    dominio=dominio,
                    nome=normalizar_nome_pasta(nome_por_eot),
                    identificada=True,
                    origem="eot",
                )

        texto_busca = extrair_texto_busca_operadora(sender_email)
        nome_por_dominio = bd_tabelas.buscar_nome_fantasia(texto_busca)

        if nome_por_dominio is None:
            logger.warning(
                f"Operadora não identificada para '{caminho_arquivo.name}' "
                f"(eot='{eot}', dominio='{dominio}', texto_busca='{texto_busca}')"
            )
            return OperadoraResultado(dominio=dominio, nome=None, identificada=False)

        return OperadoraResultado(
            dominio=dominio,
            nome=normalizar_nome_pasta(nome_por_dominio),
            identificada=True,
            origem="dominio",
        )
