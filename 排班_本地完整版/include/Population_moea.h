#pragma once
//
//  Population.h
//  MOEA
//
//  Created by yunglynn on 17-12-14.
//  Copyright (c) 2017�� yunglynn. All rights reserved.
//
#include <random>
#include <iostream>
#include <fstream>
using namespace std;

#ifndef MOEA_Population_h
#define MOEA_Population_h
# define INF 1.0e14
# define EPS 1.0e-14
# define E  2.71828182845905
# ifndef PI
# define PI 3.14159265358979
# endif

typedef struct Individual_properties
{
    float* x;
    float* obj;
    float* obj_norm;
    int* bin;
    float fitness;
    float distance;    //store the crowdDistance in NSGA
    float fit_Norm;
    
    int GR;
    int GCD;
    float GCPD;
}individual;

class Population_moea
{
public:
    Population_moea();
    Population_moea(int h, bool r_level, int nn, int no, float lb, float ub, int pop_override = -1);
    virtual ~Population_moea();

public:
    individual* pop_all;
    individual* pop_sel;
    individual* pop_new;
    //GrEA
    individual* pop_candi;

    int H;
    bool rps_Dlevel;
    int hOutSize;  //size of the first level rps
    int Popsize;
    int EP_capability;
    int fullSize;
    int fullSize2;

    int Nvar;
    int Nobj;
    float Ubound;
    float Lbound;

public:
    void allocate_memory_ind(individual* ind);
    void deallocate_memory_ind(individual* ind);

    individual* allocate_memory_indArray(int size);
    void deallocate_memory_indArray(individual* ind, int size);

    individual* reallocate_memory_indArray(individual* ind, int old_size, int new_size);

    void copy(individual* ind_a, individual* ind_b);
    void swap(individual* ind_a, individual* ind_b);

    void heap_adjust_descending(individual* pp, int s, int len, int obit, int flag);
    void heap_sort_descending(individual* pp, int len, int obit, int flag);
    void heap_adjust_ascending(individual* pp, int s, int len, int obit, int flag);
    void heap_sort_ascending(individual* pp, int len, int obit, int flag);

    int check_dominance(individual& ind_a, individual& ind_b, int noObjectives);
    bool check_equality(individual& ind_a, individual& ind_b, int is_obj);

    int FilterNondominatedSet(individual* pp, int len, int noObjectives);

    void model_variable(int nn, int no, int h);
};

float moea_randval(float lb, float ub);
int moea_irand(int Range);
int moea_combination(int n, int m); //upper m, lower n --> c^m_n
float moea_EuclideanDistance(float* x1, float* x2, int len);
void moea_minFastSort(float* x, int* idx, int n, int m);
//void maxFastSort(float *x, int *idx, int n, int m);
template <typename T>
void maxFastSort(T* x, int* idx, int n, int m);
void moea_GuassianElimination(float* x, float** A, float* b, int N);
float moea_determinRadius(float** c, int size);
float moea_uniform();
float moea_gauss();

template <typename T>
void maxFastSort(T* x, int* idx, int n, int m)
{
    int i, j;
    double temp;
    int id;

    for (i = 0; i < m; i++)
    {
        for (j = i + 1; j < n; j++)
        {
            if (x[i] < x[j])
            {
                temp = x[i];
                x[i] = x[j];
                x[j] = temp;
                id = idx[i];
                idx[i] = idx[j];
                idx[j] = id;
            }
        }
    }
}

#endif
