For better compatibility with vscode, it needs separate communication channels

1. For sending information about which file, and options
2. actual response (for terminal based )
3. for text editors, it will want to show highlights for which it will need to take a peek of headers. sending headers
   for terminal could be bad.

options for communication

1) http protocol
2) shell based protocol

request

```json
{
  "requestType": "runFile",
  "uid": "<random generate id>",
  "file": "<>",
  "env": [
    "<env1>",
    "<env2>",
    "<env3>"
  ],
  "props": {
    "<key1>": "<value1>",
    "<key2>": "<value2>"
  }
}
```

response types needed

```json
{
  "uid": "<return back requested id>",
  "error": "property not found, server not running ...., timeout exceeded",
  "response": "<response as text>",
  "headers": {
    "content-type": "application/json"
  },
  "statusCode": 200
}
```
