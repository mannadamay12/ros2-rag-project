import sys
from pathlib import Path
from clearml import PipelineDecorator

app_path = str(Path(__file__).parent / "app")
if app_path not in sys.path:
    sys.path.append(app_path)

from app.pipelines.clearml_etl_pipeline import etl_pipeline_logic

if __name__ == "__main__":
    PipelineDecorator.run_locally()
    etl_pipeline_logic() 