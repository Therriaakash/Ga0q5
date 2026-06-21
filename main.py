from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from io import StringIO
import traceback
import sys
import os

from google import genai
from google.genai import types

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    error: List[int]
    result: str


class ErrorAnalysis(BaseModel):
    error_lines: List[int]


def execute_python_code(code: str):
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code, {})
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}

    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}

    finally:
        sys.stdout = old_stdout


def analyze_error_with_ai(code: str, tb: str):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
Analyze the following Python code and traceback.

CODE:
{code}

TRACEBACK:
{tb}

Return the line number(s) where the error occurred.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "error_lines": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["error_lines"],
            },
        ),
    )

    result = ErrorAnalysis.model_validate_json(response.text)
    return result.error_lines


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/code-interpreter", response_model=CodeResponse)
def code_interpreter(req: CodeRequest):

    execution = execute_python_code(req.code)

    if execution["success"]:
        return {"error": [], "result": execution["output"]}

    error_lines = analyze_error_with_ai(req.code, execution["output"])

    return {"error": error_lines, "result": execution["output"]}
