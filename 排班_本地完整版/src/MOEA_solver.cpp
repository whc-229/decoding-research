
#include <algorithm>
#include <iostream>
#include <cmath>
#include <bitset>
#include <vector>
#include "MOEA_solver.h"

// Map helper symbols to MOEA-specific implementations to avoid clashing with single-objective utilities
#define randval moea_randval
#define irand moea_irand
#define EuclideanDistance moea_EuclideanDistance
#define determinRadius moea_determinRadius
#define minFastSort moea_minFastSort
#define GuassianElimination moea_GuassianElimination
#define uniform moea_uniform
#define gauss moea_gauss
#define combination moea_combination

using namespace std;

static std::unordered_map<std::string, int> g_moea_op_usage;

// Toggle verbose MOEA logging via environment variable MOEA_VERBOSE
static bool moea_verbose = (std::getenv("MOEA_VERBOSE") != nullptr);


MOEA_solver::MOEA_solver(int h, bool r_level, int nn, int no, float lb, float ub, MOEA_FF evaluate, int M, int pop_override)
	: Population_moea(h, r_level, nn, no, lb, ub, pop_override), probM(M), lb(nullptr), d(nullptr)
{
	
	EvaluFunc = evaluate;

	//BCE
	//MOEA/D
	niche = Popsize / 5;
	weight = new float* [Popsize];
	for (int i = 0; i < Popsize; i++)
		weight[i] = new float[Nobj];
	neighbor = new int* [Popsize];
	for (int i = 0; i < Popsize; i++)
		neighbor[i] = new int[niche];

	//HypE
	HypeFitness = new float[fullSize2];
	HypeRef = new float[Nobj];
	HypeMin = new float[Nobj];

	//IBEA
	curBoundmin = new float[Nobj];
	curBoundmax = new float[Nobj];
	fitcomp = new float* [fullSize];
	for (int i = 0; i < fullSize; i++)
		fitcomp[i] = new float[fullSize];
	referencePoint = new float[Nobj];


	//NSGA
	levelSize = new int[fullSize2];
	levelF = new int* [fullSize2];
	for (int i = 0; i < fullSize2; i++)
		levelF[i] = new int[fullSize2];
	idealPoint = new float[Nobj];

	//PICEA-g
	Ngoal = Popsize;
	FitJointS = new float[fullSize2];
	FitJointG = new float[2 * Ngoal];
	Goal = new float* [Ngoal];
	GoalC = new float* [Ngoal];
	index_nd_jointS = new int[fullSize2];
	for (int i = 0; i < Ngoal; i++)
	{
		Goal[i] = new float[Nobj];
		GoalC[i] = new float[Nobj];
	}
	JointGoal = new float* [2 * Ngoal];
	for (int i = 0; i < 2 * Ngoal; i++)
		JointGoal[i] = new float[Nobj];

	// NSGA-III reference points container
	RefPns.resize(Popsize);
	for (int i = 0; i < Popsize; ++i)
	{
		RefPns[i].pos = new float[Nobj];
		RefPns[i].clusterSize = 0;
	}

	// operator sequence (optional)
	op_sequence.clear();

	//RVEA
	//Popsize = UniformPoint(Popsize, Nobj);


	//GrEA
	G = new int* [Nobj];
	for (int i = 0; i < Nobj; i++)
		G[i] = new int[fullSize2];
	GD = new int* [fullSize2];
	for (int i = 0; i < fullSize2; i++)
		GD[i] = new int[fullSize2];

	promising = new int[EP_capability];

	//R1HCA
	DirectionV = new float* [Popsize];
	for (int i = 0; i < Popsize; i++)
		DirectionV[i] = new float[Nobj];
	R2Tensor = new float** [Popsize + 1];
	for (int i = 0; i < Popsize + 1; i++)
	{
		R2Tensor[i] = new float* [Popsize]; //the size of DirectionV
		for (int j = 0; j < Popsize; j++)
			R2Tensor[i][j] = new float[Popsize + 1];
	}

	//array temp is used to store the points which are used to calculate the area of this slice
	pop_temp = allocate_memory_indArray(fullSize);

	getHp();
}

MOEA_solver::~MOEA_solver()
{
	// Explicitly do nothing; teardown is skipped to avoid invalid frees between requests.
}

void MOEA_solver::Initial(const moea_opeset& set)
{
	Opeset = set;
	probM = set.hypeSamples > 0 ? set.hypeSamples : probM;
	M = set.binaryBits > 0 ? set.binaryBits : M;
	variationPc = set.pc;
	mutationPm = set.pm;
	etaC = set.etaC;
	etaM = set.etaM;
	deF = set.F;
	deCR = set.CR;
	cauchyScale = set.cauchyScale;
	soMutationPm = set.soMutationPm;
	kappa = set.ibeaKappa;
	tournament = set.tournament > 0 ? set.tournament : 2;
	rvea_alpha = set.rveaAlpha;
	sraPc = set.sraPc;
}

void MOEA_solver::GenerateDirectionV()
{


	for (int i = 0; i < Popsize; i++)
	{
		for (int j = 0; j < Nobj; j++)
			DirectionV[i][j] = gauss();

		float sum = 0;
		for (int j = 0; j < Nobj; j++)
			sum += DirectionV[i][j] * DirectionV[i][j];
		sum = sqrt(sum);
		for (int j = 0; j < Nobj; j++)
			DirectionV[i][j] /= sum;
	}

}

void MOEA_solver::initialR2Tensor()
{
	float rho = 1 + 1 / Hp;
	for (int k = 0; k < Popsize + 1; k++)
	{
		for (int j = 0; j < Popsize; j++)
		{
			int index = 0, i = 0;
			while (index < Popsize + 1)   //assume pop_all has N+1 valid item
			{
				if (index == k)
					index++;
				R2Tensor[i][j][k] = (pop_all[index].obj_norm[0] - pop_all[k].obj_norm[0]) / DirectionV[j][0];
				for (int l = 1; l < Nobj; l++)
				{
					float g_2tch = (pop_all[index].obj_norm[l] - pop_all[k].obj_norm[l]) / DirectionV[j][l];
					if (g_2tch > R2Tensor[i][j][k])
						R2Tensor[i][j][k] = g_2tch;
				}
				if (R2Tensor[i][j][k] > 1e5)
					R2Tensor[i][j][k] = 1e5;
				//cout << "R2Tensor[" << i << "][" << j << "][" << k << "] = " << R2Tensor[i][j][k] << endl;
				index++;
				i++;
			}
			R2Tensor[Popsize][j][k] = abs(pop_all[k].obj_norm[0] - rho) / DirectionV[j][0];
			for (int l = 1; l < Nobj; l++)
			{
				float g_mtch = abs(pop_all[k].obj_norm[l] - rho) / DirectionV[j][l];
				if (g_mtch < R2Tensor[Popsize][j][k])
					R2Tensor[Popsize][j][k] = g_mtch;
			}
			if (R2Tensor[Popsize][j][k] > 1e5)
				R2Tensor[Popsize][j][k] = 1e5;

			//cout << "R2Tensor[" << Popsize << "][" << j << "][" << k << "] = " << R2Tensor[Popsize][j][k] << endl;

		}
	}
}

void MOEA_solver::initialize()
{
	//Read problem parameters
	

	int i, j;
	std::random_device rd;

	for (i = 0; i < Popsize; i++)
	{
		//

		for (j = 0; j < Nvar; j++)
		{
			pop_sel[i].x[j] = randval(Lbound, Ubound);
			pop_new[i].x[j] = randval(Lbound, Ubound);
		}

		EvaluFunc(pop_sel[i].x, pop_sel[i].obj, Nvar, Nobj);
		EvaluFunc(pop_new[i].x, pop_new[i].obj, Nvar, Nobj);
		pop_sel[i].fitness = 0;
		pop_new[i].fitness = 0;
	}
	for (i = 0; i < fullSize; i++)
	{
		for (j = 0; j < Nvar; j++)
			pop_all[i].x[j] = randval(Lbound, Ubound);
		EvaluFunc(pop_all[i].x, pop_all[i].obj, Nvar, Nobj);
		pop_all[i].fitness = 0;
	}

	EP.clear();
	int pcN = FilterNondominatedSet(pop_all, fullSize, Nobj);
	for (i = 0; i < pcN; i++)
	{
		individual new_element;
		allocate_memory_ind(&new_element);
		copy(&new_element, pop_all + i);
		EP.push_back(new_element);
	}
	
	//NSGA     //PICEA-g
	for (i = 0; i < fullSize2; i++)
		levelSize[i] = 0;
	//generate reference point
	int* weight_serial = new int[Nobj];
	for (i = 0; i < Nobj; i++)
		weight_serial[i] = 0;
	NSGA_initializeWeight(H, 0, 0, weight_serial);
	if (rps_Dlevel)
	{
		for (i = 0; i < Nobj; i++)
			weight_serial[i] = 0;
		NSGA_initializeWeight(H - 1, 0, 0, weight_serial);

		double center = 1.0 / Nobj;
		for (i = hOutSize; i < Popsize; i++)
			for (j = 0; j < Nobj; j++)
				RefPns[i].pos[j] = (center + RefPns[i].pos[j]) / 2;
	}

	//-----------generate reference point
	calcBounds(pop_all, fullSize);
	for (int i = 0; i < Popsize + 1; i++)
		ObjectiveNormalization(pop_all[i]);

	goal_generator(0);

	//BCE    //MOEA/D   //hypeE   //MOEADD
	nvector = 0;
	if (rps_Dlevel)
	{
		double center = 1.0 / Nobj;
		for (i = hOutSize; i < Popsize; i++)
			for (j = 0; j < Nobj; j++)
				weight[i][j] = (center + weight[i][j]) / 2;
	}
	delete[] weight_serial;
	initializeNeighbor();  //the first item of neighbor[i] is its own index;

	//IBEA
	alphaSize_IB = fullSize - Popsize;

	
	//R2HCA

	GenerateDirectionV();
	initialR2Tensor();

	promising_num = 0;
	eval_count = 0;
	alphaSize_BCE = 1.5 * Popsize;
	
	//DAEA
	if (M <= 0) M = 7;
	int n,k;
	vector<int> bit(7, 0);

	for (i = 0; i < Popsize; i++)
	{
		for (k = 0; k < Nvar; k++)
		{
			pop_all[i].x[k] = randval(Lbound, Ubound);
		}
	}
	for (i = 0; i < Popsize; i++)
	{
		for (k = 0; k < Nvar; k++)
		{
			//cout << "bit10:" << 100 * pop_all[i].x[k] << endl;
			bit = toBinary(100 * pop_all[i].x[k]);
			/*for (j = 0; j < 7; j++)
			{
				cout << bit[j] << " ";
			}*/
			//cout << endl;
			for (n = M * k; n <= M * k + 6; n++)
			{
				//cout << "bit:" << bit[n - M * k] << ": " << n - M * k  << endl;
				pop_all[i].bin[n] = bit[n - M * k];
			}
		}
	}
	int T = min(Nvar * M, Popsize * 3);
	
	if (T < Nvar * M)
	{
		for (i = 0; i < Popsize; i++)
		{
			// Safe init: zero all bits, then flip up to T random positions within bounds
			for (j = 0; j < Nvar * M; j++)
				pop_all[i].bin[j] = 0;
			int k0 = rand() % T; // 0..T-1 flips
			for (int m = 0; m < k0; m++)
			{
				int idx = rand() % (Nvar * M); // valid index 0..Nvar*M-1
				pop_all[i].bin[idx] = 1;
			}
		}
	}
	else
		for (i = 0; i < Popsize; i++)
		{
			for (j = 0; j < Nvar * M; j++)
			{
				pop_all[i].bin[j] = rand() % 2;
			}
		}
}

vector<int> MOEA_solver::toBinary(int n)
{
	vector<int> a(7, 0);
	vector<int> s(7, 0);
	int i;
	//int count = 0;
	for (i = 0; n > 0; i++)
	{
		a[i] = n % 2;
		n = n / 2;
		//count++;
	}
	for (i = 0; i < 7; i++)
	{
		s[6 - i] = a[i];
	}
	return s;
}

void MOEA_solver::getHp()
{
	Hp = 0;
	int N = 0;
	for (; Hp < 100; Hp++)
	{
		N = combination(Hp + Nobj - 1, Nobj - 1);
		if (N > Popsize)
			break;
	}
	Hp++;
}

void MOEA_solver::calcBoundsEP()
{
	int i, j;
	if (EP.empty()) return;

	for (j = 0; j < Nobj; j++)
	{
		curBoundmin[j] = EP[0].obj[j];
		curBoundmax[j] = EP[0].obj[j];
	}
	for (i = 1; i < EP.size(); i++)
	{
		for (j = 0; j < Nobj; j++)
		{
			if (EP[i].obj[j] < curBoundmin[j])
				curBoundmin[j] = EP[i].obj[j];
			if (EP[i].obj[j] > curBoundmax[j])
				curBoundmax[j] = EP[i].obj[j];
		}
	}

}

void MOEA_solver::calcBounds(individual* pp, int len)
{
	int i, j;
	float rho = 1 + 1 / Hp;

	for (j = 0; j < Nobj; j++)
	{
		curBoundmin[j] = pp[0].obj[j];
		curBoundmax[j] = pp[0].obj[j];
	}
	for (i = 1; i < len; i++)
	{
		for (j = 0; j < Nobj; j++)
		{
			if (pp[i].obj[j] < curBoundmin[j])
				curBoundmin[j] = pp[i].obj[j];
			if (pp[i].obj[j] > curBoundmax[j])
				curBoundmax[j] = pp[i].obj[j];
		}
	}
	for (j = 0; j < Nobj; j++)
		referencePoint[j] = curBoundmin[j] + rho * (curBoundmax[j] - curBoundmin[j]);
}

void MOEA_solver::updateBounds(individual& ind)
{
	for (int i = 0; i < Nobj; i++)
	{
		if (ind.obj[i] < curBoundmin[i])
			curBoundmin[i] = ind.obj[i];
		else if (ind.obj[i] > curBoundmax[i])
			curBoundmax[i] = ind.obj[i];
	}
}

void MOEA_solver::SBX(individual* parent_a, individual* parent_b, individual* child_a, individual* child_b, float pc, float eta_c) //eta_c: distribution index of simulated binary crossover
{
	int i;
	float rand;
	float y1, y2, c1, c2;
	float alpha, beta, betaq, ee;

	if (randval(0, 1) <= pc)
	{
		for (i = 0; i < Nvar; i++)
		{
			if (randval(0, 1) <= 0.5)
			{
				if (parent_a->x[i] < parent_b->x[i])
				{
					y1 = parent_a->x[i];
					y2 = parent_b->x[i];
				}
				else
				{
					y1 = parent_b->x[i];
					y2 = parent_a->x[i];
				}

				if (fabs(parent_a->x[i] - parent_b->x[i]) > EPS)
				{
					rand = randval(0, 1);
					beta = 1.0 + (2 * (y1 - Lbound) / (y2 - y1 + EPS));
					alpha = 2.0 - pow(beta, -(eta_c + 1.0));
					if (rand <= 1.0 / (alpha + EPS))
						betaq = pow(rand * alpha, 1.0 / (eta_c + 1.0));
					else
					{
						ee = abs(1.0 / (2.0 - rand * alpha + EPS));
						betaq = pow(ee, 1.0 / (eta_c + 1.0));
					}
					c1 = 0.5 * (y1 + y2 - betaq * (y2 - y1));

					beta = 1.0 + 2 * (Ubound - y2) / (y2 - y1 + EPS);
					alpha = 2.0 + pow(beta, -(eta_c + 1.0));
					if (rand <= 1.0 / (alpha + EPS))
						betaq = pow(rand * alpha, 1.0 / (eta_c + 1.0));
					else
					{
						ee = abs(1.0 / (2.0 - rand * alpha + EPS));
						betaq = pow(ee, 1.0 / (eta_c + 1.0));
					}

					c2 = 0.5 * (y1 + y2 - betaq * (y2 - y1));

					if (randval(0, 1) <= 0.5)
					{
						child_a->x[i] = c2;
						child_b->x[i] = c1;
					}
					else
					{
						child_a->x[i] = c1;
						child_b->x[i] = c2;
					}

					if (isnan(child_a->x[i]) || isnan(child_b->x[i]))
						cout << "nan happend!!!!!!!!!!!!!!" << endl;
					if (child_a->x[i] < Lbound)
						child_a->x[i] = Lbound;
					else if (child_a->x[i] > Ubound)
						child_a->x[i] = Ubound;
					if (child_b->x[i] < Lbound)
						child_b->x[i] = Lbound;
					else if (child_b->x[i] > Ubound)
						child_b->x[i] = Ubound;
				}
				else
				{
					child_a->x[i] = parent_a->x[i];
					child_b->x[i] = parent_b->x[i];
				}
			}
			else
			{
				child_a->x[i] = parent_a->x[i];
				child_b->x[i] = parent_b->x[i];
			}
		}
	}
	else
	{
		for (i = 0; i < Nvar; i++)
		{
			child_a->x[i] = parent_a->x[i];
			child_b->x[i] = parent_b->x[i];
		}
	}
}

