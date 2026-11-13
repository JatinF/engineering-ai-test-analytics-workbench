"""Write the FastAPI schema. Importing the app builds the synthetic lab."""

import json
from pathlib import Path

from eng_workbench.api import app

target = Path(__file__).resolve().parents[1] / "api" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(target)
