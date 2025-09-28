#!/usr/bin/env python3
"""
创建测试PDF文件
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def create_test_pdf():
    """创建一个简单的测试PDF文件"""
    filename = "/tmp/test_document.pdf"
    
    # 创建PDF
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # 第一页
    c.drawString(100, height - 100, "Test Document - Page 1")
    c.drawString(100, height - 150, "This is a test PDF document created for conversion testing.")
    c.drawString(100, height - 200, "It contains multiple pages with text content.")
    c.drawString(100, height - 250, "The purpose is to test PDF to DOCX conversion libraries.")
    
    # 添加一些表格数据
    c.drawString(100, height - 300, "Sample Table:")
    c.drawString(120, height - 320, "Name          | Age | City")
    c.drawString(120, height - 340, "John Doe      | 25  | New York")
    c.drawString(120, height - 360, "Jane Smith    | 30  | Los Angeles")
    c.drawString(120, height - 380, "Bob Johnson   | 35  | Chicago")
    
    c.showPage()
    
    # 第二页
    c.drawString(100, height - 100, "Test Document - Page 2")
    c.drawString(100, height - 150, "This is the second page of the test document.")
    c.drawString(100, height - 200, "It contains additional text content for testing.")
    c.drawString(100, height - 250, "Multiple pages help test page break handling.")
    
    # 添加更多内容
    c.drawString(100, height - 300, "Additional Information:")
    c.drawString(120, height - 320, "• This is a bullet point")
    c.drawString(120, height - 340, "• Another bullet point")
    c.drawString(120, height - 360, "• Third bullet point")
    
    c.showPage()
    
    # 第三页
    c.drawString(100, height - 100, "Test Document - Page 3")
    c.drawString(100, height - 150, "This is the final page of the test document.")
    c.drawString(100, height - 200, "It concludes our test content.")
    c.drawString(100, height - 250, "Thank you for testing the conversion!")
    
    c.save()
    
    print(f"✅ 测试PDF文件已创建: {filename}")
    print(f"📊 文件大小: {os.path.getsize(filename) / 1024:.2f} KB")
    
    return filename

if __name__ == "__main__":
    create_test_pdf()
