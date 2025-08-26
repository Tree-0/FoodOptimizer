from ortools.linear_solver import pywraplp
import pandas as pd

class Solver:
    def __init__(self):
        pass

    def solve(self, df: pd.DataFrame, min_protein: float, max_qty_per_item: float = None):
        """
        df must contain these columns:
          - 'energy_kcal' (calories per 100 g)
          - 'protein_g' (protein grams per 100 g)
        min_protein: required total protein in grams (g)
        max_qty_per_item: optional upper bound in grams for any single food (if None, unbounded)
        Returns: (selected_rows_df, totals_dict)
        """
        if min_protein < 0:
            raise ValueError("min_protein must be nonnegative")

        # copy and coerce numeric types
        data = df.copy()
        if 'energy_kcal' not in data.columns or 'protein_g' not in data.columns:
            raise KeyError("DataFrame must contain 'energy_kcal' and 'protein_g' columns")

        data['energy_per_g'] = pd.to_numeric(data['energy_kcal'], errors='coerce') / 100.0
        data['protein_per_g'] = pd.to_numeric(data['protein_g'], errors='coerce') / 100.0

        # drop rows with no useful info
        data = data.dropna(subset=['energy_per_g', 'protein_per_g']).reset_index(drop=True)
        n = len(data)
        if n == 0:
            raise ValueError("No usable foods after coercion")

        # create solver
        solver = pywraplp.Solver.CreateSolver('GLOP')   # continuous LP solver
        if solver is None:
            raise RuntimeError("GLOP solver unavailable")

        inf = solver.infinity()

        # create decision variables x_i = grams of food i
        vars = []
        for i in range(n):
            ub = max_qty_per_item if max_qty_per_item is not None else inf
            x = solver.NumVar(0.0, ub, f'x_{i}') # TODO: Create a map or rename these with the information in the DF
            vars.append(x)

        # protein constraint: sum_i protein_per_g_i * x_i >= min_protein
        protein_ct = solver.Constraint(min_protein, inf)
        for i, x in enumerate(vars):
            protein_ct.SetCoefficient(x, float(data.at[i, 'protein_per_g']))

        # objective: minimize total calories = sum_i energy_per_g_i * x_i
        objective = solver.Objective()
        for i, x in enumerate(vars):
            objective.SetCoefficient(x, float(data.at[i, 'energy_per_g']))
        objective.SetMinimization()

        # solve
        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL:
            if status == pywraplp.Solver.INFEASIBLE:
                raise RuntimeError("Problem infeasible: cannot reach protein requirement with available foods.")
            else:
                raise RuntimeError(f"Solver finished with status {status}")

        # extract solution
        amounts = [v.solution_value() for v in vars]
        data['amount_g'] = amounts

        # filter tiny numeric noise
        eps = 1e-9
        chosen = data[data['amount_g'] > eps].copy()

        totals = {
            'total_energy_kcal': float((data['energy_per_g'] * data['amount_g']).sum()),
            'total_protein_g': float((data['protein_per_g'] * data['amount_g']).sum()),
            'num_items_chosen': int((data['amount_g'] > eps).sum())
        }

        # return chosen items and totals
        return chosen, totals
