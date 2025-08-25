import dotenv 
from urllib.parse import urljoin
from pathlib import Path
import logging
import requests
import pandas as pd
import numpy as np
import json

class FoodDBClient:

    _usda_api_key = dotenv.get_key("credentials.env", "USDA_FOOD_KEY")
    base_url = "https://api.nal.usda.gov/fdc/v1/"
    foundation_foods_folder = Path("data/foundation_foods_csv_20250424")

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

    
