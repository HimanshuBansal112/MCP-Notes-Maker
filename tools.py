from mcp.server.fastmcp import FastMCP
from fastmcp.utilities.types import Image
from pypdf import PdfReader, PdfWriter
import base64
import os
from bs4 import BeautifulSoup
import re
import fitz

mcp = FastMCP(name="Study_Materials_and_Notes")

def pdf_to_img(file_path, dpi, max_size_kb=800, reduce_factor=0.9):
    output = []
    with fitz.open(file_path) as doc:
        num_pages = len(doc)
        current_dpi = dpi
        while True:
            total_size_bytes = 0
            temp_output = []
            zoom = current_dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=matrix)
                img_bytes = pix.tobytes("png")
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                size_bytes = len(img_base64.encode("utf-8"))
                total_size_bytes += size_bytes
                img_data = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": f"data:image/png;base64,{img_base64}"
                    }
                }
                temp_output.append(img_data)

            total_size_kb = total_size_bytes / 1024
            if total_size_kb <= max_size_kb or current_dpi <= 50:
                output = temp_output
                break
            else:
                current_dpi = int(current_dpi * reduce_factor)
    return output

@mcp.tool(name="Find_materials",
    description="Search the material for study and provides path for material.")
def Find_materials()->str:
    html_files = []
    for file_name in os.listdir("pdf"):
        if file_name.endswith(".pdf"):
            html_files.append(os.path.join("pdf", file_name))
    return str(html_files)

@mcp.tool(name="Reads_materials",
    description="""Reads the material which exist only and only told by find material. 
    Instructions: 
    1. It will have images of pdf, so decode carefully from base64.""")
def Reads_materials(file_path:str):
    dpi=150
    file_path = file_path.replace("/", "\\")
    while "\\\\" in file_path:
        file_path = file_path.replace("\\\\", "\\")
    parts = file_path.split(os.sep)
    if len(parts) == 2 and parts[0] == "pdf":
        return pdf_to_img(file_path, dpi)
    else:
        return "Invalid file path. Report the error and stop processing further files."

@mcp.tool(name="Reads_notes",
    description="Reads the notes")
def Reads_notes()->str:
    with open("notes.html", "r", encoding='utf-8') as file:
        content = file.read()
    return content

@mcp.tool(name="Update_notes",
    description="It update the notes. It expects body content of html and appends those to the body as last element tags. It expects notes to be pre-read for consistency(as updates).")
def Update_notes(content: str) -> str:
    with open("notes.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    if soup.body:
        html_text = content.replace("\\n", "\n").strip()
        wrapper = BeautifulSoup(f"<div class='added-section'>{html_text}</div>", "html.parser")
        soup.body.append(wrapper)

    with open("notes.html", "w", encoding="utf-8") as f:
        f.write(str(soup))

    return "Success"


@mcp.tool(name="insert_relative_to_text",
    description="""
    Inserts or replaces content in an HTML notes based on a snippet.
    
    Args:
        snippet: Text or HTML snippet to locate in the notes.(It cannot be empty, use Update_notes if starting fresh)
        new_html: HTML content to insert.(It will insert inside body only, so no need for html, head, body to resend)
        position: "before" (default), "after", or "replace".
    
    Returns:
        "Success", "Not found", or an error message.
    """)
def insert_relative_to_text(snippet: str, new_html: str, position: str = "before") -> str:
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    try:
        if not snippet.strip():
            return "Error: snippet is empty"

        with open("notes.html", "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        try:
            snippet_soup = BeautifulSoup(snippet, "html.parser")
            snippet_text = normalize(snippet_soup.get_text())
        except Exception:
            snippet_text = normalize(snippet)

        if not snippet_text:
            return "Error: snippet contains no text to match"

        target = None
        for element in soup.find_all(string=True):
            if snippet_text in normalize(element):
                target = element.parent
                break

        if not target:
            return f"Error: target element not found for snippet '{snippet_text}'"

        if not hasattr(target, "insert_before"):
            return f"Error: target element is empty or invalid for insertion"

        wrapped_html = f"<div class='inserted'>{new_html.strip()}</div>"
        new_block = BeautifulSoup(wrapped_html, "html.parser").div
        if not new_block:
            return "Error: new HTML could not be parsed into a valid element"

        if position == "before":
            for child in reversed(new_block.contents):
                target.insert_before(child)
        elif position == "after":
            for child in new_block.contents:
                target.insert_after(child)
        elif position == "replace":
            target.replace_with(new_block)
        else:
            return f"Error: invalid position '{position}'"

        with open("notes.html", "w", encoding="utf-8") as f:
            f.write(str(soup))

        return "Success"

    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    os.makedirs("pdf", exist_ok=True)
    format_html="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Notes</title>
  <script>
    MathJax = {
      tex: { inlineMath: [['$', '$']] },
      svg: { fontCache: 'global' }
    };
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
</head>
<body>
  <!-- This is the empty notes. With telling, it uses LaTeX. -->
</body>
</html>"""
    if not os.path.exists("notes.html"):
        with open("notes.html", 'w') as file:
            file.write(format_html)
    mcp.run()
