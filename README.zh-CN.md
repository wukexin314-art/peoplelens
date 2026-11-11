# PeopleLens

[English](README.md)

PeopleLens 是一个面向 Codex 的通用 HR Analytics 技能包，用于把招聘和员工数据整理成口径清楚、可复核、保护隐私的分析与报告。

## 能做什么

- Headcount 与员工流动分析
- 招聘目标、完成率与时间进度
- 招聘来源、内推趋势和 Offer 状态
- Turnover、60 天早期离职与试用期留存
- 按部门、职级、来源和 Recruiter 分析
- ATS 导出与 Headcount Tracker 对账
- 月报、看板、指标字典和变更日志
- 数据质量、敏感字段与小样本检查

该技能只用于聚合分析，不会为候选人或员工打分，也不会代替人工做录用、解雇、晋升、薪酬或纪律决定。

## 使用示例

把该文件夹放入你的 Codex 技能目录后，可以这样调用：

- “使用 `$peoplelens` 检查这些 HR 工作簿并设计统一数据模型。”
- “使用成熟 cohort 口径计算各部门 60 天离职率。”
- “对账 ATS 导出与 Headcount Tracker，并生成变更日志。”
- “生成包含指标定义和数据质量说明的月度招聘与留存报告。”

## 本地数据体检

`scripts/profile_hr_data.py` 可以检查字段结构、缺失率、重复 ID、日期解析和潜在敏感字段，并且不会打印原始单元格值：

```bash
python3 scripts/profile_hr_data.py sample.csv --id-column employee_id
python3 scripts/profile_hr_data.py workbook.xlsx --sheet "Employees" --id-column worker_id
```

CSV/TSV 只需要 Python 标准库；读取 XLSX 需要 `openpyxl`。

## 隐私

仓库中不包含公司名称、真实员工数据、内部部门映射、个人姓名、招聘目标或本地路径。所有示例均为合成内容。处理真实 HR 数据前，请同时遵守所在组织的隐私、法务与员工关系要求。

## License

MIT
