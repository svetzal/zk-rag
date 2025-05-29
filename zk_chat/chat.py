import logging

logging.basicConfig(
    level=logging.WARN
)

import argparse
import os
import sys
from importlib.metadata import entry_points
from typing import List, Optional, Tuple

from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.tools.llm_tool import LLMTool

from zk_chat.chroma_collections import ZkCollectionName
from zk_chat.cli import add_common_args, common_init, display_banner
from zk_chat.markdown.markdown_filesystem_gateway import MarkdownFilesystemGateway
from zk_chat.memory.smart_memory import SmartMemory
from zk_chat.models import ZkDocument
from zk_chat.tools.analyze_image import AnalyzeImage
from zk_chat.tools.commit_changes import CommitChanges
from zk_chat.tools.git_gateway import GitGateway
from zk_chat.tools.list_zk_documents import ListZkDocuments
from zk_chat.tools.resolve_wikilink import ResolveWikiLink
from zk_chat.tools.retrieve_from_smart_memory import RetrieveFromSmartMemory
from zk_chat.tools.store_in_smart_memory import StoreInSmartMemory
from zk_chat.tools.uncommitted_changes import UncommittedChanges

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


def _setup_chat_session(config: Config, unsafe: bool = False, use_git: bool = False, store_prompt: bool = False):
    """Set up the chat session with all necessary components."""
    # Create a single ChromaGateway instance to access multiple collections
    db_dir = os.path.join(config.vault, ".zk_chat_db")
    chroma_gateway = ChromaGateway(config.gateway, db_dir=db_dir)

    if config.gateway.value == ModelGateway.OLLAMA:
        gateway = OllamaGateway()
    elif config.gateway.value == ModelGateway.OPENAI:
        gateway = OpenAIGateway(os.environ.get("OPENAI_API_KEY"))
    else:
        raise ValueError(f"Invalid gateway: {config.gateway}")

    filesystem_gateway = MarkdownFilesystemGateway(config.vault)
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
        filesystem_gateway=filesystem_gateway
    )

    llm = LLMBroker(config.model, gateway=gateway)

    # Create SmartMemory with the smart_memory collection
    smart_memory = SmartMemory(
        chroma_gateway=chroma_gateway,
        gateway=gateway
    )

    tools: List[LLMTool] = [
        ResolveDateTool(),
        ReadZkDocument(zk),
        ListZkDocuments(zk),
        ResolveWikiLink(filesystem_gateway),
        FindExcerptsRelatedTo(zk),
        FindZkDocumentsRelatedTo(zk),
        StoreInSmartMemory(smart_memory),
        RetrieveFromSmartMemory(smart_memory)
    ]

    # Add AnalyzeImage tool only if a visual model is selected
    if config.visual_model:
        tools.append(AnalyzeImage(zk, LLMBroker(model=config.visual_model, gateway=gateway)))

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

