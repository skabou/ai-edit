aiEdit.py can be run via a CLI (Command Line Interface) but is intended to run on a schedule or via an external trigger without requiring a human to sit and wait for a response.

I recommend integrating it with git so you can review its PRs (to maintain the human element).

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

The second sample asks for reviews from the Code Expert agent, and Security Expert agent.  Once both agents have responded, the Summarizer agent will summarize and attempt to validate their feedback.   The implementer agent will take this feedback and make changes to the file.  The flag verbose=Y means we want to see what each agent is "thinking."