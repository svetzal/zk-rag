from datetime import datetime
import argparse
import os
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

from zk_chat.chroma_gateway import ChromaGateway
from zk_chat.config import Config, ModelGateway
from zk_chat.markdown.markdown_filesystem_gateway import MarkdownFilesystemGateway
from zk_chat.vector_database import VectorDatabase
from zk_chat.zettelkasten import Zettelkasten
from zk_chat.chroma_collections import ZkCollectionName


def reindex(config: Config, force_full: bool = False):
    db_dir = os.path.join(config.vault, ".zk_chat_db")



    chroma = ChromaGateway(config.gateway, db_dir=db_dir)

    # Create the appropriate gateway based on configuration
    if config.gateway == ModelGateway.OLLAMA:
        gateway = OllamaGateway()
    elif config.gateway == ModelGateway.OPENAI:
        gateway = OpenAIGateway(os.environ.get("OPENAI_API_KEY"))
    else:
        # Default to Ollama if not specified
        gateway = OllamaGateway()

    zk = Zettelkasten(
        tokenizer_gateway=TokenizerGateway(),
        excerpts_db=VectorDatabase(
            chroma_gateway=chroma, 
            gateway=gateway,
            collection_name=ZkCollectionName.EXCERPTS
        ),
        documents_db=VectorDatabase(
            chroma_gateway=chroma,
            gateway=gateway,
            collection_name=ZkCollectionName.DOCUMENTS
        ),
        filesystem_gateway=MarkdownFilesystemGateway(config.vault))

    last_indexed = config.get_last_indexed()
    if force_full or last_indexed is None:
        print("Performing full reindex...")
        zk.reindex(excerpt_size=config.chunk_size, excerpt_overlap=config.chunk_overlap)
    else:
        print(f"Performing incremental reindex since {last_indexed}...")
        zk.update_index(since=last_indexed, excerpt_size=config.chunk_size, excerpt_overlap=config.chunk_overlap)

    config.set_last_indexed(datetime.now())
    config.save()


def main():
    parser = argparse.ArgumentParser(description='Index the Zettelkasten vault')
    parser.add_argument('--vault', required=True, help='Path to your Zettelkasten vault')
    parser.add_argument('--full', action='store_true', default=False, help='Force full reindex')
    parser.add_argument('--gateway', choices=['ollama', 'openai'], default='ollama',
                        help='Set the model gateway to use (ollama or openai). OpenAI requires OPENAI_API_KEY environment variable')
    args = parser.parse_args()

    # Ensure vault path exists
    if not os.path.exists(args.vault):
        print(f"Error: Vault path '{args.vault}' does not exist.")
        return

    # Get absolute path to vault
    vault_path = os.path.abspath(args.vault)

    # Convert gateway string to ModelGateway enum
    gateway = ModelGateway(args.gateway)

    # Check if OpenAI API key is set when using OpenAI gateway
    if gateway == ModelGateway.OPENAI and not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set. Cannot use OpenAI gateway.")
        return

    config = Config.load(vault_path)
    if config:
        # Update gateway if different from config
        if gateway != config.gateway:
            config.gateway = gateway
            config.save()
    else:
        # Initialize new config with specified gateway
        config = Config.load_or_initialize(vault_path, gateway=gateway)

    reindex(config, force_full=args.full)


if __name__ == '__main__':
    main()
