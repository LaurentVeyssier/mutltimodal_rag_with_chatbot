from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Page 1: Text content
    c.drawString(100, 750, "Introduction to Multimodal RAG")
    c.drawString(100, 730, "This is a sample PDF document created for testing the RAG application.")
    c.drawString(100, 710, "It contains some text that the LLM should be able to retrieve and answer questions about.")
    c.drawString(100, 690, "The concept of RAG (Retrieval-Augmented Generation) combines information retrieval with text generation.")
    
    # Draw a simple shape to simulate an image (though it's vector graphics, pymupdf might extract it or we rely on text for now)
    # For actual image extraction test, we might need a real image, but let's start with text.
    c.rect(100, 500, 200, 100, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(120, 550, "This is a black rectangle")
    
    c.showPage()
    c.save()

if __name__ == "__main__":
    create_pdf("sample_test.pdf")
