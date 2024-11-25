# main.py
from pipelines.etl_pipeline import DocumentationETLPipeline
import asyncio
from loguru import logger

async def main():
    try:
        pipeline = DocumentationETLPipeline()
        await pipeline.run()
        
        # Print statistics after completion
        stats = pipeline.mongo_client.get_statistics()
        logger.info("ETL Pipeline Statistics:")
        logger.info(f"Total Documents: {stats.get('total_documents', 0)}")
        logger.info("By Subdomain:")
        for subdomain, count in stats.get('by_subdomain', {}).items():
            logger.info(f"  {subdomain}: {count}")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        exit(1)