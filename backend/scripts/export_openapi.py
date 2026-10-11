"""Print the API's OpenAPI document. `make types` pipes this into the frontend type generator."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
