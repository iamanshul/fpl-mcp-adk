## Deployment on Vertex AI Agent Engine

To deploy the agent to Google Agent Engine, first follow
[these steps](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up)
to set up your Google Cloud project for Agent Engine.

Next, you need to create a `.whl` file for your agent. From the `fpl-agent`
directory, run this command:

```bash
poetry build --format=wheel --output=deployment
```

This will create a file named `fpl_agent-0.1-py3-none-any.whl` in the
`deployment` directory.

Then run the below command. This will create a staging bucket in your GCP project and deploy the agent to Vertex AI Agent Engine:

```bash
python3 deployment/deploy.py --create
```

When this command returns, if it succeeds it will print an AgentEngine resource
name that looks something like this:
```
projects/************/locations/us-central1/reasoningEngines/7737333693403889664
```
The last sequence of digits is the AgentEngine resource ID.

Once you have successfully deployed your agent, you can interact with it
using the `test_deployment.py` script in the `deployment` directory. Store the
agent's resource ID in an environment variable and run the following command:

```bash
export RESOURCE_ID=...
export USER_ID=<any string>
python test_deployment.py --resource_id=$RESOURCE_ID --user_id=$USER_ID
```

The session will look something like this:
```
Found agent with resource ID: ...
Created session for user ID: ...
Type 'quit' to exit.
Input: Who is the most selected player right now?
Response: The most selected player is...
...
```

To delete the agent, run the following command (using the resource ID returned previously):
```bash
python3 deployment/deploy.py --delete --resource_id=RESOURCE_ID
```