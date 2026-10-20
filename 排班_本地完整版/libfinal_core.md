# 算法库在排班问题上的筛选（原请求_paiban, B_三类型720h, C_三类型1440h, D_三类型资源紧；每算法 10 次/场景）

HV 每个场景内对全部算法统一归一化；p 为与 **NSGA** 的 Mann-Whitney（HV，所有场景合并）。“到达下界”= 前沿含资源数 = 下界的解；“÷最优”= 下界层均衡度 ÷ 精确最优。生成/选择列取自算法源码里实际调用的模块（库中多数算法由这两类模块组合而成）。

| 排名 | 算法（同实现的别名） | 平均 HV 排名 | HV 均值 | p | 到达下界 | 下界层均衡度 均值 | ÷最优 | 生成子代 | 环境选择 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NSGA | 4.8 | 1.017 | — | 72% | 6.98 | 1.89 | 自带 | 自带 |
| 2 | NRV-MOEA | 5.5 | 0.996 | 0.893↓ | 90% | 7.79 | 2.08 | GA | RegionExplore |
| 3 | HREA | 5.8 | 1.009 | 0.806↓ | 85% | 7.79 | 2.11 | GA | SPEA2SDE |
| 4 | EFR-RR | 5.8 | 1.000 | 0.904↓ | 88% | 7.27 | 1.96 | GA | ReferencePreference |
| 5 | NSGA-II+ARSBX | 6.2 | 1.006 | 0.958↓ | 80% | 7.06 | 1.91 | ARSBX | NSGA |
| 6 | r-NSGA-II | 7.0 | 0.990 | 0.473↓ | 82% | 8.31 | 2.19 | GA | RNSGA |
| 7 | AFSEA | 7.2 | 0.993 | 0.651↓ | 82% | 7.50 | 2.03 | GA | Entropy |
| 8 | PESA-II | 7.2 | 0.979 | 0.814↓ | 88% | 8.03 | 2.12 | PESA | PESA |
| 9 | GrEA | 7.2 | 0.978 | 0.784↓ | 88% | 7.30 | 1.93 | 自带 | GrEA_ |
| 10 | KnEA（=KL-NSGA-II） | 8.2 | 0.975 | 0.411↓ | 92% | 8.05 | 2.15 | GA | KnEA |
| 11 | NSGA-II-SDR（=MOEA-NZD/DSSEA） | 8.5 | 0.971 | 0.386↓ | 78% | 7.38 | 1.97 | GA | ShiftedDistance |
| 12 | AGE-MOEA-II | 9.2 | 0.978 | 0.453↓ | 80% | 7.76 | 2.10 | GA | AGEMOEAII |
| 13 | NSGA-II-DTI | 10.0 | 0.988 | 0.264↓ | 78% | 7.54 | 2.04 | ARSBX+GA+RandomImmigrant | NSGA |
| 14 | MOEA-D-VOV | 12.2 | 0.954 | 0.341↓ | 80% | 7.59 | 2.07 | NeighborhoodGA | RegionExplore |
| 15 | DKCA | 15.0 | 0.787 | 0.000↓ | 38% | 7.62 | 2.07 | ModelGaussian | MOEAIGDNS |

## 按生成子代方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| （算法自带实现） | 2 | 6.0 | 4.8 |
| GenerateARSBXOffspring | 1 | 6.2 | 6.2 |
| GenerateGAOffspring | 8 | 7.2 | 5.5 |
| GeneratePESAOffspring | 1 | 7.2 | 7.2 |
| GenerateARSBXOffspring+GenerateGAOffspring+GenerateRandomImmigrantOffspring | 1 | 10.0 | 10.0 |
| GenerateNeighborhoodGAOffspring | 1 | 12.2 | 12.2 |
| GenerateModelGaussianOffspring | 1 | 15.0 | 15.0 |

## 按环境选择方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| （算法自带实现） | 1 | 4.8 | 4.8 |
| EnvironmentalSelectionSPEA2SDE | 1 | 5.8 | 5.8 |
| EnvironmentalSelectionReferencePreference | 1 | 5.8 | 5.8 |
| EnvironmentalSelectionRNSGA | 1 | 7.0 | 7.0 |
| EnvironmentalSelectionEntropy | 1 | 7.2 | 7.2 |
| EnvironmentalSelectionPESA | 1 | 7.2 | 7.2 |
| GrEA_EnvironmentalSelection | 1 | 7.2 | 7.2 |
| EnvironmentalSelectionNSGA | 2 | 8.1 | 6.2 |
| EnvironmentalSelectionKnEA | 1 | 8.2 | 8.2 |
| EnvironmentalSelectionShiftedDistance | 1 | 8.5 | 8.5 |
| EnvironmentalSelectionRegionExplore | 2 | 8.9 | 5.5 |
| EnvironmentalSelectionAGEMOEAII | 1 | 9.2 | 9.2 |
| EnvironmentalSelectionMOEAIGDNS | 1 | 15.0 | 15.0 |