void MOEA_solver::Mutate(individual* ind, float pm, float eta_m)
{
	int i;
	float rand, delta1, delta2, mut_pow, deltaq;
	float y, val, xy;

	for (i = 0; i < Nvar; i++)
	{
		if (randval(0, 1) <= pm)
		{
			y = ind->x[i];
			delta1 = (y - Lbound) / (Ubound - Lbound);
			delta2 = (Ubound - y) / (Ubound - Lbound);
			mut_pow = 1.0 / (eta_m + 1.0);
			rand = randval(0, 1);
			if (rand <= 0.5)
			{
				xy = 1.0 - delta1;
				val = 2.0 * rand + (1.0 - 2.0 * rand) * pow(xy, eta_m + 1.0);
				deltaq = pow(val, mut_pow) - 1.0;
			}
			else
			{
				xy = 1.0 - delta2;
				val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * pow(xy, eta_m + 1.0);
				deltaq = 1.0 - pow(val, mut_pow);
			}
			y += deltaq * (Ubound - Lbound);
			if (y < Lbound)
				y = Lbound;
			else if (y > Ubound)
				y = Ubound;
			ind->x[i] = y;
		}
	}
}

void MOEA_solver::discrete_mutate(individual* ind, float pm)
{
	for (int i = 0; i < Nvar; i++)
	{
		float p = randval(0, 1);
		if (p < pm)
		{
			// flip a pseudo-bit by snapping to bounds randomly
			float v = (randval(0, 1) < 0.5f) ? Lbound : Ubound;
			ind->x[i] = v;
		}
	}
}

void MOEA_solver::variationByPC(individual* ind, int promising_id)
{
	int rand;
	int EPsize = (int)EP.size();
	//cout << "EPSIZE_variation:   " << EPsize << endl;
	//cout << "pro_id:    " << promising_id << endl;
	individual child;
	allocate_memory_ind(&child);

	if (EPsize > 1)
	{
		do
		{
			rand = irand(EPsize);
		} while (promising_id == rand);
		SBX(&EP[promising_id], &EP[rand], ind, &child, variationPc, etaC);
		copy(ind, &EP[0]);
		Mutate(ind, mutationPm, etaM);
	}
	else
		copy(ind, &EP[0]);

	deallocate_memory_ind(&child);
}

void MOEA_solver::variationByNPC(individual* ind, int flag, int psize)
{
	int partner1, partner2;
	individual child;
	allocate_memory_ind(&child);

	if (flag == 0)
	{
		partner1 = irand(psize);
		do
		{
			partner2 = irand(psize);
		} while (partner2 == partner1);
		SBX(pop_sel + partner1, pop_sel + partner2, ind, &child, variationPc, etaC);//从pop_sel经过筛选之后的种群中进行交叉变异
		Mutate(ind, mutationPm, etaM);
	}
	else
	{
		partner1 = irand(psize);
		do
		{
			partner2 = irand(psize);
		} while (partner2 == partner1);
		SBX(pop_all + partner1, pop_all + partner2, ind, &child, variationPc, etaC);
		Mutate(ind, mutationPm, etaM);
	}

	deallocate_memory_ind(&child);

}

void MOEA_solver::so_crossover(individual* ind, int idx, int psize)
{
	// Seed from a base parent to ensure initialized values
	int base = idx % psize;
	copy(ind, pop_sel + base);

	int p1 = irand(psize);
	int p2;
	do { p2 = irand(psize); } while (p2 == p1);

	int point = (Nvar == 2) ? 1 : irand(Nvar - 1) + 1;
	for (int i = 0; i < point; i++)
	{
		float r = randval(0, 1);
		float blended = pop_sel[p1].x[i] * r + (1 - r) * pop_sel[p2].x[i];
		if (blended < Lbound) blended = Lbound;
		else if (blended > Ubound) blended = Ubound;
		ind->x[i] = blended;
	}
}

void MOEA_solver::so_mutate(individual* ind, int idx)
{
	// Start from an existing individual to preserve structure
	int base = idx % Popsize;
	copy(ind, pop_sel + base);
	float p = randval(0, 1);
	if (p < soMutationPm)
	{
		int gene = irand(Nvar);
		float val = randval(Lbound, Ubound);
		ind->x[gene] = val;
	}
}

void MOEA_solver::xover_basic(individual* ind, int idx, int psize)
{
	int p1 = irand(psize);
	int p2;
	do { p2 = irand(psize); } while (p2 == p1);
	int point = (Nvar == 2) ? 1 : irand(Nvar - 1) + 1;
	copy(ind, pop_sel + p1);
	for (int i = 0; i < point; i++)
	{
		float r = randval(0, 1);
		float blended = pop_sel[p1].x[i] * r + (1 - r) * pop_sel[p2].x[i];
		if (blended < Lbound) blended = Lbound;
		else if (blended > Ubound) blended = Ubound;
		ind->x[i] = blended;
	}
}

void MOEA_solver::de_crossover(individual* ind, int idx, int psize, float F, float CR)
{
	if (psize < 4)
	{
		variationByNPC(ind, 0, psize);
		return;
	}
	int r1, r2, r3;
	int base;
	base = irand(psize);
	do { r1 = irand(psize); } while (r1 == base);
	do { r2 = irand(psize); } while (r2 == base || r2 == r1);
	do { r3 = irand(psize); } while (r3 == base || r3 == r2 || r3 == r1);
	int jrand = irand(Nvar);
	for (int j = 0; j < Nvar; j++)
	{
		float trial;
		float r = randval(0, 1);
		if (r < CR || j == jrand)
			trial = pop_sel[r1].x[j] + F * (pop_sel[r2].x[j] - pop_sel[r3].x[j]);
		else
			trial = pop_sel[base].x[j];
		if (trial < Lbound) trial = Lbound;
		else if (trial > Ubound) trial = Ubound;
		ind->x[j] = trial;
	}
}

void MOEA_solver::de_mutate(individual* ind, int idx, int strategy)
{
	// reuse DE/rand/1 style with different F per strategy
	float F = deF;
	float CR = deCR;
	switch (strategy)
	{
	case 2: F = deF + 0.1f; break;
	case 3: F = deF + 0.2f; break;
	case 4: F = deF + 0.3f; break;
	case 5: F = deF + 0.5f; break;
	default: break;
	}
	de_crossover(ind, idx, Popsize, F, CR);
}

void MOEA_solver::cauchy_mutation(individual* ind, int idx)
{
	int gene = irand(Nvar);
	float step = gauss(); // use gaussian as proxy; library lacks direct cauchy
	float val = ind->x[gene] + step * cauchyScale * (Ubound - Lbound);
	if (val < Lbound) val = Lbound;
	else if (val > Ubound) val = Ubound;
	ind->x[gene] = val;
}

void MOEA_solver::pop_niche(individual* /*ind*/)
{
	// placeholder: no-op niche adjustment
}

void MOEA_solver::localsearch(individual* ind)
{
	// simple hill-climb step on one gene
	int gene = irand(Nvar);
	float delta = 0.05f * (randval(-1, 1));
	float val = ind->x[gene] + delta * (Ubound - Lbound);
	if (val < Lbound) val = Lbound;
	else if (val > Ubound) val = Ubound;
	ind->x[gene] = val;
}

void MOEA_solver::newpop_localstep(individual* ind)
{
	localsearch(ind);
}

void MOEA_solver::newpop_bit_climbing(individual* ind)
{
	// bit-flip on one gene's binary encoding surrogate
	int gene = irand(Nvar);
	float val = ind->x[gene];
	float span = (Ubound - Lbound) * 0.1f;
	val += (randval(0, 1) < 0.5f ? -span : span);
	if (val < Lbound) val = Lbound;
	else if (val > Ubound) val = Ubound;
	ind->x[gene] = val;
}

void MOEA_solver::newpop_simplex(individual* ind)
{
	// minimal simplex-like perturbation: average with two others
	int a = irand(Popsize);
	int b;
	do { b = irand(Popsize); } while (b == a);
	for (int j = 0; j < Nvar; ++j)
	{
		float val = (ind->x[j] + pop_sel[a].x[j] + pop_sel[b].x[j]) / 3.0f;
		if (val < Lbound) val = Lbound;
		else if (val > Ubound) val = Ubound;
		ind->x[j] = val;
	}
}

void MOEA_solver::setOperatorSequence(const std::vector<std::string>& seq)
{
	op_sequence = seq;
}

void MOEA_solver::resetOpUsage()
{
	g_moea_op_usage.clear();
}

const std::unordered_map<std::string, int>& MOEA_solver::getOpUsage() const
{
	return g_moea_op_usage;
}

void MOEA_solver::applyVariationOp(individual* ind, int idx, int flag, int psize)
{
	// Start from a real individual so mutation-only ops don't touch garbage
	copy(ind, pop_sel + (idx % psize));

	if (op_sequence.empty())
	{
		variationByNPC(ind, flag, psize);
		return;
	}

	std::string op = op_sequence[idx % op_sequence.size()];
	std::transform(op.begin(), op.end(), op.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });

	if (op == "NPC" || op == "SBX_PM")
	{
		variationByNPC(ind, flag, psize);
		return;
	}
	if (op == "NPC_ALL")
	{
		variationByNPC(ind, 1, psize);
		return;
	}
	if (op == "SBX" || op == "NSGA_SBX")
	{
		variationByNPC(ind, flag, psize);
		return;
	}
	if (op == "MUTATE" || op == "PM")
	{
		Mutate(ind, mutationPm, etaM);
		return;
	}
	if (op == "PC")
	{
		int prom_id = EP.empty() ? 0 : (idx % EP.size());
		variationByPC(ind, prom_id);
		return;
	}
	if (op == "DISCRETE_MUTATE" || op == "DM")
	{
		discrete_mutate(ind, mutationPm);
		return;
	}
	if (op == "SO_CROSSOVER" || op == "SO_XOVER" || op == "SO_XOVER_ARITH")
	{
		so_crossover(ind, idx, psize);
		return;
	}
	if (op == "SO_MUTATE")
	{
		so_mutate(ind, idx);
		return;
	}
	if (op == "XOVER")
	{
		xover_basic(ind, idx, psize);
		return;
	}
	if (op == "DIFFERENTIAL_CROSSOVER" || op == "DE_CROSSOVER")
	{
		de_crossover(ind, idx, psize, deF, deCR);
		return;
	}
	if (op == "CAUCHY_MUTATION")
	{
		cauchy_mutation(ind, idx);
		return;
	}
	g_moea_op_usage[op]++;
	if (op == "DIFFERENTIAL_MUTATE_1") { de_mutate(ind, idx, 1); return; }
	if (op == "DIFFERENTIAL_MUTATE_2") { de_mutate(ind, idx, 2); return; }
	if (op == "DIFFERENTIAL_MUTATE_3") { de_mutate(ind, idx, 3); return; }
	if (op == "DIFFERENTIAL_MUTATE_4") { de_mutate(ind, idx, 4); return; }
	if (op == "DIFFERENTIAL_MUTATE_5") { de_mutate(ind, idx, 5); return; }
	if (op == "POP_NICHE") { pop_niche(ind); return; }
	if (op == "LOCALSEARCH") { localsearch(ind); return; }
	if (op == "NEWPOP_LOCALSTEP") { newpop_localstep(ind); return; }
	if (op == "NEWPOP_BIT_CLIMBING") { newpop_bit_climbing(ind); return; }
	if (op == "NEWPOP_SIMPLEX") { newpop_simplex(ind); return; }

	if (op == "SIM_MUTATE")
	{
		if (custom_op) custom_op(ind);
		Mutate(ind, mutationPm, etaM);
		return;
	}
	// fallback
	variationByNPC(ind, flag, psize);
}

void MOEA_solver::Evaluation(individual* pp, int size)
{
	for (int i = 0; i < size; i++)
		EvaluFunc(pp[i].x, pp[i].obj, Nvar, Nobj);
	eval_count += size;
}

//BCE
void MOEA_solver::NormalizeAll()
{
	calcBoundsEP();
	for (auto iter = EP.begin(); iter != EP.end(); iter++)
		ObjectiveNormalization(*iter);
	for (int i = 0; i < Popsize; i++)
		ObjectiveNormalization(pop_sel[i]);
}

void MOEA_solver::BCE_EnvironmentalSelection()
{
	int i, j;
	float distance, radius;
	int count;
	int EPsize = (int)EP.size();

	float** c = new float* [EPsize];
	for (i = 0; i < EPsize; i++)
		c[i] = new float[EPsize];

	for (i = 0; i < EPsize; i++)
	{
		for (j = i + 1; j < EPsize; j++)
			c[i][j] = c[j][i] = EuclideanDistance(EP[i].obj_norm, EP[j].obj_norm, Nobj);
		c[i][i] = INF;
	}

	if (EPsize == 1)
		radius = 0;
	else
		radius = determinRadius(c, EPsize);

	for (i = 0; i < EP_capability; i++)
		promising[i] = 0;
	promising_num = 0;
	for (i = 0; i < EPsize; i++)
	{
		count = 0;
		for (j = 0; j < Popsize; j++)
		{
			distance = EuclideanDistance(EP[i].obj_norm, pop_sel[j].obj_norm, Nobj);
			if (distance <= radius * EPsize / (float)EP_capability)
				count++;
		}
		if (count < 2)
		{
			promising[promising_num] = i;
			promising_num++;
		}
	}

	for (i = 0; i < EPsize; i++)
		delete[] c[i];
	delete[] c;
}

void MOEA_solver::solutionUpdate0()
{
	individual child;
	allocate_memory_ind(&child);

	for (int i = 0; i < promising_num; i++)
	{
		EnvironmentalSelection0();
		variationByPC(&child, promising[i]);
		EvaluFunc(child.x, child.obj, Nvar, Nobj);
		eval_count++;
		updateEP(child);
		updateBounds(child);
		copy(pop_all + alphaSize_BCE + i, &child);  //update NPs
	}
	deallocate_memory_ind(&child);
}

void MOEA_solver::solutionUpdate1()
{
	for (int i = 0; i < Popsize; i++)
	{
		applyVariationOp(&pop_new[i], i, 0, Popsize);
		EvaluFunc(pop_new[i].x, pop_new[i].obj, Nvar, Nobj);
		eval_count++;
		updateEP(pop_new[i]);
		updateBounds(pop_new[i]);
		copy(pop_all + alphaSize_BCE + promising_num + i, &pop_new[i]);
	}
}

void MOEA_solver::maintainEP()
{
	int EPsize = static_cast<int>(EP.size());
	if (EPsize > EP_capability)
	{
		// Simple, safe truncation to avoid heap issues
		EP.resize(EP_capability);
	}
	else
	{
	}
}

void MOEA_solver::fastNondominatedSort()
{
	int i, j, k;
	int** S = new int* [fullSize2];   //store the indices of solutions dominated by the i-th item of pop_all;
	for (i = 0; i < fullSize2; i++)
		S[i] = new int[fullSize2];
	int* N = new int[fullSize2];
	int* lenS = new int[fullSize2];

	for (i = 0; i < fullSize2; i++)
	{
		levelSize[i] = 0;
		N[i] = 0;
	}

	for (i = 0; i < fullSize2; i++)
	{
		lenS[i] = 0;
		for (j = 0; j < fullSize2; j++)
		{
			int isDominance = check_dominance(pop_all[i], pop_all[j], Nobj);
			if (isDominance == 1)
			{
				S[i][lenS[i]] = j;
				lenS[i] ++;
			}
			else if (isDominance == -1)
				N[i] ++;
		}
		if (N[i] == 0)
		{
			//pop_all[i].fitness = 0;
			levelF[0][levelSize[0]] = i;
			levelSize[0] ++;
		}
	}

	i = 0;
	while (levelSize[i] != 0)
	{
		levelSize[i + 1] = 0;
		for (j = 0; j < levelSize[i]; j++)
		{
			int p = levelF[i][j];
			for (k = 0; k < lenS[p]; k++)
			{
				int q = S[p][k];
				N[q] --;
				if (N[q] == 0)
				{
					//pop_all[q].fitness = i + 1;
					levelF[i + 1][levelSize[i + 1]] = q;
					levelSize[i + 1] ++;
				}
			}
		}
		i++;
	}

	for (i = 0; i < fullSize2; i++)
		delete[] S[i];
	delete[] S;
	delete[] N;
	delete[] lenS;
}

