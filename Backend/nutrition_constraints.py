# file: nutrition_constraints.py
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Iterable, List, Tuple
import math

@dataclass
class NutrientConstraint:
    name: str = ""
    min_g: float = 0.0
    max_g: float = math.inf

    @classmethod
    def from_string(cls, input: str, valid_nutrients: Iterable=None):
        """
        Parses a line of text of the format `[Name],[min_g],[max_g]` into a NutrientConstraint.
        `max_g` can be assigned infinity (unbounded) with `-`.
        ## Examples:
        `'protein_g, 100, 250'`\n
        `'carbohydrate_g, 200, 400'`\n
        `'protein_g, 0, -'`
        """
        split = input.replace(' ', '').split(',')
        if len(split) != 3:
            raise ValueError("incorrect input, expected 3 elements in the form of [Name],[min_g],[max_g]")
        
        if split[1] == '-':
            min_g = 0.0
        else:
            min_g = float(split[1])

        if split[2] == '-':
            max_g = math.inf
        else:
            max_g = float(split[2])

        obj = NutrientConstraint(name=split[0], min_g=min_g, max_g=max_g)
        obj.validate(valid_nutrients)
        return obj

    def validate(self, valid_nutrients: Iterable=None):
        if self.name == "":
            raise ValueError("name must be non-empty")
        if valid_nutrients and self.name not in valid_nutrients:
            raise ValueError("name must be within the list of valid nutrients provided")
        if self.min_g < 0 or (self.max_g is not None and self.max_g < 0):
            raise ValueError("min_g and max_g must be non-negative")
        if self.max_g is not None and self.max_g < self.min_g:
            raise ValueError("max_g must be >= min_g")

class NutrientConstraints:
    """
    Container for nutrient constraints.

    - `allowed_nutrients` should be the canonical column names from the FNDDS dataset
    - All values are in the base unit in the dataset (e.g. kcal for energy, grams for protein).
    """
    def __init__(self, allowed_nutrients: Iterable[str] | None = None):
        self.allowed = set(allowed_nutrients) if allowed_nutrients is not None else None
        self.nutrients: dict[str, NutrientConstraint] = {}

    # convenience constructors
    @classmethod
    def from_dict(cls, payload: dict[str, tuple[float, float]], allowed_nutrients: Iterable[str] | None = None):
        """
        payload: { "protein_g": (min, max), "sodium_mg": (min, max) }
        max can be None or math.inf for no upper bound.
        """
        inst = cls(allowed_nutrients=allowed_nutrients)
        for nutrient, (mn, mx) in payload.items():
            inst.upsert(nutrient, mn, mx)
        return inst
    
    @classmethod
    def read_from_file(cls, file: str, valid_nutrients: Iterable=None):
        """
        file: str - the path to a text file containing rows of [name],[min_g],[max_g]
        to be parsed into NutrientConstraints.

        returns: 
            NutrientConstraints object
        """
        inst = NutrientConstraints()
        with open(file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                nc = NutrientConstraint.from_string(line)
                inst.nutrients[nc.name] = nc
        return inst


    def to_dict(self) -> Dict[str, Tuple[float, float]]:
        return {k: (v.min_g, (v.max_g if v.max_g != math.inf else None)) for k, v in self.nutrients.items()}

    # mutation
    def upsert(self, nutrient: str, min_g: float = 0.0, max_g: Optional[float] = None):
        if self.allowed is not None and nutrient not in self.allowed:
            raise ValueError(f"'{nutrient}' is not in allowed nutrients")
        if max_g is None:
            max_val = math.inf
        else:
            max_val = float(max_g)
        nc = NutrientConstraint(min_g=float(min_g), max_g=max_val)
        nc.validate()
        self.nutrients[nutrient] = nc

    def remove(self, nutrient: str):
        self.nutrients.pop(nutrient, None)

    def clear(self):
        self.nutrients.clear()

    def validate_against_columns(self, columns: Iterable[str]) -> None:
        """Ensure all constraints refer to available columns; useful early validation."""
        cols = set(columns)
        missing = [n for n in self.nutrients.keys() if n not in cols]
        if missing:
            raise KeyError(f"Constraints reference missing columns: {missing}")