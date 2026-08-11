import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from openpyxl import load_workbook as load_xl
from comum.config.logger_config import logger
from comum.config.configuration import (
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
        """
        Lê o histórico do mês.

        Um JSON corrompido devolve `{}` — mas **em alto e bom som**. Até
        2026-08-04 devolvia `{}` calado, e a consequência era grave e invisível:
        o histórico é a proteção anti-reprocessamento, então o robô refazia o mês
        inteiro como se fosse a primeira execução, reenviando arquivos e
        duplicando registros. Um `return {}` silencioso não pode carregar essa
        decisão.

        O arquivo corrompido é preservado com sufixo, não sobrescrito: ele é
        registro de auditoria do que já foi processado, e pode ser a única pista
        de por que o mês foi refeito.
        """
        if not self.caminho_json.exists():
            return {}

        try:
            with open(self.caminho_json, "r", encoding="utf-8") as arquivo:
                return json.load(arquivo)
        except (json.JSONDecodeError, OSError) as erro:
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            preservado = self.caminho_json.with_suffix(f".corrompido-{carimbo}.json")
            try:
                self.caminho_json.rename(preservado)
                destino = f"preservado em [{preservado.name}]"
            except OSError as erro_rename:
                destino = f"NÃO foi possível preservá-lo: {erro_rename}"

            logger.error(
                f"Histórico de arquivos processados ilegível em "
                f"[{self.caminho_json}]: {erro}. O arquivo foi {destino}. "
                f"ATENÇÃO: sem histórico, os arquivos deste mês serão tratados "
                f"como novos e REPROCESSADOS."
            )
            return {}

    def _salvar_json(self):
        """Persiste o dicionário atualizado em formato formatado para auditoria humana."""
        with open(self.caminho_json, "w", encoding="utf-8") as f:
            json.dump(self.historico, f, indent=4, ensure_ascii=False)

    def arquivo_ja_processado(self, caminho_arquivo: str) -> bool:
        """
        Diz se **este** arquivo já foi tratado no mês — conteúdo, não só nome.

        🔴 **Corrigido em 2026-08-10.** A comparação era só pelo caminho, e isso
        quebrava um critério explícito da HU-03: *"reenvio de arquivo com o mesmo
        nome sobrescreve o anterior e inicia novo processamento"*. O RPA 1
        sobrescrevia, sim — mas o caminho continuava o mesmo, o histórico dizia
        "já processado", e a **correção enviada pela operadora era ignorada em
        silêncio** pela validação e pelo batimento. Sem erro, sem aviso.

        Agora o caminho continua sendo a chave (o JSON segue legível e
        compatível), mas tamanho e data de modificação entram na comparação. O
        tamanho já era gravado desde sempre — só nunca tinha sido lido.

        Arquivo idêntico continua sendo pulado, que é a proteção
        anti-reprocessamento; arquivo trocado volta a ser processado.
        """
        caminho = Path(caminho_arquivo).resolve()
        registro = self.historico.get(str(caminho))

        if registro is None:
            return False

        assinatura_atual = self._assinatura(caminho)
        if assinatura_atual is None:
            # Está no histórico e sumiu do disco. Não há o que reprocessar.
            return True

        tamanho_gravado = registro.get("tamanho_bytes")
        modificado_gravado = registro.get("modificado_em")

        # Registro anterior a esta mudança não tem `modificado_em`. Comparar só
        # o que existe é melhor do que reprocessar o mês inteiro de quem já
        # rodou — e o tamanho sozinho já pega a maior parte das substituições.
        if modificado_gravado is None and tamanho_gravado is None:
            return True

        mudou = tamanho_gravado != assinatura_atual["tamanho_bytes"] or (
            modificado_gravado is not None
            and modificado_gravado != assinatura_atual["modificado_em"]
        )

        if mudou:
            logger.info(
                f"[{caminho.name}] está no histórico, mas o arquivo mudou "
                f"({tamanho_gravado} -> {assinatura_atual['tamanho_bytes']} bytes). "
                f"Será processado de novo — é o reenvio previsto na HU-03."
            )
            return False

        return True

    @staticmethod
    def _assinatura(caminho: Path) -> Optional[dict]:
        """Tamanho e data de modificação, ou `None` se o arquivo sumiu."""
        try:
            informacao = caminho.stat()
        except OSError:
            return None

        return {
            "tamanho_bytes": informacao.st_size,
            # Segundos inteiros: o `copy2` preserva o mtime com precisão de
            # subsegundo que varia entre sistemas de arquivos, e comparar o
            # float cru faria o mesmo arquivo parecer diferente de si mesmo.
            "modificado_em": int(informacao.st_mtime),
        }

    def _contar_linhas_csv(self, caminho_path: Path) -> Optional[int]:
        """
        Conta as linhas de um CSV lendo em blocos de 1 MB.

        Devolve `None` quando **não conseguiu ler** — e não zero. Zero linhas é um
        resultado legítimo (arquivo vazio); até 2026-08-04 uma falha de I/O virava
        zero em silêncio, e o histórico registrava o arquivo como processado com
        um metadado que parecia real. É o mesmo padrão "falha vira dado" já
        corrigido em `resultado_validacao`.
        """
        linhas = 0
        try:
            with open(caminho_path, "rb") as arquivo:
                for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                    linhas += bloco.count(b"\n")
            return linhas
        except OSError as erro:
            logger.warning(
                f"Não foi possível contar as linhas de [{caminho_path.name}]: "
                f"{erro}. O histórico fica sem esse metadado."
            )
            return None

    def _contar_linhas_excel(self, caminho_path: Path) -> Optional[int]:
        """
        Conta as linhas de uma planilha. `None` quando não conseguiu ler.

        Mesma razão de `_contar_linhas_csv` para não devolver zero.
        """
        try:
            # `read_only` ignora estilos e elementos pesados.
            planilha = load_xl(
                filename=str(caminho_path), read_only=True, data_only=True
            )
            total_linhas = planilha.active.max_row  # type: ignore
            planilha.close()
            return total_linhas if total_linhas is not None else 0
        except Exception as erro:
            logger.warning(
                f"Não foi possível contar as linhas de [{caminho_path.name}]: "
                f"{erro}. O histórico fica sem esse metadado."
            )
            return None

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

            assinatura = self._assinatura(path_resolvido) or {
                "tamanho_bytes": 0,
                "modificado_em": None,
            }
            tamanho_bytes = assinatura["tamanho_bytes"]
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
                # Entrou em 2026-08-10, junto com a comparação de conteúdo em
                # `arquivo_ja_processado` — é o que distingue o mesmo arquivo do
                # arquivo reenviado com o mesmo nome.
                "modificado_em": assinatura["modificado_em"],
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
