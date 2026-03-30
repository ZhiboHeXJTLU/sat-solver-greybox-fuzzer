#ifndef SAT_SAT_H
#define SAT_SAT_H

#include <stdio.h>
#include <stdlib.h>
#include "vector.h"
#include "var.h"
#include "parser.h"
#include "debugPrinter.h"
#include "queue.h"
#include "clause.h"

// --- BECAUSE C
#define max(X, Y)  ((X) > (Y) ? (X) : (Y))

#define VARDECAY 1
#define VARINC 1

extern V cnf;

// --- Propagation
extern V *watchers;
extern V *undos;
extern Q propagationQ;

// --- Ordering

extern int *activity;
extern double var_inc;
extern double var_decay;

// --- Assignments
extern unsigned int numberOfLiterals;
extern unsigned int numberOfClauses;
extern bool *assignments;
extern V trail;
extern unsigned int *trail_lim;
extern unsigned int trail_lim_size;
extern Var lastAssignedVar;
extern bool lastAssignedValue;

// --- Backtrack and learning
extern C *reason;
extern int rootLevel;
extern V learnts;
extern Var lastDecisionUndone;

// --- Decision level
extern int *level;

// --- Solver Functions
bool value(Var p);

bool conflict(V formula);

bool allVarsAssigned();

unsigned int selectVar();

bool decide(unsigned int id);

void addToWatchersOf(C clause, Var p);

void change_decision(unsigned int assigned);

void simplifyClause(V clause, V unitVars);

V watchersOf(Var p);

void undoOne();

C propagate();

void printAssignments();

int solve(V formula);

bool enqueue(Var p, C from);

int currentDecisionLevel();

void initializeAssigments();

void varBumpActivity(Var v);

void varDecayActivity();

void varRescaleActivity();

#endif //SAT_SAT_H
