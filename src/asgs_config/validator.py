import logging
import requests
from typing import Optional, Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class ActiveStormValidator:
    """
    Validates storm names and numbers against current active storms from NHC.
    """

    DEFAULT_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"

    def __init__(self, url: str = DEFAULT_URL):
        """
        Initializes the validator by fetching data from the specified URL.
        """
        self.url = url
        self._active_storms: List[Dict] = []
        self._unvalidated_mode = False
        self._fetch_data()

    def _fetch_data(self) -> None:
        """
        Fetches and parses the JSON payload from the NHC endpoint.
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self._active_storms = data.get("activeStorms", [])
            self._unvalidated_mode = False
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.warning(f"Failed to fetch or parse NHC data from {self.url}: {e}")
            self._active_storms = []
            self._unvalidated_mode = True

    @property
    def active_storms(self) -> List[Dict]:
        """
        Returns the list of active storms.
        """
        return self._active_storms

    @property
    def unvalidated_mode(self) -> bool:
        """
        Returns True if the class failed to fetch NHC data, False otherwise.
        """
        return self._unvalidated_mode

    def is_storm_number_active(self, storm_number: str) -> bool:
        """
        Checks if a given storm number exists in the active storms data.
        The storm number is the 'id' field in the storm dictionary (e.g., 'al062023').
        Returns True if unvalidated_mode is True.
        """
        if self.unvalidated_mode:
            return True
        
        search_id = storm_number.lower()
        for storm in self._active_storms:
            if storm.get("id", "").lower() == search_id:
                return True
        return False

    def get_storm_number_by_name(self, storm_name: str) -> Optional[str]:
        """
        Checks if a given storm name exists in the active storms data.
        Returns the corresponding 'id' as a string if found.
        Returns None if not found or if unvalidated_mode is True.
        """
        if self.unvalidated_mode:
            return None

        search_name = storm_name.upper()
        for storm in self._active_storms:
            if storm.get("name", "").upper() == search_name:
                return storm.get("id")
        return None

    def get_storm_data(self, identifier: str) -> Optional[Dict]:
        """
        Retrieves the dictionary of a storm by its name or ID.
        Returns None if not found or if unvalidated_mode is True.
        """
        if self.unvalidated_mode:
            return None

        search_id = identifier.lower()
        search_name = identifier.upper()

        for storm in self._active_storms:
            if storm.get("id", "").lower() == search_id or storm.get("name", "").upper() == search_name:
                return storm
        
        return None

    def get_storm_key(self, identifier: str, key: str) -> Optional[Any]:
        """
        Queries a specific key from a storm's dictionary by its name or ID.
        Returns None if the storm or key is not found or if unvalidated_mode is True.
        """
        if self.unvalidated_mode:
            return None

        search_id = identifier.lower()
        search_name = identifier.upper()

        for storm in self._active_storms:
            if storm.get("id", "").lower() == search_id or storm.get("name", "").upper() == search_name:
                return storm.get(key)
        
        return None
