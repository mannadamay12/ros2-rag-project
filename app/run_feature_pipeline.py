import asyncio
from loguru import logger
from pipelines.feature_pipeline import FeaturePipeline

def main():
    try:
        # Initialize and run the feature pipeline
        pipeline = FeaturePipeline()
        pipeline.process_documents(batch_size=5)  # Adjust batch size as needed
        logger.info("Feature pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Error running feature pipeline: {str(e)}")
        raise

if __name__ == "__main__":
    main() 