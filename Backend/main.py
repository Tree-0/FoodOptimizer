import pandas as pd
import os, pathlib
from solver import Solver, SolverSettings
from food_db_client import FoodDBClient
from nutrition_constraints import NutrientConstraints

print("CALORIE OPTIMIZER V1")


BASE_DIR = pathlib.Path(__file__).resolve().parent  # folder containing main.py
food_file = BASE_DIR / "data" / "cleaned_fndds_nutrients.parquet"

# try to read from parquet file, otherwise create the cleaned DF for the first time
if os.path.exists(food_file):
    foods_df = pd.read_parquet(food_file)
    print(f"Loaded data from {food_file}")
else:
    print(f"Creating {food_file} for the first time...")
    foods_df = FoodDBClient.clean_fndds_foods_for_solve(FoodDBClient.get_fndds_foods())
    os.makedirs(os.path.dirname(food_file), exist_ok=True)
    foods_df.to_parquet(food_file)
    print(f"Data saved to {food_file}")


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

# display amount of each type of food we chose and total nutrient amounts from the solution
display_cols = ['main_food_description','amount_g'] + [f"{nutrient}_contrib" for nutrient in opt_nutrients]
print(chosen[display_cols])
print(totals)

print("\nSOLVER DONE")