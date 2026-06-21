from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from typing import List
from io import StringIO
import traceback
import sys
import os
import re


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
        compiled = compile(code, "<user_code>", "exec")
        exec(compiled, {})

        return {
            "success": True,
            "output": sys.stdout.getvalue()
        }

    except Exception:
        return {
            "success": False,
            "output": traceback.format_exc()
        }

    finally:
        sys.stdout = old_stdout


def analyze_error_with_ai(code: str, tb: str):
    match = re.search(
        r'File "<user_code>", line (\d+)',
        tb
    )

    if match:
        return [int(match.group(1))]

    return []


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
