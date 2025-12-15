"""
Abstract base class for storage backends.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any


class StorageBackend(ABC):
    """
    Abstract base class for match data storage.

    Implementations should handle:
    - Saving match data (matches, maps, player stats)
    - Deduplication
    - Querying for last scraped data
    """

    @abstractmethod
    def save_match(self, match_data: Dict[str, Any]) -> bool:
        """
        Save a single match with all its data.

        Args:
            match_data: Complete match data including maps and player stats

        Returns:
            bool: True if saved successfully, False if duplicate or error
        """
        pass

    @abstractmethod
    def save_matches(self, matches: List[Dict[str, Any]]) -> int:
        """
        Save multiple matches (batch operation).

        Args:
            matches: List of match data dictionaries

        Returns:
            int: Number of matches successfully saved
        """
        pass

    @abstractmethod
    def match_exists(self, match_id: str) -> bool:
        """
        Check if a match already exists in storage.

        Args:
            match_id: HLTV match ID

        Returns:
            bool: True if match exists
        """
        pass

    @abstractmethod
    def get_last_scraped_date(self) -> Optional[datetime]:
        """
        Get the date of the most recently scraped match.

        Returns:
            datetime: Date of last scraped match, or None if no data
        """
        pass

    @abstractmethod
    def get_match_count(self) -> int:
        """
        Get total number of matches in storage.

        Returns:
            int: Total match count
        """
        pass

    @abstractmethod
    def get_scraped_match_ids(self) -> List[str]:
        """
        Get list of all scraped match IDs.

        Returns:
            list: List of match ID strings
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            dict: Storage statistics including counts and metadata
        """
        pass
