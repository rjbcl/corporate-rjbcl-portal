import requests #type: ignore
from django.core.cache import cache #type: ignore
from django.conf import settings #type: ignore
import logging

logger = logging.getLogger(__name__)

class GroupAPIService:
    """Service to fetch and cache groups from corporate API"""
    
    CACHE_KEY = 'corporate_groups_data'
    CACHE_TTL = 86400  # 24 hours
    API_ENDPOINT = f"{settings.CORPORATE_API_BASE_URL}/groups/"
    
    @classmethod
    def fetch_groups_from_api(cls):
        """Fetch all groups from the API with pagination"""
        all_groups = []
        url = cls.API_ENDPOINT
        
        try:
            while url:
                response = requests.get(url, timeout=settings.CORPORATE_API_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                # Extract only group_id and group_name
                for group in data.get('results', []):
                    all_groups.append({
                        'groupid': group.get('group_id'),
                        'groupname': group.get('group_name')
                    })
                
                # Get next page URL
                url = data.get('next')
            
            logger.info(f"Successfully fetched {len(all_groups)} groups from API")
            return all_groups
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch groups from API: {str(e)}")
            raise
    
    @classmethod
    def get_groups(cls, force_refresh=False):
        """
        Get groups from cache or API
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
        
        Returns:
            List of dicts with 'groupid' and 'groupname'
        """
        if not force_refresh:
            # Try to get from cache first
            cached_groups = cache.get(cls.CACHE_KEY)
            if cached_groups is not None:
                logger.info(f"Retrieved {len(cached_groups)} groups from cache")
                return cached_groups
        
        # Cache miss or force refresh - fetch from API
        logger.info("Cache miss or force refresh - fetching groups from API")
        groups = cls.fetch_groups_from_api()
        
        # Store in cache
        cache.set(cls.CACHE_KEY, groups, cls.CACHE_TTL)
        
        return groups
    
    @classmethod
    def refresh_cache(cls):
        """Manually refresh the cache"""
        return cls.get_groups(force_refresh=True)
    
    @classmethod
    def clear_cache(cls):
        """Clear the groups cache"""
        cache.delete(cls.CACHE_KEY)
        logger.info("Groups cache cleared")