//BCE2
void MOEA_solver::EnvironmentalSelection1()
{
	int i, j, worst;
	int new_size = alphaSize_BCE + Popsize + promising_num;
	for (i = 0; i < Popsize; i++)  //fullSize - alphaSize_BCE = Popsize
	{
		worst = 0;
		for (j = 1; j < new_size; j++)
			if (pop_all[worst].fitness < pop_all[j].fitness)
				worst = j;

		for (j = 0; j < new_size; j++)
			pop_all[j].fitness -= fitcomp[worst][j];

		swap(pop_all + new_size - 1, pop_all + worst);
		new_size--;
	}
}

void MOEA_solver::matingSelection(bool flag)//0
{
	int i, j;
	int alphaSize;
	if (flag)
		alphaSize = alphaSize_IB;
	else
		alphaSize = alphaSize_BCE;
	for (i = 0; i < Popsize; i++)
	{
		int winner = irand(alphaSize);
		for (j = 1; j < tournament; j++)
		{
			int opponent = irand(alphaSize);
			if (pop_all[opponent].fitness < pop_all[winner].fitness || winner == opponent)
				winner = opponent;
		}
		copy(pop_sel + i, pop_all + winner);//pop_sel是经过二元竞标赛胜出的个体
	}
}

void MOEA_solver::EnvironmentalSelection0()
{
	int i, j;
	float distance, radius;
	int count;
	int EPsize = (int)EP.size();
	cout << "EPSIZE_environment0:   " << EPsize << endl;

	float** c = new float* [EPsize];
	for (i = 0; i < EPsize; i++)
		c[i] = new float[EPsize];

	for (i = 0; i < EPsize; i++)
	{
		for (j = i + 1; j < EPsize; j++)
			c[i][j] = c[j][i] = EuclideanDistance(EP[i].obj_norm, EP[j].obj_norm, Nobj);
		c[i][i] = INF;
	}

	if (EPsize == 1)
		radius = 0;
	else
		radius = determinRadius(c, EPsize);

	for (i = 0; i < EP_capability; i++)
		promising[i] = 0;
	promising_num = 0;
	for (i = 0; i < EPsize; i++)
	{
		count = 0;
		for (j = 0; j < Popsize; j++)
		{
			distance = EuclideanDistance(EP[i].obj_norm, pop_sel[j].obj_norm, Nobj);
			if (distance <= radius * EPsize / (float)EP_capability)
				count++;
		}
		if (count < 2)
		{
			promising[promising_num] = i;
			promising_num++;
		}
	}
	cout << "promise     " << promising_num - 1 << endl;
	for (i = 0; i < EPsize; i++)
		delete[] c[i];
	delete[] c;
}

//GrEA

//hypeE
void  MOEA_solver::HypeFitnessEstimation(individual* pop, int len, int removed_k, int M)
{
	int* UP = new int[len];
	float* l = new float[Nobj];
	float* u = new float[Nobj];
	float V = 1.0;

	for (int i = 0; i < len; i++)
	{
		HypeFitness[i] = 0;
	}



	HypeCalcRef(pop, len);
	for (int i = 0; i < Nobj; i++)
	{
		l[i] = HypeMin[i];
		u[i] = HypeRef[i];

		V *= (u[i] - l[i]);
	}

	for (int j = 0; j < M; j++)
	{
		float* s = new float[Nobj];

		int UPsize = 0;
		float alpha = 1.0;

		for (int i = 0; i < Nobj; i++)
		{
			s[i] = randval(l[i], u[i]);
		}

		for (int i = 0; i < len; i++)
		{
			if (1 == check_partial_dominance(pop[i], s, 0))
			{
				UP[UPsize] = i;
				UPsize++;
			}
		}


		if (UPsize <= removed_k)
		{
			if (UPsize == 1)
			{
				alpha = 1.0;
			}
			else if (UPsize > 1)
			{
				for (int l = 1; l < UPsize; l++)
				{
					alpha *= (removed_k - l) * 1.0 / (len - l);
				}
			}

			for (int i = 0; i < UPsize; i++)
			{
				HypeFitness[UP[i]] += alpha / UPsize * V / M;
			}
		}





	}

	delete[] UP;
	delete[] l;
	delete[] u;
}

void MOEA_solver::HypeMatingSelection(int m)
{
	int i, j;
	int index;


	fastNondominatedSort();
	i = 0;
	index = 0;
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}
	if (index < Popsize)
	{
		int size = levelSize[i];

		individual* pop_temp;
		pop_temp = allocate_memory_indArray(size);
		int* idx = new int[size];
		for (int j = 0; j < levelSize[i]; j++)
		{
			copy(pop_temp + j, pop_all + levelF[i][j]);
			idx[j] = j;
		}

		if (Nobj <= 3)
		{
			HypeFitnessExact(pop_temp, size, Popsize - index);
		}
		else
		{
			HypeFitnessEstimation(pop_temp, size, Popsize - index, m);
		}

		maxFastSort(HypeFitness, idx, size, size);

		for (j = 0; j < Popsize - index; j++)
			copy(pop_sel + index + j, pop_temp + idx[j]);


		deallocate_memory_indArray(pop_temp, size);
		delete[] idx;
	}
}

void MOEA_solver::HypeEnvironmentalSelection(int m)
{
	std::random_device rd;
	int EPsize = (int)EP.size();
	int* idx = new int[EPsize];

	for (int i = 0; i < EPsize; i++)
	{
		idx[i] = i;
	}

	if (EPsize > EP_capability)
	{
		if (Nobj <= 3)
		{
			HypeFitnessExact(&EP[0], EPsize, EPsize - EP_capability);
		}
		else
		{
			HypeFitnessEstimation(&EP[0], EPsize, EPsize - EP_capability, m);
		}


		minFastSort(HypeFitness, idx, EPsize, EPsize);
		int* s = new int[EPsize - EP_capability];
		for (int i = 0; i < EPsize - EP_capability; i++)
		{
			s[i] = i;
		}
		maxFastSort(idx, s, EPsize - EP_capability, EPsize - EP_capability);

		for (int i = 0; i < EPsize - EP_capability; i++)
		{
			EP.erase(EP.begin() + idx[i]);
		}
		delete[] s;
	}
	delete[] idx;

	calcBounds(pop_all, fullSize2);
}

void MOEA_solver::HypeFitnessExact(individual* pop, int len, int removed_k)
{
	for (int i = 0; i < len; i++)
	{
		HypeFitness[i] = 0;
	}

	/*pop_sel[0].obj[0] = -10;
	pop_sel[0].obj[1] = -3;
	//	pop_sel[0].obj[2] = -2;

	pop_sel[1].obj[0] = -8;
	pop_sel[1].obj[1] = -1;
	//	pop_sel[1].obj[2] = -8;

	pop_sel[2].obj[0] = -6;
	pop_sel[2].obj[1] = -8;
	//	pop_sel[2].obj[2] = -10;

	pop_sel[3].obj[0] = -4;
	pop_sel[3].obj[1] = -5;
	//	pop_sel[3].obj[2] = -11;*/

	//calcBounds(pop_sel, len);//reference point
	HypeCalcRef(pop, len);//reference point

	float* position = new float[Nobj];
	for (int i = 0; i < Nobj; i++)
	{
		position[i] = INF;
	}

	//HypeDoSlicing(pop_sel, 4, HypeFitness, 2, Nobj, 1, position);
	HypeDoSlicing(pop, len, HypeFitness, removed_k, Nobj, 1, position);


	delete[] position;
}

void MOEA_solver::HypeDoSlicing(individual* pop, int len, float* curFitness, int removed_k, int dim, float partialVolume, float* pos)
{

	int* UP = new int[len];
	int UPsize = 0;
	for (int i = 0; i < len; i++)
	{
		if (1 == check_partial_dominance(pop[i], pos, dim - 1))
		{
			UP[UPsize] = i;
			UPsize++;
		}
	}
	sort_dim_ascending(pop, UP, UPsize, dim - 1);

	if (dim == 0)//only 1 refenrence point
	{
		float alpha = 1.0;
		float k = (float)removed_k;
		float l = (float)len;
		if (UPsize == 1)
		{
			alpha = 1.0;
		}
		else if (UPsize > 1 && UPsize <= removed_k)
		{
			for (int j = 1; j < UPsize; j++)
			{
				alpha *= (k - j) * 1.0 / (l - j);
			}
		}
		else
		{
			alpha = 0;
		}

		if (alpha != 0)
		{
			for (int i = 0; i < UPsize; i++)
			{
				*(curFitness + UP[i]) += alpha * partialVolume / UPsize;
			}
		}


	}
	else if (dim > 0)
	{
		float u_star = pos[dim - 1];

		for (int i = 0; i < UPsize; i++)
		{
			float* postemp = new float[Nobj];
			//float postemp[OBJNUM] = { INF };
			for (int i = 0; i < Nobj; i++)
			{
				postemp[i] = pos[i];
			}
			float voltemp = partialVolume;
			if (i == UPsize - 1)
			{
				u_star = pop[UP[i]].obj[dim - 1];
				voltemp *= (HypeRef[dim - 1] - u_star);
				postemp[dim - 1] = u_star;
				HypeDoSlicing(pop, len, curFitness, removed_k, dim - 1, voltemp, postemp);
			}
			else
			{
				u_star = pop[UP[i]].obj[dim - 1];
				voltemp *= (pop[UP[i + 1]].obj[dim - 1] - u_star);
				postemp[dim - 1] = u_star;
				HypeDoSlicing(pop, len, curFitness, removed_k, dim - 1, voltemp, postemp);
			}

		}



	}

	delete[] UP;

}

int MOEA_solver::check_partial_dominance(individual& ind, float* pos, int dimStart)
{
	if (dimStart < 0)
	{
		dimStart = 0;
	}
	for (int j = dimStart; j < Nobj; j++)
	{
		if (ind.obj[j] > pos[j])
			return 0;
	}
	return 1;
}

void MOEA_solver::sort_dim_ascending(individual* pop, int* popno, int size, int dim)
{
	for (int i = 0; i < size; i++)
	{

		for (int j = 0; j < size - i - 1; j++)
		{
			if (pop[popno[j]].obj[dim] > pop[popno[j + 1]].obj[dim])
			{
				int temp;
				temp = popno[j + 1];
				*(popno + j + 1) = popno[j];
				*(popno + j) = temp;
			}
		}


	}
}

void MOEA_solver::HypeCalcRef(individual* pp, int len)
{
	int i, j;
	float rho = 1 + 1 / Hp;
	int flag = 0;
	float* min = new float[Nobj];
	float* max = new float[Nobj];


	for (j = 0; j < Nobj; j++)
	{
		if (pp[0].obj[j] == PUNISHMENT)
		{
			min[j] = PUNISHMENT;
			max[j] = -PUNISHMENT;

		}
		else
		{
			min[j] = pp[0].obj[j];
			max[j] = pp[0].obj[j];
		}
	}


	for (i = 0; i < len; i++)
	{
		if (pp[i].obj[0] != PUNISHMENT)
		{
			for (j = 0; j < Nobj; j++)
			{
				if (pp[i].obj[j] < min[j])
					min[j] = pp[i].obj[j];
				if (pp[i].obj[j] > max[j])
					max[j] = pp[i].obj[j];
			}
		}
	}

	for (j = 0; j < Nobj; j++)
	{
		HypeRef[j] = min[j] + rho * (max[j] - min[j]);
		HypeMin[j] = min[j];
	}

	delete[] min;
	delete[] max;
}

//IBEA
void MOEA_solver::mergeOffspring()
{
	int i;
	for (i = 0; i < Popsize; i++)
		copy(pop_all + alphaSize_IB + i, pop_new + i);
}

void MOEA_solver::calcFitnessIndicator(int type)
{
	float maxAbsIndicatorValue = 0;
	int i, j;

	for (i = 0; i < fullSize; i++)
	{
		for (j = 0; j < fullSize; j++)
		{
			if (type == 0)
				fitcomp[i][j] = calcAddEpsIndicator(pop_all + i, pop_all + j);
			else
			{
				if (check_dominance(pop_all[i], pop_all[j], Nobj) > 0)
					fitcomp[i][j] = -calcHypervolumeIndicator(pop_all + i, pop_all + j, Nobj);
				else
					fitcomp[i][j] = calcHypervolumeIndicator(pop_all + j, pop_all + i, Nobj);

			}
			if (maxAbsIndicatorValue < fabs(fitcomp[i][j]))
				maxAbsIndicatorValue = fabs(fitcomp[i][j]);
		}
	}

	for (i = 0; i < fullSize; i++)
	{
		for (j = 0; j < fullSize; j++)
		{
			float etm = (-fitcomp[i][j] / (maxAbsIndicatorValue + 1));
			fitcomp[i][j] = exp(etm / kappa);
		}
	}

	double sum;
	for (i = 0; i < fullSize; i++)
	{
		sum = 0;
		for (j = 0; j < fullSize; j++)
		{
			if (i != j)
				sum += fitcomp[j][i];
		}
		pop_all[i].fitness = sum;
	}
}

float MOEA_solver::calcAddEpsIndicator(individual* ind_a, individual* ind_b)
{
	int i;
	float r;
	float eps = 0;

	r = curBoundmax[0] - curBoundmin[0];
	eps = (ind_a->obj[0] - curBoundmin[0]) / r - (ind_b->obj[0] - curBoundmin[0]) / r;
	for (i = 1; i < Nobj; i++)
	{
		r = curBoundmax[i] - curBoundmin[i];
		float temp_eps = (ind_a->obj[i] - curBoundmin[i]) / r - (ind_b->obj[i] - curBoundmin[i]) / r;
		if (eps < temp_eps)
			eps = temp_eps;
	}
	return eps;
}

float MOEA_solver::calcHypervolumeIndicator(individual* ind_a, individual* ind_b, int d)
{
	float a, b, r;
	float volume = 0;

	r = 1.1 * (curBoundmax[d - 1] - curBoundmin[d - 1]);

	a = ind_a->obj[d - 1];
	if (ind_b == NULL)
		b = referencePoint[d - 1];
	else
		b = ind_b->obj[d - 1];

	if (d == 1)
	{
		if (a < b)
			volume = (b - a) / r;
		else
			volume = 0;
	}
	else
	{
		if (a < b)
		{
			volume = calcHypervolumeIndicator(ind_a, NULL, d - 1) * (b - a) / (r + 1);
			volume += calcHypervolumeIndicator(ind_a, ind_b, d - 1) * (referencePoint[d - 1] - b) / r;
		}
		else
		{
			volume = calcHypervolumeIndicator(ind_a, ind_b, d - 1) * (referencePoint[d - 1] - a) / r;
		}
	}
	return volume;
}

void MOEA_solver::IBEA_environmentalSelection()
{
	int i, j, worst;
	int new_size = fullSize;
	for (i = 0; i < Popsize; i++)  //fullSize - alphaSize_IB = Popsize
	{
		worst = 0;
		for (j = 1; j < new_size; j++)
			if (pop_all[worst].fitness < pop_all[j].fitness)
				worst = j;

		for (j = 0; j < new_size; j++)
			pop_all[j].fitness -= fitcomp[worst][j];

		swap(pop_all + new_size - 1, pop_all + worst);//将最差的都放后面前2.5个popsize都是ok的
		new_size--;
	}

	//
	//pop_all[0].x
}

void MOEA_solver::updateEP()
{
	for (int i = 0; i < Popsize; i++)
	{
		if (EP.empty())
		{
			individual new_element;
			allocate_memory_ind(&new_element);
			copy(&new_element, pop_new + i);
			EP.push_back(new_element);
			continue;
		}
		auto iter = EP.begin();
		do
		{
			int flag = check_dominance(pop_new[i], *iter, Nobj);
			int equality_flag = check_equality(pop_new[i], *iter, 1);//一样返回1，不一样返回0
			if (flag == 1)
			{
				iter = EP.erase(iter);
			}
			else if (flag == -1 || equality_flag)
				// return;
				break;
			else
			{
				iter++;
			}
		} while (iter != EP.end());
		individual new_element;
		allocate_memory_ind(&new_element);
		copy(&new_element, pop_new + i);
		EP.push_back(new_element);
	}
}

