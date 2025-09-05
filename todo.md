
# TO DO:
- [X] write clean_fndds_foods_for_solve( )
    - [ ] `clean_duplicates: bool` removes highly similar foods
    - [X] remove baby, toddler, infant food
    - [X] aggregate omega3 fatty acids
    - [X] when solving, remove 0 calorie foods ??
- [ ] 

- [X] aggregate list of FNDDS WWEIA category descriptions to a separate csv
- [ ] 

- [X] adjust solve() and main.py to take a list of nutrient parameters
- [ ] abstract main.py into a master() class instead of a script

# FUTURE 
- Integrate branded foods... will require cleaning and storing lots of different datasets
- Integrate pricing
    - May need to start with a heuristic
        - Map branded/foundational foods to their categories
        - Map those categories to an average price-per-gram dataset
            - BLS data?
- Basic: single-page frontend interface
    - To start, literally just a list of sliders and a display of the results

- Final: host website