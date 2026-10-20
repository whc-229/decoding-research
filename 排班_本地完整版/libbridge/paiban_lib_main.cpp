//
//  main.cpp
//  MOEA
//
//  Created by yunglynn on 17-12-14.
//  Copyright (c) 2017年 yunglynn. All rights reserved.
//
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include "MOEA_solver.h"
#include <time.h>

static int g_budget = 1000;
#define MAXGEN g_budget
#define LEN 4
#define n 4
#define N 4

using namespace std;

void ZDT1_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    ZDT1(var, obj, nvar, 2);
}

void ZDT2_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    ZDT2(var, obj, nvar, NULL);
}

void ZDT3_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    ZDT3(var, obj, nvar, 2);
}

void ZDT4_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    ZDT4(var, obj, nvar, 2);
}

void ZDT6_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    ZDT6(var, obj, nvar, 2);
}

void DTLZ1_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ1(var, obj, nvar, 3);
}

void DTLZ2_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ2(var, obj, nvar, 3);
}

void DTLZ3_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ3(var, obj, nvar, 3);
}

void DTLZ4_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ4(var, obj, nvar, 3);
}

void DTLZ5_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ5(var, obj, nvar, 3);
}

void DTLZ6_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ6(var, obj, nvar, 3);
}

void DTLZ7_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    DTLZ7(var, obj, nvar, 3);
}

enum AlgorithmType
{
    ALG_BCE,
    ALG_BCE2,
    ALG_HYPE,
    ALG_IBEA,
    ALG_MOEAD,
    ALG_NSGA,
    ALG_NSGA_III,
    ALG_PICEAG,
    ALG_RVEA,
    ALG_GREA,
    ALG_R2HCA,
    ALG_VAEA,
    ALG_MOEADD,
    ALG_SRA,
    ALG_SPEA2,
    ALG_SPEA2SDE,
    ALG_GDE3,
    ALG_SMSEMOA,
    ALG_SMPSO,
    ALG_MOPSOCD,
    ALG_MOPSO,
    ALG_MOCELL,
    ALG_PESAII,
    ALG_MOEADDE,
    ALG_AGEMOEA,
    ALG_BIGE,
    ALG_RPDNSGAII,
    ALG_RNSGAII,
    ALG_KNEA,
    ALG_RPEA,
    ALG_AGEMOEAII,
    ALG_GNSGAII,
    ALG_NSGAIIARSBX,
    ALG_MOMBIII,
    ALG_RVEAA,
    ALG_TDEA,
    ALG_SIBEA,
    ALG_SPEAR,
    ALG_MOEAIGDNS,
    ALG_MPAES,
    ALG_NMPSO,
    ALG_MPSOD,
    ALG_AGEII,
    ALG_BCEIBEA,
    ALG_BCEMOEAD,
    ALG_MOEADDRA,
    ALG_MOEADSTM,
    ALG_MOEADAWA,
    ALG_MOEADM2M,
    ALG_MOEADUR,
    ALG_MOEADPAS,
    ALG_ADAW,
    ALG_WASFGA,
    ALG_GWASFGA,
    ALG_ISIBEA,
    ALG_TWOARCH2,
    ALG_RSEA,
    ALG_NSGAIISDR,
    ALG_MOEAPC,
    ALG_EMOEA,
    ALG_DMOPSO,
    ALG_MORINGPSOSCD,
    ALG_ENSMOEAD,
    ALG_MOEADDU,
    ALG_MOEADVOV,
    ALG_MOEADCMA,
    ALG_MCEAD,
    ALG_SFADE,
    ALG_MOEADDCWV,
    ALG_MOEADMRDL,
    ALG_MOEARE,
    ALG_MAOEAIGD,
    ALG_MAOEACSS,
    ALG_MAOEADDFC,
    ALG_HEA,
    ALG_HEEMOEA,
    ALG_NSGAIICONFLICT,
    ALG_TSNSGAII,
    ALG_PEEA,
    ALG_ONEBYONEEA,
    ALG_NRVMOEA,
    ALG_MSEA,
    ALG_ANSGAIII,
    ALG_AENSGAII,
    ALG_ARMOEA,
    ALG_CCGDE3,
    ALG_DEAGNG,
    ALG_DGEA,
    ALG_DNNSGAII,
    ALG_DNSGAII,
    ALG_EAGMOEAD,
    ALG_IDBEA,
    ALG_KLNSGAII,
    ALG_MAOEAHAP,
    ALG_MAOEAIT,
    ALG_MOEAD2WA,
    ALG_MOEADFRRMAB,
    ALG_MOEADPFE,
    ALG_MOEADVA,
    ALG_MOEANZD,
    ALG_MSOPSII,
    ALG_NNIA,
    ALG_RMMEDA,
    ALG_MOCMA,
    ALG_HREA,
    ALG_RVEAIGNG,
    ALG_RMOEADVA,
    ALG_MAOEARD,
    ALG_SIBEAKEMOSS,
    ALG_LMOCSO,
    ALG_LMEA,
    ALG_LSMOF,
    ALG_MOEADURAW,
    ALG_MOEADDYTS,
    ALG_SMEA,
    ALG_NSLS,
    ALG_MYODEMR,
    ALG_MMOPSO,
    ALG_MOBCA,
    ALG_CAMOEA,
    ALG_DWU,
    ALG_EFRRR,
    ALG_CMOEAD,
    ALG_CTAEA,
    ALG_CTSEA,
    ALG_DCNSGAIII,
    ALG_DMOEAEC,
    ALG_ICMA,
    ALG_MSCEA,
    ALG_PREA,
    ALG_SGEA,
    ALG_SSCEA,
    ALG_HPAEA,
    ALG_TDEACPBI,
    ALG_KRVEA,
    ALG_IMMOEAD,
    ALG_IMMOEA,
    ALG_LMOEADS,
    ALG_LRMOEA,
    ALG_MOEGS,
    ALG_MOSD,
    ALG_FLEA,
    ALG_BICO,
    ALG_NSBIDICO,
    ALG_C3M,
    ALG_CAEAD,
    ALG_CCMO,
    ALG_CGLP,
    ALG_CLIA,
    ALG_CMDEIPCM,
    ALG_CMEGL,
    ALG_CMME,
    ALG_CMMO,
    ALG_CMOBR,
    ALG_CMOCSO,
    ALG_CMODEFTR,
    ALG_CMOEA2S,
    ALG_CMOEAAOP,
    ALG_CMOEACD,
    ALG_CMOEAMS,
    ALG_CMOEAMSG,
    ALG_CMOES,
    ALG_ACMMEA,
    ALG_AFSEA,
    ALG_AGSEA,
    ALG_APSEA,
    ALG_CMOEAMOP,
    ALG_CNSDEDVC,
    ALG_COMMEA,
    ALG_DKCA,
    ALG_DMMOEA,
    ALG_DPPPS,
    ALG_DPCPRA,
    ALG_DPVAPS,
    ALG_DSPCMDE,
    ALG_DSSEA,
    ALG_DVCEA,
    ALG_FDV,
    ALG_GFMMOEA,
    ALG_GLMO,
    ALG_GPSOM,
    ALG_HHCMMEA,
    ALG_ADSAPSO,
    ALG_CIEMO,
    ALG_CMOPSO,
    ALG_CPSMOEA,
    ALG_DAEA,
    ALG_EGES,
    ALG_FRCGM,
    ALG_GDVTSF,
    ALG_ILCMO,
    ALG_IMCMOEAD,
    ALG_KLEA,
    ALG_LCMEA,
    ALG_LMPFE,
    ALG_MCCMO,
    ALG_MFFS,
    ALG_MFOSPEA2,
    ALG_MOCGDE,
    ALG_MOEACKF,
    ALG_MOEADCMT,
    ALG_MOEADDAE,
    ALG_CMOSMA,
    ALG_CMADPPS,
    ALG_EMCMO,
    ALG_EMMOEA,
    ALG_EMCMMS,
    ALG_EMYOC,
    ALG_MGCEA,
    ALG_MMEAARM,
    ALG_MMEAWI,
    ALG_MMEAPSL,
    ALG_MMOEABH,
    ALG_MOL2SMEA,
    ALG_MOEAIB,
    ALG_MPMMEA,
    ALG_MSCMO,
    ALG_NUCEA,
    ALG_OSPNSDE,
    ALG_PBNSGAIII,
    ALG_PBRVEA,
    ALG_PIEA,
    ALG_EDNARMOEA,
    ALG_IMTCMO,
    ALG_IMTCMOBS,
    ALG_LCSA,
    ALG_LDSAF,
    ALG_LERD,
    ALG_NBLEA,
    ALG_NNDREAMO,
    ALG_POCEA,
    ALG_PPS,
    ALG_PRCEA,
    ALG_PRDH,
    ALG_RGAM12,
    ALG_RGAM22,
    ALG_SCDAS,
    ALG_SECSO,
    ALG_SNSGAII,
    ALG_SCEA,
    ALG_SGECF,
    ALG_SLMEA,
    ALG_MTS,
    ALG_WVMOEAP,
    ALG_WOF,
    ALG_TRIMOEATAR,
    ALG_NSGAIIDTI
};

