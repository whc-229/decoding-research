# 算法库在排班问题上的筛选（原请求_paiban, B_三类型720h, C_三类型1440h, D_三类型资源紧；每算法 10 次/场景）

HV 每个场景内对全部算法统一归一化；p 为与 **NSGA** 的 Mann-Whitney（HV，所有场景合并）。“到达下界”= 前沿含资源数 = 下界的解；“÷最优”= 下界层均衡度 ÷ 精确最优。生成/选择列取自算法源码里实际调用的模块（库中多数算法由这两类模块组合而成）。

| 排名 | 算法（同实现的别名） | 平均 HV 排名 | HV 均值 | p | 到达下界 | 下界层均衡度 均值 | ÷最优 | 生成子代 | 环境选择 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NSGA | 5.2 | 1.017 | — | 72% | 6.98 | 1.89 | 自带 | 自带 |
| 2 | EFR-RR | 6.0 | 1.000 | 0.912↓ | 88% | 7.27 | 1.96 | GA | ReferencePreference |
| 3 | HREA | 6.5 | 1.010 | 0.814↓ | 85% | 7.79 | 2.11 | GA | SPEA2SDE |
| 4 | NRV-MOEA | 7.0 | 0.997 | 0.893↓ | 90% | 7.79 | 2.08 | GA | RegionExplore |
| 5 | NSGA-II+ARSBX | 7.2 | 1.007 | 0.950↓ | 80% | 7.06 | 1.91 | ARSBX | NSGA |
| 6 | r-NSGA-II | 8.2 | 0.990 | 0.479↓ | 82% | 8.31 | 2.19 | GA | RNSGA |
| 7 | PESA-II | 8.2 | 0.979 | 0.829↓ | 88% | 8.03 | 2.12 | PESA | PESA |
| 8 | GrEA | 8.2 | 0.978 | 0.776↓ | 88% | 7.30 | 1.93 | 自带 | GrEA_ |
| 9 | AFSEA | 8.5 | 0.993 | 0.630↓ | 82% | 7.50 | 2.03 | GA | Entropy |
| 10 | LB-rNSGA | 9.5 | 0.985 | 0.433↓ | 80% | 7.36 | 1.97 | 自带 | 自带 |
| 11 | NSGA-II-SDR（=MOEA-NZD/DSSEA） | 9.8 | 0.972 | 0.397↓ | 78% | 7.38 | 1.97 | GA | ShiftedDistance |
| 12 | KnEA（=KL-NSGA-II） | 10.0 | 0.975 | 0.416↓ | 92% | 8.05 | 2.15 | GA | KnEA |
| 13 | LevelNiche-ARSBX | 10.2 | 0.973 | 0.402↓ | 90% | 7.84 | 2.11 | 自带 | 自带 |
| 14 | AGE-MOEA-II | 11.0 | 0.978 | 0.459↓ | 80% | 7.76 | 2.10 | GA | AGEMOEAII |
| 15 | LevelNiche-GA | 11.2 | 0.946 | 0.397↓ | 92% | 8.24 | 2.19 | 自带 | 自带 |
| 16 | NSGA-II-DTI | 12.0 | 0.989 | 0.268↓ | 78% | 7.54 | 2.04 | ARSBX+GA+RandomImmigrant | NSGA |
| 17 | MOEA-D-VOV | 14.0 | 0.954 | 0.346↓ | 80% | 7.59 | 2.07 | NeighborhoodGA | RegionExplore |
| 18 | DKCA | 18.0 | 0.788 | 0.000↓ | 38% | 7.62 | 2.07 | ModelGaussian | MOEAIGDNS |

## 按生成子代方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| GenerateARSBXOffspring | 1 | 7.2 | 7.2 |
| GeneratePESAOffspring | 1 | 8.2 | 8.2 |
| GenerateGAOffspring | 8 | 8.4 | 6.0 |
| （算法自带实现） | 5 | 8.9 | 5.2 |
| GenerateARSBXOffspring+GenerateGAOffspring+GenerateRandomImmigrantOffspring | 1 | 12.0 | 12.0 |
| GenerateNeighborhoodGAOffspring | 1 | 14.0 | 14.0 |
| GenerateModelGaussianOffspring | 1 | 18.0 | 18.0 |

## 按环境选择方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| EnvironmentalSelectionReferencePreference | 1 | 6.0 | 6.0 |
| EnvironmentalSelectionSPEA2SDE | 1 | 6.5 | 6.5 |
| EnvironmentalSelectionRNSGA | 1 | 8.2 | 8.2 |
| EnvironmentalSelectionPESA | 1 | 8.2 | 8.2 |
| GrEA_EnvironmentalSelection | 1 | 8.2 | 8.2 |
| EnvironmentalSelectionEntropy | 1 | 8.5 | 8.5 |
| （算法自带实现） | 4 | 9.1 | 5.2 |
| EnvironmentalSelectionNSGA | 2 | 9.6 | 7.2 |
| EnvironmentalSelectionShiftedDistance | 1 | 9.8 | 9.8 |
| EnvironmentalSelectionKnEA | 1 | 10.0 | 10.0 |
| EnvironmentalSelectionRegionExplore | 2 | 10.5 | 7.0 |
| EnvironmentalSelectionAGEMOEAII | 1 | 11.0 | 11.0 |
| EnvironmentalSelectionMOEAIGDNS | 1 | 18.0 | 18.0 |
