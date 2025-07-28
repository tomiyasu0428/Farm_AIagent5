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
    try:
        # Farmers collection indexes
        await database.farmers.create_index("line_user_id", unique=True)
        
        # Fields collection indexes
        await database.fields.create_index("farmer_line_id")
        await database.fields.create_index("name")
        
        # Tasks collection indexes
        await database.tasks.create_index([("field_id", 1), ("status", 1)])
        await database.tasks.create_index("scheduled_date")
        
        # Farm data collection indexes
        await database.farm_data.create_index([("field_id", 1), ("timestamp", -1)])
        await database.farm_data.create_index("source_type")
        
        # Agent states collection indexes
        await database.agent_states.create_index("thread_id", unique=True)
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    return database


async def close_database():
    """Close the database connection."""
    if client:
        client.close()
        logger.info("Database connection closed")