//MOEAD
void MOEA_solver::initializeWeight(int h, int index_obj, int pre_sum, int* weight_vector)
{
	int i, j;
	if (index_obj != Nobj - 2)
	{
		for (i = 0; i <= h - pre_sum; i++)
		{
			weight_vector[index_obj] = i;
			initializeWeight(h, index_obj + 1, pre_sum + i, weight_vector);
		}
	}
	else
	{
		for (i = 0; i <= h - pre_sum; i++)
		{
			weight_vector[index_obj] = i;
			weight_vector[index_obj + 1] = h - (pre_sum + i);
			for (j = 0; j < Nobj; j++)
				weight[nvector][j] = (float)weight_vector[j] / (float)h;
			nvector++;
		}
	}
}

void MOEA_solver::initializeNeighbor()//为每个个体找到欧式距离最近的niche个个体（邻居）
{
	int i, j, k;
	float* x = new float[Popsize];
	int* idx = new int[Popsize];

	for (i = 0; i < Popsize; i++)
	{
		for (j = 0; j < Popsize; j++)
		{
			x[j] = EuclideanDistance(weight[i], weight[j], Nobj);
			idx[j] = j;
		}
		minFastSort(x, idx, Popsize, niche);

		for (k = 0; k < niche; k++)
			neighbor[i][k] = idx[k];
	}
	delete[] x;
	delete[] idx;
}

float MOEA_solver::Tchebycheff(float* obj, float* lambda)
{
	int j;
	float max_fun, diff, feval;

	max_fun = -1 * INF;
	for (j = 0; j < Nobj; j++)
	{
		diff = fabs(obj[j] - curBoundmin[j]);
		if (lambda[j] == 0)
			feval = diff * 0.00001;
		else
			feval = diff * lambda[j];

		if (feval > max_fun)
			max_fun = feval;
	}
	return max_fun;
}

void MOEA_solver::updateNP()
{
	int i, j;
	float f1, f2;
	for (i = 0; i < Popsize; i++)
	{
		updateBounds(pop_new[i]);

		for (j = 0; j < niche; j++)
		{
			int idx = neighbor[i][j];
			f1 = Tchebycheff(pop_sel[idx].obj, weight[idx]);
			f2 = Tchebycheff(pop_new[i].obj, weight[idx]);

			if (f2 < f1)
				copy(pop_sel + idx, pop_new + i);  //这里是在判断新解好还是旧的解好
		}

	}
}

//NSGA
void MOEA_solver::NSGA_initializeWeight(int h, int index_obj, int pre_sum, int* weight_vector)
{
	int i, j;
	if (index_obj != Nobj - 2)
	{
		for (i = 0; i <= h - pre_sum; i++)
		{
			weight_vector[index_obj] = i;
			NSGA_initializeWeight(h, index_obj + 1, pre_sum + i, weight_vector);
		}
	}
	else
	{
		for (i = 0; i <= h - pre_sum; i++)
		{
			weight_vector[index_obj] = i;
			weight_vector[index_obj + 1] = h - (pre_sum + i);
			Ref cur_rp;
			cur_rp.clusterSize = 0;
			cur_rp.pos = new float[Nobj];
			for (j = 0; j < Nobj; j++)
				cur_rp.pos[j] = (float)weight_vector[j] / (float)h; //rps[start_ind + nvector]
			RefPns.push_back(cur_rp);
			//nvector ++;
		}
	}
}

void MOEA_solver::crowdDistanceAssignment(int level)
{
	int size = levelSize[level];
	if (size <= 0)
		return;

	float* Xobj = new float[size];
	int* idx = new int[size];

	// Compute bounds using the actual members of the current front to avoid invalid pointers
	for (int j = 0; j < Nobj; j++)
	{
		float minv = pop_all[levelF[level][0]].obj[j];
		float maxv = minv;
		for (int i = 1; i < size; i++)
		{
			int index = levelF[level][i];
			minv = std::min(minv, pop_all[index].obj[j]);
			maxv = std::max(maxv, pop_all[index].obj[j]);
		}
		curBoundmin[j] = minv;
		curBoundmax[j] = maxv;
	}

	int i, j;
	for (i = 0; i < size; i++)
		pop_all[levelF[level][i]].distance = 0;
	for (j = 0; j < Nobj; j++)
	{
		for (i = 0; i < size; i++)
		{
			int index = levelF[level][i];
			Xobj[i] = pop_all[index].obj[j];
			idx[i] = index;
		}
		minFastSort(Xobj, idx, size, size);
		pop_all[idx[0]].distance = pop_all[idx[size - 1]].distance = INF;
		float denom = curBoundmax[j] - curBoundmin[j];
		if (denom == 0)
			continue;
		for (i = 1; i < size - 1; i++)
			pop_all[idx[i]].distance += (pop_all[idx[i + 1]].obj[j]
				- pop_all[idx[i - 1]].obj[j])
			/ denom;
	}

	delete[] Xobj;
	delete[] idx;
}

void MOEA_solver::solutionUpdate()
{
	for (int i = 0; i < Popsize; i++)
		copy(pop_all + i, pop_sel + i);

	for (int i = 0; i < Popsize; i++)
		copy(pop_all + Popsize + i, pop_new + i);
}

void MOEA_solver::NSGA_matingSelection()
{
	int i, j;
	int index;
	fastNondominatedSort();
	i = 0;
	index = 0;
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}
	if (index < Popsize)
	{
		int size = levelSize[i];
		float* Dis = new float[size];
		int* idx = new int[size];

		crowdDistanceAssignment(i);
		for (j = 0; j < size; j++)
		{
			Dis[j] = pop_sel[levelF[i][j]].distance;
			idx[j] = levelF[i][j];
		}
		maxFastSort(Dis, idx, size, size);

		for (j = 0; j < Popsize - index; j++)
			copy(pop_sel + index + j, pop_all + idx[j]);

		delete[] Dis;
		delete[] idx;
	}
}

//NSGGA_III
void MOEA_solver::translateObjectives()
{
	int i, j;
	for (j = 0; j < Nobj; j++)
		idealPoint[j] = INF;
	for (i = 0; i < levelSize[0]; i++)  //find ideal point from only the first front
	{
		for (j = 0; j < Nobj; j++)
		{
			if (pop_all[levelF[0][i]].obj[j] < idealPoint[j])
				idealPoint[j] = pop_all[levelF[0][i]].obj[j];
		}
	}

	for (i = 0; i < fullSize2; i++)
		for (j = 0; j < Nobj; j++)
			pop_all[i].obj_norm[j] = pop_all[i].obj[j];
	for (i = 0; i < fullSize2; i++)
		for (j = 0; j < Nobj; j++)
			pop_all[i].obj_norm[j] -= idealPoint[j];
}

float MOEA_solver::ASF(individual& ind, int obit)
{
	float max_ratio = -INF;
	float w, ratio;
	for (int i = 0; i < Nobj; i++)
	{
		w = (obit == i) ? 1.0 : 0.00001;
		ratio = ind.obj_norm[i] / w;
		if (max_ratio < ratio)
			max_ratio = ratio;
	}
	return max_ratio;
}

void MOEA_solver::hyperplaneAndNormalization()
{
	int i, j;
	int* extreme_points = new int[Nobj];

	//find extreme points by ASF scaling
	for (j = 0; j < Nobj; j++)
	{
		float min_ASF = INF;
		int min_indv = -1;
		for (i = 0; i < levelSize[0]; i++)
		{
			double asf = ASF(pop_all[levelF[0][i]], j);
			if (asf < min_ASF)
			{
				min_ASF = asf;
				min_indv = levelF[0][i];
			}
		}
		extreme_points[j] = min_indv;
	}

	// Check whether there are duplicate extreme points.
	// This might happen but the original paper does not mention how to deal with it.
	bool duplicate = false;
	for (i = 0; i < Nobj; i++)
	{
		for (j = i + 1; j < Nobj; j++)
		{
			if (extreme_points[i] == extreme_points[j])
				duplicate = true;
		}
		if (duplicate)
			break;
	}

	float* intercepts = new float[Nobj];

	bool negative_intercept = false;
	if (!duplicate)
	{
		//find the equation of the hyperplane
		float** A = new float* [Nobj];
		for (i = 0; i < Nobj; i++)
			A[i] = new float[Nobj];
		float* b = new float[Nobj];
		for (i = 0; i < Nobj; i++)
			for (j = 0; j < Nobj; j++)
				A[i][j] = pop_all[extreme_points[i]].obj_norm[j];
		for (j = 0; j < Nobj; j++)
			b[j] = 1.0;
		float* x = new float[Nobj];
		GuassianElimination(x, A, b, Nobj);

		//find intercepts
		for (i = 0; i < Nobj; i++)
		{
			intercepts[i] = 1.0 / x[i];
			if (x[i] < 0)
			{
				negative_intercept = true;
				break;
			}
		}
		for (i = 0; i < Nobj; i++)
			delete[] A[i];
		delete[] A;
		delete[] b;
		delete[] x;
	}

	if (duplicate || negative_intercept)
	{
		for (j = 0; j < Nobj; j++)
		{
			intercepts[j] = 0;
			for (i = 0; i < fullSize2; i++)
				if (intercepts[j] < pop_all[i].obj_norm[j])
					intercepts[j] = pop_all[i].obj_norm[j];
		}
	}

	//Normalize objectives
	for (i = 0; i < fullSize2; i++)
	{
		for (j = 0; j < Nobj; j++)
		{
			if (fabs(intercepts[j]) > EPS)
				pop_all[i].obj_norm[j] = pop_all[i].obj_norm[j] / (intercepts[j] - idealPoint[j]);
			else
				pop_all[i].obj_norm[j] = pop_all[i].obj_norm[j] / (EPS - idealPoint[j]);
		}
	}

	delete[] extreme_points;
	delete[] intercepts;
}

float MOEA_solver::perpendicularDistance(Ref& direction, individual& ind)
{
	int i;
	float numerator = 0, denominator = 0;
	for (i = 0; i < Nobj; i++)
	{
		numerator += direction.pos[i] * ind.obj_norm[i];
		denominator += direction.pos[i] * direction.pos[i];
	}
	float k = numerator / denominator;

	float d = 0;
	for (i = 0; i < Nobj; i++)
		d += pow(k * direction.pos[i] - ind.obj_norm[i], 2.0);
	d = sqrt(d);
	return d;
}

void MOEA_solver::Associate(vector<Ref>& rps)
{
	int i, j, k;
	i = 0;
	while (levelSize[i] > 0)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			int min_rp = 0;
			float min_dist = perpendicularDistance(rps[0], pop_all[levelF[i][j]]);
			for (k = 1; k < rps.size(); k++)
			{
				float d = perpendicularDistance(rps[k], pop_all[levelF[i][j]]);
				if (d < min_dist)
				{
					min_dist = d;
					min_rp = k;
				}
			}

			if (levelSize[i + 1] > 0)
				rps[min_rp].clusterSize++;
			else
			{
				rps[min_rp].PotentialM_dist.push_back(min_dist);
				rps[min_rp].PotentialM_indv.push_back(levelF[i][j]);
			}
		}
		i++;
	}
}

int MOEA_solver::findNicheRps(vector<Ref>& rps)
{
	int i;
	int min_size = INF;
	for (i = 0; i < rps.size(); i++)
		if (rps[i].clusterSize < min_size)
			min_size = rps[i].clusterSize;

	vector<int> min_rps;
	for (i = 0; i < rps.size(); i++)
		if (rps[i].clusterSize == min_size)
			min_rps.push_back(i);

	std::random_device rd;
	return min_rps[rd() % min_rps.size()];
}

int MOEA_solver::findClosestMember(Ref& rp)
{
	float min_dist = INF;
	int min_indv = -1;
	for (int i = 0; i < rp.PotentialM_indv.size(); i++)
	{
		if (rp.PotentialM_dist[i] < min_dist)
		{
			min_dist = rp.PotentialM_dist[i];
			min_indv = rp.PotentialM_indv[i];
		}
	}
	return min_indv;
}

int MOEA_solver::selectClusterMember(Ref& rp)
{
	int chosen = -1;
	if (rp.PotentialM_indv.size())
	{
		if (rp.clusterSize == 0)
			chosen = findClosestMember(rp);
		else
			chosen = rp.PotentialM_indv[irand((int)rp.PotentialM_indv.size())];
	}
	return chosen;
}

void MOEA_solver::removePotential(Ref& rp, int chosen)
{
	for (int i = 0; i < rp.PotentialM_indv.size(); i++)
	{
		if (rp.PotentialM_indv[i] == chosen)
		{
			rp.PotentialM_indv.erase(rp.PotentialM_indv.begin() + i);
			rp.PotentialM_dist.erase(rp.PotentialM_dist.begin() + i);
			break;
		}
	}
	rp.clusterSize++;
}

void MOEA_solver::NSGA_III_environmentalSelection()
{
	int i, j, index;
	vector<Ref> temp_rps;
	temp_rps.clear();
	for (auto iter = RefPns.begin(); iter != RefPns.end(); iter++)
	{
		Ref curP;
		curP.pos = new float[Nobj];
		curP.clusterSize = 0;
		curP.PotentialM_indv.clear();
		curP.PotentialM_dist.clear();
		for (j = 0; j < Nobj; j++)
			curP.pos[j] = iter->pos[j];
		temp_rps.push_back(curP);
	}

	i = 0;
	index = 0;
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}

	for (j = i + 1; j < fullSize2; j++)
		levelSize[j] = 0;

	translateObjectives();
	hyperplaneAndNormalization();
	Associate(temp_rps);

	while (index < Popsize && temp_rps.size() != 0)
	{
		int min_rp = findNicheRps(temp_rps);

		int chosen = selectClusterMember(temp_rps[min_rp]);
		if (chosen < 0)
		{
			delete[] temp_rps[min_rp].pos;
			temp_rps[min_rp].PotentialM_dist.clear();
			temp_rps[min_rp].PotentialM_indv.clear();
			temp_rps.erase(temp_rps.begin() + min_rp);
		}
		else
		{
			temp_rps[min_rp].clusterSize++;
			removePotential(temp_rps[min_rp], chosen);
			copy(pop_sel + index, pop_all + chosen);
			index++;
		}
	}

	for (auto iter = temp_rps.begin(); iter != temp_rps.end(); iter++)
	{
		delete[] iter->pos;
		iter->PotentialM_indv.clear();
		iter->PotentialM_dist.clear();
	}
	temp_rps.clear();
}



//PICEAg

void MOEA_solver::merge_popall()
{
	for (int i = 0; i < Popsize; i++)
	{
		copy(pop_all + i, pop_sel + i);
		copy(pop_all + Popsize + i, pop_new + i);
	}
}

void MOEA_solver::goal_generator(int flag)
{
	float alpha = 1.2; //suggested [1,2]
	float* goalUpper;
	float* goalLower;
	goalUpper = new float[Nobj];
	goalLower = new float[Nobj];
	if (flag == 0)	//initial goal
	{
		for (int i = 0; i < Nobj; i++)
		{
			goalUpper[i] = pop_sel[0].obj[i];
			goalLower[i] = pop_sel[0].obj[i];
		}
		for (int i = 0; i < Ngoal; i++)
		{
			for (int j = 0; j < Nobj; j++)
			{
				goalUpper[j] = max(goalUpper[j], pop_sel[i].obj[j]); //pop_all.obj max
				goalLower[j] = min(goalLower[j], pop_sel[i].obj[j]);//pop_all.obj min
			}
		}
		for (int i = 0; i < Ngoal; i++)
		{
			for (int j = 0; j < Nobj; j++)
			{
				Goal[i][j] = goalUpper[j] - randval(0, 1) * (goalUpper[j] - goalLower[j]);
			}
		}
	}
	else
	{
		for (int i = 0; i < Nobj; i++)
		{
			goalUpper[i] = pop_all[0].obj[i];
			goalLower[i] = pop_all[0].obj[i];
		}
		for (int i = 0; i < 2 * Ngoal; i++)
		{
			for (int j = 0; j < Nobj; j++)
			{
				goalUpper[j] = max(goalUpper[j], pop_all[i].obj[j]); //pop_all.obj max
				goalLower[j] = min(goalLower[j], pop_all[i].obj[j]);//pop_all.obj min
			}
		}
		for (int i = 0; i < Ngoal; i++)
		{
			for (int j = 0; j < Nobj; j++)
			{
				GoalC[i][j] = goalUpper[j] - randval(0, 1) * (goalUpper[j] - goalLower[j]);
			}
		}
	}
	delete[] goalUpper;
	delete[] goalLower;
}

void MOEA_solver::jointG()
{
	for (int i = 0; i < Ngoal; i++)
	{
		for (int j = 0; j < Nobj; j++)
		{
			JointGoal[i][j] = GoalC[i][j];
			JointGoal[Ngoal + i][j] = Goal[i][j];
		}
	}
}

