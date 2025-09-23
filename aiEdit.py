# pip install --pre -r requirements.txt

import sys, os, argparse, pathlib, asyncio, logging
import glob
from typing import Optional
from functools import partial
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder
import yaml

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress noisy HTTP and Azure SDK logs
for noisy_logger in [
    'azure.core.pipeline.policies.http_logging_policy',
    'azure.identity',
    'azure.ai',
    'urllib3',
    'httpx',
    'requests',
    'msrest',
    'msal',
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_all_agents(agent_list, summarizer, implementer):
    """Return a deduplicated list of all agent names, including summarizer and implementer if provided."""
    agents = agent_list + [a for a in (summarizer, implementer) if a]
    return list(dict.fromkeys(filter(None, agents)))

def check_agent_files(all_agents):
    """Check for existence and validity of agent YAML files. Returns a dict of agent configs."""
    base_dir = pathlib.Path(__file__).resolve().parent
    agent_configs = {}
    missing = []
    for a in all_agents:
        # Only allow YAML in agents
        yaml_path = base_dir / "agents" / f"{a}.yml"
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    try:
                        config = yaml.safe_load(f)
                    except yaml.YAMLError as ye:
                        logger.error(f"YAML parsing error in '{yaml_path}': {ye}")
                        sys.exit(1)
                # Validate required fields
                errors = []
                if not ("model" in config and isinstance(config["model"], dict)):
                    errors.append("missing 'model' section")
                else:
                    if not config["model"].get("id"):
                        errors.append("missing 'model.id'")
                    if not ("options" in config["model"] and isinstance(config["model"]["options"], dict)):
                        errors.append("missing 'model.options'")
                    else:
                        if config["model"]["options"].get("temperature") is None:
                            errors.append("missing 'model.options.temperature'")
                        if config["model"]["options"].get("top_p") is None:
                            errors.append("missing 'model.options.top_p'")
                if not config.get("instructions"):
                    errors.append("missing 'instructions'")
                # Tool validation (optional, but if present must be valid)
                if "tools" in config and config["tools"]:
                    tool = config["tools"][0]
                    if not (tool.get("type") == "mcp" and tool.get("id") and tool.get("options") and tool["options"].get("server_url")):
                        errors.append("invalid or incomplete MCP tool config in 'tools'")
                if errors:
                    logger.error(f"Agent '{a}' YAML errors: {', '.join(errors)}")
                    sys.exit(1)
                agent_configs[a] = config
            except Exception as e:
                logger.error(f"Unexpected error loading agent YAML '{yaml_path}': {e}")
                sys.exit(1)
        else:
            missing.append(a)
    if missing:
        logger.error(f"Missing agent YAML file(s) in agents: {', '.join(missing)}")
        sys.exit(1)
    return agent_configs

def get_azure_clients():
    """Create and return Azure agents client using environment variables."""
    endpoint = os.environ.get('AZURE_PROJECT_ENDPOINT')
    if not endpoint:
        logger.critical("AZURE_PROJECT_ENDPOINT environment variable is not set.")
        sys.exit(1)
    # Check for a bad or malformed endpoint (basic validation)
    if not (endpoint.startswith("https://") and ".azure" in endpoint):
        logger.critical(f"AZURE_PROJECT_ENDPOINT appears invalid: {endpoint}")
        sys.exit(1)
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint, credential)
    agents_client = project_client.agents
    return agents_client


