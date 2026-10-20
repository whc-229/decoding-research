#pragma once
//
//  MOEA_solver.h
//  MOEA
//
//  Created by yunglynn on 17-12-14.
//  Copyright (c) 2017�� yunglynn. All rights reserved.
//

#include "Population_moea.h"
#include <vector>
#include <random>
#include <algorithm>
#include <string>
#include <unordered_map>
#include <functional>
using namespace std;
#define PUNISHMENT 50
#define Divi 10;

#ifndef __MOEA__MOEA_solver__
#define __MOEA__MOEA_solver__da

typedef void(*MOEA_FF) (float *xreal, float *obj, int Nvar, int Nobj);
//typedef void(*FF) (float* var, float* obj, int TaskN, DisassemblyTAOG* Model, int M);

typedef struct ref_point
{
	float* pos;
	int clusterSize;
	vector<float> PotentialM_dist;
	vector<int> PotentialM_indv;
}Ref;

typedef struct moea_operator_set
{
	int H = 13;
	bool rpsLevel = false;
	int hypeSamples = 1000;
	int binaryBits = 7;

	float pc = 0.8f;
	float pm = 0.15f;
	float etaC = 20.0f;
	float etaM = 20.0f;
	float F = 0.5f;
	float CR = 0.9f;
	float cauchyScale = 0.1f;
	float soMutationPm = 0.15f;

	float ibeaKappa = 0.05f;
	int tournament = 2;
	float rveaAlpha = 2.0f;
	float sraPc = 0.5f;
} moea_opeset;

class MOEA_solver : public Population_moea
{
public:
	MOEA_solver(int h, bool rps_level, int nn, int no, float lb, float ub, MOEA_FF evaluate, int M, int pop_override = -1);
	~MOEA_solver();

public:
	//DisassemblyTAOG* Model;
	MOEA_FF EvaluFunc;
	int eval_count;
	int probM;
	moea_opeset Opeset;

	//BCE
	int* promising;
	int promising_num;
	int alphaSize_BCE;

	//HypE
	float* HypeFitness;
	float* HypeRef;
	float* HypeMin;

	//IBEA
	int alphaSize_IB;
	float kappa = 0.05f;
	int tournament = 2;
	float** fitcomp;
	float* curBoundmin, * curBoundmax;

	//MOEAD
	int niche;
	int nvector;    //record the number of weighting vectors in initialization
	float** weight;
	int** neighbor;

	//NSGA_III
	int* levelSize;
	int** levelF;
	float* idealPoint;
	vector<Ref> RefPns;

	//PICEA-g
	int Ngoal;
	float** Goal;
	float** GoalC;
	float** JointGoal;
	float* FitJointS;
	float* FitJointG;
	int* index_nd_jointS;

	//rvea
	float* acosVV;
	float rvea_alpha = 2.0;
	float** rvea_weight;
	float** rvea_weight_init;
	int adaption_count = 1;

	//GrEA
	int** G;
	int** GD;
	int pbest;
	float* d, * lb;
	int* candi_F;

	//R1HCA
	float** DirectionV;
	float*** R2Tensor;

	//DAEA
	int M = 7;
	//
	float variationPc = 0.8f;
	float mutationPm = 0.15f;
	float etaC = 20.0f;
	float etaM = 20.0f;
	float deF = 0.5f;
	float deCR = 0.9f;
	float cauchyScale = 0.1f;
	float soMutationPm = 0.15f;
	float sraPc = 0.5f;

	vector<individual> EP;  //nonDominatedSet
	int* OperType;
	std::vector<std::string> op_sequence; // optional operator cycle

	float Hp;
	float* referencePoint;
	individual* pop_temp;

public:
	void getHp();
	void GenerateDirectionV();
	void Initial(const moea_opeset& set);
	void initialize();
	void setOperatorSequence(const std::vector<std::string>& seq);
	// 研究用扩展（2026-10-14，仅本地研究版）
	std::function<void(individual*)> custom_op;   // 算子序列中名为 SIM_MUTATE 的位置调用它，之后再做多项式变异
	void seedIndividuals(const std::vector<std::vector<float>>& xs);   // 用给定个体替换 pop_all 前若干个并重建外部档案
	void resetOpUsage();
	const std::unordered_map<std::string, int>& getOpUsage() const;
	
