import sys
from pathlib import Path

# Add the app directory to Python path
app_path = str(Path(__file__).parent / "app")
if app_path not in sys.path:
    sys.path.append(app_path)

from pipelines.clearml_etl_pipeline import etl_pipeline_logic

if __name__ == "__main__":
    etl_pipeline_logic() 