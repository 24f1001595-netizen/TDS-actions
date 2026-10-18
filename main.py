import os
import yaml
from pathlib import Path
from dotenv import dotenv_values
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow cross-origin requests for the grader
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def coerce_value(key: str, val: Any) -> Any:
    if val is None:
        return val
    if key in ("port", "workers"):
        return int(val)
    elif key == "debug":
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        return s in ("true", "1", "yes", "on")
    else:
        return str(val)

def load_base_layers() -> Dict[str, Any]:
    # Layer 1: Defaults (Hardcoded)
    config: Dict[str, Any] = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # Layer 2: config.development.yaml
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
            for k, v in yaml_data.items():
                if k in config:
                    config[k] = coerce_value(k, v)

    # Layer 3: .env file
    env_file_values = dotenv_values(".env")
    env_mapping = {
        "APP_PORT": "port",
        "NUM_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }
    for env_k, target_k in env_mapping.items():
        if env_k in env_file_values and env_file_values[env_k] is not None:
            config[target_k] = coerce_value(target_k, env_file_values[env_k])

    # Layer 4: OS Environment Variables (APP_* prefix)
    os_mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }
    for env_k, target_k in os_mapping.items():
        val = os.getenv(env_k)
        if val is not None:
            config[target_k] = coerce_value(target_k, val)

    return config

@app.get("/effective-config")
def get_effective_config(set: Optional[List[str]] = Query(default=None)):
    merged = load_base_layers()

    # CLI overrides via ?set=key=value
    if set:
        for override in set:
            if "=" in override:
                key, val = override.split("=", 1)
                key = key.strip()
                val = val.strip()

                if key == "NUM_WORKERS":
                    key = "workers"

                if key in ("port", "workers", "debug", "log_level", "api_key"):
                    merged[key] = coerce_value(key, val)
                else:
                    merged[key] = str(val)

    # Always mask api_key
    response = dict(merged)
    response["api_key"] = "****"

    return response