	void calcBoundsEP();
	void calcBounds(individual* pp, int len);//hypE
	void updateBounds(individual& ind);
	
	void ObjectiveNormalization(individual& ind);

	void PPX(individual* parent_a, individual* parent_b, individual* child_a, individual* child_b, float pc);
	void SBX(individual* parent_a, individual* parent_b, individual* child_a, individual* child_b, float pc, float eta_c);
	void Mutate(individual* ind, float pm, float eta_m);
	void discrete_mutate(individual* ind, float pm);

	void variationByPC(individual* ind, int promising_id);
	void variationByNPC(individual* ind, int flag, int psize);
	void applyVariationOp(individual* ind, int idx, int flag, int psize);
	void so_crossover(individual* ind, int idx, int psize);
	void so_mutate(individual* ind, int idx);
	void xover_basic(individual* ind, int idx, int psize);
	void de_crossover(individual* ind, int idx, int psize, float F, float CR);
	void de_mutate(individual* ind, int idx, int strategy);
	void cauchy_mutation(individual* ind, int idx);
	void pop_niche(individual* ind);
	void localsearch(individual* ind);
	void newpop_localstep(individual* ind);
	void newpop_bit_climbing(individual* ind);
	void newpop_simplex(individual* ind);
	void Evaluation(individual* pp, int size);

	//BCE
	void NormalizeAll();
	void BCE_EnvironmentalSelection();
	void updateEP(individual& ind);
	void updateNP0(individual& ind);
	void updateNP1(individual& ind, int id, int type);
	void solutionUpdate0();
	void solutionUpdate1();
	void maintainEP();
	//BCE2
	void EnvironmentalSelection0();
	void EnvironmentalSelection1();
	void matingSelection(bool flag);

	//HypE(HypE: An Algorithm for Fast Hypevolume-Based Many-Objective Optimization)
	void HypeFitnessEstimation(individual* pop, int len, int removed_k, int M);
	void HypeMatingSelection(int m);
	void HypeEnvironmentalSelection(int m);
	void HypeFitnessExact(individual* pop, int len, int removed_k);
	void HypeDoSlicing(individual* pop, int len, float* curFitness, int removed_k, int dim, float partialVolume, float* pos);
	int check_partial_dominance(individual& ind, float* pos, int dimStart);
	void sort_dim_ascending(individual* pop, int* popno, int size, int dim);
	void HypeCalcRef(individual* pp, int len);
	void fastNondominatedSort();

	//IBEA
	void mergeOffspring();
	void calcFitnessIndicator(int type);
	float calcAddEpsIndicator(individual* ind_a, individual* ind_b);
	float calcHypervolumeIndicator(individual* ind_a, individual* ind_b, int d);
	void Evaluation(int flag);
	void updateEP();
	void IBEA_environmentalSelection();

	//MOEAD
	void initializeWeight(int h, int index_obj, int pre_sum, int* weight_vector);
	void initializeNeighbor();
	float Tchebycheff(float* obj, float* lambda);
	void updateNP();

	//NSGA
	void crowdDistanceAssignment(int level);
	void solutionUpdate();
	void NSGA_matingSelection();
	void NSGA_initializeWeight(int h, int index_obj, int pre_sum, int* weight_vector);

	//NSGA_III
	void translateObjectives();
	void hyperplaneAndNormalization();
	float ASF(individual& ind, int obit);
	float perpendicularDistance(Ref& direction, individual& ind);
	void Associate(vector<Ref>& rps);
	int findNicheRps(vector<Ref>& rps);
	int selectClusterMember(Ref& rp);
	int findClosestMember(Ref& rp);
	void removePotential(Ref& rp, int chosen);
	void NSGA_III_environmentalSelection();


