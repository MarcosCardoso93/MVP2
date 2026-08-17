-- DDL real do banco WebFat, lido por espelhar_banco.py
-- Gerado em 2026-08-06 15:42
-- Responde à pendência Q22 (o DDL nunca foi publicado pela V2).

-- tbl_anexo5_processado
CREATE TABLE `tbl_anexo5_processado` (
  `id` int NOT NULL AUTO_INCREMENT,
  `EOT` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `Nome Fantasia` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Razao Social` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `CSP` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Tipo de Servico` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Modalidade / Banda` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Area de Prestacao` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Holding` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `CNPJ` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Inscricao Estadual` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Endereco de Emissao Nota Fiscal` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Endereco de Correspondencia` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `UF` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Regiao` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Concessao` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `RN1` int DEFAULT NULL,
  `SPID` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_eot` (`EOT`),
  KEY `idx_nome_fantasia` (`Nome Fantasia`)
) ENGINE=InnoDB AUTO_INCREMENT=2794 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- tbl_detraf_mapeamento_descritores
CREATE TABLE `tbl_detraf_mapeamento_descritores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `final_descritor` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'Caractere final do descritor (ex: 9, C, I)',
  `remuneracao_fixa` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'Tipo de remuneração (ex: PTL, TU-COM, VU-M)',
  `observacao` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Observação/categoria (ex: TRANSITO, ITX)',
  `ativo` tinyint(1) DEFAULT NULL COMMENT 'Se o mapeamento está ativo',
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `produto` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_tbl_detraf_mapeamento_descritores_final_descritor` (`final_descritor`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- tbl_detraf_tarifas
CREATE TABLE `tbl_detraf_tarifas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sentido` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tipo_remuneracao` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `regiao` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `gh` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `tarifa` float DEFAULT NULL,
  `data_inicio` datetime NOT NULL,
  `data_fim` datetime NOT NULL,
  `regra_desc` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `tipo_dado` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `ativa` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `created_by` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `updated_at` datetime DEFAULT NULL,
  `updated_by` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `observacao` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `eot_devedora` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `eot_vivo` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'EOT VIVO credora (934, 964, 916, etc)',
  `eot_operadora` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'EOT operadora devedora (042, 043, etc)',
  `tipo_servico_vivo` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Tipo servico VIVO (SMP, STFC)',
  `tipo_servico_oper` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Tipo servico operadora (STFC, SMP)',
  PRIMARY KEY (`id`),
  KEY `idx_eot_vivo` (`eot_vivo`,`eot_operadora`,`tipo_servico_vivo`,`tipo_servico_oper`)
) ENGINE=InnoDB AUTO_INCREMENT=128 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- tbl_rpa_log_detraf_despesa_arquivos
CREATE TABLE `tbl_rpa_log_detraf_despesa_arquivos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tipo_registro` enum('DETRAF','EXPECTATIVA','ERRO') NOT NULL,
  `nome_arquivo` varchar(255) DEFAULT NULL,
  `periodo` varchar(20) DEFAULT NULL,
  `empresa` varchar(150) DEFAULT NULL,
  `tipo_servico_operadora` varchar(100) DEFAULT NULL,
  `tipo_servico_vivo` varchar(100) DEFAULT NULL,
  `remuneracoes` varchar(255) DEFAULT NULL,
  `minuto_desp` decimal(18,6) DEFAULT NULL,
  `valor_bruto_desp` decimal(18,6) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `codigo_erro` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- tbl_rpa_log_detraf_despesa_contestacao
CREATE TABLE `tbl_rpa_log_detraf_despesa_contestacao` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tipo_servico_vivo` varchar(100) DEFAULT NULL,
  `remuneracoes` varchar(255) DEFAULT NULL,
  `eot_tbra` varchar(100) DEFAULT NULL,
  `eot_operadora` varchar(100) DEFAULT NULL,
  `empresa` varchar(100) DEFAULT NULL,
  `referencia` varchar(50) DEFAULT NULL,
  `trafego` varchar(100) DEFAULT NULL,
  `minutos_tbra` decimal(18,6) DEFAULT NULL,
  `vb_tbra` decimal(18,6) DEFAULT NULL,
  `minutos_operadora` decimal(18,6) DEFAULT NULL,
  `vb_operadora` decimal(18,6) DEFAULT NULL,
  `minutos_diferenca` decimal(18,6) DEFAULT NULL,
  `vb_diferenca` decimal(18,6) DEFAULT NULL,
  `minutos_variacao_perc` decimal(10,4) DEFAULT NULL,
  `vb_variacao_perc` decimal(10,4) DEFAULT NULL,
  `carga_agi` varchar(50) DEFAULT NULL,
  `tipo_contestacao` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
