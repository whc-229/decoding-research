# 算法库在排班问题上的筛选（B_三类型720h；每算法 3 次/场景）

HV 每个场景内对全部算法统一归一化；p 为与 **NSGA** 的 Mann-Whitney（HV，所有场景合并）。“到达下界”= 前沿含资源数 = 下界的解；“÷最优”= 下界层均衡度 ÷ 精确最优。生成/选择列取自算法源码里实际调用的模块（库中多数算法由这两类模块组合而成）。

| 排名 | 算法（同实现的别名） | 平均 HV 排名 | HV 均值 | p | 到达下界 | 下界层均衡度 均值 | ÷最优 | 生成子代 | 环境选择 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | r-NSGA-II | 1.0 | 1.157 | 1.000↑ | 100% | 5.87 | 1.73 | GA | RNSGA |
| 2 | HREA | 2.0 | 1.156 | 1.000↑ | 100% | 6.97 | 2.06 | GA | SPEA2SDE |
| 3 | DAEA | 3.0 | 1.156 | 1.000↑ | 100% | 10.19 | 3.01 | BestGuidedDE+DirectionRestrictedDE+GA | RegionExplore |
| 4 | MOEA-D-VOV | 4.0 | 1.155 | 1.000↑ | 100% | 8.11 | 2.39 | NeighborhoodGA | RegionExplore |
| 5 | CNSDE-DVC | 5.0 | 1.155 | 1.000↑ | 100% | 8.97 | 2.65 | DirectionRestrictedDE | ShiftedDistance |
| 6 | NSGA-II-SDR（=MOEA-NZD/DSSEA） | 6.0 | 1.155 | 1.000↑ | 100% | 9.49 | 2.80 | GA | ShiftedDistance |
| 7 | RVEAa | 7.0 | 1.152 | 1.000↑ | 100% | 8.55 | 2.53 | GA | RVEAa |
| 8 | AGE-MOEA-II | 8.0 | 1.152 | 1.000↑ | 100% | 7.38 | 2.18 | GA | AGEMOEAII |
| 9 | NRV-MOEA | 9.0 | 1.151 | 1.000↑ | 100% | 6.52 | 1.93 | GA | RegionExplore |
| 10 | S-CDAS | 10.0 | 1.150 | 1.000↑ | 100% | 8.56 | 2.53 | GA | Conflict |
| 11 | RPEA | 11.0 | 1.150 | 1.000↑ | 100% | 9.17 | 2.71 | GA | RPEA |
| 12 | RPD-NSGA-II | 12.0 | 1.150 | 0.663↑ | 100% | 7.75 | 2.29 | GA | RPDNSGA |
| 13 | I-SIBEA | 13.0 | 1.149 | 0.663↑ | 100% | 7.46 | 2.20 | 自带 | SIBEA |
| 14 | MFO-SPEA2 | 14.0 | 1.149 | 1.000↑ | 100% | 8.73 | 2.58 | GA | SPEA2 |
| 15 | NSGA | 15.0 | 1.148 | — | 100% | 8.01 | 2.36 | 自带 | 自带 |
| 16 | DNSGA-II | 16.0 | 1.145 | 1.000↓ | 100% | 12.11 | 3.58 | ARSBX | Entropy |
| 17 | MaOEA-CSS | 17.0 | 1.145 | 0.663↓ | 100% | 8.02 | 2.37 | GA | Entropy |
| 18 | EFR-RR | 18.0 | 1.144 | 0.663↓ | 67% | 6.05 | 1.79 | GA | ReferencePreference |
| 19 | SGEA（=CMOEA-CD） | 19.0 | 1.144 | 0.663↓ | 100% | 9.32 | 2.75 | GA | ShiftedDistance |
| 20 | MaOEA-HAP | 20.0 | 1.143 | 0.663↓ | 100% | 7.84 | 2.32 | ARSBX | Entropy |
| 21 | MOMBI-II | 21.0 | 1.143 | 0.663↓ | 100% | 8.01 | 2.36 | GA | MOMBI |
| 22 | KnEA（=KL-NSGA-II） | 22.0 | 1.143 | 0.663↓ | 100% | 6.54 | 1.93 | GA | KnEA |
| 23 | DCNSGA-III | 23.0 | 1.142 | 0.383↓ | 100% | 10.62 | 3.14 | GA | Conflict+RVEAa |
| 24 | NSGA-II-DTI | 24.0 | 1.142 | 1.000↓ | 100% | 6.25 | 1.85 | ARSBX+GA+RandomImmigrant | NSGA |
| 25 | AFSEA | 25.0 | 1.141 | 0.663↓ | 100% | 6.00 | 1.77 | GA | Entropy |
| 26 | IBEA | 26.0 | 1.141 | 1.000↓ | 100% | 9.27 | 2.74 | 自带 | IBEA_environmentalSelection |
| 27 | VaEA | 27.0 | 1.140 | 0.825↓ | 100% | 10.37 | 3.06 | 自带 | VaEA_environmentalSelection |
| 28 | SIBEA（=BCE-IBEA/I-DBEA） | 28.0 | 1.139 | 0.663↓ | 100% | 9.37 | 2.77 | GA | SIBEA |
| 29 | WASF-GA | 29.0 | 1.139 | 1.000↓ | 100% | 9.61 | 2.84 | GA | ReferencePreference |
| 30 | GDVTSF | 30.0 | 1.138 | 0.663↓ | 100% | 9.68 | 2.86 | DirectionRestrictedDE | ShiftedDistance |
| 31 | CMOEA-2S | 31.0 | 1.138 | 1.000↓ | 100% | 7.77 | 2.29 | DirectionRestrictedDE+GA | RegionExplore+TwoArchive |
| 32 | one-by-one EA | 32.0 | 1.138 | 0.383↓ | 100% | 8.45 | 2.50 | 自带 | 自带 |
| 33 | MaOEA-R&D | 33.0 | 1.137 | 0.383↓ | 100% | 10.87 | 3.21 | GA | Entropy |
| 34 | CI-EMO | 34.0 | 1.137 | 0.663↓ | 100% | 7.90 | 2.33 | GA | Conflict |
| 35 | DWU | 35.0 | 1.137 | 0.663↓ | 100% | 10.49 | 3.10 | DirectionRestrictedDE+GA | MPSOD |
| 36 | S-NSGA-II | 36.0 | 1.136 | 1.000↓ | 67% | 8.11 | 2.39 | ARSBX+BestGuidedDE+GA | ShiftedDistance |
| 37 | MSOPS-II | 37.0 | 1.136 | 0.383↓ | 100% | 8.97 | 2.65 | GA | MPSOD |
| 38 | LDS-AF | 38.0 | 1.135 | 0.663↓ | 100% | 11.10 | 3.28 | DirectionRestrictedDE+GA+LocalSearch | Entropy |
| 39 | SIBEA-kEMOSS | 39.0 | 1.135 | 0.825↓ | 67% | 7.96 | 2.35 | GA | SIBEA |
| 40 | HypE | 40.0 | 1.134 | 0.663↓ | 100% | 9.09 | 2.69 | 自带 | Hype |
| 41 | BiGE | 41.0 | 1.134 | 0.663↓ | 100% | 6.92 | 2.04 | GA | BiGE |
| 42 | MOEA-RE | 42.0 | 1.133 | 0.825↓ | 100% | 7.91 | 2.34 | GA | RegionExplore |
| 43 | RGA-M1-2 | 43.0 | 1.133 | 0.383↓ | 100% | 7.01 | 2.07 | GA | GNSGA |
| 44 | EMMOEA | 44.0 | 1.133 | 0.383↓ | 100% | 9.71 | 2.87 | ARSBX+DirectionRestrictedDE+RandomImmigrant | NSGA |
| 45 | PPS | 45.0 | 1.133 | 1.000↓ | 100% | 8.45 | 2.50 | BestGuidedDE+GA | EpsilonGrid |
| 46 | MSEA | 46.0 | 1.133 | 0.383↓ | 67% | 8.11 | 2.39 | ARSBX | Entropy |
| 47 | R2HCA | 47.0 | 1.133 | 0.383↓ | 67% | 9.52 | 2.81 | 自带 | 自带 |
| 48 | NSGA-II+ARSBX | 48.0 | 1.132 | 0.383↓ | 67% | 5.77 | 1.70 | ARSBX | NSGA |
| 49 | MSCEA | 49.0 | 1.132 | 0.383↓ | 100% | 10.20 | 3.01 | DirectionRestrictedDE+GA+LocalSearch | NSGA+RegionExplore+TwoArchive |
| 50 | DPCPRA | 50.0 | 1.132 | 1.000↓ | 100% | 8.60 | 2.54 | DirectionRestrictedDE | ReferencePreference |
| 51 | MOEADD | 51.0 | 1.132 | 0.383↓ | 100% | 8.05 | 2.38 | 自带 | 自带 |
| 52 | DKCA | 52.0 | 1.131 | 0.663↓ | 100% | 5.64 | 1.67 | ModelGaussian | MOEAIGDNS |
| 53 | SPEA2 | 53.0 | 1.131 | 0.383↓ | 67% | 12.35 | 3.65 | GA | SPEA2 |
| 54 | HeE-MOEA | 54.0 | 1.131 | 0.663↓ | 100% | 8.11 | 2.39 | GA | TwoArchive |
| 55 | C-TAEA（=BiCo） | 55.0 | 1.130 | 0.663↓ | 100% | 6.98 | 2.06 | GA | TwoArchive |
| 56 | AE-NSGA-II | 56.0 | 1.130 | 1.000↓ | 67% | 5.76 | 1.70 | ARSBX | EpsilonGrid |
| 57 | g-NSGA-II | 57.0 | 1.130 | 0.663↓ | 100% | 6.64 | 1.96 | GA | GNSGA |
| 58 | CMOEA-AOP | 58.0 | 1.130 | 1.000↓ | 67% | 9.84 | 2.91 | CMAStyle+DirectionRestrictedDE+GA+LocalSearch | ShiftedDistance |
| 59 | DGEA | 59.0 | 1.128 | 0.663↓ | 67% | 8.22 | 2.43 | GA | RegionExplore |
| 60 | A-NSGA-III | 60.0 | 1.128 | 0.383↓ | 100% | 8.38 | 2.48 | ARSBX | RVEAa |
| 61 | APSEA | 61.0 | 1.128 | 1.000↓ | 67% | 7.71 | 2.28 | GA | ReferencePreference |
| 62 | GrEA | 62.0 | 1.128 | 1.000↓ | 67% | 5.76 | 1.70 | 自带 | GrEA_ |
| 63 | DSPCMDE | 63.0 | 1.127 | 1.000↓ | 100% | 10.00 | 2.95 | DirectionRestrictedDE | TwoArchive |
| 64 | MOEA-IGD-NS（=MaOEA-IGD） | 64.0 | 1.127 | 0.383↓ | 100% | 8.12 | 2.40 | GA | MOEAIGDNS |
| 65 | NSGA_III | 65.0 | 1.127 | 1.000↓ | 100% | 8.73 | 2.58 | 自带 | NSGA_III_environmentalSelection |
| 66 | MOEA-D-DCWV | 66.0 | 1.127 | 0.383↓ | 67% | 8.25 | 2.44 | NeighborhoodGA | ReferencePreference |
| 67 | PB-NSGA-III | 67.0 | 1.127 | 0.663↓ | 100% | 9.54 | 2.82 | GA | ReferencePreference |
| 68 | RSEA | 68.0 | 1.126 | 1.000↓ | 67% | 8.11 | 2.39 | GA | ReferencePreference |
| 69 | AR-MOEA | 69.0 | 1.125 | 0.383↓ | 100% | 9.63 | 2.84 | GA | ReferencePreference |
| 70 | SCEA | 70.0 | 1.125 | 0.663↓ | 67% | 6.41 | 1.89 | GA+LocalSearch | Conflict |
| 71 | RGA-M2-2 | 71.0 | 1.125 | 0.383↓ | 67% | 8.69 | 2.57 | ARSBX+GA+RandomImmigrant | NSGA |
| 72 | CCMO | 72.0 | 1.123 | 0.383↓ | 67% | 9.81 | 2.90 | GA | TwoArchive |
| 73 | MOEAD | 73.0 | 1.122 | 0.663↓ | 67% | 8.77 | 2.59 | 自带 | 自带 |
| 74 | MOEA-DVA | 74.0 | 1.121 | 0.663↓ | 67% | 13.00 | 3.84 | NeighborhoodDE | RegionExplore |
| 75 | EMCMO | 75.0 | 1.121 | 0.383↓ | 100% | 11.57 | 3.42 | BestGuidedDE+DirectionRestrictedDE+GA | TwoArchive |
| 76 | PB-RVEA | 76.0 | 1.121 | 0.663↓ | 67% | 8.65 | 2.55 | ARSBX+BestGuidedDE+GA | RVEAa |
| 77 | NSBiDiCo | 77.0 | 1.120 | 0.268↓ | 100% | 8.11 | 2.39 | GA | Conflict+TwoArchive |
| 78 | MMEA-WI | 78.0 | 1.119 | 0.663↓ | 100% | 9.00 | 2.66 | GA | ReferencePreference |
| 79 | PeEA | 79.0 | 1.119 | 0.190↓ | 100% | 8.08 | 2.39 | GA | Entropy |
| 80 | TriMOEA-TA&R | 80.0 | 1.118 | 0.663↓ | 67% | 6.17 | 1.82 | ArchiveGA+GA+RandomImmigrant | TwoArchive |
| 81 | MaOEA-DDFC（=NSGA-II-conflict/DN-NSGA-II） | 81.0 | 1.118 | 0.383↓ | 100% | 8.83 | 2.61 | GA | Conflict |
| 82 | PESA-II | 82.0 | 1.118 | 1.000↓ | 67% | 4.90 | 1.45 | PESA | PESA |
| 83 | TS-NSGA-II | 83.0 | 1.117 | 0.383↓ | 100% | 8.12 | 2.40 | GA | ReferencePreference |
| 84 | DP-PPS | 84.0 | 1.117 | 0.383↓ | 100% | 10.81 | 3.19 | NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 85 | MOEA-D-UR | 85.0 | 1.116 | 0.190↓ | 67% | 7.55 | 2.23 | NeighborhoodGA | ReferencePreference |
| 86 | MOEA-D-MRDL | 86.0 | 1.115 | 0.383↓ | 67% | 8.42 | 2.49 | ARSBX | ReferencePreference |
| 87 | MO-L2SMEA | 87.0 | 1.115 | 0.663↓ | 67% | 8.52 | 2.52 | ARSBX+GA+LocalSearch | Entropy |
| 88 | AGE-II | 88.0 | 1.113 | 0.190↓ | 100% | 8.78 | 2.59 | GA | MOEAIGDNS |
| 89 | CMOEA-MOP | 89.0 | 1.112 | 0.383↓ | 67% | 8.31 | 2.45 | DirectionRestrictedDE+GA | TwoArchive |
| 90 | HEA | 90.0 | 1.112 | 0.383↓ | 67% | 9.29 | 2.74 | GA | RegionExplore |
| 91 | PICEAg | 91.0 | 1.112 | 0.190↓ | 100% | 7.81 | 2.31 | 自带 | 自带 |
| 92 | AdaW | 92.0 | 1.112 | 0.383↓ | 100% | 7.77 | 2.30 | NeighborhoodGA | MPSOD |
| 93 | MOEA-D-M2M | 93.0 | 1.111 | 0.190↓ | 100% | 8.14 | 2.40 | GA | MPSOD |
| 94 | CPS-MOEA | 94.0 | 1.110 | 0.190↓ | 67% | 10.41 | 3.07 | DirectionRestrictedDE+GA | TwoArchive |
| 95 | C-TSEA | 95.0 | 1.106 | 0.190↓ | 33% | 5.88 | 1.74 | DirectionRestrictedDE+GA | RegionExplore+TwoArchive |
| 96 | MOEA-D-AWA | 96.0 | 1.106 | 0.383↓ | 67% | 6.92 | 2.04 | NeighborhoodGA | DecompositionReplacement |
| 97 | MOEA-D-FRRMAB | 97.0 | 1.105 | 0.383↓ | 67% | 12.09 | 3.57 | NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 98 | CMaDPPs | 98.0 | 1.105 | 0.383↓ | 67% | 8.92 | 2.64 | GA | TwoArchive |
| 99 | OSP-NSDE | 99.0 | 1.105 | 0.190↓ | 33% | 8.56 | 2.53 | BestGuidedDE+DirectionRestrictedDE+GA | ShiftedDistance |
| 100 | RVEA | 100.0 | 1.104 | 0.190↓ | 67% | 8.52 | 2.52 | 自带 | 自带 |
| 101 | HHC-MMEA | 101.0 | 1.104 | 0.190↓ | 67% | 9.09 | 2.68 | GA+LocalSearch+ModelGaussian | TwoArchive |
| 102 | MOEA-D-URAW | 102.0 | 1.103 | 0.190↓ | 67% | 12.86 | 3.80 | NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 103 | LERD | 103.0 | 1.102 | 0.190↓ | 67% | 8.29 | 2.45 | BestGuidedDE+DirectionRestrictedDE+GA | RegionExplore |
| 104 | K-RVEA（=DPVAPS） | 104.0 | 1.102 | 0.190↓ | 67% | 8.95 | 2.64 | CMAStyle | RVEAa |
| 105 | SMS-EMOA | 105.0 | 1.101 | 0.383↓ | 67% | 9.71 | 2.87 | GA | SMS |
| 106 | NUCEA | 106.0 | 1.101 | 0.383↓ | 100% | 9.85 | 2.91 | ARSBX+BestGuidedDE+GA | NSGA |
| 107 | LMOEA-DS | 107.0 | 1.100 | 0.190↓ | 67% | 11.50 | 3.40 | DirectionRestrictedDE | MPSOD |
| 108 | MSCMO | 108.0 | 1.100 | 0.190↓ | 33% | 8.11 | 2.39 | DirectionRestrictedDE+GA | Conflict+TwoArchive |
| 109 | S-ECSO | 109.0 | 1.099 | 0.190↓ | 67% | 15.06 | 4.45 | CompetitiveSwarm | Entropy |
| 110 | BCE2 | 110.0 | 1.099 | 0.190↓ | 67% | 9.11 | 2.69 | 自带 | 0+1 |
| 111 | LCMEA | 111.0 | 1.098 | 0.663↓ | 33% | 9.14 | 2.70 | CMAStyle | ReferencePreference |
| 112 | MOSD | 112.0 | 1.098 | 0.190↓ | 67% | 10.89 | 3.22 | LocalSearch | NSGA |
| 113 | IMTCMO | 113.0 | 1.097 | 0.081↓ | 33% | 8.11 | 2.39 | DirectionRestrictedDE+GA | Conflict+TwoArchive |
| 114 | MOCell | 114.0 | 1.097 | 0.190↓ | 67% | 12.73 | 3.76 | 自带 | 自带 |
| 115 | DMOEA-eC | 115.0 | 1.096 | 0.190↓ | 67% | 11.26 | 3.33 | NeighborhoodDE | ReferencePreference |
| 116 | t-DEA（=MaOEA-IT/tDEA-CPBI） | 116.0 | 1.096 | 0.663↓ | 67% | 7.16 | 2.12 | GA | TDEA |
| 117 | NSLS | 117.0 | 1.096 | 0.190↓ | 33% | 4.94 | 1.46 | LocalSearch | NSGA |
| 118 | MOEA-D-DYTS | 118.0 | 1.095 | 0.190↓ | 67% | 8.98 | 2.65 | BestGuidedDE+CMAStyle+NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 119 | PRDH | 119.0 | 1.094 | 0.190↓ | 67% | 10.64 | 3.14 | BestGuidedDE+DirectionRestrictedDE+GA | RPDNSGA |
| 120 | GWASF-GA（=hpaEA） | 120.0 | 1.094 | 0.190↓ | 33% | 8.11 | 2.39 | GA | ReferencePreference |
| 121 | CMMO | 121.0 | 1.093 | 0.383↓ | 67% | 9.34 | 2.76 | DirectionRestrictedDE | MPSOD |
| 122 | PRCEA | 122.0 | 1.093 | 0.081↓ | 67% | 8.77 | 2.59 | BestGuidedDE+GA | ReferencePreference |
| 123 | SPEA-R | 123.0 | 1.093 | 0.190↓ | 67% | 9.19 | 2.71 | 自带 | SPEAR |
| 124 | MOEA-CKF | 124.0 | 1.092 | 0.190↓ | 0% | nan | nan | BestGuidedDE+CMAStyle | KnEA |
| 125 | SSCEA | 125.0 | 1.091 | 0.190↓ | 67% | 10.36 | 3.06 | DirectionRestrictedDE | ShiftedDistance |
| 126 | Two_Arch2 | 126.0 | 1.091 | 0.081↓ | 33% | 13.58 | 4.01 | ArchiveGA+GA | TwoArchive |
| 127 | EDN-ARMOEA | 127.0 | 1.090 | 0.190↓ | 67% | 8.52 | 2.52 | ARSBX+BestGuidedDE+GA | AGEMOEAII+NSGA |
| 128 | MCEA-D | 128.0 | 1.090 | 0.190↓ | 67% | 10.94 | 3.23 | BestGuidedDE | MPSOD |
| 129 | LMPFE | 129.0 | 1.089 | 0.190↓ | 33% | 10.30 | 3.04 | LocalSearch | Entropy |
| 130 | SPEA2+SDE | 130.0 | 1.088 | 0.081↓ | 67% | 9.34 | 2.76 | GA | SPEA2SDE |
| 131 | MOEA-D-STM | 131.0 | 1.088 | 0.081↓ | 67% | 10.10 | 2.98 | NeighborhoodDE | MPSOD |
| 132 | MOEA-D-DE | 132.0 | 1.088 | 0.190↓ | 67% | 9.11 | 2.69 | DE | 自带 |
| 133 | CCGDE3 | 133.0 | 1.087 | 0.190↓ | 33% | 7.95 | 2.35 | NeighborhoodDE | NSGA |
| 134 | RVEA-iGNG | 134.0 | 1.087 | 0.190↓ | 67% | 10.08 | 2.98 | CMAStyle | RVEAa |
| 135 | CMOES | 135.0 | 1.087 | 0.081↓ | 67% | 15.49 | 4.58 | CMAStyle | SMS |
| 136 | LMEA | 136.0 | 1.086 | 0.190↓ | 33% | 8.11 | 2.39 | DirectionRestrictedDE | MOEAIGDNS |
| 137 | IM-C-MOEA-D | 137.0 | 1.086 | 0.190↓ | 33% | 13.20 | 3.90 | NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 138 | DEA-GNG | 138.0 | 1.086 | 0.663↓ | 67% | 10.01 | 2.96 | NeighborhoodDE | RegionExplore |
| 139 | AGE-MOEA | 139.0 | 1.085 | 0.081↓ | 100% | 8.55 | 2.53 | GA | AGE |
| 140 | MOEA-IB | 140.0 | 1.084 | 0.081↓ | 33% | 15.66 | 4.63 | BestGuidedDE+GA | SIBEA |
| 141 | CoMMEA | 141.0 | 1.084 | 0.081↓ | 100% | 12.28 | 3.63 | DirectionRestrictedDE+ModelGaussian | TwoArchive |
| 142 | CMODE-FTR | 142.0 | 1.084 | 0.190↓ | 33% | 19.31 | 5.70 | DirectionRestrictedDE | RegionExplore |
| 143 | KLEA | 143.0 | 1.083 | 0.190↓ | 33% | 9.44 | 2.79 | GA | KnEA |
| 144 | MP-MMEA | 144.0 | 1.083 | 0.081↓ | 67% | 8.53 | 2.52 | BestGuidedDE+GA+ModelGaussian | TwoArchive |
| 145 | MMEA-ARM | 145.0 | 1.083 | 0.190↓ | 33% | 12.99 | 3.84 | BestGuidedDE+GA+LocalSearch | TwoArchive |
| 146 | SGECF | 146.0 | 1.082 | 0.190↓ | 100% | 10.63 | 3.14 | ARSBX+BestGuidedDE+GA | EpsilonGrid |
| 147 | MOEA-D-PaS | 147.0 | 1.081 | 0.081↓ | 67% | 9.40 | 2.78 | NeighborhoodDE | ReferencePreference |
| 148 | e-MOEA | 148.0 | 1.081 | 0.190↓ | 33% | 8.64 | 2.55 | ArchiveGA | EpsilonGrid |
| 149 | FRCG-M | 149.0 | 1.081 | 0.081↓ | 67% | 12.86 | 3.80 | BestGuidedDE | ReferencePreference |
| 150 | EGES | 150.0 | 1.081 | 0.190↓ | 67% | 7.77 | 2.30 | BestGuidedDE+GA+LocalSearch | EpsilonGrid |
| 151 | PIEA | 151.0 | 1.081 | 0.121↓ | 33% | 8.11 | 2.39 | ARSBX+GA+RandomImmigrant | NSGA |
| 152 | MO-CMA | 152.0 | 1.079 | 0.190↓ | 33% | 9.15 | 2.70 | CMAStyle | SMS |
| 153 | ILCMO | 153.0 | 1.079 | 0.081↓ | 67% | 9.64 | 2.85 | ArchiveGA+BestGuidedDE | TwoArchive |
| 154 | EMyO-C | 154.0 | 1.079 | 0.081↓ | 67% | 8.62 | 2.55 | ARSBX+BestGuidedDE+GA | Conflict |
| 155 | ICMA | 155.0 | 1.078 | 0.190↓ | 67% | 12.30 | 3.63 | DirectionRestrictedDE | SIBEA |
| 156 | NNIA | 156.0 | 1.077 | 0.190↓ | 67% | 10.26 | 3.03 | ArchiveGA | ShiftedDistance |
| 157 | LRMOEA | 157.0 | 1.075 | 0.190↓ | 67% | 9.60 | 2.84 | DirectionRestrictedDE+LocalSearch | TwoArchive |
| 158 | GLMO | 158.0 | 1.075 | 0.190↓ | 33% | 10.27 | 3.03 | LocalSearch+ModelGaussian | MOEAIGDNS |
| 159 | WOF | 159.0 | 1.075 | 0.081↓ | 33% | 8.11 | 2.39 | GA+LocalSearch+NeighborhoodDE+RandomImmigrant | NSGA+RVEAa |
| 160 | CMOBR | 160.0 | 1.071 | 0.081↓ | 0% | nan | nan | Besiege | RegionExplore |
| 161 | MOPSO | 161.0 | 1.071 | 0.081↓ | 67% | 8.73 | 2.58 | PSOFromArchive | 自带 |
| 162 | CMDEIPCM | 162.0 | 1.070 | 0.081↓ | 33% | 10.95 | 3.23 | NeighborhoodDE | ReferencePreference |
| 163 | MOEA-D-DU | 163.0 | 1.070 | 0.081↓ | 67% | 9.09 | 2.68 | NeighborhoodGA | DecompositionReplacement |
| 164 | C3M（=DVCEA） | 164.0 | 1.070 | 0.190↓ | 33% | 6.79 | 2.00 | DirectionRestrictedDE | Conflict |
| 165 | MTS | 165.0 | 1.068 | 0.190↓ | 67% | 7.49 | 2.21 | BestGuidedDE+LocalSearch+RandomImmigrant | NSGA |
| 166 | MOEA-D-CMA | 166.0 | 1.067 | 0.081↓ | 0% | nan | nan | BestGuidedDE | DecompositionReplacement |
| 167 | MOEA-D-DAE | 167.0 | 1.066 | 0.190↓ | 67% | 12.90 | 3.81 | BestGuidedDE+NeighborhoodDE+NeighborhoodGA | DecompositionReplacement |
| 168 | DM-MOEA | 168.0 | 1.065 | 0.190↓ | 67% | 8.80 | 2.60 | DirectionRestrictedDE+GA+LocalSearch | RegionExplore |
| 169 | MO-EGS | 169.0 | 1.063 | 0.081↓ | 67% | 8.75 | 2.58 | LocalSearch | RegionExplore |
| 170 | CMME | 170.0 | 1.062 | 0.081↓ | 67% | 14.23 | 4.20 | CMAStyle | Entropy |
| 171 | MMOPSO | 171.0 | 1.061 | 0.081↓ | 67% | 9.98 | 2.95 | CompetitiveSwarm | RegionExplore |
| 172 | MOEA-D-DRA | 172.0 | 1.061 | 0.190↓ | 33% | 8.60 | 2.54 | NeighborhoodDE | DecompositionReplacement |
| 173 | dMOPSO | 173.0 | 1.057 | 0.081↓ | 0% | nan | nan | DecompositionPSO | MPSOD |
| 174 | MMEAPSL | 174.0 | 1.057 | 0.081↓ | 67% | 13.14 | 3.88 | LocalSearch+ModelGaussian | MOEAIGDNS |
| 175 | CLIA | 175.0 | 1.056 | 0.081↓ | 33% | 12.31 | 3.63 | ModelGaussian | SIBEA |
| 176 | IMTCMO_BS | 176.0 | 1.056 | 0.190↓ | 67% | 9.78 | 2.89 | Besiege+BestGuidedDE | TwoArchive |
| 177 | MOCGDE | 177.0 | 1.056 | 0.081↓ | 33% | 11.15 | 3.29 | BestGuidedDE | NSGA |
| 178 | GDE3 | 178.0 | 1.055 | 0.190↓ | 33% | 18.60 | 5.49 | DE | NSGA |
| 179 | EAG-MOEA-D | 179.0 | 1.053 | 0.081↓ | 33% | 10.11 | 2.98 | BestGuidedDE | DecompositionReplacement |
| 180 | LMOCSO | 180.0 | 1.052 | 0.081↓ | 33% | 11.28 | 3.33 | CompetitiveSwarm | MPSOD |
| 181 | SRA | 181.0 | 1.052 | 0.081↓ | 33% | 9.14 | 2.70 | 自带 | SRA_environmentalSelection |
| 182 | SFA-DE | 182.0 | 1.051 | 0.081↓ | 0% | nan | nan | BestGuidedDE | ShiftedDistance |
| 183 | MOEA-PC | 183.0 | 1.051 | 0.081↓ | 33% | 13.83 | 4.09 | NeighborhoodDE | EpsilonGrid |
| 184 | NNDREA-MO | 184.0 | 1.050 | 0.081↓ | 0% | nan | nan | BestGuidedDE+GA+ModelGaussian | MOEAIGDNS+NSGA |
| 185 | MGCEA | 185.0 | 1.049 | 0.081↓ | 33% | 7.81 | 2.31 | GA+ModelGaussian | RegionExplore |
| 186 | C-MOEA-D（=CAEAD） | 186.0 | 1.048 | 0.081↓ | 33% | 12.05 | 3.56 | NeighborhoodDE | DecompositionReplacement |
| 187 | MPSO-D | 187.0 | 1.048 | 0.081↓ | 67% | 13.78 | 4.07 | DecompositionPSO | MPSOD |
| 188 | WV-MOEA-P | 188.0 | 1.047 | 0.081↓ | 33% | 9.44 | 2.79 | BestGuidedDE+NeighborhoodDE+NeighborhoodGA | ReferencePreference |
| 189 | NMPSO | 189.0 | 1.047 | 0.081↓ | 0% | nan | nan | ArchiveGA+PSOFromArchive | 自带 |
| 190 | SMPSO | 190.0 | 1.046 | 0.081↓ | 33% | 9.19 | 2.72 | PSO | NSGA |
| 191 | MyO-DEMR | 191.0 | 1.046 | 0.081↓ | 0% | nan | nan | DirectionRestrictedDE | RVEAa |
| 192 | MOBCA | 192.0 | 1.046 | 0.081↓ | 33% | 22.57 | 6.66 | Besiege | EpsilonGrid |
| 193 | LSMOF | 193.0 | 1.045 | 0.081↓ | 33% | 8.47 | 2.50 | LocalSearch | NSGA |
| 194 | BCE | 194.0 | 1.045 | 0.081↓ | 0% | nan | nan | 自带 | BCE_ |
| 195 | RMOEA-DVA | 195.0 | 1.045 | 0.081↓ | 0% | nan | nan | DirectionRestrictedDE | RegionExplore |
| 196 | GPSO-M（=CMOPSO） | 196.0 | 1.044 | 0.081↓ | 33% | 12.46 | 3.68 | PSOFromArchive | EpsilonGrid |
| 197 | POCEA | 197.0 | 1.043 | 0.081↓ | 0% | nan | nan | BestGuidedDE+CMAStyle+GA | TwoArchive |
| 198 | CGLP | 198.0 | 1.042 | 0.081↓ | 0% | nan | nan | LocalSearch | RegionExplore |
| 199 | EMCMMS | 199.0 | 1.041 | 0.081↓ | 67% | 10.65 | 3.14 | ModelGaussian | TwoArchive |
| 200 | CMOSMA | 200.0 | 1.040 | 0.081↓ | 33% | 7.74 | 2.29 | Besiege+LocalSearch | Entropy |
| 201 | LCSA | 201.0 | 1.040 | 0.081↓ | 67% | 10.45 | 3.09 | CompetitiveSwarm | ShiftedDistance |
| 202 | MOEA-D-CMT | 202.0 | 1.037 | 0.081↓ | 33% | 9.57 | 2.83 | NeighborhoodDE | DecompositionReplacement |
| 203 | MCCMO | 203.0 | 1.036 | 0.081↓ | 33% | 12.33 | 3.64 | BestGuidedDE | TwoArchive |
| 204 | NBLEA | 204.0 | 1.035 | 0.081↓ | 0% | nan | nan | NeighborhoodDE | ReferencePreference |
| 205 | MOEA-D-2WA | 205.0 | 1.034 | 0.081↓ | 0% | nan | nan | NeighborhoodDE | DecompositionReplacement |
| 206 | CMOCSO | 206.0 | 1.032 | 0.081↓ | 33% | 8.40 | 2.48 | CompetitiveSwarm | TwoArchive |
| 207 | M-PAES | 207.0 | 1.032 | 0.081↓ | 0% | nan | nan | ArchiveGA | PESA |
| 208 | MOEA-D-PFE | 208.0 | 1.032 | 0.081↓ | 0% | nan | nan | NeighborhoodDE | ReferencePreference |
| 209 | ENS-MOEA-D | 209.0 | 1.031 | 0.081↓ | 0% | nan | nan | NeighborhoodDE | DecompositionReplacement |
| 210 | CA-MOEA | 210.0 | 1.028 | 0.081↓ | 67% | 13.35 | 3.94 | ModelGaussian | RegionExplore |
| 211 | MO_Ring_PSO_SCD | 211.0 | 1.028 | 0.081↓ | 33% | 10.07 | 2.97 | RingPSO | ShiftedDistance |
| 212 | SLMEA | 212.0 | 1.025 | 0.081↓ | 33% | 9.14 | 2.70 | LocalSearch+ModelGaussian | MOEAIGDNS |
| 213 | MFFS | 213.0 | 1.023 | 0.081↓ | 67% | 12.05 | 3.56 | ModelGaussian | Entropy |
| 214 | ADSAPSO | 214.0 | 1.023 | 0.081↓ | 33% | 13.34 | 3.94 | CompetitiveSwarm+PSOFromArchive | EpsilonGrid |
| 215 | MOPSO-CD | 215.0 | 1.020 | 0.081↓ | 0% | nan | nan | PSOFromArchive | 自带 |
| 216 | BCE-MOEA-D | 216.0 | 1.019 | 0.081↓ | 0% | nan | nan | NeighborhoodGA | DecompositionReplacement |
| 217 | MMOEA-BH | 217.0 | 1.019 | 0.081↓ | 33% | 14.13 | 4.17 | Besiege | TwoArchive |
| 218 | CMEGL | 218.0 | 1.019 | 0.081↓ | 33% | 10.27 | 3.03 | CompetitiveSwarm | MPSOD |
| 219 | SMEA | 219.0 | 1.008 | 0.081↓ | 33% | 12.67 | 3.74 | ModelGaussian | ShiftedDistance |
| 220 | AGSEA | 220.0 | 1.007 | 0.081↓ | 0% | nan | nan | ModelGaussian | EpsilonGrid |
| 221 | IM-MOEA-D | 221.0 | 1.006 | 0.081↓ | 0% | nan | nan | ModelGaussian | DecompositionReplacement |
| 222 | AC-MMEA | 222.0 | 1.006 | 0.081↓ | 33% | 12.67 | 3.74 | ModelGaussian | TwoArchive |
| 223 | CMOEA-MS | 223.0 | 0.995 | 0.081↓ | 0% | nan | nan | GA+ModelGaussian | Entropy |
| 224 | PREA | 224.0 | 0.987 | 0.081↓ | 33% | 11.16 | 3.30 | ModelGaussian | RegionExplore |
| 225 | RM-MEDA | 225.0 | 0.986 | 0.081↓ | 0% | nan | nan | ModelGaussian | ShiftedDistance |
| 226 | GFM-MOEA | 226.0 | 0.984 | 0.081↓ | 0% | nan | nan | ModelGaussian | RegionExplore |
| 227 | FLEA | 227.0 | 0.983 | 0.081↓ | 0% | nan | nan | ModelGaussian | Entropy |
| 228 | CMOEA-MSG | 228.0 | 0.979 | 0.081↓ | 0% | nan | nan | ModelGaussian | EpsilonGrid |
| 229 | FDV | 229.0 | 0.975 | 0.081↓ | 0% | nan | nan | LocalSearch | Entropy |
| 230 | IM-MOEA | 230.0 | 0.966 | 0.081↓ | 0% | nan | nan | ModelGaussian | MOEAIGDNS |

