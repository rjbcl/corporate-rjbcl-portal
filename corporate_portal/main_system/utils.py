from django.core.cache import cache #type: ignore
from django.conf import settings #type: ignore
from django.db import DatabaseError #type: ignore
import logging

logger = logging.getLogger(__name__)

class GroupAPIService:
    """Service to fetch and cache groups from database"""
    
    CACHE_KEY = 'corporate_groups_data'
    CACHE_TTL = 86400  # 24 hours
    
    @classmethod
    def fetch_groups_from_db(cls):
        """Fetch all groups from the database"""
        from api_corporate.models import GroupInformation
        
        try:
            # Query all groups from company_external database
            groups_queryset = GroupInformation.objects.using('company_external').all()
            
            # Convert to list of dicts with groupid and groupname
            all_groups = []
            for group in groups_queryset:
                all_groups.append({
                    'groupid': group.group_id,
                    'groupname': group.group_name
                })
            
            logger.info(f"Successfully fetched {len(all_groups)} groups from database")
            return all_groups
            
        except DatabaseError as e:
            logger.error(f"Failed to fetch groups from database: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching groups: {str(e)}")
            raise
    
    @classmethod
    def get_groups(cls, force_refresh=False):
        """
        Get groups from cache or database
        
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
        
        # Cache miss or force refresh - fetch from database
        logger.info("Cache miss or force refresh - fetching groups from database")
        groups = cls.fetch_groups_from_db()
        
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