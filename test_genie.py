import os
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="myenv")
response = w.genie.start_conversation_and_wait(
    space_id="01f127a4bd121688a25e50c1ffe93651",
    content="Are there any trends in purchase orders?"
)
print("Type:", type(response))
print("Dir:", dir(response))
if hasattr(response, 'content'):
    print("Content:", response.content)
if hasattr(response, 'attachments'):
    print("Attachments:", response.attachments)
if hasattr(response, 'as_dict'):
    print("Dict:", response.as_dict())
