# PeopleLens

[English](README.md)

PeopleLens 是一个面向 Codex 的 HR Analytics 技能包，用于把招聘和员工数据整理成口径清楚、可复核、保护隐私的聚合分析与报告。

## 当前可直接运行的能力

- CSV、TSV、XLSX 和 Parquet 结构体检，不打印原始单元格值
- 成熟 cohort 口径的招聘漏斗、流失、耗时、Aging、积压和分群
- Employment-spell 口径的 Headcount、入职、离职、增长、近似 Turnover、FTE 和 N 天留存
- OPM 入职、离职、类别构成与净人员行动流
- Greenhouse Analytics 阶段变更 CSV 标准化
- 自包含 HTML 报告、指标字典、质量检查、小样本抑制和运行清单

该技能还提供职位、招聘计划、内部流动、晋升、工作簿对账和周期报告的方法指导。这些属于引导式分析，目前不是独立的自动化模块，结果取决于用户提供的数据和业务定义。

该技能只用于聚合分析，不会为候选人或员工打分，也不会代替人工做录用、解雇、晋升、薪酬或纪律决定。

## 使用示例

把该文件夹放入你的 Codex 技能目录后，可以这样调用：

- “使用 `$peoplelens` 检查这些 HR 工作簿并设计统一数据模型。”
- “使用成熟 cohort 口径计算各部门 60 天离职率。”
- “按招聘 cohort 分析从申请到入职的漏斗转化、流失和阶段耗时。”
- “对账 ATS 导出与 Headcount Tracker，并生成变更日志。”
- “生成包含指标定义和数据质量说明的月度招聘与留存报告。”

所有确定性工作流可以从统一入口运行：

```bash
python3 scripts/peoplelens.py --help
```

## 可执行招聘漏斗

PeopleLens 现在包含一个零第三方依赖的 ATS 阶段事件分析器：

```bash
python3 scripts/analyze_recruiting_funnel.py \
  examples/recruiting-funnel/applications.csv \
  --config configs/recruiting-funnel.example.yaml \
  --mapping configs/mappings/canonical-event-history.yaml \
  --output-dir /tmp/peoplelens-output
```

它会生成 cohort 口径的阶段转化、累计转化、终止结果、阶段耗时、当前积压、Aging、隐私抑制后的分群结果、映射诊断、配置化指标、指标字典、自动数据质量报告和运行清单。仓库包含合成数据与标准输出，可直接复现。

漏斗指标只使用满足最短观察期的 entry cohort，并要求同一个 Application 按时间顺序进入下一阶段。晚于截至时间的事件会被排除，晚于截至时间的阶段退出会按尚未退出处理。可以使用 `--as-of-date YYYY-MM-DD` 临时覆盖配置中的截至日。

分群结果通过 `minimum_cell_size` 抑制小样本，默认阈值为 5。`mapping_report.csv` 会列出已映射和未映射的原始阶段，但不包含候选人明细；`cohort_summary.csv` 会记录 cohort 窗口与成熟度。

配置采用 JSON-compatible YAML，无需安装额外 Python 包。字段映射文件只是起点，使用真实 ATS 导出前必须确认字段与阶段映射。

## 本地数据体检

`scripts/profile_hr_data.py` 可以检查字段结构、缺失率、重复 ID、日期解析和潜在敏感字段，并且不会打印原始单元格值：

```bash
python3 scripts/profile_hr_data.py sample.csv --id-column employee_id
python3 scripts/profile_hr_data.py workbook.xlsx --sheet "Employees" --id-column worker_id
python3 scripts/profile_hr_data.py workforce.parquet --id-column employee_id
```

CSV/TSV 只需要 Python 标准库；读取 XLSX 需要 `openpyxl`。读取 Parquet 需要安装 `requirements-parquet.txt` 中的 `pyarrow`，并采用分批处理，不会一次性把大型文件全部载入内存。

## OPM 员工流动分析

PeopleLens 可以直接分析 OPM Federal Workforce Data 的版本化入职与离职 Parquet 文件：

```bash
python3 -m pip install -r requirements-parquet.txt
python3 scripts/analyze_opm_workforce_flow.py \
  --accessions accessions_202608_1.parquet \
  --separations separations_202608_1.parquet \
  --start-month 2026-08 \
  --end-month 2026-08 \
  --group-by department \
  --output-dir /tmp/peoplelens-opm-output
```

输出包括按月人员行动流、入职和离职类别构成、经过小样本抑制的部门结果、数据质量检查、分析摘要和运行清单。净人员行动流不会被误标成 Headcount Growth 或 Turnover。可复现的来源、版本与预期结果见[公开数据验证目录](examples/public-data-validation/README.md)。

## 可执行员工分析

对于每行一个 Employment Spell 的 CSV，可以计算期初和期末人数、期间入职与离职、人数增长、近似 Turnover、期末 FTE、离职类型以及成熟 cohort 的早期离职与留存：

```bash
python3 scripts/peoplelens.py workforce \
  examples/workforce/employee-spells.csv \
  --config configs/workforce.example.yaml \
  --output-dir /tmp/peoplelens-workforce
```

合成示例见 [workforce example](examples/workforce/README.md)。重新入职应作为新的 Employment Spell；使用期初和期末人数近似平均人数时，输出会明确标注限制。

## Greenhouse 适配器与 HTML 报告

Greenhouse Analytics 中基于 **Application stage changes** subject 的 CSV 可以先转换成 PeopleLens 标准事件历史：

```bash
python3 scripts/peoplelens.py adapt-greenhouse greenhouse-stage-changes.csv \
  --output canonical-stage-events.csv
```

阶段名称会保持原样，必须根据组织自己的 Interview Plan 建立映射。Current-pipeline 快照不会被当作完整阶段历史。

转换后的 CSV 仍然是行级招聘数据，可能包含 Application ID、Recruiter 姓名和其他内部字段。应保存在获批的本地位置，只发布聚合结果。

招聘漏斗或员工分析输出目录可以进一步生成一个不依赖外部资源的聚合 HTML 报告：

```bash
python3 scripts/peoplelens.py report /tmp/peoplelens-workforce \
  --output /tmp/peoplelens-workforce.html
```

## 隐私

仓库中不包含公司名称、真实员工数据、内部部门映射、个人姓名、招聘目标或本地路径。所有示例均为合成内容。处理真实 HR 数据前，请同时遵守所在组织的隐私、法务与员工关系要求。

## License

MIT
