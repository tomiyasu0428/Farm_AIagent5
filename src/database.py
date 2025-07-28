"""Database connection and initialization for MongoDB."""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from src.config import settings

logger = logging.getLogger(__name__)

# Global database instances
client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None


async def init_database():
    """Initialize MongoDB connection."""
    global client, database
    
    try:
        # Create MongoDB client
        client = AsyncIOMotorClient(settings.mongodb_uri)
        database = client[settings.mongodb_database]
        
        # Test connection
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB database: {settings.mongodb_database}")
        
        # Create indexes
        await create_indexes()
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


async def create_indexes():
    """Create necessary database indexes."""
    indexes_to_create = [
        # (collection_name, index_spec, options)
        ("farmers", "line_user_id", {"unique": True}),
        ("groups", "group_id", {"unique": True}),
        ("groups", "members.line_user_id", {}),
        ("fields", "farmer_line_id", {}),
        ("fields", "name", {}),
        ("fields", "field_code", {"unique": True, "sparse": True}),  # sparse for existing data
        ("tasks", [("field_id", 1), ("status", 1)], {}),
        ("tasks", "scheduled_date", {}),
        ("work_logs", [("user_id", 1), ("work_date", -1), ("category", 1)], {}),
        ("work_logs", [("user_id", 1), ("extracted_data.field_id", 1), ("work_date", -1)], {}),
        ("work_logs", [("user_id", 1), ("extracted_data.material_ids", 1)], {}),
        ("farm_data", [("field_id", 1), ("timestamp", -1)], {}),
        ("farm_data", "source_type", {}),
        ("agent_states", "thread_id", {"unique": True}),
        ("materials", "name", {}),
        ("crops", [("name", 1), ("category", 1)], {}),
    ]
    
    success_count = 0
    for collection_name, index_spec, options in indexes_to_create:
        try:
            collection = database[collection_name]
            await collection.create_index(index_spec, **options)
            success_count += 1
            logger.debug(f"Created index on {collection_name}: {index_spec}")
        except Exception as e:
            if "duplicate key" in str(e).lower() or "11000" in str(e):
                logger.warning(f"Duplicate key constraint on {collection_name}.{index_spec} - index may already exist or data conflicts")
            else:
                logger.warning(f"Failed to create index on {collection_name}.{index_spec}: {e}")
    
    # Try to create text indexes separately (they often fail)
    text_indexes = [
        ("work_logs", [("original_message", "text"), ("extracted_data.field_name", "text")]),
        ("materials", [("name", "text")]),
    ]
    
    for collection_name, index_spec in text_indexes:
        try:
            collection = database[collection_name]
            await collection.create_index(index_spec)
            success_count += 1
            logger.debug(f"Created text index on {collection_name}")
        except Exception as e:
            logger.warning(f"Failed to create text index on {collection_name}: {e}")
    
    logger.info(f"Database index creation completed: {success_count} indexes processed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    return database


async def close_database():
    """Close the database connection."""
    if client:
        client.close()
        logger.info("Database connection closed")