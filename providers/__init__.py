"""W1 endpoint roster. Stable IDs, as accepted by `bench run --endpoints`.
Provider A and B adapters live in private/providers/."""
from .clay import ClaySingle, ClayWaterfall

ADAPTERS = {a.name: a for a in (ClayWaterfall(), ClaySingle())}
