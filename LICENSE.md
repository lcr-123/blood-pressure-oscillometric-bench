数据与代码分开授权
==================

本仓库同时包含**代码**与**数据**，两者用不同的许可。凭据、厂商文件与历史归档不在授权范围内。

代码 —— MIT
-----------

适用范围：`tools/**`、`blood pressure monitor/tools/**`、`blood pressure monitor/Core/**`、
`docs/*.py`、仓库根目录的 `*.py`。

许可见 [`LICENSE`](LICENSE)（MIT）。可自由使用、修改、再分发，包括商用，只需保留版权声明。

数据 —— CC BY 4.0
-----------------

适用范围：`data/raw/**` 下的波形与元数据、`data/reports/**` 的分析报告与图表、
`data/manifest.csv`、`data/manifest.json`、`data/checksums.sha256`、
`data/protocols/**` 的协议与冻结记录。

许可见 [`data/LICENSE`](data/LICENSE)（Creative Commons Attribution 4.0 International）。
允许复制、再分发、修改与商用，**前提是署名**，署名方式见下节。

不在授权范围内
--------------

- `blood pressure monitor/Drivers/**/LICENSE.txt` —— 厂商（ST）文件，按各自条款。
- `archive/historical/**` —— 历史材料，仅作追溯，**未获授权再分发**。
  2026-11-26 起该目录已从版本库移除（`.gitignore` 里有一条 `archive/`），
  工作区副本保留仅供本地追溯。注意：移除的是 HEAD，不是历史——首个提交
  `2430964` 里仍有这些字节，克隆旧提交仍能取到。
- `data/raw/human_*.ndjson`、`data/raw/human_v2_*.ndjson`、
  `data/raw/nonhuman_160_test.ndjson` —— **来源未确认的早期遥测，不属于本数据集**。
  同样于 2026-11-26 从 HEAD 移除，理由见
  [`data/reports/dataset_scope_statement.md`](data/reports/dataset_scope_statement.md)
  的「2026-11-26 补充」：现有指标无法区分其与同晚的非人体记录，不能排除含真人数据。
- `tmp/**`、`软件下载/**` —— 临时与本地目录，不入库。
- 硬编码在未跟踪 `cloud/` 目录里的服务凭据，不属于本仓库授权内容（该目录未提交，
  2026-11-26 起写进 `.gitignore`）。

怎么署名
--------

引用数据时请同时满足两点：一按 `data/LICENSE` 给出 CC BY 4.0 的署名与变更说明；
二按 [`data/reports/dataset_limitations.md`](data/reports/dataset_limitations.md) 的
「引用时必须声明的最小集」逐条声明采集条件与边界。两件事互不替代：许可要求的是"谁做的"，
最小集要求的是"这份数据能证明什么、不能证明什么"。

机器可读的引用元数据见 [`CITATION.cff`](CITATION.cff)。
