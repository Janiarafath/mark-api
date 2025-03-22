from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
import io

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

@app.get("/")
async def root():
    return {"message": "API is working"}

@app.post("/analyze-marksheet")
async def analyze_marksheet(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        response = model.generate_content([STRUCTURED_PROMPT, image])
        response.resolve()
        
        if response.text:
            clean_text = response.text.split("Notes:")[0].strip()
            return {"status": "success", "data": clean_text}
            
    except Exception as e:
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