class AgentManager:
    """Manages agent lifecycle and deployment."""
    def __init__(self, agent_configs: dict, agents_client, verbose: bool = False):
        self.agent_configs = agent_configs
        self.agents_client = agents_client
        self.verbose = verbose
        self.agent_feedback = []
        self.agent_objs = {}

    async def create_agent(self, agent_name: str):
        loop = asyncio.get_running_loop()
        config = self.agent_configs[agent_name]
        # All required fields are validated in check_agent_files
        model_deployment_name = config["model"]["id"]
        temperature = config["model"]["options"]["temperature"]
        top_p = config["model"]["options"]["top_p"]
        instructions = config["instructions"]
        tools = []
        if "tools" in config and config["tools"]:
            tool = config["tools"][0]
            mcp_tool_dict = {
                "type": "mcp",
                "server_url": tool["options"]["server_url"],
                "server_label": tool.get("options", {}).get("server_label", "Unknown"),
                "allowed_tools": [tool["id"]],
            }
            tools.append(mcp_tool_dict)
        agent = await loop.run_in_executor(
            None,
            partial(
                self.agents_client.create_agent,
                model=model_deployment_name,
                name=f"agent-{agent_name}",
                instructions=instructions,
                tools=tools if tools else None,
                temperature=temperature,
                top_p=top_p
            )
        )
        mcp_server = None
        if tools and tools[0].get("type") == "mcp":
            mcp_server = tools[0].get("allowed_tools")
        logger.info(f"Created agent: {agent.id} ({agent_name}, model={model_deployment_name}, MCP={mcp_server})")
        self.agent_objs[agent_name] = {"agent": agent, "agents_client": self.agents_client}

    async def delete_all_agents(self):
        loop = asyncio.get_running_loop()
        for agent_name, agent_obj in self.agent_objs.items():
            agent = agent_obj["agent"]
            try:
                await loop.run_in_executor(None, self.agents_client.delete_agent, agent.id)
                logger.info(f"Deleted agent: {agent.id} ({agent_name})")
            except Exception as e:
                logger.warning(f"Could not delete agent {agent.id} ({agent_name}): {e}")

    async def deploy_agent(self, agent_name: str, filename: str, agent_system_prompt: str, summarizer: Optional[str] = None, implementer: Optional[str] = None):
        loop = asyncio.get_running_loop()
        agent_obj = self.agent_objs[agent_name]
        agents_client = agent_obj['agents_client']
        agent_id = agent_obj['agent'].id
        thread = await loop.run_in_executor(None, agents_client.threads.create)
        user_prompt = ""
        file_content = ""
        config = self.agent_configs[agent_name]
        instructions = config.get("instructions", agent_system_prompt)
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                file_content = f.read()
            if agent_name == summarizer:
                user_prompt = f"{instructions}\n\nAGENT FEEDBACK START\n\n{self.agent_feedback}\nAGENT FEEDBACK END"
            elif agent_name == implementer:
                user_prompt = f"{instructions}\n\nEdit the content (between CONTENT_START and CONTENT_END) based on the agent feedback.\n\nAGENT FEEDBACK START\n\n{self.agent_feedback}\nAGENT FEEDBACK END\n\nCONTENT START\n{file_content}\nCONTENT END"
            else:
                user_prompt = f"{instructions}\n\nReview the following content and provide feedback.\n\nCONTENT START\n{file_content}\nCONTENT END"
            await loop.run_in_executor(
                None,
                partial(
                    agents_client.messages.create,
                    thread_id=thread.id,
                    content=user_prompt,
                    role="user"
                )
            )

        run = await loop.run_in_executor(
            None,
            partial(agents_client.runs.create, thread_id=thread.id, agent_id=agent_id)
        )
        logger.info(f"Created run ({agent_name}), ID: {run.id}")
        while run.status in ["queued", "in_progress", "requires_action"]:
            await asyncio.sleep(1)
            run = await loop.run_in_executor(None, agents_client.runs.get, thread.id, run.id)
        if run.status == "failed":
            logger.info(f"Run failed: {run.last_error}")
            return ""

        file_output = ""
        messages = await loop.run_in_executor(
            None,
            partial(agents_client.messages.list, thread_id=thread.id, order=ListSortOrder.ASCENDING)
        )
        for msg in messages:
            if getattr(msg, 'role', None) == "assistant" and msg.text_messages:
                feedback = msg.text_messages[-1].text.value
                if summarizer and agent_name == summarizer:
                    self.agent_feedback.clear()
                    self.agent_feedback.append(feedback)
                    if self.verbose:
                        logger.info(f"\n[{agent_name}]:\n{feedback}\n{'-'*100}")
                elif agent_name == implementer:
                    file_output = feedback
                else:
                    self.agent_feedback.append(feedback)
                    if self.verbose:
                        logger.info(f"\n[{agent_name}]:\n{feedback}\n{'-'*100}")
        try:
            if agent_name == implementer:
                logger.info(f"Saving changes to file: {filename}\n")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(file_output)
        except Exception as e:
            logger.warning(f"Error in agent '{agent_name}': {e}")
        return ""

