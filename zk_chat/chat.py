import logging

from zk_chat.memory.smart_memory import SmartMemory
from zk_chat.tools.retrieve_from_smart_memory import RetrieveFromSmartMemory
from zk_chat.tools.store_in_smart_memory import StoreInSmartMemory

logging.basicConfig(
    level=logging.WARN
)

from mojentic.llm.tools.date_resolver import ResolveDateTool

from zk_chat.tools.find_excerpts_related_to import FindExcerptsRelatedTo
from zk_chat.tools.find_zk_documents_related_to import FindZkDocumentsRelatedTo
from zk_chat.tools.read_zk_document import ReadZkDocument
from zk_chat.tools.write_zk_document import WriteZkDocument
from zk_chat.tools.wikipedia_content import LookUpTopicOnWikipedia
from zk_chat.vector_database import VectorDatabase

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.gateways.embeddings_gateway import EmbeddingsGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

from zk_chat.config import Config
from zk_chat.chroma_gateway import ChromaGateway
from zk_chat.zettelkasten import Zettelkasten


def chat(config: Config, unsafe: bool = False):
    zk_chroma = ChromaGateway()
    zk = Zettelkasten(root_path=config.vault,
                      tokenizer_gateway=TokenizerGateway(),
                      vector_db=VectorDatabase(chroma_gateway=zk_chroma, embeddings_gateway=EmbeddingsGateway()))
    llm = LLMBroker(config.model)

    sm_chroma = ChromaGateway(partition_name="smart_memory")
    smart_memory = SmartMemory(chroma_gateway=sm_chroma, embeddings_gateway=EmbeddingsGateway())

    tools = [
        ResolveDateTool(),
        ReadZkDocument(zk),
        FindExcerptsRelatedTo(zk),
        FindZkDocumentsRelatedTo(zk),
        LookUpTopicOnWikipedia(),
        StoreInSmartMemory(smart_memory),
        RetrieveFromSmartMemory(smart_memory),
    ]

    if unsafe:
        tools.append(WriteZkDocument(zk))

    chat_session = ChatSession(
        llm,
        system_prompt="You are a helpful research assistant.",
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


def main():
    config = Config.load_or_initialize()
    chat(config)


if __name__ == '__main__':
    main()