void MOEA_solver::fitness_assignment()
{
	int* gSolved;
	gSolved = new int[2 * Ngoal];
	int** goalMatrix;
	goalMatrix = new int* [fullSize2];
	for (int i = 0; i < fullSize2; i++)
	{
		goalMatrix[i] = new int[2 * Ngoal];
		FitJointS[i] = 0;
	}

	for (int i = 0; i < (2 * Ngoal); i++)	//for each goal and goalc vector
	{
		gSolved[i] = 0;
		FitJointG[i] = 0;
		for (int j = 0; j < fullSize2; j++)
		{
			goalMatrix[j][i] = check_goal_dominance(pop_all[j], JointGoal[i]);	//goalMatrix[1][i] ÿ�и��У����е�solution�Ƿ�֧���i��goal
		}
	}
	//compute score for each solution 
	for (int i = 0; i < (2 * Ngoal); i++)
	{
		for (int j = 0; j < fullSize2; j++)
		{
			gSolved[i] = gSolved[i] + goalMatrix[j][i];	//gSolved[i]:֧���i��goal��solution����
		}
	}
	for (int i = 0; i < fullSize2; i++)
	{
		for (int j = 0; j < (2 * Ngoal); j++)
		{
			if (goalMatrix[i][j] == 1)
			{
				//solution[i]֧��goal[j],��Ҫ����
				if (gSolved[j] != 0)
				{
					FitJointS[i] = FitJointS[i] + 1.0 / gSolved[j];
				}
			}
		}
	}
	float temp = 0;
	for (int i = 0; i < (2 * Ngoal); i++)
	{
		if (gSolved[i] == 0)
		{
			FitJointG[i] = 0.5;
		}
		else
		{
			temp = (gSolved[i] - 1.0) / (fullSize2 - 1.0);
			FitJointG[i] = 1.0 / (1.0 + temp);
		}
	}
	for (int i = 0; i < fullSize2; i++)
	{
		delete[] goalMatrix[i];
	}
	delete[] goalMatrix;
	delete[] gSolved;
}

void MOEA_solver::Fitness_assignment()
{
	// Wrapper for legacy naming used by GrEA
	fitness_assignment();
}

void MOEA_solver::Initailization(int level_index)
{
	if (level_index < 0) return;
	int length = levelSize[level_index];
	if (length <= 0) return;

	for (int j = 0; j < length; j++)
	{
		pop_candi[j].GR = 0;
		pop_candi[j].GCD = 0;
		pop_candi[j].GCPD = 0;
	}

	GCD_calculation(false, length);
	GCPD_calculation(length);
}

int MOEA_solver::check_goal_dominance(individual& ind_a, float* goal)
{
	//if pop_all[j] ֧�� JointGoal[i], goalMatrix[j][i]=1,else goalMatrix[j][i]=0
	int flag = 0;
	for (int i = 0; i < Nobj; i++)
	{
		if (ind_a.obj[i] <= goal[i])
			flag++;
	}
	if (flag == Nobj)
		return 1;
	else
		return 0;
}

void MOEA_solver::truncation_selection()
{
	int* ixS;
	ixS = new int[fullSize2];
	int* ixG;
	ixG = new int[2 * Ngoal];
	for (int i = 0; i < fullSize2; i++)
	{
		ixS[i] = i;
	}
	for (int i = 0; i < 2 * Ngoal; i++)
	{
		ixG[i] = i;
	}
	//update pop_sel
	maxFastSort(FitJointS, ixS, fullSize2, fullSize2);
	for (int i = 0; i < Popsize; i++)
	{
		// copy pop_all with better fitness to pop_sel
		copy(pop_sel + i, pop_all + ixS[i]);
	}
	// update goal vector
	maxFastSort(FitJointG, ixG, 2 * Ngoal, 2 * Ngoal);
	for (int i = 0; i < Ngoal; i++)
	{
		for (int j = 0; j < Nobj; j++)
		{
			Goal[i][j] = JointGoal[ixG[i]][j];
		}
	}
	delete[] ixS;
	delete[] ixG;
}

void MOEA_solver::obtainEP()
{
	int EPsize = (int)EP.size();
	if (EPsize > EP_capability)
	{
		//index_nd_jointS[i]
		for (int i = 0; i < fullSize2; i++)
		{
			if (index_nd_jointS[i] == 0)
				FitJointS[i] = 0;
		}
		truncation_selection();
	}
	else
	{
		truncation_selection();
	}
}

void MOEA_solver::updateEP(individual& ind)
{
	if (EP.empty())
	{
		individual new_element;
		allocate_memory_ind(&new_element);
		copy(&new_element, &ind);
		EP.push_back(new_element);
		return;
	}

	auto iter = EP.begin();
	do
	{
		int flag = check_dominance(ind, *iter, Nobj);
		int equality_flag = check_equality(ind, *iter, Nobj);
		if (flag == 1)
		{
			iter = EP.erase(iter);
		}
		else if (flag == -1 || equality_flag)
			return;
		else
		{
			iter++;
		}
	} while (iter != EP.end());
	individual new_element;
	allocate_memory_ind(&new_element);
	copy(&new_element, &ind);
	EP.push_back(new_element);
}

void MOEA_solver::ObjectiveNormalization(individual& ind)
{
	for (int j = 0; j < Nobj; j++)
	{
		if (curBoundmin[j] != curBoundmax[j])
			ind.obj_norm[j] = (ind.obj[j] - curBoundmin[j]) / (curBoundmax[j] - curBoundmin[j]);
		else
			ind.obj_norm[j] = 0;
	}
}

//RVEA

int MOEA_solver::UniformPoint(int N, int M)
{
	int h1, h2;
	float** w1, ** w2;
	int w1_size = 0;
	int w2_size = 0;
	w2 = new float* [w2_size];
	int weightsize = 0;
	//float **w;
	float zeromin = 0.000001;
	//h1
	h1 = 1;
	while (combination(h1 + M, M - 1) <= N)
		h1 = h1 + 1;
	w1_size = combination(h1 + M - 1, M - 1);
	w1 = new float* [w1_size];
	for (int i = 0; i < w1_size; i++)
		w1[i] = new float[M];
	updateUniformWeight(h1, M, N, w1);
	weightsize = w1_size;
	//h2
	if (h1 < M)
	{
		h2 = 0;
		while (combination(h1 + M - 1, M - 1) + combination(h2 + M, M - 1) <= N)
			h2 = h2 + 1;

		if (h2 > 0)
		{

			w2_size = combination(h2 + M - 1, M - 1);
			w2 = new float* [w2_size];
			for (int i = 0; i < w2_size; i++)
				w2[i] = new float[M];
			updateUniformWeight(h2, M, N, w2);
			weightsize = w1_size + w2_size;
		}
	}

	rvea_weight = new float* [weightsize];
	rvea_weight_init = new float* [weightsize];

	for (int i = 0; i < w1_size; i++)
	{
		rvea_weight[i] = new float[M];
		rvea_weight_init[i] = new float[M];
		for (int j = 0; j < M; j++)
		{
			rvea_weight_init[i][j] = max(w1[i][j], zeromin);
		}
	}
	if (weightsize != w1_size)
	{
		for (int i = 0; i < w2_size; i++)
		{
			rvea_weight[w1_size + i] = new float[M];
			rvea_weight_init[w1_size + i] = new float[M];
			for (int j = 0; j < M; j++)
			{
				float w2_t = w2[i][j] / 2.0 + 1.0 / (2 * M);
				rvea_weight_init[w1_size + i][j] = max(w2_t, zeromin);
			}
		}
	}
	for (int i = 0; i < Popsize; i++)
	{
		float line_abs = 0;
		line_abs = update_uFunctionValue_abs(rvea_weight_init[i], Nobj);
		for (int j = 0; j < Nobj; j++)
		{
			rvea_weight_init[i][j] = rvea_weight_init[i][j] / line_abs;
			rvea_weight[i][j] = rvea_weight_init[i][j];
		}
	}
	/*cout << "-------w----------" << endl;
	for (int i = 0; i < weightsize; i++)
	{
	for (int j = 0; j < M; j++)
	cout << w[i][j] << "\t" << "\t";
	cout << endl;
	}*/
	for (int i = 0; i < w1_size; i++)
		delete[] w1[i];
	for (int i = 0; i < w2_size; i++)
		delete[] w2[i];
	delete[] w1;
	delete[] w2;
	return weightsize;
}

void MOEA_solver::Cij(int i, int j, vector<int>& r, int num, vector<vector<int> >& result)
{
	//������Ϲ�ʽCij
	if (j == 1)
	{
		for (int k = 0; k < i; k++)
		{
			vector<int> temp(num);
			r[0] = k;
			for (int i = 0; i < num; i++)
			{
				temp[i] = r[i];
				//cout << r[i] << ' ';
			}
			result.push_back(temp);
			//cout << endl;
		}
	}
	else if (j == 0)
	{
		//do nothing!
	}
	else
	{
		for (int k = i; k >= j; k--)
		{
			r[j - 1] = k - 1;
			Cij(k - 1, j - 1, r, num, result);
		}
	}
}

void MOEA_solver::updateUniformWeight(int h, int M, int N, float** w)
{
	float** weight1;
	float** weight2;
	float** aa;
	//Cij 
	vector<int> resulttemp(M - 1);
	vector<vector<int> > result;
	Cij(h + M - 1, M - 1, resulttemp, M - 1, result);
	//w initialization
	int resultsize = result.size();
	weight1 = new float* [resultsize];
	weight2 = new float* [resultsize];
	aa = new float* [resultsize];
	for (int i = 0; i < resultsize; i++)
	{
		weight1[i] = new float[M];
		weight2[i] = new float[M];
		aa[i] = new float[M];
		for (int j = 0; j < M - 1; j++)
		{
			aa[i][j] = j;
		}
	}
	//update weight1 & weight2
	for (int i = 0; i < resultsize; i++)
	{
		for (int j = 0; j < M - 1; j++)
		{
			weight1[i][j] = result[i].at(j) - aa[i][j];
			weight2[i][j + 1] = result[i].at(j) - aa[i][j];
		}
		weight1[i][M - 1] = h;
		weight2[i][0] = 0;
	}
	//update w
	for (int i = 0; i < resultsize; i++)
	{
		for (int j = 0; j < M; j++)
		{
			w[i][j] = (weight1[i][j] - weight2[i][j]) / h;
		}
	}
	for (int i = 0; i < resultsize; i++)
	{
		delete[] weight1[i];
		delete[] weight2[i];
		delete[] aa[i];
	}
	delete[] weight1;
	delete[] weight2;
	delete[] aa;
}

float MOEA_solver::dotproduct(float* va, float* vb, int M)
{
	float dotp = 0;
	for (int i = 0; i < M; i++)
	{
		dotp = dotp + va[i] * vb[i];
	}
	return dotp;
}

void MOEA_solver::reference_vector_guided_selection(int maxgene)
{
	float theta0;
	/*float* Zmin;
	Zmin = new float[Nobj];*/
	float** functionValue;
	functionValue = new float* [fullSize2];
	float** ufunctionValue;
	ufunctionValue = new float* [fullSize2];
	float** cosine_fvalue_vec;
	cosine_fvalue_vec = new float* [fullSize2];
	int** maxindex;
	maxindex = new int* [fullSize2];
	float** acos_fv;
	acos_fv = new float* [fullSize2];
	float* D_all;
	D_all = new float[fullSize2];
	int* Dall_index;
	Dall_index = new int[fullSize2];
	vector<vector<int>> vector_associate;
	for (int i = 0; i < Popsize; i++)
	{
		vector<int> vi;
		vector_associate.push_back(vi);
	}
	for (int i = 0; i < fullSize2; i++)
	{
		functionValue[i] = new float[Nobj];
		ufunctionValue[i] = new float[Nobj];
		cosine_fvalue_vec[i] = new float[Popsize];
		acos_fv[i] = new float[Popsize];
		maxindex[i] = new int[Popsize];
		D_all[i] = 1000000;
	}
	//calcZmin(Zmin);
	updateFunctionValue(functionValue);
	update_uFunctionValue(ufunctionValue, functionValue);
	for (int i = 0; i < fullSize2; i++)
	{

		for (int j = 0; j < Popsize; j++)
		{
			cosine_fvalue_vec[i][j] = dotproduct(ufunctionValue[i], rvea_weight[j], Nobj);
			maxindex[i][j] = j;
			acos_fv[i][j] = acos(cosine_fvalue_vec[i][j]);
		}
	}
	//calculate the minimun angle between ufunctionvalue and rvea_weight, select Popsize angle
	for (int i = 0; i < fullSize2; i++)
	{
		maxFastSort(cosine_fvalue_vec[i], maxindex[i], Popsize, 2);
		int ve = maxindex[i][0];
		vector_associate[ve].push_back(i);  //every vector dominates the other population
	}
	theta0 = (float)(eval_count / maxgene);
	theta0 = Nobj * (pow(theta0, rvea_alpha));
	vector<int> un_updatepop;
	for (int i = 0; i < Popsize; i++)
	{
		//APD
		int v_size = vector_associate[i].size();
		if (v_size != 0)
		{
			//associate with vector[i]
			float* D;
			int* D_index;
			D = new float[v_size];
			D_index = new int[v_size];
			for (int k = 0; k < v_size; k++)
			{
				int fvalue_index = vector_associate[i].at(k);
				D_index[k] = fvalue_index;//D_index is the index for fullsize series
				float D0 = update_uFunctionValue_abs(functionValue[fvalue_index], Nobj);
				D[k] = D0 * (1 + theta0 * (acos_fv[fvalue_index][i] / acosVV[i]));
			}
			minFastSort(D, D_index, v_size, 1);
			if (v_size > 1)
			{
				for (int k = 1; k < v_size; k++)
				{
					int dall_index = D_index[k];
					Dall_index[dall_index] = dall_index;
					D_all[dall_index] = D[k];
				}
			}
			copy(pop_sel + i, pop_all + D_index[0]);
			delete[] D;
			delete[] D_index;
		}
		else
		{
			//if vector i has not minimum population individual
			un_updatepop.push_back(i);
		}
		//min
		//update EP
	}
	minFastSort(D_all, Dall_index, fullSize2, fullSize2);
	for (int i = 0; i < un_updatepop.size(); i++)
	{
		int need_update_pop = un_updatepop.at(i);
		copy(pop_sel + need_update_pop, pop_all + Dall_index[i]);
	}

	for (int i = 0; i < fullSize2; i++)
	{
		delete[] functionValue[i];
		delete[] ufunctionValue[i];
		delete[] cosine_fvalue_vec[i];
		delete[] maxindex[i];
		delete[] acos_fv[i];
	}
	delete[] cosine_fvalue_vec;
	delete[] maxindex;
	delete[] acos_fv;
	delete[] Dall_index;
	delete[] D_all;
	delete[] functionValue;
	delete[] ufunctionValue;
	//delete[] Zmin;
}

void MOEA_solver::calcZmin(float* Zmin)
{

	int i, j;
	double temp;
	int id;

	for (i = 0; i < Nobj; i++)
	{
		Zmin[i] = pop_all[0].obj[i];
		for (int j = 0; j < fullSize2; j++)
		{
			if (pop_all[j].obj[i] < Zmin[i])
			{
				Zmin[i] = pop_all[j].obj[i];
			}
		}
	}
}

void MOEA_solver::calcZmax(float* Zmax)
{

	int i, j;
	double temp;
	int id;

	for (i = 0; i < Nobj; i++)
	{
		Zmax[i] = pop_all[0].obj[i];
		for (int j = 0; j < fullSize2; j++)
		{
			if (pop_all[j].obj[i] > Zmax[i])
			{
				Zmax[i] = pop_all[j].obj[i];
			}
		}
	}
}

void MOEA_solver::updateFunctionValue(float** functionValue)
{
	for (int i = 0; i < fullSize2; i++)
	{
		for (int j = 0; j < Nobj; j++)
		{
			functionValue[i][j] = pop_all[i].obj[j] - curBoundmin[j];
		}
	}
}

void MOEA_solver::update_uFunctionValue(float** ufunctionValue, float** fValue)
{
	for (int i = 0; i < fullSize2; i++)
	{
		float line_abs = 0;
		line_abs = update_uFunctionValue_abs(fValue[i], Nobj);
		for (int j = 0; j < Nobj; j++)
		{
			ufunctionValue[i][j] = fValue[i][j] / line_abs;
		}
	}
}

float MOEA_solver::update_uFunctionValue_abs(float* fValue, int num)
{
	float abs = 0;
	for (int i = 0; i < num; i++)
	{
		abs = abs + pow(fValue[i], 2.0);
	}
	abs = pow(abs, 0.5);
	return abs;
}

