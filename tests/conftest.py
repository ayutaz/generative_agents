"""
conftest.py — pytest設定とスタブモジュールの注入。

utils.pyはAPIキーを含むためリポジトリに存在しない。
バックエンドモジュールは全て `from utils import *` でインポートするため、
テスト実行時にインポートが失敗しないようスタブを注入する。
"""
import sys
import os
import types
import pathlib

# ---------------------------------------------------------------------------
# 1. sys.path に reverie/backend_server を追加
# ---------------------------------------------------------------------------
_BACKEND = str(pathlib.Path(__file__).resolve().parent.parent
               / "reverie" / "backend_server")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# ---------------------------------------------------------------------------
# 2. utils スタブモジュールを sys.modules["utils"] に注入
# ---------------------------------------------------------------------------
_utils_stub = types.ModuleType("utils")
_utils_stub.openai_api_key = "test-key"
_utils_stub.maze_assets_loc = ""
_utils_stub.env_matrix = ""
_utils_stub.env_visuals = ""
_utils_stub.fs_storage = ""
_utils_stub.fs_temp_storage = ""
_utils_stub.collision_block_id = "32125"
_utils_stub.debug = False
sys.modules["utils"] = _utils_stub

# ---------------------------------------------------------------------------
# 3. persona.prompt_template.gpt_structure スタブを注入
# ---------------------------------------------------------------------------
_gpt_struct = types.ModuleType("persona.prompt_template.gpt_structure")

def _get_embedding_stub(text, *args, **kwargs):
    """ダミーembedding: テキスト長に基づく決定的ベクトルを返す（tuple）"""
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()
    return tuple(int(c, 16) / 15.0 for c in h[:10])

_gpt_struct.get_embedding = _get_embedding_stub
_gpt_struct.ChatGPT_request = lambda *a, **kw: ""
_gpt_struct.GPT4_request = lambda *a, **kw: ""
_gpt_struct.GPT4_safe_generate_response = lambda *a, **kw: ""
_gpt_struct.ChatGPT_safe_generate_response = lambda *a, **kw: ""
_gpt_struct.GPT_request = lambda *a, **kw: ""
_gpt_struct.generate_prompt = lambda *a, **kw: ""
_gpt_struct.safe_generate_response = lambda *a, **kw: ""

sys.modules["persona.prompt_template.gpt_structure"] = _gpt_struct

# Also make sure parent packages exist in sys.modules
for _pkg in ["persona", "persona.prompt_template",
             "persona.cognitive_modules", "persona.memory_structures"]:
    if _pkg not in sys.modules:
        _mod = types.ModuleType(_pkg)
        # Set __path__ so Python treats the stub as a package and can
        # resolve child modules from the real filesystem.
        _pkg_dir = os.path.join(_BACKEND, _pkg.replace(".", os.sep))
        _mod.__path__ = [_pkg_dir]
        sys.modules[_pkg] = _mod

# ---------------------------------------------------------------------------
# 4. persona.prompt_template.run_gpt_prompt スタブを注入
# ---------------------------------------------------------------------------
_run_gpt = types.ModuleType("persona.prompt_template.run_gpt_prompt")
_run_gpt.run_gpt_prompt_focal_pt = lambda *a, **kw: (["focal"], None)
_run_gpt.run_gpt_prompt_insight_and_guidance = lambda *a, **kw: ({}, None)
_run_gpt.run_gpt_prompt_event_triple = lambda *a, **kw: (("s", "p", "o"), None)
_run_gpt.run_gpt_prompt_event_poignancy = lambda *a, **kw: (1, None)
_run_gpt.run_gpt_prompt_chat_poignancy = lambda *a, **kw: (1, None)
_run_gpt.run_gpt_prompt_planning_thought_on_convo = lambda *a, **kw: ("thought", None)
_run_gpt.run_gpt_prompt_memo_on_convo = lambda *a, **kw: ("memo", None)

sys.modules["persona.prompt_template.run_gpt_prompt"] = _run_gpt

# ---------------------------------------------------------------------------
# 5. 共通フィクスチャパスのヘルパー
# ---------------------------------------------------------------------------
import pytest

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"

@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR
