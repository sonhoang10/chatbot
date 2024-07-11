from fpdf import FPDF

class ChatPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Chat History', 0, 1, 'C')

    def chapter_body(self, body, is_user):
        if is_user:
            self.set_font('Arial', 'B', 14)
        else:
            self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

def convert_chat_to_pdf(input_file_path, output_file_path):
    # Read the content of the text file
    with open(input_file_path, 'r') as file:
        chat_lines = file.readlines()

    # Initialize PDF
    pdf = ChatPDF()
    pdf.add_page()

    # Parse and add content to PDF
    is_user = True
    for line in chat_lines:
        line = line.strip()
        if line.startswith('User:'):
            is_user = True
            content = line.replace('User:', '').strip()
            pdf.chapter_body(content, is_user)
        elif line.startswith('AI:'):
            is_user = False
            content = line.replace('AI:', '').strip()
            pdf.chapter_body(content, is_user)

    # Save the PDF
    pdf.output(output_file_path)

# Example usage:
#input_file_path = 'chat_history.txt'  # Path to your input chat history text file
#output_file_path = 'Chat_History.pdf'  # Path where you want to save the output PDF
#convert_chat_to_pdf(input_file_path, output_file_path)