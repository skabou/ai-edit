#!/bin/bash

# Exit immediately if a command fails
set -e

# Edit the file(s)
python aiEdit.py --agents=typocheck,azure_expert,security_expert --summarizer=summarizer --implementer=code_implementer example-code.py --verbose=Y

# Step 1: Stash current changes
git stash push -m "Temp stash before branch switch"

# Step 2: Create and switch to new branch
git checkout -b edit-pr

# Step 3: Apply stashed changes to the new branch
git stash pop

# Step 4: Stage all changes
git add .

# Step 5: Commit changes
git commit -m "Moved changes to edit-pr branch"

# Step 6: Push to remote
git push origin edit-pr

# Step 7: Create a pull request
gh pr create --base main --head edit-pr --title "Edit PR changes" --body "Moved local changes to edit-pr branch and ready for review."
