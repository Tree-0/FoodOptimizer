import math
import pandas as pd
from dataclasses import dataclass
from ortools.linear_solver import pywraplp
from nutrition_constraints import NutrientConstraints
from typing import Iterable

@dataclass
class SolverSettings:
    nutrition_constraints: NutrientConstraints
    nutrients_to_optimize: Iterable[str] 
    max_qty_per_food: float = None
    objective_type: str = "min"

class Solver:
    def __init__(self):
        pass

    def solve(self, df:pd.DataFrame, settings: SolverSettings) -> tuple[pd.DataFrame, dict[str,float]]:
        """
        ## Arguments
        `df: pd.DataFrame`
            - Must contain columns whose names match the names of all nutrients in the provided `nutrition_constraints` object.\n
        `nutrition_constraints`: NutritionConstraints object containing minimum maximum values for selected nutrients.\n
        `max_qty_per_food`: optional upper bound in grams for any chosen single food (if None, unbounded)\n
        ## Returns: 
            - tuple(selected_foods_df, totals_dict)
        """
        print("solve: STARTING...")

        nutrition_constraints = settings.nutrition_constraints
        nutrients_to_optimize = settings.nutrients_to_optimize
        max_qty_per_food = settings.max_qty_per_food
        objective_type = settings.objective_type

        if len(nutrition_constraints.nutrients) == 0:
            raise ValueError("No constraints in nutrition_constraints object, nothing to solve")
        
        if len(nutrients_to_optimize) == 0:
            raise ValueError("No nutrients to were given to optimize for")

        # Check that nutrition constraints are for valid nutrient types that exist in df
        data = df.copy()
        for col in (list(nutrition_constraints.nutrients.keys()) + nutrients_to_optimize):
            if col not in df.columns:
                raise ValueError(f"{col} is not present in the dataframe")

        n = len(data)
        if n == 0:
            raise ValueError("No foods (rows) in dataframe")

        # create solver
        solver = pywraplp.Solver.CreateSolver('GLOP')   # continuous LP solver
        if solver is None:
            raise RuntimeError("GLOP solver unavailable")
        inf = solver.infinity()

        # Create decision variables and keep stable map to foods (use food_code if present)
        var_list = []
        var_ids = []
        for i in range(n):
            ub = max_qty_per_food if max_qty_per_food is not None else inf
            fid = str(data.iloc[i]['food_code'])
            var = solver.NumVar(0.0, ub, f"x_{fid}")
            var_list.append(var)
            var_ids.append(fid)

        # Build coefficient arrays for all relevant nutrients (constraints + objective)
        coeff_arrays = {}
        all_nutrients = set(list(nutrition_constraints.nutrients.keys()) + nutrients_to_optimize)
        for nutrient in all_nutrients:
            coeff_arrays[nutrient] = data[nutrient].to_numpy() # np array length n
            
        # Add constraints: lb <= sum_i coeff_ij * x_i <= ub, FORALL j in NUTRIENTS
        for nutrient, bounds in nutrition_constraints.nutrients.items():
            # support bounds being object-like with min_g/max_g or tuple/dict
            lb = getattr(bounds, 'min_g', None)
            ub = getattr(bounds, 'max_g', None)
            
            # fallback if bounds are dict-like or tuple-like can be added as needed
            if lb is None:
                lb = 0.0
            if ub is None or (isinstance(ub, float) and math.isinf(ub)):
                ub_val = inf
            else:
                ub_val = float(ub)
            c = solver.Constraint(float(lb), ub_val)
            coeffs = coeff_arrays[nutrient]
            for i, var in enumerate(var_list):
                c.SetCoefficient(var, float(coeffs[i]))

        # Objective: linear combination of nutrients_to_optimize (default: equal weight)
        # objective_coefs[i] = sum_k weight_k * coeff_arrays[nutrient_k][i]
        objective = solver.Objective()
        # equal weights
        weights = {nut: 1.0 for nut in nutrients_to_optimize}
        for i, var in enumerate(var_list):
            coef = 0.0
            for nut in nutrients_to_optimize:
                coef += float(weights.get(nut, 1.0)) * float(coeff_arrays[nut][i])
            objective.SetCoefficient(var, coef)

        if objective_type in ["min", "minimize", "minimization"]:
            objective.SetMinimization()
        elif objective_type in ["max", "maximize", "maximization"]:
            objective.SetMaximization()
        else:
            raise ValueError(f"Unrecognized objective_type '{settings.objective_type}'")

        # Solve
        status = solver.Solve()
        if status != pywraplp.Solver.OPTIMAL:
            if status == pywraplp.Solver.INFEASIBLE:
                raise RuntimeError("Problem infeasible: cannot meet nutrition constraints with available foods.")
            else:
                raise RuntimeError(f"Solver finished with status {status}")

        # Extract solution amounts
        amounts = [v.solution_value() for v in var_list]
        data['amount_g'] = amounts

        # Compute contribution columns for each constrained nutrient
        for nutrient in all_nutrients:
            data[f"{nutrient}_contrib"] = data['amount_g'] * data[nutrient]

        # energy contribution (kcal)
        data['energy_kcal_contrib'] = data['amount_g'] * data['energy_kcal']

        # filter tiny numeric noise -> selected
        eps = 1e-9
        chosen_foods = data[data['amount_g'] > eps].copy().reset_index(drop=True)

        # Totals
        totals: dict[str, float] = {}
        totals['num_items_chosen'] = int((chosen_foods['amount_g'] > 0).sum())
        totals['objective_value'] = float(objective.Value())
        totals['total_energy_kcal'] = float((data['energy_kcal_contrib']).sum())
        # totals for each nutrient in constraints & objective
        for nutrient in all_nutrients:
            totals[f"total_{nutrient}"] = float(data[f"{nutrient}_contrib"].sum())

        # attach some diagnostics to returned df (optional)
        chosen_foods.attrs['solver_status'] = 'OPTIMAL'
        chosen_foods.attrs['objective_value'] = totals['objective_value']

        print("solve: ...DONE")
        return chosen_foods, totals
