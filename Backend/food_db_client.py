import dotenv 
from urllib.parse import urljoin
from pathlib import Path
import logging
import requests
import pandas as pd
import numpy as np
import json
import os

class FoodDBClient:

    dotenv.load_dotenv("credentials.env")
    _usda_api_key = os.getenv("USDA_FOOD_KEY")
    base_url = "https://api.nal.usda.gov/fdc/v1/"
    foundation_foods_folder = Path("data/FoodData_Central_foundation_foods_csv_2025-04-24")
    fndds_foods_file = Path("data/2021-2023_FNDDS_Nutrient_Values.xlsx")

    # console prints when enabled
    debug_enabled = False

    # DataFrames that will be queried frequently
    #   For now, these are pretty small, so it's ok to store them like this. 
    #   In the future, it would probably be pertinent to consider an external database.

    @classmethod
    def get_food_by_id(cls, fdcId):
        """
        Takes a food id and returns the corresponding entry in the USDA foods database.

        Args: 
            fdcId (str): The food id to look up.
        
        Returns:
            Pandas.DataFrame: Dataframe containing the food, if it exists.
        """
        if isinstance(fdcId, str):
            if not fdcId.isnumeric():
                logger = logging.getLogger(__name__)
                logger.error(f"Invalid fdcId: {fdcId} - must be numeric")
                raise ValueError(f"fdcId must be numeric, got '{fdcId}'")
        
        url = urljoin(cls.base_url, f"food/{fdcId}")
        response = requests.get(url, params={"api_key" : cls._usda_api_key})
        
        if cls.debug_enabled:
            print(json.dumps(response.json(), indent=4))

        if response.status_code == 200:
            return pd.json_normalize(response.json())
        else:
            response.raise_for_status()

    @classmethod
    def get_all_nutrients(cls):
        """
        Retrieves a dataframe of all possible nutrients which can be associated with foods.

        Args:

        Returns:
            pd.DataFrame: A DataFrame of nutrient data
        """

        filePath = Path.joinpath(cls.foundation_foods_folder, "nutrient.csv")

        if cls.debug_enabled:
            print(f"Loaded all nutrients from {filePath}")

        return pd.read_csv(filePath)
    
    @classmethod
    def get_food_nutrients(cls, fdcId):
        """
        Returns a dataframe of the foodNutrient schema associated with a particular food.
        """
        filePath = Path.joinpath(cls.foundation_foods_folder, "food_nutrient.csv")
        
        # eventually, need to find a way to query this more efficiently, instead of loading the whole thing in.
        nutrients_df = pd.read_csv(filePath)

        if cls.debug_enabled:
            print(f"Loaded nutrients for fdcId {fdcId}")

        return nutrients_df[nutrients_df['fdc_id'] == fdcId]

    @classmethod 
    def get_fndds_foods(cls) -> pd.DataFrame:
        """
        Cleans and returns a dataframe of the FNDDS foods csv. 
        """
        print("get_fndds_foods: STARTING...")
        fndds_df = pd.read_excel(FoodDBClient.fndds_foods_file)

        # Clean column names: remove newlines, extra spaces, and replace special characters
        fndds_df.columns = (
            fndds_df.columns
            .str.replace('\n', ' ', regex=True)
            .str.replace(r'\s+', '_', regex=True)
            .str.strip()
            .str.replace('(', '', regex=False)
            .str.replace(')', '', regex=False)
            .str.replace('-', '_', regex=False)
            .str.replace(',', '', regex=False)
            .str.replace('/', '_', regex=False)
            .str.lower()
        )

        # Aggregate omega-3 fatty acids: 18:3, 20:5 n-3, 22:5 n-3, 22:6 n-3
        omega3_cols = ['18:3 g', '20:5 n-3 g', '22:5 n-3 g', '22:6 n-3 g']

        # Some columns may have slightly different names after cleaning
        matched_cols = [col for col in fndds_df.columns if any(omega in col for omega in omega3_cols)]
        fndds_df['omega3_total_g'] = fndds_df[matched_cols].sum(axis=1)

        # Drop columns with semicolons in their names (fatty acids)
        fatty_acid_cols = [col for col in fndds_df.columns if ':' in col]
        fndds_df = fndds_df.drop(columns=fatty_acid_cols)
        
        print("get_fndds_foods: ...DONE")
        return fndds_df

    @classmethod
    def clean_fndds_foods_for_solve(cls, fndds_df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes the DataFrame acquired from get_fndds_foods() and cleans the DataFrame for use 
        in the solver. This includes removing 0 calorie food and baby food, as well as changing
        nutritional values to be per 1g instead of per 100g of food. 

        Returns: 
            pd.DataFrame: The cleaned dataframe
        """
        print("clean_fndds_foods_for_solve: STARTING...")

        cleaned_df = fndds_df.copy()
        # remove zero-cal foods
        cleaned_df = cleaned_df[cleaned_df["energy_kcal"] > 0]
        # remove baby foods
        cleaned_df = cls.remove_baby_food_data(cleaned_df)
        # convert to per_g rather than per_100_g units
        nutrient_cols = cls.get_nutrient_cols(cleaned_df)
        cleaned_df[nutrient_cols] = cleaned_df[nutrient_cols] / 100

        print("clean_fndds_foods_for_solve: ...DONE")
        return cleaned_df
    
    @classmethod
    def remove_baby_food_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        unique_wweia_categories = sorted(df["wweia_category_description"].unique())
        keywords = ["baby", "infant", "toddler"]
        baby_food_categories = [cat for cat in unique_wweia_categories if any(k in cat.lower() for k in keywords)]
        new_df = df[~df["wweia_category_description"].isin(baby_food_categories)]
        return new_df

    @classmethod
    def get_nutrient_cols(cls, df: pd.DataFrame) -> list[str]:
        """
        Get the column names for all nutrients recorded in the table.
        """
        numeric_cols = df.select_dtypes(include=['float64','int64']).columns
        exclude_cols = ['food_code', 'wweia_category_number']
        nutrient_cols = [col for col in numeric_cols if col not in exclude_cols]
        return nutrient_cols