## 按生成子代方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| GenerateARSBXOffspring+GenerateDirectionRestrictedDEOffspring+GenerateRandomImmigrantOffspring | 1 | 44.0 | 44.0 |
| GenerateARSBXOffspring | 7 | 47.4 | 16.0 |
| GenerateGAOffspring | 52 | 52.9 | 1.0 |
| GenerateCMAStyleOffspring+GenerateDirectionRestrictedDEOffspring+GenerateGAOffspring+GenerateLocalSearchOffspring | 1 | 58.0 | 58.0 |
| GenerateGAOffspring+GenerateLocalSearchOffspring | 1 | 70.0 | 70.0 |
| （算法自带实现） | 18 | 75.8 | 13.0 |
| GenerateBestGuidedDEOffspring+GenerateDirectionRestrictedDEOffspring+GenerateGAOffspring | 5 | 79.8 | 3.0 |
| GenerateArchiveGAOffspring+GenerateGAOffspring+GenerateRandomImmigrantOffspring | 1 | 80.0 | 80.0 |
| GenerateDirectionRestrictedDEOffspring+GenerateGAOffspring | 7 | 80.7 | 31.0 |
| GeneratePESAOffspring | 1 | 82.0 | 82.0 |
| GenerateARSBXOffspring+GenerateGAOffspring+GenerateRandomImmigrantOffspring | 3 | 82.0 | 24.0 |
| GenerateDirectionRestrictedDEOffspring+GenerateGAOffspring+GenerateLocalSearchOffspring | 3 | 85.0 | 38.0 |
| GenerateARSBXOffspring+GenerateGAOffspring+GenerateLocalSearchOffspring | 1 | 87.0 | 87.0 |
| GenerateGAOffspring+GenerateLocalSearchOffspring+GenerateModelGaussianOffspring | 1 | 101.0 | 101.0 |
| GenerateBestGuidedDEOffspring+GenerateGAOffspring | 3 | 102.3 | 45.0 |
| GenerateNeighborhoodGAOffspring | 7 | 103.1 | 4.0 |
| GenerateNeighborhoodDEOffspring+GenerateNeighborhoodGAOffspring | 4 | 105.0 | 84.0 |
| GenerateARSBXOffspring+GenerateBestGuidedDEOffspring+GenerateGAOffspring | 6 | 107.5 | 36.0 |
| GenerateDirectionRestrictedDEOffspring | 13 | 114.2 | 5.0 |
| GenerateBestGuidedDEOffspring+GenerateCMAStyleOffspring+GenerateNeighborhoodDEOffspring+GenerateNeighborhoodGAOffspring | 1 | 118.0 | 118.0 |
| GenerateBestGuidedDEOffspring+GenerateCMAStyleOffspring | 1 | 124.0 | 124.0 |
| GenerateArchiveGAOffspring+GenerateGAOffspring | 1 | 126.0 | 126.0 |
| GenerateCMAStyleOffspring | 6 | 134.3 | 104.0 |
| GenerateDirectionRestrictedDEOffspring+GenerateModelGaussianOffspring | 1 | 141.0 | 141.0 |
| GenerateBestGuidedDEOffspring+GenerateGAOffspring+GenerateLocalSearchOffspring | 2 | 147.5 | 145.0 |
| GenerateArchiveGAOffspring+GenerateBestGuidedDEOffspring | 1 | 153.0 | 153.0 |
| GenerateDEOffspring | 2 | 155.0 | 132.0 |
| GenerateDirectionRestrictedDEOffspring+GenerateLocalSearchOffspring | 1 | 157.0 | 157.0 |
| GenerateGAOffspring+GenerateLocalSearchOffspring+GenerateNeighborhoodDEOffspring+GenerateRandomImmigrantOffspring | 1 | 159.0 | 159.0 |
| GenerateLocalSearchOffspring | 7 | 163.9 | 112.0 |
| GenerateBestGuidedDEOffspring+GenerateGAOffspring+GenerateModelGaussianOffspring | 2 | 164.0 | 144.0 |
| GenerateNeighborhoodDEOffspring | 15 | 164.6 | 74.0 |
| GenerateBestGuidedDEOffspring+GenerateLocalSearchOffspring+GenerateRandomImmigrantOffspring | 1 | 165.0 | 165.0 |
| GenerateBestGuidedDEOffspring | 7 | 169.1 | 128.0 |
| GenerateArchiveGAOffspring | 3 | 170.3 | 148.0 |
| GenerateBesiegeOffspring+GenerateBestGuidedDEOffspring | 1 | 176.0 | 176.0 |
| GenerateBestGuidedDEOffspring+GenerateNeighborhoodDEOffspring+GenerateNeighborhoodGAOffspring | 2 | 177.5 | 167.0 |
| GenerateDecompositionPSOOffspring | 2 | 180.0 | 173.0 |
| GenerateCompetitiveSwarmOffspring | 6 | 180.8 | 109.0 |
| GenerateLocalSearchOffspring+GenerateModelGaussianOffspring | 3 | 181.3 | 158.0 |
| GenerateArchiveGAOffspring+GeneratePSOOffspringFromArchive | 1 | 189.0 | 189.0 |
| GenerateBesiegeOffspring | 3 | 189.7 | 160.0 |
| GeneratePSOOffspring | 1 | 190.0 | 190.0 |
| GeneratePSOOffspringFromArchive | 3 | 190.7 | 161.0 |
| GenerateBestGuidedDEOffspring+GenerateCMAStyleOffspring+GenerateGAOffspring | 1 | 197.0 | 197.0 |
| GenerateBesiegeOffspring+GenerateLocalSearchOffspring | 1 | 200.0 | 200.0 |
| GenerateGAOffspring+GenerateModelGaussianOffspring | 2 | 204.0 | 185.0 |
| GenerateModelGaussianOffspring | 15 | 206.1 | 52.0 |
| GenerateRingPSOOffspring | 1 | 211.0 | 211.0 |
| GenerateCompetitiveSwarmOffspring+GeneratePSOOffspringFromArchive | 1 | 214.0 | 214.0 |