typedef struct Algorithm_config
{
    const char *name;
    AlgorithmType type;
} AlgorithmConfig;

void run_algorithm_step(MOEA_solver &solver, AlgorithmType type)
{
    switch (type)
    {
    case ALG_BCE:
        solver.BCE();
        break;
    case ALG_BCE2:
        solver.BCE2();
        break;
    case ALG_HYPE:
        solver.hypE();
        break;
    case ALG_IBEA:
        solver.IBEA();
        break;
    case ALG_MOEAD:
        solver.MOEAD();
        break;
    case ALG_NSGA:
        solver.NSGA();
        break;
    case ALG_NSGA_III:
        solver.NSGA_III();
        break;
    case ALG_PICEAG:
        solver.PICEAg();
        break;
    case ALG_RVEA:
        solver.RVEA(MAXGEN);
        break;
    case ALG_GREA:
        solver.GrEA();
        break;
    case ALG_R2HCA:
        solver.R2HCA();
        break;
    case ALG_VAEA:
        solver.VaEA();
        break;
    case ALG_MOEADD:
        solver.MOEADD();
        break;
    case ALG_SRA:
        solver.SRA();
        break;
    case ALG_SPEA2:
        solver.SPEA2();
        break;
    case ALG_SPEA2SDE:
        solver.SPEA2SDE();
        break;
    case ALG_GDE3:
        solver.GDE3();
        break;
    case ALG_SMSEMOA:
        solver.SMSEMOA();
        break;
    case ALG_SMPSO:
        solver.SMPSO();
        break;
    case ALG_MOPSOCD:
        solver.MOPSOCD();
        break;
    case ALG_MOPSO:
        solver.MOPSO();
        break;
    case ALG_MOCELL:
        solver.MOCell();
        break;
    case ALG_PESAII:
        solver.PESAII();
        break;
    case ALG_MOEADDE:
        solver.MOEADDE();
        break;
    case ALG_AGEMOEA:
        solver.AGEMOEA();
        break;
    case ALG_BIGE:
        solver.BiGE();
        break;
    case ALG_RPDNSGAII:
        solver.RPDNSGAII();
        break;
    case ALG_RNSGAII:
        solver.RNSGAII();
        break;
    case ALG_KNEA:
        solver.KnEA();
        break;
    case ALG_RPEA:
        solver.RPEA();
        break;
    case ALG_AGEMOEAII:
        solver.AGEMOEAII();
        break;
    case ALG_GNSGAII:
        solver.GNSGAII();
        break;
    case ALG_NSGAIIARSBX:
        solver.NSGAIIARSBX();
        break;
    case ALG_MOMBIII:
        solver.MOMBIII();
        break;
    case ALG_RVEAA:
        solver.RVEAa();
        break;
    case ALG_TDEA:
        solver.TDEA();
        break;
    case ALG_SIBEA:
        solver.SIBEA();
        break;
    case ALG_SPEAR:
        solver.SPEAR();
        break;
    case ALG_MOEAIGDNS:
        solver.MOEAIGDNS();
        break;
    case ALG_MPAES:
        solver.MPAES();
        break;
    case ALG_NMPSO:
        solver.NMPSO();
        break;
    case ALG_MPSOD:
        solver.MPSOD();
        break;
    case ALG_AGEII:
        solver.AGEII();
        break;
    case ALG_BCEIBEA:
        solver.BCEIBEA();
        break;
    case ALG_BCEMOEAD:
        solver.BCEMOEAD();
        break;
    case ALG_MOEADDRA:
        solver.MOEADDRA();
        break;
    case ALG_MOEADSTM:
        solver.MOEADSTM();
        break;
    case ALG_MOEADAWA:
        solver.MOEADAWA();
        break;
    case ALG_MOEADM2M:
        solver.MOEADM2M();
        break;
    case ALG_MOEADUR:
        solver.MOEADUR();
        break;
    case ALG_MOEADPAS:
        solver.MOEADPaS();
        break;
    case ALG_ADAW:
        solver.AdaW();
        break;
    case ALG_WASFGA:
        solver.WASFGA();
        break;
    case ALG_GWASFGA:
        solver.GWASFGA();
        break;
    case ALG_ISIBEA:
        solver.ISIBEA();
        break;
    case ALG_TWOARCH2:
        solver.TwoArch2();
        break;
    case ALG_RSEA:
        solver.RSEA();
        break;
    case ALG_NSGAIISDR:
        solver.NSGAIISDR();
        break;
    case ALG_MOEAPC:
        solver.MOEAPC();
        break;
    case ALG_EMOEA:
        solver.EMOEA();
        break;
    case ALG_DMOPSO:
        solver.DMOPSO();
        break;
    case ALG_MORINGPSOSCD:
        solver.MORingPSOSCD();
        break;
    case ALG_ENSMOEAD:
        solver.ENSMOEAD();
        break;
    case ALG_MOEADDU:
        solver.MOEADDU();
        break;
    case ALG_MOEADVOV:
        solver.MOEADVOV();
        break;
    case ALG_MOEADCMA:
        solver.MOEADCMA();
        break;
    case ALG_MCEAD:
        solver.MCEAD();
        break;
    case ALG_SFADE:
        solver.SFADE();
        break;
    case ALG_MOEADDCWV:
        solver.MOEADDCWV();
        break;
    case ALG_MOEADMRDL:
        solver.MOEADMRDL();
        break;
    case ALG_MOEARE:
        solver.MOEARE();
        break;
    case ALG_MAOEAIGD:
        solver.MaOEAIGD();
        break;
    case ALG_MAOEACSS:
        solver.MaOEACSS();
        break;
    case ALG_MAOEADDFC:
        solver.MaOEADDFC();
        break;
    case ALG_HEA:
        solver.HEA();
        break;
    case ALG_HEEMOEA:
        solver.HeEMOEA();
        break;
    case ALG_NSGAIICONFLICT:
        solver.NSGAIIConflict();
        break;
    case ALG_TSNSGAII:
        solver.TSNSGAII();
        break;
    case ALG_PEEA:
        solver.PeEA();
        break;
    case ALG_ONEBYONEEA:
        solver.OneByOneEA();
        break;
    case ALG_NRVMOEA:
        solver.NRVMOEA();
        break;
    case ALG_MSEA:
        solver.MSEA();
        break;
    case ALG_ANSGAIII:
        solver.ANSGAIII();
        break;
    case ALG_AENSGAII:
        solver.AENSGAII();
        break;
    case ALG_ARMOEA:
        solver.ARMOEA();
        break;
    case ALG_CCGDE3:
        solver.CCGDE3();
        break;
    case ALG_DEAGNG:
        solver.DEAGNG();
        break;
    case ALG_DGEA:
        solver.DGEA();
        break;
    case ALG_DNNSGAII:
        solver.DNNSGAII();
        break;
    case ALG_DNSGAII:
        solver.DNSGAII();
        break;
    case ALG_EAGMOEAD:
        solver.EAGMOEAD();
        break;
    case ALG_IDBEA:
        solver.IDBEA();
        break;
    case ALG_KLNSGAII:
        solver.KLNSGAII();
        break;
    case ALG_MAOEAHAP:
        solver.MaOEAHAP();
        break;
    case ALG_MAOEAIT:
        solver.MaOEAIT();
        break;
    case ALG_MOEAD2WA:
        solver.MOEAD2WA();
        break;
    case ALG_MOEADFRRMAB:
        solver.MOEADFRRMAB();
        break;
    case ALG_MOEADPFE:
        solver.MOEADPFE();
        break;
    case ALG_MOEADVA:
        solver.MOEADVA();
        break;
    case ALG_MOEANZD:
        solver.MOEANZD();
        break;
    case ALG_MSOPSII:
        solver.MSOPSII();
        break;
    case ALG_NNIA:
        solver.NNIA();
        break;
    case ALG_RMMEDA:
        solver.RMMEDA();
        break;
    case ALG_MOCMA:
        solver.MOCMA();
        break;
    case ALG_HREA:
        solver.HREA();
        break;
    case ALG_RVEAIGNG:
        solver.RVEAiGNG();
        break;
    case ALG_RMOEADVA:
        solver.RMOEADVA();
        break;
    case ALG_MAOEARD:
        solver.MaOEARD();
        break;
    case ALG_SIBEAKEMOSS:
        solver.SIBEAkEMOSS();
        break;
    case ALG_LMOCSO:
        solver.LMOCSO();
        break;
    case ALG_LMEA:
        solver.LMEA();
        break;
    case ALG_LSMOF:
        solver.LSMOF();
        break;
    case ALG_MOEADURAW:
        solver.MOEADURAW();
        break;
    case ALG_MOEADDYTS:
        solver.MOEADDYTS();
        break;
    case ALG_SMEA:
        solver.SMEA();
        break;
    case ALG_NSLS:
        solver.NSLS();
        break;
    case ALG_MYODEMR:
        solver.MyODEMR();
        break;
    case ALG_MMOPSO:
        solver.MMOPSO();
        break;
    case ALG_MOBCA:
        solver.MOBCA();
        break;
    case ALG_CAMOEA:
        solver.CAMOEA();
        break;
    case ALG_DWU:
        solver.DWU();
        break;
    case ALG_EFRRR:
        solver.EFRRR();
        break;
    case ALG_CMOEAD:
        solver.CMOEAD();
        break;
    case ALG_CTAEA:
        solver.CTAEA();
        break;
    case ALG_CTSEA:
        solver.CTSEA();
        break;
    case ALG_DCNSGAIII:
        solver.DCNSGAIII();
        break;
    case ALG_DMOEAEC:
        solver.DMOEAeC();
        break;
    case ALG_ICMA:
        solver.ICMA();
        break;
    case ALG_MSCEA:
        solver.MSCEA();
        break;
    case ALG_PREA:
        solver.PREA();
        break;
    case ALG_SGEA:
        solver.SGEA();
        break;
    case ALG_SSCEA:
        solver.SSCEA();
        break;
    case ALG_HPAEA:
        solver.HPAEA();
        break;
    case ALG_TDEACPBI:
        solver.TDEACPBI();
        break;
    case ALG_KRVEA:
        solver.KRVEA();
        break;
    case ALG_IMMOEAD:
        solver.IMMOEAD();
        break;
    case ALG_IMMOEA:
        solver.IMMOEA();
        break;
    case ALG_LMOEADS:
        solver.LMOEADS();
        break;
    case ALG_LRMOEA:
        solver.LRMOEA();
        break;
    case ALG_MOEGS:
        solver.MOEGS();
        break;
    case ALG_MOSD:
        solver.MOSD();
        break;
    case ALG_FLEA:
        solver.FLEA();
        break;
    case ALG_BICO:
        solver.BiCo();
        break;
    case ALG_NSBIDICO:
        solver.NSBiDiCo();
        break;
    case ALG_C3M:
        solver.C3M();
        break;
    case ALG_CAEAD:
        solver.CAEAD();
        break;
    case ALG_CCMO:
        solver.CCMO();
        break;
    case ALG_CGLP:
        solver.CGLP();
        break;
    case ALG_CLIA:
        solver.CLIA();
        break;
    case ALG_CMDEIPCM:
        solver.CMDEIPCM();
        break;
    case ALG_CMEGL:
        solver.CMEGL();
        break;
    case ALG_CMME:
        solver.CMME();
        break;
    case ALG_CMMO:
        solver.CMMO();
        break;
    case ALG_CMOBR:
        solver.CMOBR();
        break;
    case ALG_CMOCSO:
        solver.CMOCSO();
        break;
    case ALG_CMODEFTR:
        solver.CMODEFTR();
        break;
    case ALG_CMOEA2S:
        solver.CMOEA2S();
        break;
    case ALG_CMOEAAOP:
        solver.CMOEAAOP();
        break;
    case ALG_CMOEACD:
        solver.CMOEACD();
        break;
    case ALG_CMOEAMS:
        solver.CMOEAMS();
        break;
    case ALG_CMOEAMSG:
        solver.CMOEAMSG();
        break;
    case ALG_CMOES:
        solver.CMOES();
        break;
    case ALG_ACMMEA:
        solver.ACMMEA();
        break;
    case ALG_AFSEA:
        solver.AFSEA();
        break;
    case ALG_AGSEA:
        solver.AGSEA();
        break;
    case ALG_APSEA:
        solver.APSEA();
        break;
    case ALG_CMOEAMOP:
        solver.CMOEAMOP();
        break;
    case ALG_CNSDEDVC:
        solver.CNSDEDVC();
        break;
    case ALG_COMMEA:
        solver.CoMMEA();
        break;
    case ALG_DKCA:
        solver.DKCA();
        break;
    case ALG_DMMOEA:
        solver.DMMOEA();
        break;
    case ALG_DPPPS:
        solver.DPPPS();
        break;
    case ALG_DPCPRA:
        solver.DPCPRA();
        break;
    case ALG_DPVAPS:
        solver.DPVAPS();
        break;
    case ALG_DSPCMDE:
        solver.DSPCMDE();
        break;
    case ALG_DSSEA:
        solver.DSSEA();
        break;
    case ALG_DVCEA:
        solver.DVCEA();
        break;
    case ALG_FDV:
        solver.FDV();
        break;
    case ALG_GFMMOEA:
        solver.GFMMOEA();
        break;
    case ALG_GLMO:
        solver.GLMO();
        break;
    case ALG_GPSOM:
        solver.GPSOM();
        break;
    case ALG_HHCMMEA:
        solver.HHCMMEA();
        break;
    case ALG_ADSAPSO:
        solver.ADSAPSO();
        break;
    case ALG_CIEMO:
        solver.CIEMO();
        break;
    case ALG_CMOPSO:
        solver.CMOPSO();
        break;
    case ALG_CPSMOEA:
        solver.CPSMOEA();
        break;
    case ALG_DAEA:
        solver.DAEA();
        break;
    case ALG_EGES:
        solver.EGES();
        break;
    case ALG_FRCGM:
        solver.FRCGM();
        break;
    case ALG_GDVTSF:
        solver.GDVTSF();
        break;
    case ALG_ILCMO:
        solver.ILCMO();
        break;
    case ALG_IMCMOEAD:
        solver.IMCMOEAD();
        break;
    case ALG_KLEA:
        solver.KLEA();
        break;
    case ALG_LCMEA:
        solver.LCMEA();
        break;
    case ALG_LMPFE:
        solver.LMPFE();
        break;
    case ALG_MCCMO:
        solver.MCCMO();
        break;
    case ALG_MFFS:
        solver.MFFS();
        break;
    case ALG_MFOSPEA2:
        solver.MFOSPEA2();
        break;
    case ALG_MOCGDE:
        solver.MOCGDE();
        break;
    case ALG_MOEACKF:
        solver.MOEACKF();
        break;
    case ALG_MOEADCMT:
        solver.MOEADCMT();
        break;
    case ALG_MOEADDAE:
        solver.MOEADDAE();
        break;
    case ALG_CMOSMA:
        solver.CMOSMA();
        break;
    case ALG_CMADPPS:
        solver.CMaDPPs();
        break;
    case ALG_EMCMO:
        solver.EMCMO();
        break;
    case ALG_EMMOEA:
        solver.EMMOEA();
        break;
    case ALG_EMCMMS:
        solver.EMCMMS();
        break;
    case ALG_EMYOC:
        solver.EMyOC();
        break;
    case ALG_MGCEA:
        solver.MGCEA();
        break;
    case ALG_MMEAARM:
        solver.MMEAARM();
        break;
    case ALG_MMEAWI:
        solver.MMEAWI();
        break;
    case ALG_MMEAPSL:
        solver.MMEAPSL();
        break;
    case ALG_MMOEABH:
        solver.MMOEABH();
        break;
    case ALG_MOL2SMEA:
        solver.MOL2SMEA();
        break;
    case ALG_MOEAIB:
        solver.MOEAIB();
        break;
    case ALG_MPMMEA:
        solver.MPMMEA();
        break;
    case ALG_MSCMO:
        solver.MSCMO();
        break;
    case ALG_NUCEA:
        solver.NUCEA();
        break;
    case ALG_OSPNSDE:
        solver.OSPNSDE();
        break;
    case ALG_PBNSGAIII:
        solver.PBNSGAIII();
        break;
    case ALG_PBRVEA:
        solver.PBRVEA();
        break;
    case ALG_PIEA:
        solver.PIEA();
        break;
    case ALG_EDNARMOEA:
        solver.EDNARMOEA();
        break;
    case ALG_IMTCMO:
        solver.IMTCMO();
        break;
    case ALG_IMTCMOBS:
        solver.IMTCMOBS();
        break;
    case ALG_LCSA:
        solver.LCSA();
        break;
    case ALG_LDSAF:
        solver.LDSAF();
        break;
    case ALG_LERD:
        solver.LERD();
        break;
    case ALG_NBLEA:
        solver.NBLEA();
        break;
    case ALG_NNDREAMO:
        solver.NNDREAMO();
        break;
    case ALG_POCEA:
        solver.POCEA();
        break;
    case ALG_PPS:
        solver.PPS();
        break;
    case ALG_PRCEA:
        solver.PRCEA();
        break;
    case ALG_PRDH:
        solver.PRDH();
        break;
    case ALG_RGAM12:
        solver.RGAM12();
        break;
    case ALG_RGAM22:
        solver.RGAM22();
        break;
    case ALG_SCDAS:
        solver.SCDAS();
        break;
    case ALG_SECSO:
        solver.SECSO();
        break;
    case ALG_SNSGAII:
        solver.SNSGAII();
        break;
    case ALG_SCEA:
        solver.SCEA();
        break;
    case ALG_SGECF:
        solver.SGECF();
        break;
    case ALG_SLMEA:
        solver.SLMEA();
        break;
    case ALG_MTS:
        solver.MTS();
        break;
    case ALG_WVMOEAP:
        solver.WVMOEAP();
        break;
    case ALG_WOF:
        solver.WOF();
        break;
    case ALG_TRIMOEATAR:
        solver.TriMOEATAR();
        break;
    case ALG_NSGAIIDTI:
        solver.NSGAIIDTI();
        break;
    }
}

