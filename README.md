# MCP-Notes-Maker
## Install and setup python uv
1. Install `uv` by running `pip install uv` in Command Prompt.
2. Go to the project folder
3. Run
   
   ```bash
   uv venv
   .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

## How to use:
1. Place `input.pdf` in `lecture notes` folder.
2. Run `split_pdf.py` using uv.

## For AI connection
You can connect any client to this tool either programmatically or using AI apps.

### How to add to Claude Desktop on Windows
1. Open `claude_desktop_config.json`
2. Add this configuration:
   ```json
    "mcpServers": {
     "notesMaker": {
       "command": "path_to_uv",
       "args": [
         "run",
         "--directory",
         "path_to_this_project",
         "tools.py"
       ]
     }
   }
   ```
   You can get `path_to_uv` using `where uv` in cmd.
   
   You have to paste parent directory of `tools.py` in `path_to_this_project`.

3. Restart Claude Desktop
