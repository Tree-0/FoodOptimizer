import requests
import dotenv
import pandas as pd

url = "https://api.nal.usda.gov/fdc/v1/foods/list"
_api_key = dotenv.get_key("credentials.env", "USDA_FOOD_KEY")

# get list of branded / basic foundational foods, sorted by name
response = requests.get(url, params={
    "api_key":_api_key,
    "dataType":["Branded", "Foundation"],
    "sortBy":"dataType.keyword"
})

if response.status_code == 200:
    foods_data = response.json()
    foods_df = pd.DataFrame(foods_data)
    print(foods_df.head(50))
    print(f"Total records: {len(foods_df)}")
else:
    print(f"Error: {response.status_code} - {response.text}")

#print(response.content)