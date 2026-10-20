# 算法库在排班问题上的筛选（E01_1080h, E02_1080h, E03_1080h, H01_720h, H02_720h, H03_720h, H04_480h, M01_480h, M02_480h, M03_720h, M04_720h, M05_480h；每算法 4 次/场景）

HV 每个场景内对全部算法统一归一化；p 为与 **NSGA** 的 Mann-Whitney（HV，所有场景合并）。“到达下界”= 前沿含资源数 = 下界的解；“÷最优”= 下界层均衡度 ÷ 精确最优。生成/选择列取自算法源码里实际调用的模块（库中多数算法由这两类模块组合而成）。

| 排名 | 算法（同实现的别名） | 平均 HV 排名 | HV 均值 | p | 到达下界 | 下界层均衡度 均值 | ÷最优 | 生成子代 | 环境选择 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NSGA | 3.8 | 0.796 | — | 69% | 10.33 | nan | 自带 | 自带 |
| 2 | LevelNiche-GA | 4.2 | 0.796 | 0.985↑ | 73% | 10.48 | nan | 自带 | 自带 |
| 3 | NSGA-II-SDR（=MOEA-NZD/DSSEA） | 4.8 | 0.805 | 0.855↑ | 71% | 10.76 | nan | GA | ShiftedDistance |
| 4 | EFR-RR | 5.1 | 0.782 | 0.781↓ | 67% | 9.96 | nan | GA | ReferencePreference |
| 5 | r-NSGA-II | 5.3 | 0.772 | 0.585↓ | 67% | 10.85 | nan | GA | RNSGA |
| 6 | HREA | 5.8 | 0.759 | 0.466↓ | 67% | 10.89 | nan | GA | SPEA2SDE |
| 7 | LevelNiche-ARSBX | 5.8 | 0.774 | 0.800↓ | 67% | 9.46 | nan | 自带 | 自带 |
| 8 | LB-rNSGA | 6.6 | 0.750 | 0.493↓ | 69% | 10.17 | nan | 自带 | 自带 |
| 9 | NRV-MOEA | 6.8 | 0.744 | 0.342↓ | 67% | 10.47 | nan | GA | RegionExplore |
| 10 | KnEA（=KL-NSGA-II） | 7.0 | 0.748 | 0.375↓ | 75% | 11.11 | nan | GA | KnEA |

## 按生成子代方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| （算法自带实现） | 4 | 5.1 | 3.8 |
| GenerateGAOffspring | 6 | 5.8 | 4.8 |

## 按环境选择方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| EnvironmentalSelectionShiftedDistance | 1 | 4.8 | 4.8 |
| （算法自带实现） | 4 | 5.1 | 3.8 |
| EnvironmentalSelectionReferencePreference | 1 | 5.1 | 5.1 |
| EnvironmentalSelectionRNSGA | 1 | 5.3 | 5.3 |
| EnvironmentalSelectionSPEA2SDE | 1 | 5.8 | 5.8 |
| EnvironmentalSelectionRegionExplore | 1 | 6.8 | 6.8 |
| EnvironmentalSelectionKnEA | 1 | 7.0 | 7.0 |
