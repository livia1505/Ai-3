# Goal

Detail out the different Agents - their roles, responsibilities and Tools.

# Planner Agent

## Role
Make a plan using the available agents to service the user's request - powered by a LLM.

## Responsibilities
- Ask the user for clarification on request
- Present the plan to the user for approval & edits
- Prepare a detailed plan
- Invoke the agents in sequence according to the plan
- Inform the user about the final successful output
- Inform the user about any errors

## Tools
- Access Pre-curated plans
- Invoke other agents as tools
- Interact with user