void print_ep_summary(const char *algorithm_name, MOEA_solver &solver, ostream &out)
{
    out << "\n[" << algorithm_name << "] EP size = " << solver.EP.size() << ", eval_count = " << solver.eval_count
        << endl;
    out << fixed << setprecision(4);
    for (auto iter = solver.EP.begin(); iter != solver.EP.end(); iter++)
    {
        for (int j = 0; j < solver.Nobj; j++)
        {
            if (j > 0)
                out << "  ";
            out << iter->obj[j];
        }
        out << endl;
    }
}

int algorithm_step_evaluation_upper_bound(MOEA_solver &solver, AlgorithmType type)
{
    switch (type)
    {
    case ALG_BCE:
    case ALG_BCE2:
        return solver.Popsize + solver.EP_capability;
    case ALG_PICEAG:
        return solver.fullSize2;
    case ALG_NMPSO:
        return solver.Popsize * 2;
    case ALG_R2HCA:
        return 1;
    default:
        return solver.Popsize;
    }
}

void consume_remaining_evaluations(MOEA_solver &solver, int evaluation_budget)
{
    float *x = new float[solver.Nvar];
    float *obj = new float[solver.Nobj];

    while (solver.eval_count < evaluation_budget)
    {
        for (int i = 0; i < solver.Nvar; i++)
            x[i] = randval(solver.Lbound, solver.Ubound);
        solver.EvaluFunc(x, obj, solver.Nvar, solver.Model, solver.probM);
        solver.eval_count++;
    }

    delete[] x;
    delete[] obj;
}


