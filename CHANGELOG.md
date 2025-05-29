# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Next]

### Added
- Rich text UI for the CLI interface with a 2-panel layout (conversation history and input area)
- `--simple` flag to use the traditional CLI interface instead of the Rich UI

## [2.6.1] - 2025-04-05

### Added

- Added a friendlier banner for the CLI

## [2.6.0] - 2025-04-01

### Added

- Visual analysis capability for images in Zettelkasten
  - Added AnalyzeImage tool for examining and describing image content
  - Added support for configuring a separate visual model
  - Updated CLI and GUI to support visual model selection
- ResolveWikiLink tool for converting wikilinks to relative file paths for navigation between documents

### Changed

- Locked chromadb version to 0.6.3 and chroma-hnswlib to 0.7.6 for compatibility

## [2.5.1] - 2025-03-28

### Fixed

- Improved new (to zk-rag) vault and first-time installation experience

### Changed

- Updated README and refactored CLI and config for model handling and environment setup
- Streamlined vault path handling and gateway selection in CLI
- Refactored commit message generation to use updated LLM method

## [2.5.0] - 2025-03-26

### Added

- Document deletion functionality for better document management
  - Added DeleteZkDocument tool for safely removing documents from the Zettelkasten
  - Implemented safeguards to prevent accidental deletion of non-existent documents

## [2.4.0] - 2025-03-25

### Added

- Document renaming functionality
- List documents tool for better document management

### Changed

- Enhanced function descriptions for Zettelkasten tools to improve clarity and usability

## [2.3.0] - 2025-03-24

### Changed

- Added the ability to select (per vault) which gateway to use (Ollama or OpenAI) for chat
- Improved code organization and documentation
- Enhanced error handling and logging
- Performance optimizations

## [2.2.0] - 2025-03-23

### Added

- Git integration for vault management
  - Added GitGateway for Git operations
  - Added UncommittedChanges tool to view pending changes
  - Added CommitChanges tool with AI-generated commit messages
  - Added --git command-line flag to enable Git integration

## [2.1.0] - 2025-03-22

### Added

- Added significantly improved document search
- Added class docstring for Zettelkasten class

### Changed

- Updated requirements.txt to match dependencies in pyproject.toml
- Removed unnecessary f-string in logger.info call

## [2.0.0] - 2025-03-22

### Added

- Vault path argument for command-line tools
- Bookmark management for vault paths in CLI
- Global configuration handling
- MarkdownUtilities for handling markdown files with metadata
- MarkdownFilesystemGateway for markdown file operations

### Changed

- **Breaking**: Refactored ChromaGateway to support multiple collections
- **Breaking**: Updated Zettelkasten integration with new gateway architecture
- Streamlined bookmark handling in CLI by removing deprecated options

## [1.5.1] - 2025-03-09

### Fixed

- Properly passing LLM instance to plugins to enable LLM capabilities

## [1.5.0] - 2025-03-09

### Added

- **Breaking**: Enhanced plugin system to provide plugins with access to LLM capabilities
- Support for multiple indexers in Zettelkasten (one for excerpts and one for document titles/summaries)

### Changed

- Restructured Zettelkasten to externalize indexing functionality

## [1.4.0] - 2025-03-09

### Added

- Enhanced testing guidelines with detailed BDD-style section
- Configuration passing to plugin initialization

### Changed

- Renamed internal "chunks" concept to "excerpts" for better clarity
- Extracted filesystem operations into a dedicated filesystem gateway
- Improved code organization and structure

## [1.3.0] - 2025-03-03

### Added

- Plugin system for adding tools

### Changed

- Removed wikipedia lookup tool and [made it a plugin](https://pypi.org/project/zk-rag-wikipedia/) instead

## [1.2.0] - 2025-03-02

### Added

- Smart Memory mechanism for long-term context retention
- Wikipedia Lookup tool for external knowledge

### Changed

- Enhanced configuration options through both CLI and GUI
- Improved model selection interface

## [1.1.0] - 2025-02-19

### Added

- Configurable Zettelkasten folder, use of ~/.zk_rag for configuration
- Document manipulation tools for creating and updating Zettelkasten content

### Changed

- Improved document indexing system
- Enhanced RAG query capabilities

## [1.0.0] - 2024-02-13

### Added

- Initial release
- Rudimentary Command-line interface
- RAG (Retrieval-Augmented Generation) queries
- Interactive chat with Zettelkasten context
- Integration with Ollama for local LLM support
- Markdown document indexing
- Basic document search and retrieval
