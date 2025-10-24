"""
Check MongoDB Schema Validators
This script checks what validators are configured in MongoDB
"""

import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database.config import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_validators():
    """Check collection validators"""
    db_manager = DatabaseManager()
    db = db_manager.db
    
    logger.info("\n" + "="*80)
    logger.info("📋 MONGODB SCHEMA VALIDATORS")
    logger.info("="*80 + "\n")
    
    # Check video_file collection
    logger.info("📁 video_file collection:")
    logger.info("-" * 60)
    try:
        video_info = db.command("listCollections", filter={"name": "video_file"})
        if video_info and 'cursor' in video_info and 'firstBatch' in video_info['cursor']:
            collections = video_info['cursor']['firstBatch']
            if collections:
                col_info = collections[0]
                if 'options' in col_info and 'validator' in col_info['options']:
                    import json
                    logger.info(json.dumps(col_info['options']['validator'], indent=2))
                    logger.info(f"✅ Validator is SET")
                    if 'validationLevel' in col_info['options']:
                        logger.info(f"Validation Level: {col_info['options']['validationLevel']}")
                    if 'validationAction' in col_info['options']:
                        logger.info(f"Validation Action: {col_info['options']['validationAction']}")
                else:
                    logger.warning("⚠️  NO VALIDATOR CONFIGURED")
            else:
                logger.error("❌ Collection not found")
        else:
            logger.error("❌ Could not list collections")
    except Exception as e:
        logger.error(f"❌ Error checking video_file: {e}")
    
    logger.info("\n" + "-" * 60 + "\n")
    
    # Check event collection
    logger.info("📁 event collection:")
    logger.info("-" * 60)
    try:
        event_info = db.command("listCollections", filter={"name": "event"})
        if event_info and 'cursor' in event_info and 'firstBatch' in event_info['cursor']:
            collections = event_info['cursor']['firstBatch']
            if collections:
                col_info = collections[0]
                if 'options' in col_info and 'validator' in col_info['options']:
                    import json
                    logger.info(json.dumps(col_info['options']['validator'], indent=2))
                    logger.info(f"✅ Validator is SET")
                    if 'validationLevel' in col_info['options']:
                        logger.info(f"Validation Level: {col_info['options']['validationLevel']}")
                    if 'validationAction' in col_info['options']:
                        logger.info(f"Validation Action: {col_info['options']['validationAction']}")
                else:
                    logger.warning("⚠️  NO VALIDATOR CONFIGURED")
            else:
                logger.error("❌ Collection not found")
        else:
            logger.error("❌ Could not list collections")
    except Exception as e:
        logger.error(f"❌ Error checking event: {e}")
    
    logger.info("\n" + "="*80)
    logger.info("\n💡 RECOMMENDATIONS:")
    logger.info("If validators are NOT set or validationLevel is 'off'/'moderate':")
    logger.info("  1. MongoDB Atlas allows setting validators in Database > Collections > Validation")
    logger.info("  2. Set validationLevel to 'strict'")
    logger.info("  3. Set validationAction to 'error'")
    logger.info("  4. This will enforce schema compliance at the database level")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    check_validators()
