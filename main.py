from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
import io
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Marksheet Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
GEMINI_API_KEY = "AIzaSyDKxXUzpWvGQiTeJZIKZKLfBMM2TTLDYrI"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Marksheet Analysis</title>
            <style>
                body { font-family: Arial; padding: 20px; max-width: 800px; margin: 0 auto; }
                .form-container { margin: 20px 0; padding: 20px; border: 1px solid #ccc; border-radius: 5px; }
                #result { white-space: pre-wrap; margin-top: 20px; padding: 10px; background: #f5f5f5; }
                .loading { display: none; }
            </style>
        </head>
        <body>
            <h1>Marksheet Analysis</h1>
            <div class="form-container">
                <form id="uploadForm">
                    <input type="file" id="file" name="file" accept="image/*" required>
                    <button type="submit">Analyze Marksheet</button>
                </form>
                <div id="loading" class="loading">Processing...</div>
            </div>
            <div id="result"></div>

            <script>
                const form = document.getElementById('uploadForm');
                const loading = document.getElementById('loading');
                const result = document.getElementById('result');

                form.onsubmit = async (e) => {
                    e.preventDefault();
                    loading.style.display = 'block';
                    result.textContent = '';

                    const formData = new FormData();
                    formData.append('file', document.getElementById('file').files[0]);
                    
                    try {
                        const response = await fetch('/analyze-marksheet', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        result.textContent = data.data;
                    } catch (error) {
                        result.textContent = 'Error processing image';
                    } finally {
                        loading.style.display = 'none';
                    }
                };
            </script>
        </body>
    </html>
    """

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

@app.post("/analyze-marksheet")
async def analyze_marksheet(file: UploadFile = File(...)):
    try:
        # Validate file
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid file type")

        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Process image with Gemini
        try:
            response = model.generate_content([STRUCTURED_PROMPT, image])
            response.resolve()  # Ensure response is complete
            
            if response.text:
                # Clean response and format
                clean_text = response.text
                if "Notes:" in clean_text:
                    clean_text = clean_text.split("Notes:")[0].strip()
                
                # Format response for better display
                formatted_response = {
                    "status": "success",
                    "data": clean_text.replace('\n', '<br>')  # Convert newlines to HTML breaks
                }
                return formatted_response
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")  # Debug log
            raise HTTPException(status_code=500, detail="Analysis failed")

    except Exception as e:
        print(f"Processing error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail="Processing error")

# Your structured prompt
STRUCTURED_PROMPT = """CRITICAL INSTRUCTIONS:

1. Register Number (RRN) Extraction:
   - Locate any numeric sequence that appears to be a registration/roll number
   - Valid formats include 6-12 digit numbers
   - Can be in any ink color (black, blue, red)
   - Usually found at the top of the sheet

2. Subject/Course Code Detection:
   - Format: XXXX-YY (where X = letters, Y = numbers)
   - Must include the hyphen
   - Typically found near the top
   - Can be in any standard ink color

3. Mark Extraction Rules:
   - Focus on marks written in RED ink only
   - Each mark should be between 0-20
   - Look for these specific patterns:
     * Single digits (0-9)
     * Double digits (10-20)
     * Dashes (-) indicating unmarked questions
   - Ignore all marks in other colors

4. Section-wise Processing:
   Part A:
   - Questions 1-5
   - Each worth up to 20 marks
   - Look for single column format

   Part B:
   - Questions 6-7
   - Each has subsections a & b
   - Each subsection has i, ii, iii parts
   - Maximum 20 marks per subpart

   Part C:
   - Question 8
   - Similar structure to Part B questions
   - a & b subsections with i, ii, iii parts
   - Maximum 20 marks per subpart

5. Data Validation:
   - Verify all extracted marks are within 0-20 range
   - Confirm section totals are calculated correctly
   - Flag any anomalies or unclear entries

Output Format:
RRN: [extracted number]
Course Code: [extracted code]

Part A:
Q1: [mark]
Q2: [mark]
Q3: [mark]
Q4: [mark]
Q5: [mark]

Part B:
Q6:
a.i: [mark]
a.ii: [mark]
a.iii: [mark]
b.i: [mark]
b.ii: [mark]
b.iii: [mark]

Q7:
[same format as Q6]

Part C:
Q8:
[same format as Q6]

Notes:
- Use "-" for unmarked questions
- Only process marks in red ink
- Each mark must be 0-20
- Maintain exact format shown above"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)