void MOEA_solver::reference_vector_adaptation()
{
	multiply_boundary();
	for (int i = 0; i < Popsize; i++)
	{
		float line_abs = 0;
		line_abs = update_uFunctionValue_abs(rvea_weight[i], Nobj);
		for (int j = 0; j < Nobj; j++)
		{
			rvea_weight[i][j] = rvea_weight[i][j] / line_abs;
		}
	}

	float** cosineVV;
	int** rvea_neighbor;
	cosineVV = new float* [Popsize];
	rvea_neighbor = new int* [Popsize];
	for (int i = 0; i < Popsize; i++)
	{
		cosineVV[i] = new float[Popsize];
		rvea_neighbor[i] = new int[Popsize];
		for (int j = 0; j < Popsize; j++)
		{
			cosineVV[i][j] = dotproduct(rvea_weight[i], rvea_weight[j], Nobj);
			rvea_neighbor[i][j] = j;//-------------------------------------------------Ҫ��û�ÿ���ɾ��
		}
	}
	//sort every line and pick up the second column as the maximum theta
	for (int i = 0; i < Popsize; i++)
	{
		maxFastSort(cosineVV[i], rvea_neighbor[i], Popsize, 2);
		acosVV[i] = acos(cosineVV[i][1]);//�������ҵ�����������Ӧ�ĽǶ�
	}
	for (int i = 0; i < Popsize; i++)
	{
		delete[] cosineVV[i];
		delete[] rvea_neighbor[i];
	}
	delete[] cosineVV;
	delete[] rvea_neighbor;

	/*delete[] Zmin;
	delete[] Zmax;*/
}

void MOEA_solver::multiply_boundary()
{
	for (int i = 0; i < Popsize; i++)
	{
		for (int j = 0; j < Nobj; j++)
		{
			rvea_weight[i][j] = rvea_weight_init[i][j];
			rvea_weight[i][j] = rvea_weight[i][j] * (curBoundmax[j] - curBoundmin[j]);
		}
	}
}

//GrEA
void MOEA_solver::fastNondominatedSort(individual* popsort, int len_p)
{
	int i, j, k;

	int** S = new int* [len_p];   //store the indices of solutions dominated by the i-th item of (*(popsort));
	for (i = 0; i < len_p; i++)
		S[i] = new int[len_p];
	int* N = new int[len_p];
	int* lenS = new int[len_p];

	for (i = 0; i < len_p; i++)
	{
		levelSize[i] = 0;
		N[i] = 0;
	}

	for (i = 0; i < len_p; i++)
	{
		lenS[i] = 0;
		for (j = 0; j < len_p; j++)
		{
			int isDominance = check_dominance(popsort[i], popsort[j], Nobj);
			if (isDominance == 1)
			{
				S[i][lenS[i]] = j;
				lenS[i] ++;
			}
			else if (isDominance == -1)
				N[i] ++;
		}
		if (N[i] == 0)
		{
			popsort[i].fitness = 0;
			levelF[0][levelSize[0]] = i;
			levelSize[0] ++;
		}
	}

	i = 0;
	while (levelSize[i] != 0)
	{
		levelSize[i + 1] = 0;
		for (j = 0; j < levelSize[i]; j++)
		{
			int p = levelF[i][j];
			for (k = 0; k < lenS[p]; k++)
			{
				int q = S[p][k];
				N[q] --;
				if (N[q] == 0)
				{
					popsort[q].fitness = i + 1;
					levelF[i + 1][levelSize[i + 1]] = q;
					levelSize[i + 1] ++;
				}
			}
		}
		i++;
	}

	for (i = 0; i < len_p; i++)
		delete[] S[i];

	delete[] S;
	delete[] N;
	delete[] lenS;
}

void MOEA_solver::tournament_Selection()
{
	int dominance_pa, dominance_g;
	int p, q;
	while (randval(0, 1) < 0.5)
	{
		p = irand(Popsize);
		do
		{
			q = irand(Popsize);
		} while (p != q);
		dominance_pa = check_dominance(pop_sel[p], pop_sel[q], 7);
		dominance_g = grid_dominance(p, q);
		if (dominance_pa == 1 || dominance_g)
			copy(pop_sel + q, pop_sel + p);
		else if (dominance_pa == -1 || dominance_g == -1)
			copy(pop_sel + p, pop_sel + q);
		else if (pop_sel[p].GCD < pop_sel[q].GCD)
			copy(pop_sel + q, pop_sel + p);
		else if (pop_sel[q].GCD < pop_sel[p].GCD)
			copy(pop_sel + p, pop_sel + q);
		else if ((irand(100) / 100) < 0.5)
			copy(pop_sel + q, pop_sel + p);
		else
			copy(pop_sel + p, pop_sel + q);
	}
}

void MOEA_solver::Grid_setting(individual* pop_set, int len)
{
	if (lb == nullptr) lb = new float[Nobj];
	if (d == nullptr) d = new float[Nobj];
	std::vector<float> ub(Nobj, 0.0f);

	calcBounds(pop_set, len);
	for (int i = 0; i < Nobj; i++)
	{
		lb[i] = curBoundmin[i];
		ub[i] = curBoundmax[i];
		if (curBoundmax[i] == curBoundmin[i])
		{
			d[i] = 1.0f;
			continue;
		}
		double exp = 1.0 / static_cast<double>(Nobj);
		int nint = static_cast<int>(pow(static_cast<double>(len), exp));
		if (nint <= 0) nint = 1;
		d[i] = 1.1f * (ub[i] - lb[i]) / nint;
	}

	for (int i = 0; i < len; i++)
		for (int j = 0; j < len; j++)
			GD[i][j] = 0;

	for (int i = 0; i < Nobj; i++)
		for (int j = 0; j < len; j++)
			G[i][j] = (pop_set[j].obj[i] - lb[i]) / d[i];

	for (int j = 0; j < len; j++)
		pop_candi[j].GCD = 0;
}

void MOEA_solver::GCD_calculation(bool flag, int length)
{
	individual** FI;
	if (flag)
	{
		FI = &pop_sel;
	}
	else
	{
		FI = &pop_candi;
	}
	// reset GCD before accumulation to avoid carrying stale values
	if (flag)
	{
		for (int i = 0; i < Popsize; i++)
			pop_sel[i].GCD = 0;
	}
	else
	{
		for (int i = 0; i < length; i++)
			pop_candi[i].GCD = 0;
	}
	// zero GD then fill
	for (int p = 0; p < length; p++)
		for (int q = 0; q < length; q++)
			GD[p][q] = 0;
	GD_set(length);
	int p, q;
	for (p = 0; p < length; p++)
	{
		for (q = 0; q < length; q++)
		{
			if (GD[p][q] < Nobj)
				(*FI)[p].GCD += (Nobj - GD[p][q]);
		}
	}

}

void MOEA_solver::GD_set(int length)
{
	for (int i = 0; i < length; i++)
	{
		for (int j = 0; j < length; j++)
		{
			for (int k = 0; k < Nobj; k++)
				GD[i][j] += abs(G[k][i] - G[k][j]);
		}
	}
}

void MOEA_solver::GCPD_calculation(int length)
{
	float GCPD_temp = 0.0;
	if (length == Popsize)
		for (int i = 0; i < Popsize; i++)
		{
			for (int j = 0; j < Nobj; j++)
				GCPD_temp += pow((pop_sel[i].obj[j] - lb[j] + G[j][i] * d[j]) / d[j], 2.0);
			pop_sel[i].GCPD = sqrt(GCPD_temp);
		}
	else
		for (int i = 0; i < length; i++)
		{
			for (int j = 0; j < Nobj; j++)
				GCPD_temp += pow((pop_candi[i].obj[j] - lb[j] + G[j][i] * d[j]) / d[j], 2.0);
			pop_candi[i].GCPD = sqrt(GCPD_temp);
		}
}

void MOEA_solver::Findout_best(int* FI, int length)
{
	if (length <= 0) return;
	pbest = 0;
	for (int i = 1; i < length; i++)
	{
		int idx_i = FI[i];
		int idx_best = FI[pbest];
		if (idx_i < 0 || idx_i >= length || idx_best < 0 || idx_best >= length) continue;
		if (pop_candi[idx_i].GR < pop_candi[idx_best].GR)
			pbest = i;
		else if (pop_candi[idx_i].GR == pop_candi[idx_best].GR)
		{
			if (pop_candi[idx_i].GCD < pop_candi[idx_best].GCD)
				pbest = i;
			else if (pop_candi[idx_i].GCD == pop_candi[idx_best].GCD)
			{
				if (pop_candi[idx_i].GCPD < pop_candi[idx_best].GCPD)
					pbest = i;
			}
		}
	}
	//delete []FI;
}

void MOEA_solver::GR_adjustment(int* candi_f, int levelsize)
{

	// Use levelsize to avoid overrunning Popsize-sized buffers when the last front is large.
	float* PD = new float[levelsize]();
	int* E_pbest = new int[levelsize]();
	int* G_pbest = new int[levelsize]();
	int* N_pbest = new int[levelsize]();
	pbest = 0;
	//int e_size = 0, g_size;
	for (int j = 0; j < levelsize; j++)
	{
		if (GD[candi_f[j]][candi_f[pbest]] == 0)
		{
			pop_candi[candi_f[j]].GR += (Nobj + 2);
			E_pbest[candi_f[j]] = 1;
			//E_pbest[e_size] = candi_f[j];
			//e_size++;
		}
		if (grid_dominance(candi_f[pbest], candi_f[j]))
		{
			pop_candi[candi_f[j]].GR += Nobj;
			G_pbest[candi_f[j]] = 1;
		}
		else if (E_pbest[candi_f[j]] == 0)
			PD[candi_f[j]] = 0;
		if (GD[candi_f[j]][candi_f[pbest]] < Nobj)
		{
			N_pbest[candi_f[j]] = 1;
		}
	}
	for (int j = 0; j < levelsize; j++)
	{
		if (N_pbest[candi_f[j]] && G_pbest[candi_f[j]] == 0 && E_pbest[candi_f[j]] == 0)
			if (PD[candi_f[j]] < (Nobj - GD[candi_f[j]][candi_f[pbest]]))
			{
				PD[candi_f[j]] = Nobj - GD[candi_f[j]][candi_f[pbest]];
				for (int r = 0; r < levelsize; r++)
					if (grid_dominance(candi_f[j], candi_f[r]) && (grid_dominance(candi_f[pbest], candi_f[r]) != 1 || E_pbest[candi_f[r]] != 1))
						if (PD[candi_f[r]] < PD[candi_f[j]])
							PD[candi_f[r]] = PD[candi_f[j]];
			}
		if (G_pbest[candi_f[j]] == 0 && E_pbest[candi_f[j]] == 0)
			pop_candi[candi_f[j]].GR += PD[candi_f[j]];
	}
	delete[] E_pbest;
	delete[] G_pbest;
	delete[] N_pbest;
	delete[] PD;
}

int MOEA_solver::grid_dominance(int a, int b)
{
	int i, flag1 = 0, flag2 = 0, dominance = 0;
	for (i = 0; i < Nobj; i++)
	{
		if (G[i][a] < G[i][b])
			flag1++;
		else if (G[i][a] > G[i][b])
			flag2++;
	}
	if (flag1 == 0 && flag2 > 0)
		dominance = -1;
	else if (flag1 > 0 && flag2 == 0)
		dominance = 1;
	return dominance;
}