## 按环境选择方式汇总（使用该模块的算法的平均排名，越小越好）

| 模块 | 算法数 | 平均排名 | 最好排名 |
|---|---|---|---|
| EnvironmentalSelectionRNSGA | 1 | 1.0 | 1.0 |
| EnvironmentalSelectionAGEMOEAII | 1 | 8.0 | 8.0 |
| EnvironmentalSelectionRPEA | 1 | 11.0 | 11.0 |
| EnvironmentalSelectionMOMBI | 1 | 21.0 | 21.0 |
| EnvironmentalSelectionConflict+EnvironmentalSelectionRVEAa | 1 | 23.0 | 23.0 |
| IBEA_environmentalSelection | 1 | 26.0 | 26.0 |
| VaEA_environmentalSelection | 1 | 27.0 | 27.0 |
| EnvironmentalSelectionSPEA2 | 2 | 33.5 | 14.0 |
| HypeEnvironmentalSelection | 1 | 40.0 | 40.0 |
| EnvironmentalSelectionBiGE | 1 | 41.0 | 41.0 |
| EnvironmentalSelectionNSGA+EnvironmentalSelectionRegionExplore+EnvironmentalSelectionTwoArchive | 1 | 49.0 | 49.0 |
| EnvironmentalSelectionGNSGA | 2 | 50.0 | 43.0 |
| GrEA_EnvironmentalSelection | 1 | 62.0 | 62.0 |
| EnvironmentalSelectionRegionExplore+EnvironmentalSelectionTwoArchive | 2 | 63.0 | 31.0 |
| NSGA_III_environmentalSelection | 1 | 65.0 | 65.0 |
| EnvironmentalSelectionRPDNSGA | 2 | 65.5 | 12.0 |
| EnvironmentalSelectionSPEA2SDE | 2 | 66.0 | 2.0 |
| EnvironmentalSelectionConflict | 6 | 85.5 | 10.0 |
| EnvironmentalSelectionSIBEA | 6 | 91.7 | 13.0 |
| EnvironmentalSelectionRVEAa | 6 | 95.3 | 7.0 |
| EnvironmentalSelectionKnEA | 3 | 96.3 | 22.0 |
| EnvironmentalSelectionConflict+EnvironmentalSelectionTwoArchive | 3 | 99.3 | 77.0 |
| （算法自带实现） | 12 | 101.7 | 15.0 |
| EnvironmentalSelectionReferencePreference | 22 | 103.9 | 18.0 |
| EnvironmentalSelectionEntropy | 17 | 109.5 | 16.0 |
| EnvironmentalSelection0+EnvironmentalSelection1 | 1 | 110.0 | 110.0 |
| EnvironmentalSelectionShiftedDistance | 14 | 112.3 | 5.0 |
| EnvironmentalSelectionTDEA | 1 | 116.0 | 116.0 |
| EnvironmentalSelectionNSGA | 14 | 122.1 | 24.0 |
| EnvironmentalSelectionSPEAR | 1 | 123.0 | 123.0 |
| EnvironmentalSelectionMPSOD | 12 | 125.2 | 35.0 |
| EnvironmentalSelectionAGEMOEAII+EnvironmentalSelectionNSGA | 1 | 127.0 | 127.0 |
| EnvironmentalSelectionRegionExplore | 20 | 128.5 | 3.0 |
| EnvironmentalSelectionSMS | 3 | 130.7 | 105.0 |
| EnvironmentalSelectionTwoArchive | 23 | 133.3 | 54.0 |
| EnvironmentalSelectionAGE | 1 | 139.0 | 139.0 |
| EnvironmentalSelectionMOEAIGDNS | 8 | 139.2 | 52.0 |
| EnvironmentalSelectionPESA | 2 | 144.5 | 82.0 |
| EnvironmentalSelectionNSGA+EnvironmentalSelectionRVEAa | 1 | 159.0 | 159.0 |
| DecompositionReplacement | 17 | 160.0 | 84.0 |
| EnvironmentalSelectionEpsilonGrid | 11 | 161.6 | 45.0 |
| SRA_environmentalSelection | 1 | 181.0 | 181.0 |
| EnvironmentalSelectionMOEAIGDNS+EnvironmentalSelectionNSGA | 1 | 184.0 | 184.0 |
| BCE_EnvironmentalSelection | 1 | 194.0 | 194.0 |
