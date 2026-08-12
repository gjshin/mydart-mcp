"""Vercel 진입점. 저장소를 Vercel에 연결하면 이 파일이 함수 하나가 된다."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mydart_mcp.dart import hide_api_key_in_logs  # noqa: E402
from mydart_mcp.http import app  # noqa: E402,F401

hide_api_key_in_logs()
