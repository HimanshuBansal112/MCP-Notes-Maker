from mcp.server.fastmcp import FastMCP
from fastmcp.utilities.types import Image
from pypdf import PdfReader, PdfWriter
import base64
import os
from bs4 import BeautifulSoup, NavigableString
import re
import fitz

mcp = FastMCP(name="Study_Materials_and_Notes")

BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer",
    "ul", "ol", "li", "table", "tr", "td", "th",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"
}

def remove_whitespace_nodes(node):
    for element in node.find_all(True):
        for child in list(element.contents):
            if isinstance(child, NavigableString) and not child.strip():
                child.extract()

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


@mcp.tool(name="insert_relative_to_content",
    description="""
Inserts or replaces content in an HTML notes file based on a snippet.

This function operates in two distinct modes depending on the snippet:

1. TAG-BASED MODE (HTML element match) — STRUCTURE-AWARE
   - Triggered when the snippet is a single root HTML element.
     Example:
       snippet = "<h3 class='sub-title'>Title</h3>"
   - Matches elements exactly by tag, attributes, and structure.
   - Operations:
       "before"  → insert before the element (as sibling)
       "after"   → insert after the element (as sibling)
       "replace" → replace the entire element
   - Output is prettified HTML.

   Use this mode when:
       You want sibling-level control (before/after an element)
       You want to replace an entire element (e.g. <h3>, <div>)
       You want to avoid nested/invalid HTML

---

2. TEXT-BASED MODE (plain text match) — CONTENT-LEVEL EDITING
   - Triggered when the snippet is not a single HTML element.
     Example:
       snippet = "What is ML?"
   - Performs direct string replacement in the HTML.
   - Only the first occurrence is modified.

   IMPORTANT:
   - Operations occur at the text location inside the document.
   - Inserted HTML will appear INSIDE the element containing the matched text.

   Example:
       <h3>Title</h3> + replace "Title" with "<div>Card</div>"
       → <h3><div>Card</div></h3>  (child, not sibling)

   Capabilities:
       Can insert multiple tags
       Can insert block or inline HTML
       Can handle large or complex replacements

   Limitation:
       Cannot control element boundaries (no sibling-level placement)

---

Limitations:
- Multiple top-level HTML elements in the snippet are not supported in tag mode.
- Mixed HTML fragments (e.g. "Hello <b>world</b>") are treated as text.
- Text matching is exact and case-sensitive.
- Text mode may match inside HTML attributes.
- Only the first match is processed.

Args:
    snippet: A single HTML element (for structure edits) or plain text (for content edits).
    new_html: HTML content to insert or replace with.
    position: "before", "after", or "replace" (default)

Returns:
    "Success" or an error message.
"""
)
def insert_relative_to_content(snippet: str, new_html: str, position: str = "replace") -> str:
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    try:
        if not snippet.strip():
            return "Error: snippet is empty"

        with open("notes.html", "r", encoding="utf-8") as f:
            original_content = f.read()

        soup = BeautifulSoup(original_content, "html.parser")
        remove_whitespace_nodes(soup)

        snippet_soup = BeautifulSoup(snippet, "html.parser")
        remove_whitespace_nodes(snippet_soup)

        elements = [el for el in snippet_soup.contents if getattr(el, "name", None)]
        is_tag_mode = len(elements) == 1 and len(snippet_soup.contents) == 1

        if is_tag_mode:
            snippet_element = elements[0]

            target = None
            candidates = soup.find_all(snippet_element.name, attrs=snippet_element.attrs)

            for element in candidates:
                if element.decode() == snippet_element.decode():
                    target = element
                    break

            if not target:
                return f"Error: target element not found for snippet '{str(snippet_element)}'"

            new_content = BeautifulSoup(new_html, "html.parser")
            remove_whitespace_nodes(new_content)

            if position == "before":
                for child in reversed(new_content.contents):
                    target.insert_before(child)
            elif position == "after":
                for child in new_content.contents:
                    target.insert_after(child)
            elif position == "replace":
                if len(new_content.contents) == 1:
                    target.replace_with(new_content.contents[0])
                else:
                    for child in reversed(new_content.contents):
                        target.insert_after(child)
                    target.decompose()
            else:
                return f"Error: invalid position '{position}'"

            with open("notes.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())

        else:
            snippet_text = normalize(snippet_soup.get_text())
            if not snippet_text:
                return "Error: snippet text empty"

            if snippet_text not in original_content:
                return f"Error: text snippet not found '{snippet_text}'"

            if position == "replace":
                updated_content = original_content.replace(snippet_text, new_html, 1)
            elif position == "before":
                updated_content = original_content.replace(snippet_text, new_html + snippet_text, 1)
            elif position == "after":
                updated_content = original_content.replace(snippet_text, snippet_text + new_html, 1)
            else:
                return f"Error: invalid position '{position}'"

            with open("notes.html", "w", encoding="utf-8") as f:
                f.write(updated_content)

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
