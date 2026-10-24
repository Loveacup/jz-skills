# 公开发布范围 · 1.1.0

本版提供FDM项目的需求确认、现场归档、分阶段快审、几何与切片检查、结构/美学方法、Dot协调和窄幅复盘。正文及附件维护在所属项目，Obsidian不留副本或跳转占位；普通小改不反复全库研究或重审。

公开包包括主入口、按需参考、四模块研究摘记、公开来源索引、核心需求模板与客户端界面描述。私人项目版本链、反馈、验证/成本数字、设备库存组合、records、会话/文件ID、现场媒体、模型/3MF、研究证据包及runtime均不随包提供。通用机制不代表某件产品通过验证；公开模型的数字摘记按特定来源定位，原证据未打包，采用前应取得真实原件核查。

## 元数据适配

本包采用Codex Agent Skills的前置字段契约：顶层使用name、description、metadata，版本置于metadata.version。仓库通用示例中的顶层version/author不直接移入此包：Codex skill-creator的quick_validate.py将顶层字段限制为name、description、license、allowed-tools、metadata，额外顶层字段会被拒绝。该选择遵循仓库skill-authoring/author所要求的实际消费者格式核查；保留仓库版本记录，同时不修改仓库治理或其他技能。格式通过不代表其他CLI加载已验证。

## 权限与来源边界

设备、材料、工具可用性与权限由当前项目核实。本包不安装兄弟技能，不承诺Dot连接、自动消息往返、后台监听或runtime部署。静态校验不证明CAD、切片、设备控制或实物性能。

本次发布未新增原创文字许可或权利归属声明。引用文章、MakerWorld模型及其设计各受其自身许可约束；不分发第三方原模型/图片/源码，也不授予其派生物商用或再分发许可。下载、改模或发布前另核具体许可与授权。

## print-prep方法吸收

1.1.0新增切片设置建议/质量排查触发与参数耦合方法：按需核机料、几何、目标和成功基线；估算体积流量限速而非冒称实际速度；联动温度、冷却、层时间、墙序/接缝和填充重叠；区分校准值与起点，按授权做最小工程差量。六阶段、项目需求先读、原件保全与保存重开复切保持。

研究来源为adilkalam/orca提交`6c37fb572336f47de02e6ca082d4cc2d976e29a2`的[print-prep/SKILL.md](https://github.com/adilkalam/orca/blob/6c37fb572336f47de02e6ca082d4cc2d976e29a2/skills/print-prep/SKILL.md)及[filament-data.md](https://github.com/adilkalam/orca/blob/6c37fb572336f47de02e6ca082d4cc2d976e29a2/skills/print-prep/references/filament-data.md)，其[MIT许可证](https://github.com/adilkalam/orca/blob/6c37fb572336f47de02e6ca082d4cc2d976e29a2/LICENSE)署名Copyright (c) 2026 ORCA-OS Contributors。本版独立中文归纳方法并修正适用边界，不复制其品牌配方表、成段原文或工具实现；后续若复制实质内容，须保留原版权及许可声明。上游个人主参考未取得，其“实测/共识”标签不视为独立核实。

不移植固定VFA禁区、为了提速直接提高未验证流量、丝绸PLA无条件满风/关闭降速/零重叠、喷嘴导热率直接换算温差、品牌参数与上游私人路径/MCP能力承诺。上游P2S默认黄铜喷嘴前提与[Bambu官方规格](https://bambulab.com/en/p2s/specs)列出的Hardened Steel冲突；实际兼容判断仍以当次实装硬件和具体材料为准。

验证范围为技能格式、包内链接和受限决策情景，不代表实际切片、校准或实物通过。没有随公开包加入私人维护记录、项目现场或运行环境，也不把本次源文件发布视为runtime部署。
