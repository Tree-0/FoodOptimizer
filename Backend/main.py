import pandas as pd
import os, pathlib
from solver import Solver, SolverSettings
from food_db_client import FoodDBClient
from nutrition_constraints import NutrientConstraints

print("CALORIE OPTIMIZER V1")

foods_df: pd.DataFrame = FoodDBClient.clean_fndds_foods_for_solve(FoodDBClient.get_fndds_foods())
nutrient_columns: list[str] = FoodDBClient.get_nutrient_cols(foods_df)

print("valid nutrient types: ")
print(nutrient_columns)

file: str = os.path.abspath(input('Enter a filename with your nutrient and energy constraints> '))
print(f"found {file}")
constraints = NutrientConstraints.read_from_file(file, nutrient_columns)

opt_type = ""
while True:
    opt_type = input('Input whether you would like to minimize ("min") or maximize ("max") select nutrients> ').strip()
    if opt_type.lower() in ["min","max","minimize","maximize","minimization","maximization"]:
        break
    else:
        print("Invalid optimization type. Enter 'min' or 'max'")

opt_nutrients_input = ""
opt_nutrients = []
while True:
    opt_nutrients_input = input('Enter the nutrient types you would like to optimize, or "done" to finish> ')
    if opt_nutrients_input.lower() == "done":
        break
    elif opt_nutrients_input.strip() in nutrient_columns:
        opt_nutrients.append(opt_nutrients_input.strip())
    else:
        print("invalid nutrient type.")
        
max_g_input = input('Input the maximum grams of one food you are willing to eat (g)> ')
max_g_per_food:int = None if max_g_input in ["none","inf","-"] else int(max_g_input)

try:
    solver_settings = SolverSettings(constraints, opt_nutrients, max_g_per_food, opt_type)
except:
    print("Sorry twin you're asking for the impossible")

chosen, totals = Solver().solve(foods_df, solver_settings)

# drop any existing description column (no error if it doesn't exist)
#chosen = chosen.drop(columns=['main_food_description'], errors=True)

print(chosen[['main_food_description','amount_g','protein_g_contrib','carbohydrate_g_contrib','energy_kcal_contrib','total_fat_g_contrib']])

print(totals)

print("\nSOLVER DONE")