About the Zettelkasten (zk):
All documents are in Markdown format, and links between them are in wikilink format (eg [[Title of Document]]).
Within the markdown:
- leave a blank line between headings, paragraphs, lists, code blocks, quotations, separators (---), and other block-level elements
- use # for headings, ## for subheadings, and so on
- don't repeat the document title as the first heading
- when nesting headings, their level should increase by one each time (#, ##, ###, etc.)
- only use `-` as the bullet marker for unordered lists, and 1. for ordered lists, renumber ordered lists if you insert or remove items
- use **bold** and *italic* for emphasis
- place blocks of code in code-fences, include a marker in the top fence for the type of code (language, json, xml, etc) eg "```python"
- when generating content use spaces (not tabs), and actual carriage returns (not `\\n` markers)
About organizing the Zettelkasten:
- An Atomic Idea is a document that contains a single idea, concept, or piece of information. It should be concise and focused, and consist of a title (the name of the document), a concise description of the core idea, a more elaborate explanation of the idea, a list of sources from which the idea was pulled (may be an external link), and a list of related ideas that are connected to the core idea (may be external links, but are likely to be wikilinks)
- Documents that refer to people should be in the form of `@Person Name` (eg under the wikilink `[[@Oscar Wilde]])
- There are several types of documents common in the zk - Atomic Ideas, editorial or blog content that expand on how Atomic Ideas relate, Maps of Content / index documents
- If the user uses a wikilink (eg [[Title of Document]], or [[@Person Name]]) to refer to a document in the zk, resolve the link to the actual document.
- If the user uses the phrase `MoC` that refers to a Map of Content, a document that indexes and links to other documents in order to assist a user in navigating the information in their vault
- The user may ask you to extract atomic ideas from a larger document, create one Atomic Idea document for each idea you find in the source document. Make sure to either transcribe the cited sources in the original document, and the original document itself.
- There must be only one reference to an Atomic Idea in the zk. If you find a duplicate, you should merge the two documents into one, and update the references to the merged document.
        """.strip()

    if zk.document_exists(system_prompt_filename):
        system_prompt = zk.read_document(system_prompt_filename).content
    else:
        system_prompt = default_system_prompt
        if store_prompt:
            zk.create_or_overwrite_document(
                ZkDocument(relative_path=system_prompt_filename, metadata={}, content=system_prompt))

    chat_session = ChatSession(
        llm,
        system_prompt=system_prompt,
        tools=tools
    )

    return chat_session


def chat(config: Config, unsafe: bool = False, use_git: bool = False, store_prompt: bool = False):
    """Traditional chat interface using simple input/output."""
    chat_session = _setup_chat_session(config, unsafe, use_git, store_prompt)

    while True:
        query = input("Query: ")
        if not query:
            print("Exiting...")
            break
        else:
            response = chat_session.send(query)
            print(response)


def rich_chat(config: Config, unsafe: bool = False, use_git: bool = False, store_prompt: bool = False):
    """Enhanced chat interface using Rich library for a better user experience."""
    chat_session = _setup_chat_session(config, unsafe, use_git, store_prompt)
    
    # Initialize conversation history
    conversation = []
    
    # Create console for rendering
    console = Console()
    
    # Get terminal size
    terminal_width, terminal_height = os.get_terminal_size()
    
    # Create the layout
    layout = Layout()
    
    # Split into chat history (top) and input area (bottom)
    layout.split(
        Layout(name="chat", ratio=1),
        Layout(name="input", size=5)  # Fixed at 5 lines as per requirements
    )

    # Keep track of current input text and cursor position
    current_input = []
    cursor_line = 0
    
    def render_conversation():
        """Render the conversation history with scrolling support."""
        if not conversation:
            return Panel(
                "[dim]No messages yet. Type your query below.[/dim]", 
                title="Chat History",
                border_style="blue", 
                height=None
            )
        
        result = []
        for role, message in conversation:
            if role == "user":
                result.append(f"[bold cyan]You:[/]\n{message}")
            else:
                # Handle markdown rendering for assistant responses
                # Use Rich's Markdown for better formatting
                result.append(f"[bold green]Assistant:[/]\n{message}")
        
        message_text = "\n\n".join(result)
        
        # Calculate visible height for the chat panel
        visible_height = terminal_height - layout["input"].size - 4  # Account for borders and padding
        
        # Basic scrolling implementation
        lines = message_text.split("\n")
        if len(lines) > visible_height:
            visible_lines = lines[-visible_height:]
            message_text = "\n".join(visible_lines)
            scroll_info = f"[dim](Showing {visible_height} of {len(lines)} lines - most recent messages)[/]"
            return Panel(
                f"{scroll_info}\n{message_text}", 
                title="Chat History", 
                border_style="blue", 
                height=None,
                padding=(1, 1)
            )
        
        return Panel(
            message_text, 
            title="Chat History", 
            border_style="blue", 
            height=None,
            padding=(1, 1)
        )

    def render_input_area():
        """Render the input area with current input text."""
        if not current_input:
            help_text = "[bold]Enter your query below[/] [dim](Submit: Empty line, Exit: Ctrl+D or Ctrl+C)[/dim]"
            return Panel(
                help_text,
                title="Input",
                border_style="green",
                height=None
            )
        
        # Show the current input text with a cursor indicator
        input_lines = current_input.copy()
        
        # Format the text with appropriate styling
        text = Text()
        for i, line in enumerate(input_lines):
            if i > 0:
                text.append("\n")
            text.append(line)
            
        return Panel(
            text,
            title="Input",
            border_style="green", 
            height=None,
            padding=(0, 1)
        )

    def update_layout():
        """Update the layout with current content."""
        layout["chat"].update(render_conversation())
        layout["input"].update(render_input_area())

    def process_keystroke(key: str) -> Tuple[bool, Optional[str]]:
        """Process a keystroke and update the current input.
        
        Returns:
            Tuple[bool, Optional[str]]: 
            - First value: True if input is complete, False otherwise
            - Second value: The final input text if complete, None otherwise
        """
        nonlocal current_input
        
        # Handle special keys
        if key == 'ctrl+c' or key == 'ctrl+d':
            return True, None
        
        if key == 'enter':
            # If enter is pressed on an empty input or after an empty line
            # following content, consider input complete
            if not current_input or (current_input and current_input[-1] == ''):
                result = '\n'.join(current_input).rstrip()
                if not result:
                    return True, None
                return True, result
            current_input.append('')
        elif key == 'backspace':
            if current_input and current_input[-1]:
                current_input[-1] = current_input[-1][:-1]
            elif len(current_input) > 1:  # Can remove empty line
                current_input.pop()
        else:
            # Regular character input
            if not current_input:
                current_input = ['']
            current_input[-1] += key
            
        return False, None

    def get_input_with_live_display(live: Live) -> Optional[str]:
        """Get multiline input while keeping the Live display active."""
        nonlocal current_input
        
        # Clear any previous input
        current_input = ['']
        update_layout()
        live.refresh()
        
        while True:
            try:
                # Use Rich's console input to capture a single keystroke
                key = console.input(password=True)
                
                # Process the keystroke
                is_complete, final_text = process_keystroke(key)
                
                # Update the display
                update_layout()
                live.refresh()
                
                if is_complete:
                    return final_text
                    
            except (EOFError, KeyboardInterrupt):
                return None

    # Display initial instructions
    console.clear()
    console.print("[bold cyan]ZkChat Rich Interface[/]")
    console.print("- Type your message in the input panel")
    console.print("- Submit with an empty line")
    console.print("- Exit with Ctrl+C or Ctrl+D")
    console.print("\nPress Enter to start...")
    input()
    console.clear()

    with Live(layout, console=console, screen=True, refresh_per_second=4) as live:
        update_layout()
        live.refresh()
        
        while True:
            # Get multiline input from user while keeping panels visible
            query = get_input_with_live_display(live)
            
            # Check for exit condition
            if query is None:
                break
                
            # Reset current_input for next query
            current_input = []
                
            # Add user query to conversation
            conversation.append(("user", query))
            update_layout()
            live.refresh()
            
            # Show "thinking" indicator
            layout["input"].update(Panel("[italic]Processing...[/]", title="Status", border_style="yellow"))
            live.refresh()
            
            # Get assistant response
            response = chat_session.send(query)
            
            # Add assistant response to conversation
            conversation.append(("assistant", response))
            update_layout()
            live.refresh()

    console.clear()
    console.print("[bold cyan]Thank you for using ZkChat![/]")
    return


def _add_available_plugins(tools, config: Config, llm: LLMBroker):
    eps = entry_points()
    plugin_entr_points = eps.select(group="zk_rag_plugins")
    for ep in plugin_entr_points:
        logging.info(f"Adding Plugin {ep.name}")
        plugin_class = ep.load()
        tools.append(plugin_class(vault=config.vault, llm=llm))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Zettelkasten Chat')
    add_common_args(parser)
    parser.add_argument('--unsafe', action='store_true', help='Allow write operations in chat mode')
    parser.add_argument('--git', action='store_true', help='Enable git integration')
    parser.add_argument('--store-prompt', action='store_false', help='Store the system prompt to the vault',
                        dest='store_prompt', default=True)
    parser.add_argument('--simple', action='store_true', help='Use simple text interface instead of rich UI')

    args = parser.parse_args()

    config = common_init(args)

    if args.git:
        git_gateway = GitGateway(config.vault)
        git_gateway.setup()

    display_banner(config, title="ZkChat", unsafe=args.unsafe, use_git=args.git, store_prompt=args.store_prompt)

    if args.simple:
        chat(config, unsafe=args.unsafe, use_git=args.git, store_prompt=args.store_prompt)
    else:
        rich_chat(config, unsafe=args.unsafe, use_git=args.git, store_prompt=args.store_prompt)
