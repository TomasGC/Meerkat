import pytest
from pathlib import Path
import sys

# Add scripts dir to path
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

DIRTY_PYTHON = """
class GodClass:
    def handle_user(self, user): pass
    def send_email(self, to, body): pass
    def generate_report(self, data): pass
    def save_to_db(self, obj): pass
    def calculate_tax(self, amount): return amount * 86400

def process_a(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def process_b(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

try:
    risky_operation()
except:
    pass

class Animal: pass
class Mammal(Animal): pass
class Dog(Mammal): pass
class Labrador(Dog): pass
class GoldenRetriever(Labrador): pass

# TODO: fix this later
x = obj.service.repo.find_by_id(42)
"""

CLEAN_PYTHON = """
SECONDS_PER_DAY = 86400

class UserService:
    def __init__(self, repo) -> None:
        self._repo = repo

    def get_user(self, user_id: int):
        return self._repo.find_by_id(user_id)

def double_positives(items):
    return [item * 2 for item in items if item > 0]

try:
    risky_operation()
except ValueError as exc:
    logger.error("failed: %s", exc)
    raise
"""


@pytest.fixture
def dirty_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(DIRTY_PYTHON)
    return tmp_path


@pytest.fixture
def clean_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(CLEAN_PYTHON)
    return tmp_path


@pytest.fixture
def mock_ollama_violations():
    return '[{"principle": "S", "line": 5, "severity": "high", "violation": "Too many responsibilities", "suggestion": "Split class"}]'


@pytest.fixture
def mock_ollama_empty():
    return "[]"