def main():
    """Main entry point for running agents and reviewer on a file."""
    parser = argparse.ArgumentParser(description="Run agents and reviewer on a file.")
    parser.add_argument("--agents", type=str, required=True, help="Comma-separated list of agent names")
    parser.add_argument("--summarizer", type=str, required=False, help="Agent name to summarize findings")
    parser.add_argument("--implementer", type=str, required=False, help="Agent name to implement findings")
    parser.add_argument("--verbose", type=str, required=False, default="N", help="Display agent feedback (Y/N)")
    parser.add_argument("filenames", type=str, nargs='+', help="File(s) to be evaluated. Supports wildcards (e.g., *.md) and multiple files.")
    args = parser.parse_args()

    agent_list = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not agent_list:
        logger.error("No worker agents specified in --agents argument.")
        sys.exit(1)

    summarizer: Optional[str] = args.summarizer.strip() if args.summarizer else None
    implementer: Optional[str] = args.implementer.strip() if args.implementer else None
    verbose = args.verbose.strip().upper() == "Y"

    logger.info(f"Worker Agents: {agent_list}")
    logger.info(f"Summarizer Agent: {summarizer}")
    logger.info(f"Implementer Agent: {implementer}")
    logger.info(f"Verbose: {verbose}")
    logger.info(f"Filenames: {args.filenames}")

    # Expand wildcards and flatten the list of files
    expanded_files = []
    for pattern in args.filenames:
        matches = glob.glob(pattern)
        if matches:
            # Filter out directories from the matches
            for match in matches:
                if os.path.isfile(match):
                    expanded_files.append(match)
                elif os.path.isdir(match):
                    logger.warning(f"Skipping directory: {match}")
        else:
            logger.warning(f"No files matched pattern: {pattern}")
    if not expanded_files:
        logger.error("No files found to process.")
        sys.exit(1)

    all_agents = get_all_agents(agent_list, summarizer, implementer)
    agent_configs = check_agent_files(all_agents)
    agents_client = get_azure_clients()
    agent_manager = AgentManager(agent_configs, agents_client, verbose=verbose)


    def get_instructions(agent: str) -> str:
        """Get instructions for a given agent from its config."""
        config = agent_configs[agent]
        return config.get("instructions", "")

    async def run_agents():
        # Create all agent objects first
        for agent_name in all_agents:
            await agent_manager.create_agent(agent_name)

        for filename in expanded_files:
            logger.info(f"Processing file: {filename}")
            # Run all agents concurrently except summarizer and implementer
            await asyncio.gather(*[
                agent_manager.deploy_agent(agent, filename, get_instructions(agent), summarizer, implementer)
                for agent in agent_list
            ])

            # Run summarizer (summarizes findings of previous agents)
            if summarizer:
                await agent_manager.deploy_agent(summarizer, filename, get_instructions(summarizer), summarizer, implementer)

            # Run implementer (updates the file with agent findings)
            if implementer:
                await agent_manager.deploy_agent(implementer, filename, get_instructions(implementer), summarizer, implementer)

        # Delete all agents at the end
        await agent_manager.delete_all_agents()

    try:
        asyncio.run(run_agents())
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()