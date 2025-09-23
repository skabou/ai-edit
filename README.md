# About
Are you part of a small team that has a large set of documents to maintain?  aiEdit may be able to help!  Build custom agents in the agents folder to assist with reviewing and maintaining your documents.

# Deploy
aiEdit.py can be run via a CLI (Command Line Interface) but is ideal to run on a schedule or via an external trigger without requiring a human to sit and wait for a response.

To maintain the human element, I recommend integrating it with GitHub so you can sit back and review the PRs.

Note: Some of the example agents are configured to use an MCP server.  [This feature is currently in preview](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/model-context-protocol).  To utilize this feature, your AI Foundry infrastructure needs to be in one of the supported regions: westus, westus2, uaenorth, southindia, or switzerlandnorth.  Alternatively, if you'd like to remove the use of the MCP server, then modify the agent's tools line as follows: `tools: []`

Setup instructions:
1. Setup your environment on [Azure AI Foundry](https://ai.azure.com/)
2. Clone this repo: `git clone https://github.com/skabou/aiEdit`
3. Paste your endpoint in the ".env" file, such as:
`AZURE_PROJECT_ENDPOINT=<your-endpoint-goes-here>`
4. Install prerequisites with `pip install --pre -r requirements.txt`




Try out the samples:

# Content Review
`python aiEdit.py --agents=typocheck,content_expert,azure_expert --summarizer=summarizer --implementer=implementer --verbose=Y example-content.md`

The first sample asks for reviews (in parallel) from the TypoCheck agent, Content Expert agent, and Azure Expert agent.  Once all 3 agents have responded, the Summarizer agent will summarize and attempt to validate their feedback.   The implementer agent will take this feedback and make changes to the file.  The flag verbose=Y means we want to see what each agent is "thinking."

# Code Review
`python aiEdit.py --agents=code_expert,security_expert --summarizer=summarizer --implementer=code_implementer --verbose=Y example-code.py`

The second sample asks for reviews (in parallel) from the Code Expert agent, and Security Expert agent.  Once both agents have responded, the Summarizer agent will summarize and attempt to validate their feedback.   The implementer agent will take this feedback and make changes to the file.  The flag verbose=Y means we want to see what each agent is "thinking."