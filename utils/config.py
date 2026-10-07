"""Environment configuration and validated learning preferences."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from dotenv import load_dotenv
load_dotenv(ROOT / '.env', override=False)
SUMMARY_MODEL = os.getenv('RECALLAI_SUMMARY_MODEL', 'Falconsai/text_summarization')
EMBEDDING_MODEL = os.getenv('RECALLAI_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
DEPTHS = {'Quick': {'length': 'Short', 'chunk_size': 320, 'concepts': 10},
          'Standard': {'length': 'Medium', 'chunk_size': 400, 'concepts': 20},
          'Deep': {'length': 'Detailed', 'chunk_size': 440, 'concepts': 30}}
DEFAULTS = {'depth': 'Standard', 'quiz_length': 5, 'difficulty': 'Adaptive', 'flashcards': 10,
            'generation': 'Balanced', 'chunk_size': None, 'retrieval_k': 4, 'feedback': 'After submission'}

def data_dir():
    path = Path(os.getenv('RECALLAI_DATA_DIR', str(ROOT / 'data' / 'private'))).expanduser()
    return (path if path.is_absolute() else ROOT/path).resolve()

def db_path():
    path = Path(os.getenv('RECALLAI_DB_PATH', str(data_dir() / 'recallai.sqlite3'))).expanduser()
    return (path if path.is_absolute() else ROOT/path).resolve()

def validate_preferences(values):
    result = {**DEFAULTS, **values}
    for key, options in {'depth': DEPTHS, 'quiz_length': [5,10,15], 'flashcards': [5,10,20],
                         'difficulty': ['Adaptive','Easy','Medium','Hard'],
                         'generation': ['Concise','Balanced','Detailed'],
                         'feedback': ['After submission','Immediate']}.items():
        if result[key] not in options:
            raise ValueError(f'Choose a valid {key.replace("_", " ")}.')
    if result['chunk_size'] is not None and not 200 <= int(result['chunk_size']) <= 440:
        raise ValueError('Advanced chunk size must be between 200 and 440.')
    if not 1 <= int(result['retrieval_k']) <= 8:
        raise ValueError('Retrieval results must be between 1 and 8.')
    return {k: result[k] for k in DEFAULTS}

def processing_location():
    # All implemented inference adapters run on this machine. No cloud adapter exists.
    return 'Local'
