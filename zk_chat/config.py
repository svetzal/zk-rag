import os
from datetime import datetime
from typing import List, Optional

import requests
from pydantic import BaseModel


def get_available_models() -> List[str]:
    try:
        response = requests.get('http://localhost:11434/api/tags')
        if response.status_code == 200:
            return [model['name'] for model in response.json()['models']]
        return []
    except:
        return []


def select_model() -> str:
    models = get_available_models()
    if not models:
        return input("No models found in Ollama. Please enter model name manually: ")

    print("\nAvailable models:")
    for idx, model in enumerate(models, 1):
        print(f"{idx}. {model}")

    while True:
        try:
            choice = int(input("\nSelect a model (enter number): "))
            if 1 <= choice <= len(models):
                return models[choice - 1]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


config_filename: str = os.path.expanduser("~/.zk_chat")


class Config(BaseModel):
    vault: str
    model: str
    chunk_size: int = 500
    chunk_overlap: int = 100
    last_indexed: Optional[datetime] = None

    @classmethod
    def load_or_initialize(cls) -> 'Config':
        if os.path.exists(config_filename):
            with open(config_filename, 'r') as f:
                return cls.model_validate_json(f.read())

        vault = input("Enter path to your zettelkasten vault: ")
        model = select_model()
        config = cls(vault=vault, model=model)
        config.save()
        return config

    def save(self) -> None:
        with open(config_filename, 'w') as f:
            f.write(self.model_dump_json())
