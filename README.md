
# aiEdit

aiEdit is a Python-based tool for automating document and code reviews using custom agents. It is designed for teams managing large sets of content, enabling scalable review and maintenance workflows. Agents are defined in the `agents` folder and can be customized for your needs and integrated with other workflows. Example agents are provided for demonstration purposes and should not be used in production without review.

## Prerequisites

- Python 3.8 or later
- Azure AI Foundry endpoint ([Get started](https://ai.azure.com/))
- [GitHub CLI](https://cli.github.com/) (for PR automation)


## Setup

1. Clone this repository:
	```shell
	git clone https://github.com/skabou/aiEdit
	cd aiEdit
	```
> **Note:** A preview version of the [Python SDK](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol-samples?pivots=python) is needed to use MCP servers.

2. Install dependencies:
    ```shell
    pip install --pre -r requirements.txt
    ```

3. Configure environment variables:
	- Create a `.env` file in the project root.
	- Add your Azure endpoint:
	  ```env
	  AZURE_PROJECT_ENDPOINT=<your-endpoint-goes-here>
	  ```
4. (Optional) Review and customize agent YAML files in the `agents` folder.

## Example Usage

aiEdit can be run via the CLI and is designed to be easily integrated with scheduled tasks or external triggers.  The below examples can be run on the provided example content.


### Content Review

```shell
python aiEdit.py --agents=typocheck,content_expert,azure_expert --summarizer=summarizer --implementer=implementer --verbose=Y examples/*.md
```

### Code Review

```shell
python aiEdit.py --agents=code_expert,security_expert --summarizer=summarizer --implementer=code_implementer --verbose=Y examples/*.py
```

### Arguments

- `--agents`: Comma-separated list of agent names (required)
- `--summarizer`: Agent name to summarize findings (optional)
- `--implementer`: Agent name to implement changes (optional)
- `--verbose`: Display agent feedback (`Y`/`N`, default: `N`)
- `filenames`: One or more files to process (supports wildcards)

## Agent Configuration

Agents are defined in YAML files in the `agents` directory. Each agent must specify:
- `model.id`: Model deployment name
- `model.options.temperature` and `model.options.top_p`: Model parameters
- `instructions`: System prompt for the agent
- `tools`: MCP server configuration (Optional)

Refer to the example YAML files for structure. Invalid or missing fields may cause the script to exit with an error.

## Error Handling

aiEdit uses robust error handling and logging. If a required file, environment variable, or agent configuration is missing or invalid, the script will log an error and exit. All errors and warnings are logged to the console with timestamps and severity levels.

## Logging

Logging is configured to display timestamps, log levels, and messages. Noisy logs from Azure SDK and HTTP libraries are suppressed for clarity. Verbose mode (`--verbose=Y`) displays agent feedback in detail.

## Contributing

Contributions are welcome! Please review the code and agent configurations for security and compliance before deploying in production.