// ======================= 排班问题接入（2026-10-14，本地研究版）=======================
// 目标函数来自 model-crow 排班模型（problem.cpp 的 robot_arrangement_moea），经 paiban_bridge.cpp 调用。
// 运行前用 paiban_decX --eval-genes 空数组 先在工作目录生成 config/（与服务端相同的运行时配置）。
// 公平起见：评价次数以"真实调用目标函数的次数"计（含初始化），每个算法同一预算；
//           结果取所有被评价过的解的非支配集（桥接层统一维护），不依赖各算法自己的 EP 实现。
int paiban_bridge_setup(const char *workdir);
void paiban_bridge_eval(float *x, float *obj, int nvar);
long long paiban_bridge_evals();
void paiban_bridge_dump(const char *path, const char *alg, double secs, int popsize, int nvar);

extern float g_paiban_lb, g_paiban_level_quota;
void PaibanLevelNiche(MOEA_solver &s, int gen_mode);
void PaibanLBRNSGA(MOEA_solver &s);

void PAIBAN_evaluation(float *var, float *obj, int nvar, DisassemblyTAOG *model, int m)
{
    paiban_bridge_eval(var, obj, nvar);
}

int main(int argc, char *argv[])
{
    string workdir = "work", out_path = "result_lib.json", selected_algorithm;
    int H = 16, budget = 500;
    bool list_only = false;
    for (int i = 1; i < argc; i++)
    {
        string a = argv[i];
        if (a == "--workdir" && i + 1 < argc) workdir = argv[++i];
        else if (a == "--out" && i + 1 < argc) out_path = argv[++i];
        else if (a == "--H" && i + 1 < argc) H = atoi(argv[++i]);
        else if (a == "--budget" && i + 1 < argc) budget = atoi(argv[++i]);
        else if (a == "--list") list_only = true;
        else if (a == "--lb" && i + 1 < argc) g_paiban_lb = atof(argv[++i]);
        else if (a == "--quota" && i + 1 < argc) g_paiban_level_quota = atof(argv[++i]);
        else selected_algorithm = a;
    }
    const AlgorithmConfig algorithms[] = {
        {"BCE", ALG_BCE},
        {"BCE2", ALG_BCE2},
        {"HypE", ALG_HYPE},
        {"IBEA", ALG_IBEA},
        {"MOEAD", ALG_MOEAD},
        {"NSGA", ALG_NSGA},
        {"NSGA_III", ALG_NSGA_III},
        {"PICEAg", ALG_PICEAG},
        {"RVEA", ALG_RVEA},
        {"SPEA2+SDE", ALG_SPEA2SDE},
        {"MOPSO-CD", ALG_MOPSOCD},
        {"MOPSO", ALG_MOPSO},
        {"MOCell", ALG_MOCELL},
        {"PESA-II", ALG_PESAII},
        {"MOEADD", ALG_MOEADD},
        {"GrEA", ALG_GREA},
        {"R2HCA", ALG_R2HCA},
        {"VaEA", ALG_VAEA},
        {"SRA", ALG_SRA},
        {"SPEA2", ALG_SPEA2},
        {"GDE3", ALG_GDE3},
        {"SMS-EMOA", ALG_SMSEMOA},
        {"SMPSO", ALG_SMPSO},
        {"MOEA-D-DE", ALG_MOEADDE},
        {"AGE-MOEA", ALG_AGEMOEA},
        {"BiGE", ALG_BIGE},
        {"RPD-NSGA-II", ALG_RPDNSGAII},
        {"r-NSGA-II", ALG_RNSGAII},
        {"KnEA", ALG_KNEA},
        {"RPEA", ALG_RPEA},
        {"AGE-MOEA-II", ALG_AGEMOEAII},
        {"g-NSGA-II", ALG_GNSGAII},
        {"NSGA-II+ARSBX", ALG_NSGAIIARSBX},
        {"MOMBI-II", ALG_MOMBIII},
        {"RVEAa", ALG_RVEAA},
        {"t-DEA", ALG_TDEA},
        {"SIBEA", ALG_SIBEA},
        {"SPEA-R", ALG_SPEAR},
        {"MOEA-IGD-NS", ALG_MOEAIGDNS},
        {"M-PAES", ALG_MPAES},
        {"NMPSO", ALG_NMPSO},
        {"MPSO-D", ALG_MPSOD},
        {"AGE-II", ALG_AGEII},
        {"BCE-IBEA", ALG_BCEIBEA},
        {"BCE-MOEA-D", ALG_BCEMOEAD},
        {"MOEA-D-DRA", ALG_MOEADDRA},
        {"MOEA-D-STM", ALG_MOEADSTM},
        {"MOEA-D-AWA", ALG_MOEADAWA},
        {"MOEA-D-M2M", ALG_MOEADM2M},
        {"MOEA-D-UR", ALG_MOEADUR},
        {"MOEA-D-PaS", ALG_MOEADPAS},
        {"AdaW", ALG_ADAW},
        {"WASF-GA", ALG_WASFGA},
        {"GWASF-GA", ALG_GWASFGA},
        {"I-SIBEA", ALG_ISIBEA},
        {"Two_Arch2", ALG_TWOARCH2},
        {"RSEA", ALG_RSEA},
        {"NSGA-II-SDR", ALG_NSGAIISDR},
        {"MOEA-PC", ALG_MOEAPC},
        {"e-MOEA", ALG_EMOEA},
        {"dMOPSO", ALG_DMOPSO},
        {"MO_Ring_PSO_SCD", ALG_MORINGPSOSCD},
        {"ENS-MOEA-D", ALG_ENSMOEAD},
        {"MOEA-D-DU", ALG_MOEADDU},
        {"MOEA-D-VOV", ALG_MOEADVOV},
        {"MOEA-D-CMA", ALG_MOEADCMA},
        {"MCEA-D", ALG_MCEAD},
        {"SFA-DE", ALG_SFADE},
        {"MOEA-D-DCWV", ALG_MOEADDCWV},
        {"MOEA-D-MRDL", ALG_MOEADMRDL},
        {"MOEA-RE", ALG_MOEARE},
        {"MaOEA-IGD", ALG_MAOEAIGD},
        {"MaOEA-CSS", ALG_MAOEACSS},
        {"MaOEA-DDFC", ALG_MAOEADDFC},
        {"HEA", ALG_HEA},
        {"HeE-MOEA", ALG_HEEMOEA},
        {"NSGA-II-conflict", ALG_NSGAIICONFLICT},
        {"TS-NSGA-II", ALG_TSNSGAII},
        {"PeEA", ALG_PEEA},
        {"one-by-one EA", ALG_ONEBYONEEA},
        {"NRV-MOEA", ALG_NRVMOEA},
        {"MSEA", ALG_MSEA},
        {"A-NSGA-III", ALG_ANSGAIII},
        {"AE-NSGA-II", ALG_AENSGAII},
        {"AR-MOEA", ALG_ARMOEA},
        {"CCGDE3", ALG_CCGDE3},
        {"DEA-GNG", ALG_DEAGNG},
        {"DGEA", ALG_DGEA},
        {"DN-NSGA-II", ALG_DNNSGAII},
        {"DNSGA-II", ALG_DNSGAII},
        {"EAG-MOEA-D", ALG_EAGMOEAD},
        {"I-DBEA", ALG_IDBEA},
        {"KL-NSGA-II", ALG_KLNSGAII},
        {"MaOEA-HAP", ALG_MAOEAHAP},
        {"MaOEA-IT", ALG_MAOEAIT},
        {"MOEA-D-2WA", ALG_MOEAD2WA},
        {"MOEA-D-FRRMAB", ALG_MOEADFRRMAB},
        {"MOEA-D-PFE", ALG_MOEADPFE},
        {"MOEA-DVA", ALG_MOEADVA},
        {"MOEA-NZD", ALG_MOEANZD},
        {"MSOPS-II", ALG_MSOPSII},
        {"NNIA", ALG_NNIA},
        {"RM-MEDA", ALG_RMMEDA},
        {"MO-CMA", ALG_MOCMA},
        {"HREA", ALG_HREA},
        {"RVEA-iGNG", ALG_RVEAIGNG},
        {"RMOEA-DVA", ALG_RMOEADVA},
        {"MaOEA-R&D", ALG_MAOEARD},
        {"SIBEA-kEMOSS", ALG_SIBEAKEMOSS},
        {"LMOCSO", ALG_LMOCSO},
        {"LMEA", ALG_LMEA},
        {"LSMOF", ALG_LSMOF},
        {"MOEA-D-URAW", ALG_MOEADURAW},
        {"MOEA-D-DYTS", ALG_MOEADDYTS},
        {"SMEA", ALG_SMEA},
        {"NSLS", ALG_NSLS},
        {"MyO-DEMR", ALG_MYODEMR},
        {"MMOPSO", ALG_MMOPSO},
        {"MOBCA", ALG_MOBCA},
        {"CA-MOEA", ALG_CAMOEA},
        {"DWU", ALG_DWU},
        {"EFR-RR", ALG_EFRRR},
        {"C-MOEA-D", ALG_CMOEAD},
        {"C-TAEA", ALG_CTAEA},
        {"C-TSEA", ALG_CTSEA},
        {"DCNSGA-III", ALG_DCNSGAIII},
        {"DMOEA-eC", ALG_DMOEAEC},
        {"ICMA", ALG_ICMA},
        {"MSCEA", ALG_MSCEA},
        {"PREA", ALG_PREA},
        {"SGEA", ALG_SGEA},
        {"SSCEA", ALG_SSCEA},
        {"hpaEA", ALG_HPAEA},
        {"tDEA-CPBI", ALG_TDEACPBI},
        {"K-RVEA", ALG_KRVEA},
        {"IM-MOEA-D", ALG_IMMOEAD},
        {"IM-MOEA", ALG_IMMOEA},
        {"LMOEA-DS", ALG_LMOEADS},
        {"LRMOEA", ALG_LRMOEA},
        {"MO-EGS", ALG_MOEGS},
        {"MOSD", ALG_MOSD},
        {"FLEA", ALG_FLEA},
        {"BiCo", ALG_BICO},
        {"NSBiDiCo", ALG_NSBIDICO},
        {"C3M", ALG_C3M},
        {"CAEAD", ALG_CAEAD},
        {"CCMO", ALG_CCMO},
        {"CGLP", ALG_CGLP},
        {"CLIA", ALG_CLIA},
        {"CMDEIPCM", ALG_CMDEIPCM},
        {"CMEGL", ALG_CMEGL},
        {"CMME", ALG_CMME},
        {"CMMO", ALG_CMMO},
        {"CMOBR", ALG_CMOBR},
        {"CMOCSO", ALG_CMOCSO},
        {"CMODE-FTR", ALG_CMODEFTR},
        {"CMOEA-2S", ALG_CMOEA2S},
        {"CMOEA-AOP", ALG_CMOEAAOP},
        {"CMOEA-CD", ALG_CMOEACD},
        {"CMOEA-MS", ALG_CMOEAMS},
        {"CMOEA-MSG", ALG_CMOEAMSG},
        {"CMOES", ALG_CMOES},
        {"AC-MMEA", ALG_ACMMEA},
        {"AFSEA", ALG_AFSEA},
        {"AGSEA", ALG_AGSEA},
        {"APSEA", ALG_APSEA},
        {"CMOEA-MOP", ALG_CMOEAMOP},
        {"CNSDE-DVC", ALG_CNSDEDVC},
        {"CoMMEA", ALG_COMMEA},
        {"DKCA", ALG_DKCA},
        {"DM-MOEA", ALG_DMMOEA},
        {"DP-PPS", ALG_DPPPS},
        {"DPCPRA", ALG_DPCPRA},
        {"DPVAPS", ALG_DPVAPS},
        {"DSPCMDE", ALG_DSPCMDE},
        {"DSSEA", ALG_DSSEA},
        {"DVCEA", ALG_DVCEA},
        {"FDV", ALG_FDV},
        {"GFM-MOEA", ALG_GFMMOEA},
        {"GLMO", ALG_GLMO},
        {"GPSO-M", ALG_GPSOM},
        {"HHC-MMEA", ALG_HHCMMEA},
        {"ADSAPSO", ALG_ADSAPSO},
        {"CI-EMO", ALG_CIEMO},
        {"CMOPSO", ALG_CMOPSO},
        {"CPS-MOEA", ALG_CPSMOEA},
        {"DAEA", ALG_DAEA},
        {"EGES", ALG_EGES},
        {"FRCG-M", ALG_FRCGM},
        {"GDVTSF", ALG_GDVTSF},
        {"ILCMO", ALG_ILCMO},
        {"IM-C-MOEA-D", ALG_IMCMOEAD},
        {"KLEA", ALG_KLEA},
        {"LCMEA", ALG_LCMEA},
        {"LMPFE", ALG_LMPFE},
        {"MCCMO", ALG_MCCMO},
        {"MFFS", ALG_MFFS},
        {"MFO-SPEA2", ALG_MFOSPEA2},
        {"MOCGDE", ALG_MOCGDE},
        {"MOEA-CKF", ALG_MOEACKF},
        {"MOEA-D-CMT", ALG_MOEADCMT},
        {"MOEA-D-DAE", ALG_MOEADDAE},
        {"CMOSMA", ALG_CMOSMA},
        {"CMaDPPs", ALG_CMADPPS},
        {"EMCMO", ALG_EMCMO},
        {"EMMOEA", ALG_EMMOEA},
        {"EMCMMS", ALG_EMCMMS},
        {"EMyO-C", ALG_EMYOC},
        {"MGCEA", ALG_MGCEA},
        {"MMEA-ARM", ALG_MMEAARM},
        {"MMEA-WI", ALG_MMEAWI},
        {"MMEAPSL", ALG_MMEAPSL},
        {"MMOEA-BH", ALG_MMOEABH},
        {"MO-L2SMEA", ALG_MOL2SMEA},
        {"MOEA-IB", ALG_MOEAIB},
        {"MP-MMEA", ALG_MPMMEA},
        {"MSCMO", ALG_MSCMO},
        {"NUCEA", ALG_NUCEA},
        {"OSP-NSDE", ALG_OSPNSDE},
        {"PB-NSGA-III", ALG_PBNSGAIII},
        {"PB-RVEA", ALG_PBRVEA},
        {"PIEA", ALG_PIEA},
        {"EDN-ARMOEA", ALG_EDNARMOEA},
        {"IMTCMO", ALG_IMTCMO},
        {"IMTCMO_BS", ALG_IMTCMOBS},
        {"LCSA", ALG_LCSA},
        {"LDS-AF", ALG_LDSAF},
        {"LERD", ALG_LERD},
        {"NBLEA", ALG_NBLEA},
        {"NNDREA-MO", ALG_NNDREAMO},
        {"POCEA", ALG_POCEA},
        {"PPS", ALG_PPS},
        {"PRCEA", ALG_PRCEA},
        {"PRDH", ALG_PRDH},
        {"RGA-M1-2", ALG_RGAM12},
        {"RGA-M2-2", ALG_RGAM22},
        {"S-CDAS", ALG_SCDAS},
        {"S-ECSO", ALG_SECSO},
        {"S-NSGA-II", ALG_SNSGAII},
        {"SCEA", ALG_SCEA},
        {"SGECF", ALG_SGECF},
        {"SLMEA", ALG_SLMEA},
        {"MTS", ALG_MTS},
        {"WV-MOEA-P", ALG_WVMOEAP},
        {"WOF", ALG_WOF},
        {"TriMOEA-TA&R", ALG_TRIMOEATAR},
        {"NSGA-II-DTI", ALG_NSGAIIDTI},
    };
    int algorithm_count = sizeof(algorithms) / sizeof(algorithms[0]);
    if (list_only)
    {
        for (int a = 0; a < algorithm_count; a++) cout << algorithms[a].name << "\n";
        return 0;
    }
    // 面向排班结构的新算法（paiban_algs.cpp）：LevelNiche-GA / LevelNiche-ARSBX / LB-rNSGA
    int custom = selected_algorithm == "LevelNiche-GA" ? 1 : selected_algorithm == "LevelNiche-ARSBX" ? 2 :
                 selected_algorithm == "LB-rNSGA" ? 3 : 0;
    int alg = -1;
    for (int a = 0; a < algorithm_count; a++)
        if (selected_algorithm == algorithms[a].name) alg = a;
    if (alg < 0 && !custom) { cerr << "未知算法: " << selected_algorithm << "（--list 查看全部）" << endl; return 2; }
    srand((unsigned)std::random_device{}());
    int NVAR = paiban_bridge_setup(workdir.c_str());
    g_budget = budget;
    clock_t t0 = clock();
    MOEA_solver PP(H, 1, NVAR, 2, 0, 1, PAIBAN_evaluation, 0);
    PP.initializeBenchmark();
    int step_evaluations = custom ? PP.Popsize : algorithm_step_evaluation_upper_bound(PP, algorithms[alg].type);
    int guard = 0;
    while (paiban_bridge_evals() + step_evaluations <= budget && guard < 100000)
    {
        long long before = paiban_bridge_evals();
        if (custom == 1) PaibanLevelNiche(PP, 0);
        else if (custom == 2) PaibanLevelNiche(PP, 1);
        else if (custom == 3) PaibanLBRNSGA(PP);
        else run_algorithm_step(PP, algorithms[alg].type);
        if (paiban_bridge_evals() == before) guard++;   // 防止某些算法一步不评价导致死循环
        else guard = 0;
        if (guard > 1000) break;
    }
    double secs = (double)(clock() - t0) / CLOCKS_PER_SEC;
    paiban_bridge_dump(out_path.c_str(), selected_algorithm.c_str(), secs, PP.Popsize, NVAR);
    return 0;
}
