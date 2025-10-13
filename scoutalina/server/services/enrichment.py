"""Data enrichment service.

TODO:
- Geocode and reverse geocode properties
- Pull external data (schools, crime, comps) as configured
"""

from typing import Dict, Any


def enrich_property(raw_property: Dict[str, Any]) -> Dict[str, Any]:
    # TODO: implement enrichment pipeline
    return {**raw_property, "enriched": True}


