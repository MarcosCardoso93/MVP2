import json
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook as load_xl
from src.config.logger_config import logger
from src.config.configuration import (
    EXTENSOES_CSV,
    EXTENSOES_EXCEL,
    DIRETORIO_HISTORICO_ARQUIVOS,
    ANO_MES_REFERENCIA,
)


class ValidadorHistoricoRPA:
    def __init__(self):
        """
        Inicializa o controlador utilizando estritamente as definições do config.py
        """
        # 1. Captura e valida o ANOMES vindo do ambiente do S.O.
        self.anomes = ANO_MES_REFERENCIA
        if not self.anomes or not self.anomes.isdigit() or len(self.anomes) != 6:
            raise ValueError(
                "A constante ENV 'ANOMES' deve estar no formato 'YYYYMM' (ex: '202606')."
            )

        # 2. Define o caminho do arquivo JSON do mês corrente
        self.caminho_json = (
            Path(DIRETORIO_HISTORICO_ARQUIVOS)
            / "historico_arquivos_processados"
            / f"arquivos_validados_{self.anomes}.json"
        )

        # 3. Garante a criação física de toda a árvore de pastas dinamicamente
        self.caminho_json.parent.mkdir(parents=True, exist_ok=True)

        # 4. Normaliza as extensões importadas para minúsculo para evitar case-sensitivity
        self.extensoes_csv = {ext.lower() for ext in EXTENSOES_CSV}
        self.extensoes_excel = {ext.lower() for ext in EXTENSOES_EXCEL}

        # Carrega o histórico existente do mês para a memória RAM
        self.historico = self._carregar_json()

    def _carregar_json(self) -> dict:
        """Leitura rápida do arquivo JSON de histórico."""
        if self.caminho_json.exists():
            try:
                with open(self.caminho_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # Retorna um dicionário vazio se o arquivo estiver corrompido ou recém-criado
                return {}
        return {}

    def _salvar_json(self):
        """Persiste o dicionário atualizado em formato formatado para auditoria humana."""
        with open(self.caminho_json, "w", encoding="utf-8") as f:
            json.dump(self.historico, f, indent=4, ensure_ascii=False)

    def arquivo_ja_processado(self, caminho_arquivo: str) -> bool:
        """Verifica em tempo constante O(1) se o arquivo já foi tratado no mês atual."""
        caminho_normalizado = str(Path(caminho_arquivo).resolve())
        return caminho_normalizado in self.historico

    def _contar_linhas_csv(self, caminho_path: Path) -> int:
        """Conta as linhas de um CSV via buffer binário de blocos para alta performance."""
        linhas = 0
        try:
            with open(caminho_path, "rb") as f:
                # Lê blocos de 1MB por vez, ideal para arquivos gigantes com milhares de linhas
                for bloco in iter(lambda: f.read(1024 * 1024), b""):
                    linhas += bloco.count(b"\n")
            return linhas
        except Exception:
            return 0

    def _contar_linhas_excel(self, caminho_path: Path) -> int:
        """Abre planilhas em modo otimizado e extrai a contagem máxima de linhas."""
        try:
            # O modo read_only ignora estilos e elementos pesados, focando apenas nos dados puros
            wb = load_xl(filename=str(caminho_path), read_only=True, data_only=True)
            sheet = wb.active
            total_linhas = sheet.max_row  # type: ignore
            wb.close()
            return total_linhas if total_linhas is not None else 0
        except Exception:
            return 0

    def registrar_arquivos(self, lista_caminhos: list[Path], status_valido: bool):
        """
        Coleta metadados de tamanho e linhas dos arquivos e consolida de uma vez no JSON.
        Recebe uma lista de objetos Path.
        """
        status_texto = "Válido" if status_valido else "Inválido"
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Contadores para o log final
        total_processados = 0
        total_nao_encontrados = 0

        for path_obj in lista_caminhos:
            path_resolvido = path_obj.resolve()
            caminho_str = str(path_resolvido)

            if not path_resolvido.exists():
                self.historico[caminho_str] = {
                    "status": "Erro (Arquivo Não Encontrado)",
                    "data_processamento": agora,
                    "tamanho_bytes": 0,
                    "numero_de_linhas": 0,
                }
                total_nao_encontrados += 1
                continue

            tamanho_bytes = path_resolvido.stat().st_size
            extensao = path_resolvido.suffix.lower()
            num_linhas = 0

            # Validação extremamente rápida utilizando tabelas Hash (Sets)
            if extensao in self.extensoes_csv:
                num_linhas = self._contar_linhas_csv(path_resolvido)
            elif extensao in self.extensoes_excel:
                num_linhas = self._contar_linhas_excel(path_resolvido)
            else:
                num_linhas = f"Não foi possível determinar (Extensão não configurada: {extensao})"

            self.historico[caminho_str] = {
                "status": status_texto,
                "data_processamento": agora,
                "tamanho_bytes": tamanho_bytes,
                "numero_de_linhas": num_linhas,
            }
            total_processados += 1

        # Commita todo o lote de uma única vez no disco, mitigando gargalos de I/O
        self._salvar_json()

        # Log final de consolidação do lote
        logger.info(
            f"Histórico atualizado com sucesso. Lote finalizado com "
            f"{total_processados} arquivo(s) salvo(s) como '{status_texto}'."
        )
        if total_nao_encontrados > 0:
            logger.warning(
                f"Atenção: {total_nao_encontrados} arquivo(s) deste lote foram "
                f"registrados com status 'Erro (Arquivo Não Encontrado)'."
            )

    def filtrar_arquivos_novos(self, lista_total: list[Path]) -> list[Path]:
        """
        Recebe uma lista de objetos Path e filtra retendo apenas aqueles
        que ainda NÃO constam no histórico JSON do mês.

        :param lista_total: Lista contendo todos os caminhos (Path) encontrados na pasta.
        :return: Uma nova lista de objetos Path contendo apenas os arquivos inéditos.
        """
        total_originais = len(lista_total)

        # Filtra a lista retendo apenas os arquivos novos
        arquivos_filtrados = [
            path_obj
            for path_obj in lista_total
            if not self.arquivo_ja_processado(str(path_obj.resolve()))
        ]

        total_retornados = len(arquivos_filtrados)
        total_no_json = total_originais - total_retornados

        # Logs de auditoria para monitoramento do processo RPA
        logger.info(f"Filtro de Histórico concluído para o período {self.anomes}.")
        logger.info(f"Arquivos originais recebidos: {total_originais}")
        logger.info(
            f"Arquivos já processados anteriormente (encontrados no JSON): {total_no_json}"
        )
        logger.info(f"Novos arquivos retornados para execução: {total_retornados}")

        return arquivos_filtrados