	//PICEA-g
	void merge_popall();
	void goal_generator(int flag);
	void jointG();
	int check_goal_dominance(individual& ind_a, float* goal);
	void fitness_assignment();
	void truncation_selection();
	void obtainEP();

	// Utility
	std::string describeOperators(const std::string& alg_name);

	//RVEA
	void UniformPoint();
	void Cij(int i, int j, vector<int>& r, int num, vector<vector<int> >& result);
	void updateUniformWeight(int h, int M, int N, float** weight);
	int UniformPoint(int N, int M);
	float dotproduct(float* va, float* vb, int M);
	void reference_vector_guided_selection(int maxgene);
	void calcZmin(float* Zmin);
	void calcZmax(float* Zmax);
	void updateFunctionValue(float** functionValue);
	void update_uFunctionValue(float** ufunctionValue, float** fValue);
	float update_uFunctionValue_abs(float* fValue, int num);
	void reference_vector_adaptation();
	void multiply_boundary();

	//GrEA
	void tournament_Selection();
	void Grid_setting(individual* pop_set, int len);
	void Fitness_assignment();
	void Initailization(int i);
	void Findout_best(int* FI, int length);
	void GCD_calculation(bool flag, int length);
	void GCPD_calculation(int length);
	void GR_adjustment(int* candi_f, int levelsize);
	void boundfind();
	void GR_assignment(int flag, int length);
	void GD_set(int length);
	void GrEA_EnvironmentalSelection();
	int grid_dominance(int a, int b);
	void fastNondominatedSort(individual* popsort, int len_p);

	//R1HCA
	void initialR2Tensor();
	void updateR2Tensor(int Rindex, individual& pp);
	void PopReplacement(int Rindex, individual& pp);
	int findR2Worst();

	//VaEA
	void calcFitandNorm(individual* pp);
	float angle(individual& pp1, individual& pp2);
	float angleToExtreme(individual& pp, float* ExtremeV);
	void VaEA_environmentalSelection();

	//MOEADD
	void solutionUpdate_MOEADD();
	void Locate_worst();

	//SRA
	void SRA_environmentalSelection(float pc);
	float calcI1(individual* ind_a);
	float calcI2(individual* ind_a);

	//MHSO for hypervolume
	float getLowestUpperBound(individual* pp, int len, int index, int obit);
	float calculateArea_2D(individual* pp, int len, int noObjectives);
	int ReduceFront(individual* pp, int len, int noObjectives, float* slice_depth, int slice_number);
	float calculateHypervolume(individual* pp, int len, int noObjectives);

	//TRAN
	bool Autoencoder(individual* pop1, int size, int count);
	bool Autoencoder_k(individual* pop1, int size, int count);
	bool Autoencoder_k_sim(individual* pop1, int size, int count);

	//DAEA
	void NicVariation();
	float* to_xreal(int* bin, int M, int Nvar);
	void Dup_Analysis();
	void EnvironmentalSelection();
	//int is_point(int j, int* k);
	//int is_point(int j, vector<int> k);
	//float Manhattandistance(float* x1, float* x2, int len);
	//int is_point(int j, int* k);
	//float mapminmax(float y, float ymin, float ymax, float xmin, float xmax);
	float Manhattandistance(float* x1, float* x2, int len);
	float mapminmax(float x, float xmin, float xmax);
	int* randperm(int n, int k);
	int* find1(int* s, int k);
	int* find0(int* s, int k);
	vector<int> toBinary(int n);
	int pop_allsize;
	

	//algorithm
	void BCE();
	void BCE2();
	void GrEA();
	void hypE();
	void IBEA();
	
	void MOEAD();
	void NSGA();
	void NSGA_III();
	void PICEAg();
	void RVEA(int maxgen);
	void R2HCA();
	void VaEA();
	void MOEADD();
	void SRA();

	void DAEA();
};

#endif
