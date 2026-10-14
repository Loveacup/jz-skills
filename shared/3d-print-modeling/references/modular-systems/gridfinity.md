# Gridfinity：保留脚、槽、唇，替换功能体

核查2026-10-11；无打印、装配或承载实测。42网格是社区生态，下面固定实现基准不等于所有衍生件遵循的认证标准。

## 优先保留的接口

`male_foot`、`female_socket`、`stack_receiver`、`retention_pack` 独立于功能体；阵列只改变格数，别缩放脚。使用固定版本：[Rebuilt 2.0.0 / 910e22d](https://github.com/kennetek/gridfinity-rebuilt-openscad/commit/910e22d8607fd7f5f51ad5e5cbc5287a76810bfd)。源码MIT不自动覆盖网上模型许可。

- XY节距42 mm；普通连续盒外廓42n−0.5；常见Z单位7 mm。它们不是所有附件尺寸规则
- 该实现盒脚Z分层：0.8高45°倒角＋1.8直壁＋2.15高45°倒角，总4.75；上宽41.5、R3.75；下宽35.6、R0.8
- 普通母槽接口总高5：0.35底余量＋0.7倒角＋1.8直壁＋2.15倒角，槽顶42/R4。不可只把公脚整体放大当母槽
- 尖角叠放唇名义0.7＋1.8＋1.9＝4.4；圆角后实际高度另测。盒总高、7U标称高、堆叠增高分开，不强写为7n＋4.4
- 每脚孔中心(±13,±13)，26方形间距。6×2磁铁/M3是五金规格；Rebuilt普通磁铁槽为Ø6.5×2.4，不能把五金直径当打印孔尺寸
- 0.5名义间隔、0.02布尔epsilon与打印补偿不同。2.0.0发布说明与固定源码压溃筋参数有差异，涉及压溃筋时查源码证据，不从发布文案抄常数

## 已下载实现与独立性

K2_Kevin CN127813《结实的桌面整理器Gridfinity 2x2》原STL（SHA-256 `ab2f8d63ed5034e273b210e5b2380d10992a4c4b9d99cf3d006ffd597a7e502d`）按mm解释：四脚42节距、2×2外廓约83.5、脚分层及16组Ø6.5/Ø3孔与上述实现吻合；总高88.887不服从简单7n公式。量测仅针对文件，[来源](https://makerworld.com.cn/zh/models/127813-jie-shi-de-zhuo-mian-zheng-li-qi-gridfinity-2x2)。顶点合并阈值1e-5下发现2条非流形边，不能宣布完整网格通过制造检查。许可为Standard Digital File License，不自动再分发。

Olov CN955870原3MF（SHA-256 `cc7beba8c1b97f5936c8409b3718a99e6f16cdda5289246deb5a73dd9be0c583`）本体41.5×83.5×22，两脚42节距与分层吻合，但没有角孔，顶部是盖配合区。KYZ CN239655轻量底板STL（SHA-256 `fbace2ae1722afb6bdf9a7508d77d625c52ec4c9e94f3742d35fc0bbba048aeb`）84×84×4.1、顶槽趋近40.9，保留42节距却裁掉标准母槽上下部分，不能覆盖普通5/42母槽。源链接、对象路径及切面高度见数字量测；三个发布作者不等于完全无共同上游。

同作者Hex Bin不计第二独立证据；轻量/免支撑母槽尤其不能直接套普通5 mm母槽。原作者、Rebuilt、CLICKbase、Refined及Mix & Match各有共同上游或独立扩展，追踪谱系，不用网页数量投票出“标准”。

## 设计与试验

功能槽不得切穿脚工作面、唇落座区、孔周余肉；母槽避开螺钉头和加强肋。底板弹舌须有释放可达区，持续弯曲件与承载框分工。Refined侧插磁铁/M15锁紧、Clickfinity、Snapfit、Lite、花瓶及减唇为独立变体；能落座不等于锁紧/叠放相容。

先印1×1脚/槽、2×1节距桥、叠放环；磁铁孔独立试片。同材料/方向测试四向落座、摇晃、翘边、取放与保持力，再验证重心与工况。磁铁或普通重力脚朝向改变后不能自动抗拔。

详细证据：完整报告（包内路径 `evidence/gridfinity/research-report.md`）、数字量测（包内路径 `evidence/gridfinity/mesh-measurements.md`）、逐项来源（包内路径 `evidence/gridfinity/evidence.csv`）、模块/谱系/转接（包内路径 `evidence/gridfinity/module-reuse-patterns.md`）。这些报告区分源码值、数字量测与待试建议；没有实物评级。

来源文件总索引：[文件/hash/作者/许可](source-index.tsv)。上述包内路径参见[原证据范围说明](../modular-systems.md#研究报告与量测记录)；原证据未随公开包提供；按公开来源重新取得原件并复核，不能假定历史报告可读。