void MOEA_solver::GrEA_EnvironmentalSelection()
{
	int i = 0, j;
	int index = 0;
	int length = 0;

	fastNondominatedSort(pop_all, fullSize2);
	while (index + levelSize[i] <= Popsize)
	{
		for (int j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}
	// if already filled or no next front, exit
	if (index >= Popsize || levelSize[i] == 0)
		return;
	int* candi_F = new int[levelSize[i]];
	for (int k = 0; k < levelSize[i]; k++)
		candi_F[k] = 0;
	length = levelSize[i];
	for (int k = 0; k < length; k++)
	{
		copy(pop_candi + k, pop_all + levelF[i][k]);
		candi_F[k] = k; // use local indices into pop_candi
	}
	Grid_setting(pop_candi, length);
	Initailization(i);
	while (index != Popsize)
	{
		Findout_best(candi_F, length);
		int sel_idx = candi_F[pbest];
		if (sel_idx < 0 || sel_idx >= length)
		{
			// fallback to first candidate if corrupted index
			sel_idx = 0;
		}
		copy(pop_sel + index, pop_candi + sel_idx);
		length--;
		// reset candidate index list to contiguous range [0, length)
		for (j = 0; j < length; j++)
			candi_F[j] = j;
		GCD_calculation(0, length);
		GR_adjustment(candi_F, length);
		index++;
	}
	delete[]candi_F;
}



//get the index-th point's lowest upper bound at the obit-th dimension
float MOEA_solver::getLowestUpperBound(individual* pp, int len, int index, int obit)
{
	int k, bound_length;
	float upperbound, value, threshold;
	float* tempbound;

	//the number of bounds;
	bound_length = 0;

	//this array is used to store the bound value of the j-the point
	tempbound = new float[len + 1];
	//threshold is the value of index-th point at obit-th dimension
	threshold = pp[index].obj[obit];

	for (k = 0; k < len; k++)
	{
		value = pp[k].obj[obit];
		if (value > threshold)
		{
			tempbound[bound_length] = value;
			bound_length++;
		}
	}
	tempbound[bound_length] = referencePoint[obit];

	upperbound = tempbound[0];
	for (k = 1; k < bound_length; k++)
		if (tempbound[k] < upperbound)
			upperbound = tempbound[k];

	delete[] tempbound;
	return upperbound;
}

float MOEA_solver::calculateArea_2D(individual* pp, int len, int noObjectives)
{
	int i;
	float diff1 = 0, diff2 = 0;
	float s_value = 0;

	heap_sort_descending(pp, len, 0, 0);

	for (i = 0; i < len; i++)
	{
		if (i == 0)
			diff1 = pp[i].obj[noObjectives - 2] - referencePoint[noObjectives - 2];
		else
			diff1 = pp[i].obj[noObjectives - 2] - pp[i - 1].obj[noObjectives - 2];

		diff2 = pp[i].obj[noObjectives - 1] - referencePoint[noObjectives - 1];

		s_value += fabs(diff1) * fabs(diff2);
	}
	return s_value;
}

int MOEA_solver::ReduceFront(individual* pp, int len, int noObjectives, float* slice_depth, int slice_number)
{
	int n = len;
	int i;
	float threshold = 0;

	for (i = 0; i < slice_number; i++)
		threshold += slice_depth[i];

	for (i = 0; i < n; i++)
	{
		if (fabs(referencePoint[noObjectives - 1] - pp[i].obj[noObjectives - 1]) <= threshold)
		{
			n--;
			swap(pp + i, pp + n);
			i--;
		}
	}
	return n;
}


float MOEA_solver::calculateHypervolume(individual* pp, int len, int noObjectives)
{
	float volume = 0;
	if (noObjectives < 3)
	{
		volume = calculateArea_2D(pp, len, noObjectives);
		return volume;
	}

	int n = len;
	int slice_number = 0;

	float* slice_depth = new float[n];

	while (n > 0)
	{
		int i;
		int temp_length = 1;
		int noNondominatedPoints;
		int isDominage_flag, isInSet_flag;

		float tempVolume = 0;
		float area, lowest_upperbound;


		if (noObjectives > 3)
			tempVolume = calculateHypervolume(pp, n, noObjectives - 1);

		heap_sort_descending(pp, n, noObjectives - 1, 0);

		copy(pop_temp + 0, pp + 0);

		lowest_upperbound = getLowestUpperBound(pp, len, 0, noObjectives - 1);

		slice_depth[slice_number] = fabs(pop_temp[0].obj[noObjectives - 1] - lowest_upperbound);

		if (noObjectives == 3)
		{
			//copy the useful points to the temp array
			for (i = 1; i < n; i++)
			{
				//pick the points which have the same value at the 3rd dimension
				if (pp[i].obj[noObjectives - 1] == pop_temp[0].obj[noObjectives - 1])
				{
					copy(pop_temp + temp_length, pp + i);
					temp_length++;
				}
			}

			isDominage_flag = 0;
			for (i = 1; i < n; i++)
			{
				if (check_dominance(pp[i], pp[0], noObjectives - 1) == 1)
				{
					isDominage_flag = 1;
					break;
				}
			}

			if (isDominage_flag == 1)
			{
				area = calculateArea_2D(pop_temp, temp_length, noObjectives - 1);
				tempVolume = area;
			}
			else
			{
				//pick the nondominated points at the first 'noObjectives - 1' dimensions
				noNondominatedPoints = FilterNondominatedSet(pp, n, noObjectives - 1);
				for (i = 0; i < noNondominatedPoints; i++)
				{
					//check whether the nondominated points are already in the temp array or not
					isInSet_flag = 0;
					for (int k = 0; k < temp_length; k++)
					{
						if (check_equality(pop_temp[k], pp[i], 1) == 1)
						{
							isInSet_flag = 1;
							break;
						}
					}

					if (isInSet_flag == 1)
						continue;
					else
					{
						copy(pop_temp + temp_length, pp + i);
						temp_length++;
					}
				}
				area = calculateArea_2D(pop_temp, temp_length, noObjectives - 1);
				tempVolume = area;
			}
		}

		tempVolume = slice_depth[slice_number] * tempVolume;
		slice_number++;

		//sum the slice volume
		volume += tempVolume;

		//cut the useless points
		n = ReduceFront(pp, n, noObjectives, slice_depth, slice_number);
	}
	delete[] slice_depth;
	return volume;
}

void MOEA_solver::updateR2Tensor(int Rindex, individual& pp)
{
	float rho = 1 + 1 / Hp;
	for (int k = 0; k < Popsize + 1; k++)
	{
		for (int j = 0; j < Popsize; j++)
		{
			if (k == Rindex)
			{
				int pointer = 0, i = 0;
				while (pointer < Popsize + 1)   //assume pop_all has N+1 valid item
				{
					if (pointer == Rindex)
						pointer++;
					R2Tensor[i][j][k] = (pop_all[pointer].obj_norm[0] - pp.obj_norm[0]) / DirectionV[j][0];
					for (int l = 1; l < Nobj; l++)
					{
						float g_2tch = (pop_all[pointer].obj_norm[l] - pp.obj_norm[l]) / DirectionV[j][l];
						if (g_2tch > R2Tensor[i][j][k])
							R2Tensor[i][j][k] = g_2tch;
					}
					if (R2Tensor[i][j][k] > 1e5)
						R2Tensor[i][j][k] = 1e5;
					//cout << "R2Tensor[" << i << "][" << j << "][" << k << "] = " << R2Tensor[i][j][k] << endl;
					pointer++;
					i++;
				}
				R2Tensor[Popsize][j][k] = abs(pp.obj_norm[0] - rho) / DirectionV[j][0];
				for (int l = 1; l < Nobj; l++)
				{
					float g_mtch = abs(pp.obj_norm[l] - rho) / DirectionV[j][l];
					if (g_mtch < R2Tensor[Popsize][j][k])
						R2Tensor[Popsize][j][k] = g_mtch;
				}
				if (R2Tensor[Popsize][j][k] > 1e5)
					R2Tensor[Popsize][j][k] = 1e5;
			}
			else if (k < Rindex)
			{
				R2Tensor[Rindex - 1][j][k] = (pp.obj_norm[0] - pop_all[Rindex].obj_norm[0]) / DirectionV[j][0];
				for (int l = 1; l < Nobj; l++)
				{
					float g_2tch = (pp.obj_norm[l] - pop_all[Rindex].obj_norm[l]) / DirectionV[j][l];
					if (g_2tch > R2Tensor[Rindex - 1][j][k])
						R2Tensor[Rindex - 1][j][k] = g_2tch;
				}
				if (R2Tensor[Rindex - 1][j][k] > 1e5)
					R2Tensor[Rindex - 1][j][k] = 1e5;
			}
			else   //k < Rindex
			{
				R2Tensor[Rindex][j][k] = (pp.obj_norm[0] - pop_all[Rindex].obj_norm[0]) / DirectionV[j][0];
				for (int l = 1; l < Nobj; l++)
				{
					float g_2tch = (pp.obj_norm[l] - pop_all[Rindex].obj_norm[l]) / DirectionV[j][l];
					if (g_2tch > R2Tensor[Rindex][j][k])
						R2Tensor[Rindex][j][k] = g_2tch;
				}
				if (R2Tensor[Rindex][j][k] > 1e5)
					R2Tensor[Rindex][j][k] = 1e5;
			}
		}
	}
}

void MOEA_solver::PopReplacement(int Rindex, individual& pp)
{
	for (int i = 0; i < Nvar; i++)
		pop_all[Rindex].x[i] = pp.x[i];
	for (int i = 0; i < Nobj; i++)
	{
		pop_all[Rindex].obj[i] = pp.obj[i];
		pop_all[Rindex].obj_norm[i] = pp.obj_norm[i];
	}

}

int MOEA_solver::findR2Worst()
{
	fastNondominatedSort(pop_all, Popsize + 1);
	int lastFront = 0;
	while (levelSize[lastFront] > 0)
		lastFront++;
	lastFront--;
	int M = levelSize[lastFront];
	float*** ExtractedTensor = new float** [M];
	for (int i = 0; i < M; i++)
	{
		ExtractedTensor[i] = new float* [Popsize];
		for (int j = 0; j < Popsize; j++)
			ExtractedTensor[i][j] = new float[M];
	}

	//extract T'
	for (int k = 0; k < M; k++)
	{
		for (int j = 0; j < Popsize; j++)
		{
			int i_ = 0, i = 0;
			while (i_ < M)
			{
				if (i_ == k)
					i_++;
				if (i_ >= M)
					break;
				ExtractedTensor[i][j][k] = R2Tensor[levelF[lastFront][i_]][j][levelF[lastFront][k]];
				i_++;
				i++;
			}
			ExtractedTensor[M - 1][j][k] = R2Tensor[Popsize][j][k];
		}
	}

	//calc R2HCA
	float* R2HCA = new float[M];

	for (int k = 0; k < M; k++)
	{
		float temp_sum = 0;
		for (int j = 0; j < Popsize; j++)
		{
			float min_v = ExtractedTensor[0][j][k];
			for (int i = 1; i < M; i++)
			{
				if (ExtractedTensor[i][j][k] < min_v)
					min_v = ExtractedTensor[i][j][k];
			}
			temp_sum += pow(min_v, Nobj);
		}
		R2HCA[k] = temp_sum / Popsize;
	}

	int theWorstInd = 0;
	float min_R2HCA = R2HCA[0];
	for (int i = 1; i < M; i++)
	{
		if (R2HCA[i] < min_R2HCA)
		{
			min_R2HCA = R2HCA[i];
			theWorstInd = i;
		}
	}

	for (int i = 0; i < M; i++)
	{
		for (int j = 0; j < Popsize; j++)
			delete[] ExtractedTensor[i][j];
		delete[] ExtractedTensor[i];
	}
	delete[] ExtractedTensor;
	delete[] R2HCA;

	return levelF[lastFront][theWorstInd];
}

void MOEA_solver::calcFitandNorm(individual* pp)
{
	pp->fitness = 0;
	for (int i = 0; i < Nobj; i++)
		pp->fitness += pp->obj_norm[i];

	pp->fit_Norm = 0;
	for (int i = 0; i < Nobj; i++)
		pp->fit_Norm += pp->obj_norm[i] * pp->obj_norm[i];
	pp->fit_Norm = sqrt(pp->fit_Norm);
}

float MOEA_solver::angle(individual& pp1, individual& pp2)
{
	float numerator = 0;
	for (int i = 0; i < Nobj; i++)
		numerator += pp1.obj_norm[i] * pp2.obj_norm[i];

	float angle = acos(abs(numerator / (pp1.fit_Norm * pp2.fit_Norm)));

	return angle;
}

float MOEA_solver::angleToExtreme(individual& pp, float* ExtremeV)
{
	float numerator = 0;
	for (int i = 0; i < Nobj; i++)
		numerator += pp.obj_norm[i] * ExtremeV[i];

	float angle = acos(abs(numerator / pp.fit_Norm));

	return angle;
}

void MOEA_solver::VaEA_environmentalSelection()
{
	int i, j, k;
	int index;
	float** extremeVector = new float* [Nobj];
	for (i = 0; i < Nobj; i++)
		extremeVector[i] = new float[Nobj];

	for (i = 0; i < Nobj; i++)
	{
		for (j = 0; j < Nobj; j++)
		{
			if (i == j)
				extremeVector[i][j] = 1;
			else
				extremeVector[i][j] = 0;
		}
	}

	calcBounds(pop_all, fullSize2);
	for (i = 0; i < fullSize2; i++)
	{
		ObjectiveNormalization(pop_all[i]);
		calcFitandNorm(pop_all + i);
	}

	fastNondominatedSort();

	i = 0;
	index = 0;
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}
	if (index < Popsize)
	{
		int sizeFl = levelSize[i];
		int sizeP = index;
		individual* Fl = allocate_memory_indArray(sizeFl);
		bool* flagFl = new bool[sizeFl];   //label whether the elements of Fl are added to pop_sel
		float* theta = new float[sizeFl];
		int* gamma = new int[sizeFl];
		for (j = 0; j < sizeFl; j++)
		{
			copy(Fl + j, pop_all + levelF[i][j]);
			flagFl[j] = false;
			theta[j] = 360;
			gamma[j] = -1;
		}

		if (sizeP == 0)   //pop_sel is empty
		{
			heap_sort_ascending(Fl, sizeFl, 0, 2);  //sort by fitness
			//find extreme solutions and insert to pop_sel
			for (j = 0; j < Nobj; j++)
			{
				int extreme_ind = -1;
				float min_angle = 360;
				for (k = 0; k < sizeFl; k++)
				{
					float cur_angle = angleToExtreme(Fl[k], extremeVector[j]);
					if (cur_angle < min_angle)
					{
						min_angle = cur_angle;
						extreme_ind = k;
					}
				}
				if (flagFl[extreme_ind] == false)
				{
					copy(pop_sel + sizeP, Fl + extreme_ind);
					flagFl[extreme_ind] = true;
					sizeP++;
					if (sizeP == Popsize)
						return;
				}
			}
			//insert the m solutions with the smallest fitness value to pop_sel
			for (j = 0; j < Nobj; j++)
			{
				if (flagFl[j] == false)
				{
					copy(pop_sel + sizeP, Fl + j);
					flagFl[j] = true;
					sizeP++;
					if (sizeP == Popsize)
						return;
				}
			}
		}

		while (sizeP < Popsize)
		{
			float max_angle = -1, min_angle = 360;
			int max_ind = -1, min_ind = -1;
			for (j = 0; j < sizeFl; j++)
			{
				if (flagFl[j] == false)
				{
					for (k = 0; k < sizeP; k++)
					{
						float cur_angle = angle(Fl[j], pop_sel[k]);
						if (cur_angle < theta[j])
						{
							theta[j] = cur_angle;
							gamma[j] = k;
						}
					}
					//find rho and miu
					if (theta[j] > max_angle)
					{
						max_angle = theta[j];
						max_ind = j;
					}
					else if (theta[j] < min_angle)
					{
						min_angle = theta[j];
						min_ind = j;
					}
				}
			}

			if (max_ind == -1)
				return;
			else   //add the individual in Fl with the maximum vector angles to pop_sel
			{
				copy(pop_sel + sizeP, Fl + max_ind);
				flagFl[max_ind] = true;
				sizeP++;
			}
			//update the angles of the elements in Fl to pop_sel
			for (j = 0; j < sizeFl; j++)
			{
				if (flagFl[j] == false)
				{
					float cur_angle = angle(Fl[j], Fl[max_ind]);
					if (cur_angle < theta[j])
					{
						theta[j] = cur_angle;
						gamma[j] = sizeP - 1;
					}
				}
			}


			if (min_ind != -1 && min_angle < (PI / 2) / (Popsize + 1) && Fl[min_ind].fitness < pop_sel[gamma[min_ind]].fitness)
			{
				copy(pop_sel + gamma[min_ind], Fl + min_ind);
				flagFl[min_ind] = true;

				//update the angles of the elements in Fl to pop_sel
				for (j = 0; j < sizeFl; j++)
				{
					if (flagFl[j] == false)
					{
						float cur_angle = angle(Fl[j], Fl[min_ind]);
						if (gamma[j] != gamma[min_ind])
						{
							if (cur_angle < theta[j])
							{
								theta[j] = cur_angle;
								gamma[j] = gamma[min_ind];
							}
						}
						else
							theta[j] = cur_angle;
					}
				}
			}

		}




		deallocate_memory_indArray(Fl, sizeFl);
		delete[] flagFl;
		delete[] theta;
		delete[] gamma;
	}

	for (i = 0; i < Nobj; i++)
		delete[] extremeVector[i];
	delete[] extremeVector;
}

void MOEA_solver::solutionUpdate_MOEADD()
{
	int i, j;
	int index;
	fastNondominatedSort();
	i = 0;
	index = 0;
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}

	if (index < Popsize)
	{
		int sizeFl = levelSize[i];
		int sizeP = index;
		individual* Fl = allocate_memory_indArray(sizeFl);
		if (sizeFl == 1)
		{
			Locate_worst();
			while (index + levelSize[i] <= Popsize)
			{
				for (j = 0; j < levelSize[i]; j++)
				{
					copy(pop_sel + index, pop_all + levelF[i][j]);
					index++;
				}
				i++;
			}
		}
		else if (levelSize[i] == 1)
		{
			while (index + levelSize[i] <= Popsize)
			{
				for (j = 0; j < levelSize[i]; j++)
				{
					copy(pop_sel + index, pop_all + levelF[i][j]);
					index++;
				}
				i++;
			}
		}
		Locate_worst();
		while (index + levelSize[i] <= Popsize)
		{
			for (j = 0; j < levelSize[i]; j++)
			{
				copy(pop_sel + index, pop_all + levelF[i][j]);
				index++;
			}
			i++;
		}
	}
}

void MOEA_solver::Locate_worst()
{
	int i, j;
	int index;
	i = 0;
	index = 0;
	int size = levelSize[i];
	float* Dis = new float[size];
	int* idx = new int[size];
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}

	crowdDistanceAssignment(i);
	for (j = 0; j < size; j++)
	{
		Dis[j] = pop_sel[levelF[i][j]].distance;
		idx[j] = levelF[i][j];
	}
	maxFastSort(Dis, idx, size, size);

	for (j = 0; j < Popsize - index; j++)
		copy(pop_sel + index + j, pop_all + idx[j]);

	delete[] Dis;
	delete[] idx;
}

float MOEA_solver::calcI1(individual* ind_a)
{
	int i, j;
	int k = 0;
	float* max_data;
	float* I = new float[Nobj];
	float I1 = 0;
	float* cha = new float[Nobj];
	float* temp = new float[Nobj];
	for (i = 0; i < Nobj; i++)
	{
		temp[i] = ind_a->obj[i];
	}
	for (i = 0; i < Nobj - 1; i++)
	{
		cha[k] = abs(temp[i] - temp[i + 1]);
		k++;
	}
	max_data = max_element(cha, cha + Nobj);
	for (i = 0; i < Nobj - 1; i++)
	{
		I[i] = exp(((-1) * max_data[i]));
	}
	for (i = 0; i < Nobj - 1; i++)
	{
		I1 += I[i];
	}
	return I1;

	delete[] I;
	delete[] cha;
	delete[] temp;
}

float MOEA_solver::calcI2(individual* ind_a)
{
	int i;
	int k = 0;
	float sum = 0;
	float* sd = new float[Nobj];
	float* temp = new float[Nobj];
	float I2 = 0;
	for (i = 0; i < Nobj; i++)
	{
		temp[i] = ind_a->obj[i];
	}
	for (i = 0; i < Nobj - 1; i++)
	{
		if (temp[i + 1] > temp[i])
		{
			sd[k] = temp[i + 1] - temp[i];
			k++;
		}
		else {
			sd[k] = 0;
			k++;
		}

	}
	for (i = 0; i < Nobj - 1; i++)
	{
		I2 += sd[i];
	}
	return I2;

	delete[] sd;
	delete[] temp;
}

void MOEA_solver::SRA_environmentalSelection(float pc)
{
	int sweepCounter, j;
	int k = 0;
	bool swapdone = false;
	for (sweepCounter = 0; sweepCounter < Popsize / 2; sweepCounter++)
	{
		for (j = 0; j < Popsize - 1; j++)
		{
			if (randval(0, 1) < pc)
			{
				if (calcI1(pop_all + j) > calcI1(pop_all + j + 1))
				{
					swap(pop_all + j, pop_all + j + 1);
					swapdone = true;
				}
			}
			else if (calcI2(pop_all + j) > calcI2(pop_all + j + 1))
			{
				swap(pop_all + j, pop_all + j + 1);
				swapdone = true;
			}
		}
		if (swapdone)
		{
			break;
		}
	}
}


