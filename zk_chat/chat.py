import argparse
import logging
import os
from importlib.metadata import entry_points

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway

from zk_chat.chroma_collections import ZkCollectionName
from zk_chat.markdown.markdown_filesystem_gateway import MarkdownFilesystemGateway
from zk_chat.memory.smart_memory import SmartMemory
from zk_chat.models import ZkDocument
from zk_chat.tools.commit_changes import CommitChanges
from zk_chat.tools.git_gateway import GitGateway
from zk_chat.tools.list_zk_documents import ListZkDocuments
from zk_chat.tools.retrieve_from_smart_memory import RetrieveFromSmartMemory
from zk_chat.tools.store_in_smart_memory import StoreInSmartMemory
from zk_chat.tools.uncommitted_changes import UncommittedChanges

logging.basicConfig(
    level=logging.WARN
)

from mojentic.llm.tools.date_resolver import ResolveDateTool

from zk_chat.tools.find_excerpts_related_to import FindExcerptsRelatedTo
from zk_chat.tools.find_zk_documents_related_to import FindZkDocumentsRelatedTo
from zk_chat.tools.read_zk_document import ReadZkDocument
from zk_chat.tools.create_or_overwrite_zk_document import CreateOrOverwriteZkDocument
from zk_chat.tools.rename_zk_document import RenameZkDocument
from zk_chat.tools.delete_zk_document import DeleteZkDocument
from zk_chat.vector_database import VectorDatabase

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

from zk_chat.config import Config, ModelGateway
from zk_chat.chroma_gateway import ChromaGateway
from zk_chat.zettelkasten import Zettelkasten


def chat(config: Config, unsafe: bool = False, use_git: bool = False, store_prompt: bool = False):
    # Create a single ChromaGateway instance to access multiple collections
    db_dir = os.path.join(config.vault, ".zk_chat_db")
    chroma_gateway = ChromaGateway(db_dir=db_dir)

    # Create the appropriate gateway based on configuration
    if config.gateway.value == ModelGateway.OLLAMA:
        gateway = OllamaGateway()
    elif config.gateway.value == ModelGateway.OPENAI:
        gateway = OpenAIGateway(os.environ.get("OPENAI_API_KEY"))

    # Create Zettelkasten with the excerpts collection
    zk = Zettelkasten(
        tokenizer_gateway=TokenizerGateway(),
        excerpts_db=VectorDatabase(
            chroma_gateway=chroma_gateway,
            gateway=gateway,
            collection_name=ZkCollectionName.EXCERPTS
        ),
        documents_db=VectorDatabase(
            chroma_gateway=chroma_gateway,
            gateway=gateway,
            collection_name=ZkCollectionName.DOCUMENTS
        ),
        filesystem_gateway=MarkdownFilesystemGateway(config.vault)
    )

    llm = LLMBroker(config.model, gateway=gateway)

    # Create SmartMemory with the smart_memory collection
    smart_memory = SmartMemory(
        chroma_gateway=chroma_gateway,
        gateway=gateway
    )

    tools = [
        ResolveDateTool(),
        ReadZkDocument(zk),
        ListZkDocuments(zk),
        FindExcerptsRelatedTo(zk),
        FindZkDocumentsRelatedTo(zk),
        StoreInSmartMemory(smart_memory),
        RetrieveFromSmartMemory(smart_memory)
    ]

    if use_git:
        git_gateway = GitGateway(config.vault)
        tools.append(UncommittedChanges(config.vault, git_gateway))
        tools.append(CommitChanges(config.vault, llm, git_gateway))

    if unsafe:
        tools.append(CreateOrOverwriteZkDocument(zk))
        tools.append(RenameZkDocument(zk))
        tools.append(DeleteZkDocument(zk))

    _add_available_plugins(tools, config, llm)

    system_prompt_filename = "ZkSystemPrompt.md"
    default_system_prompt = """
You are a helpful research assistant, with access to one of the user's knowledge-bases (which the user may refer to as their vault, or zk, or Zettelkasten).
If you're not sure what the user is talking about, use your available tools try and find out.
If you don't find the information you need from the first tool you try, try the next best tool until you find what you need or exhaust your options..

About the Zettelkasten:
All documents are in Markdown format, and links between them are in wikilink format (eg [[Title of Document]]).
Within the markdown:
- leave a blank line between headings, paragraphs, lists, code blocks, separators (---), and other block-level elements
- use # for headings, ## for subheadings, and so on
- don't repeat the document title as the first heading
- when nesting headings, their level should increase by one each time (#, ##, ###, etc.)
- only use - for unordered lists, and 1. for ordered lists, renumber ordered lists if you insert or remove items
- use **bold** and *italic* for emphasis
About organizing the Zettelkasten:
- If the user uses the phrase `MoC` that refers to a Map of Content, a document that links to other documents in order to assist a user in navigating the information in their vault
- An Atomic Idea is a document that contains a single idea, concept, or piece of information. It should be concise and focused, and consist of a title (the name of the document), a concise description of the core idea, a more elaborate explanation of the idea, a list of sources from which the idea was pulled (may be an external link), and a list of related ideas that are connected to the core idea (may be external links, but are likely to be wikilinks
- The user may ask you to extract atomic ideas from a larger document, create one Atomic Idea document for each idea you find in the source document. Make sure to either transcribe the cited sources in the original document, or the original document itself.
- There must be only one reference to an Atomic Idea in the zk. If you find a duplicate, you should merge the two documents into one, and update the references to the merged document.
        """.strip()

    if zk.document_exists(system_prompt_filename):
        system_prompt = zk.read_document(system_prompt_filename).content
    else:
        system_prompt = default_system_prompt
        if store_prompt:
            zk.create_or_overwrite_document(ZkDocument(relative_path=system_prompt_filename, metadata={}, content=system_prompt))

    chat_session = ChatSession(
        llm,
        system_prompt=system_prompt,
        tools=tools
    )

    while True:
        query = input("Query: ")
        if not query:
            break
        else:
            # response = rag_query(chat_session, zk, query)
            response = chat_session.send(query)
            print(response)


def _add_available_plugins(tools, config: Config, llm: LLMBroker):
    eps = entry_points()
    plugin_entr_points = eps.select(group="zk_rag_plugins")
    for ep in plugin_entr_points:
        logging.info(f"Adding Plugin {ep.name}")
        plugin_class = ep.load()
        tools.append(plugin_class(vault=config.vault, llm=llm))


def main():
    parser = argparse.ArgumentParser(description='Chat with your Zettelkasten vault')
    parser.add_argument('--vault', required=True, help='Path to your Zettelkasten vault')
    parser.add_argument('--unsafe', action='store_true', help='Allow write operations in chat mode')
    args = parser.parse_args()

    # Ensure vault path exists
    if not os.path.exists(args.vault):
        print(f"Error: Vault path '{args.vault}' does not exist.")
        return

    # Get absolute path to vault
    vault_path = os.path.abspath(args.vault)

    config = Config.load_or_initialize(vault_path)
    chat(config, unsafe=args.unsafe)


if __name__ == '__main__':
    main()
