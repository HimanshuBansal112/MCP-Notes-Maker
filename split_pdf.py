from pypdf import PdfReader, PdfWriter
import base64
import os

def split_pdf(input_pdf, pages_per_pdf):
    reader = PdfReader(input_pdf)
    
    total_pages = len(reader.pages)

    for i in range(0, total_pages, pages_per_pdf):
        writer = PdfWriter()
        if i>0:
            writer.add_page(reader.pages[i-1])
        for j in range(i, min(i + pages_per_pdf, total_pages)):
            writer.add_page(reader.pages[j])
        
        if i > 0:
            output_pdf = f"pdf/pages_{i}_to_{min(i+pages_per_pdf, total_pages)}.pdf"
        else:
            output_pdf = f"pdf/pages_{i+1}_to_{min(i+pages_per_pdf, total_pages)}.pdf"
            
        with open(output_pdf, "wb") as f:
            writer.write(f)
        
os.makedirs("pdf", exist_ok=True)
split_pdf("lecture notes/input.pdf",4)