void MOEA_solver::NicVariation()
{
	int T = max(4, int(ceil(Popsize * 0.2)));
	cout << T << endl;
	int i, j, k;
	float* x = new float[Popsize];
	int* idx = new int[Popsize];
	//float** c = new float* [Popsize];
	for (i = 0; i < Popsize; i++)
		for (j = 0; j < Nobj; j++)
			pop_all[i].obj_norm[j] = mapminmax(pop_all[i].obj[j], 0, 1);
	        cout << pop_all[i].obj_norm[j];
			cout << ' ' << endl;
	for (i = 0; i < Popsize; i++)
	{
		for (j = 0; j < Popsize; j++)
		{
			x[j] = EuclideanDistance(pop_all[i].obj_norm, pop_all[j].obj_norm, Nobj);
			idx[j] = j;
		}
		minFastSort(x, idx, Popsize, T);

		for (k = 0; k < T; k++)
			neighbor[i][k] = idx[k];
	}
	delete[] x;
	delete[] idx;

	int* IP_2 = new int[Popsize];
	vector<int> IP_1;
	for (i = 0; i < Popsize; i++)
	{
		IP_1[i] = i + 1;
	}
	for (i = 1; i <= Popsize; i++)
	{
		if (rand() < 0.8)
		{
			j = rand() % (T - 1 + 1) + 1;
			IP_2[i] = neighbor[i][j];
		}
		else
		{
			j = rand() % (Popsize - 1 - 1 + 1) + 1;
			IP_2[i] = j;
		}
	}

	//kλ����
	//int* k = new int[];
	vector<int> t;
	vector<int> m;
	vector<int> point;
	int count = 0;
	
	for (i = 0; i < Popsize; i++)
	{
		
		for (j = 0; j < Nvar * M; j++)
		{
			pop_new[i].bin[j] = pop_all[IP_1[i]].bin[j];
			if (pop_all[IP_2[i]].bin[j] != pop_all[i].bin[j])
			{
				t[count] = j;
				count++;
			}
		}
		if (count > 1)
		{
			int u = rand() % (count - 1 - 1 + 1) + 1;
			int* s = randperm(count, u);
			for (int r = 0; r < u; r++)
			{
				point[r] = t[s[r]];
				pop_new[r].bin[point[r]] = pop_all[IP_2[i]].bin[point[r]];
			}
		}
	}

	//mutation
	for (i = 0; i < Popsize; i++)
	{
		if (rand() < 0.2)
		{
			int* j1 = find1(pop_all[IP_2[i]].bin, Nvar * M);
			int* j2 = find0(pop_all[IP_2[i]].bin, Nvar * M);
			for (k = 0; k < sizeof(j1); k++)
			{
				if (rand() < 1 / (1 + sizeof(j1)))
				{
					pop_new[i].x[k] = 0;
				}
			}
			for (k = 0; k < sizeof(j2); k++)
			{
				if (rand() < 1 / (1 + sizeof(j2)))
				{
					pop_new[i].x[k] = 1;
				}
			}
		}
		else
		{
			for (int l = 0; l < Nvar; l++)
			{
				if (rand() < 1 / Nvar)
				{
					pop_new[i].x[l] = 1 - pop_new[i].x[l];
				}
			}
		}
	}

	for (i = 0; i < Popsize; i++)
	{
		copy(pop_all + Popsize + i, pop_new + i);
	}
	//get unique Offspring and individuals (function evaluated)
	///////////////
}

///
void MOEA_solver::EnvironmentalSelection()
{
	int i,j,k;
	///Get unique individuals in decision space
	float** Dist = new float* [Popsize*2];
	for (i = 0; i < Popsize*2; i++)
	{
		for (j = 0; j < Popsize*2 && j!=i ;j++)
		{
			Dist[i][j] = Manhattandistance(pop_all[i].x,pop_all[j].x,Nvar);
		}
		Dist[i][i] = 0;
	}
	int repeat_num=0,u,n,t=0;
	vector<int> outFlag(Popsize * 2, 0);
	for (i = 0; i < Popsize * 2; i++)
	{
		if (outFlag[i] != 0) continue;          //�Ѿ���������
		for (j = 0; j < Popsize * 2; j++)
		{
			if (outFlag[j] != 0) continue;       //�Ѿ���������
			//�ж��ظ�
			for (k = 0; k < Popsize * 2; k++)
			{
				if (pop_all[i].obj[k] != pop_all[j].obj[k]) break;
			}
			if (k == Popsize * 2)  //�ظ�
			{
				outFlag[i] = 1;//�ظ���i�б�Ǳ���, ������Ƕ���
				outFlag[j] = 2;//��j�б�Ƕ���
			}
		}

		for (u = 0; u < Popsize * 2; u++)
		{
			if (outFlag[u] != 0)
				repeat_num++;
		}
		vector<float> Diss(repeat_num, 0);

		if (repeat_num > 1)
		{
			for (u = 0; u < Nvar * M; u++)
				t += pop_all[i].bin[u];

			for (k = 0; k < repeat_num; k++) {
				for (u = 0; u < Popsize && outFlag[u] != 0; u++) {
					for (n = 0; n < Popsize && outFlag[n] != 0; n++)
						if (Diss[k] > Dist[u][n])
							Diss[k] = Dist[u][n];
				}
				Diss[k] = Dist[u][n] / 2 / t;
			}
			float threshold = 0.8 - 0.6 * (t - 1) / (Nvar * M - 1);
			
			vector<int> s(repeat_num, INF);
			int sum = 0;
			for (k = 0; k < repeat_num; k++) {
				if (Diss[k] < threshold) {
					s[u] = k;
					u++;
				}
					//
				else
					for (n = 0; n < Popsize * 2; n++) {
						copy(pop_all + n, pop_all + k);
						sum++;
					}
			}
			//for (k = 0; k < repeat_num; k++)
				int r = rand() % (u - 1);
			//ѡȡs[u]�㸴�Ƶ���Ⱥ�У�
				copy(pop_all + sum + 1, pop_all + s[u]);

				cout << "sum = " << sum << endl;

		}
		
	}

	//int i, j;
	int index;
	fastNondominatedSort();
	i = 0;
	index = 0;
	
	while (index + levelSize[i] <= Popsize)
	{
		for (j = 0; j < levelSize[i]; j++)
		{
			copy(pop_sel + index, pop_all + levelF[i][j]);
			index++;
		}
		i++;
	}
	crowdDistanceAssignment(i);

	//select last front
	if (index < Popsize)
	{
		int size = levelSize[i];
		float* Dis = new float[size];
		int* idx = new int[size];
		int* Div_Vert = new int[i];
		Div_Vert = { 0 };
		vector<int> k;
		int temp = INF;
		int n = 0;
		
		//crowdDistanceAssignment(i); //�ȼ�i���ӵ����
		for (j = 0; j < size; j++)
		{
			Dis[j] = pop_sel[levelF[i][j]].distance;
			idx[j] = levelF[i][j];
		}
		maxFastSort(Dis, idx, size, size); //����Dis��ֵ��distance���Ӵ�С��������µ�Dis[]��idx[]
		//
		for (j = 0; j < size; j++)
		{
			for (int r = 0; r < n; r++)
			{
				if(j!=k[r])
				{
					if (pop_sel[j].obj[1] == pop_all[i].obj[1])
					{
						Div_Vert[j]++;
					}
				}
			}
			
		}
		//��С��Div_Vert
		for (j = 0; j < i; j++)
		{
			if (Div_Vert[j] < temp)
			{
				temp = Div_Vert[j];
				k[n] = j;
				n++;
			}
		}
		//
		//add k 
		copy(pop_sel + index + 1, pop_all + k[n - 1]);
		index++;

		delete[] Dis;
		delete[] idx;
	}
}
///
float MOEA_solver::Manhattandistance(float* x1, float* x2, int len)
{
	float sum = 0;
	for (int i = 0; i < len; i++)
		sum += abs(x1[i] - x2[i]);
	return sum;
}

/*float** uniquee(float** a)
{
	int n,i,j,k;
	int number = 0;
	vector<int> repeat;
	//float** s = new float* [sizeof(a[0]) / sizeof(a[0][0])];
	//float** s = new float* [][sizeof(a[0]) / sizeof(a[0][0])] = { 0 };
	int rowsnum = sizeof(a) / sizeof(a[0]);
	int colsnum = sizeof(a[0]) / sizeof(a[0][0]);
	char outFlag[sizeof(a) / sizeof(a[0])] = { 0 };

	for (i = 0; i < rowsnum; i++)
	{
		if (outFlag[i] != 0) continue;          //�Ѿ���������
		for (j = 0; j < rowsnum; j++)
		{
			if (outFlag[j] != 0) continue;       //�Ѿ���������
			//�ж��ظ�
			for (k = 0; k < colsnum; k++)
			{
				if (a[i][k] != a[j][k]) break;
			}
			if (k == colsnum)  //�ظ�
			{
				outFlag[i] = 1;//�ظ���i�б�Ǳ���, ������Ƕ���
				outFlag[j] = 2;//��j�б�Ƕ���
			}
		}
	}
		int count = -1;
		for (i = 0; i < rowsnum; i++)
		{
			if (outFlag[i] == 1)
			{
				count++;
				for (j = 0; j < colsnum; j++)
				{
					s[count][j] = a[i][j];
				}
			}
		}
		return s;
}*/

float MOEA_solver::mapminmax(float x, float xmin, float xmax)
{
	if (xmax == xmin) return xmin;
	return (x - xmin) / (xmax - xmin) + xmin;
}

int* MOEA_solver::randperm(int n, int k)
{
	//vector<int> s;
	int* s = new int[k];
	vector<int> numbres;
	for (int i = 0; i < n; i++)
	{
		numbres.push_back(i);
	}
	std::random_shuffle(numbres.begin(), numbres.end());
	for (int j = 0; j < k; j++)
	{
		s[j] = numbres[j];
	}
	return s;
}

int* MOEA_solver::find1(int* s, int k)
{
	//vector<int> t;
	int* t = new int[k];
	int count = 0;
	for (int i = 0; i < sizeof(s); i++)
	{
		if (s[i] != 0)
		{
			t[count] = i;
			count++;
		}
	}
	return t;
}

int* MOEA_solver::find0(int* s, int k)
{
	int* t = new int[k];
	int count = 0;
	for (int i = 0; i < sizeof(s); i++)
	{
		if (s[i] == 0)
		{
			t[count] = i;
			count++;
		}
	}
	return t;
}

/////////////////////////////////////////////////////new list systemstically
void MOEA_solver::BCE()
{
	// Fallback to BCE2 pipeline while original BCE implementation remains unavailable
	BCE2();
}

void MOEA_solver::BCE2()
{
	maintainEP();
	NormalizeAll();
	EnvironmentalSelection1();
	matingSelection(1);
	//EnvironmentalSelection0();
	solutionUpdate0();
	solutionUpdate1();
}

void MOEA_solver::hypE()
{
	HypeMatingSelection(probM);
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	HypeEnvironmentalSelection(probM);
}

void MOEA_solver::IBEA()
{
	mergeOffspring();
	calcBounds(pop_all, fullSize);
	calcFitnessIndicator(1);
	IBEA_environmentalSelection();
	matingSelection(0);

	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	updateEP();
	maintainEP();
}

void MOEA_solver::DAEA()
{
	NicVariation();
	EnvironmentalSelection();

	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	updateEP();
	maintainEP();
}

void MOEA_solver::MOEAD()
{
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	updateEP();
	updateNP();
	maintainEP();
}

void MOEA_solver::NSGA()
{
	NSGA_matingSelection();
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	solutionUpdate();
	updateEP();
	maintainEP();
	}

void MOEA_solver::NSGA_III()
{
	fastNondominatedSort();
	NSGA_III_environmentalSelection();
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	solutionUpdate();
	updateEP();
	maintainEP();
}

void MOEA_solver::PICEAg()
{
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	merge_popall();
	goal_generator(1);
	jointG();
	Evaluation(pop_all, fullSize2);
	fitness_assignment();
	updateEP();
	obtainEP();
	maintainEP();
}

void MOEA_solver::GrEA()
{
	Fitness_assignment();
	tournament_Selection();
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	solutionUpdate();
	GrEA_EnvironmentalSelection();
	updateEP();
	maintainEP();
}

void MOEA_solver::RVEA(int maxgen)
{
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	updateEP();
	merge_popall();
	calcBounds(pop_all, fullSize2);
	reference_vector_guided_selection(maxgen);
	if ((eval_count / maxgen) > (float)(adaption_count / 10.0))
	{
		reference_vector_adaptation();
		adaption_count++;
	}
	maintainEP();
}

void MOEA_solver::R2HCA()
{
	individual child;
	allocate_memory_ind(&child);

	applyVariationOp(&child, 0, 1, Popsize + 1);

	EvaluFunc(child.x, child.obj, Nvar, Nobj);

	ObjectiveNormalization(child);
	eval_count++;

	int Rindex = findR2Worst();
	updateR2Tensor(Rindex, child);
	PopReplacement(Rindex, child);

	updateEP(child);
	maintainEP();

	deallocate_memory_ind(&child);
}

void MOEA_solver::VaEA()
{
	VaEA_environmentalSelection();
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	solutionUpdate();
	updateEP();
	maintainEP();
}

void MOEA_solver::MOEADD()
{
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	solutionUpdate_MOEADD();
	updateEP();
	maintainEP();
}

void MOEA_solver::SRA()
{
	SRA_environmentalSelection(sraPc);
	for (int i = 0; i < Popsize; i++)
		applyVariationOp(pop_new + i, i, 0, Popsize);
	Evaluation(pop_new, Popsize);
	updateEP();
	maintainEP();
}

std::string MOEA_solver::describeOperators(const std::string& alg_name_raw)
{
	std::string alg = alg_name_raw;
	std::transform(alg.begin(), alg.end(), alg.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });

	if (alg == "NSGA" || alg == "NSGA2")
		return "selection=fast-nondominated-sort+crowding; variation=SBX+polynomial-mutation (variationByNPC)";
	if (alg == "NSGA3" || alg == "NSGA-III" || alg == "NSGA_III")
		return "NSGA-III: reference-points+crowding; variation=SBX+polynomial-mutation (variationByNPC)";
	if (alg == "BCE" || alg == "BCE2")
		return "BCE: environmental-selection=BCE; variation=PC(promising)+NPC (SBX+PM)";
	if (alg == "MOEAD")
		return "MOEA/D: decomposition+Tchebycheff; variation=SBX+polynomial-mutation (variationByNPC)";
	if (alg == "IBEA")
		return "IBEA: indicator-based selection; variation=SBX+polynomial-mutation";
	if (alg == "GREA")
		return "GrEA: grid ranking; variation=SBX+polynomial-mutation";
	if (alg == "HYPE")
		return "HypE: hypervolume indicator; variation=SBX+polynomial-mutation";
	if (alg == "PICEAG")
		return "PICEA-g: goal vectors; variation=SBX+polynomial-mutation";
	if (alg == "RVEA")
		return "RVEA: reference vectors; variation=SBX+polynomial-mutation";
	if (alg == "R2HCA")
		return "R2HCA: R2 tensor; variation=SBX+polynomial-mutation";
	if (alg == "VAEA")
		return "VaEA: angle-based; variation=SBX+polynomial-mutation";
	if (alg == "MOEADD")
		return "MOEADD: decomposition+angle; variation=SBX+polynomial-mutation";
	if (alg == "SRA")
		return "SRA: reference angle; variation=SBX+polynomial-mutation";
	if (alg == "DAEA")
		return "DAEA: discrete encoding; variation=SBX+polynomial-mutation";

	return "variation=SBX+polynomial-mutation (variationByNPC)";
}











// ===== 研究用扩展（2026-10-14，仅本地研究版）：播种 =====
void MOEA_solver::seedIndividuals(const std::vector<std::vector<float>>& xs)
{
	int k = 0;
	for (const auto& v : xs)
	{
		if (k >= fullSize) break;
		for (int j = 0; j < Nvar; j++)
			pop_all[k].x[j] = j < (int)v.size() ? v[j] : 0.0f;
		EvaluFunc(pop_all[k].x, pop_all[k].obj, Nvar, Nobj);
		pop_all[k].fitness = 0;
		k++;
	}
	// 与 initialize() 末尾相同的方式重建外部档案
	EP.clear();
	int pcN = FilterNondominatedSet(pop_all, fullSize, Nobj);
	for (int i = 0; i < pcN; i++)
	{
		individual new_element;
		allocate_memory_ind(&new_element);
		copy(&new_element, pop_all + i);
		EP.push_back(new_element);
	}
}
