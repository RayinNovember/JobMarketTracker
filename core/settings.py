import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED = ['APIFY_TOKEN', 'SUPABASE_DB_URL']

def get(name:str) -> str:
    """Get a required environment variable."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

def check() -> None:
    """Check that all required environment variables are set."""
    for name in REQUIRED:
        value = os.environ.get(name,"")
        status = f'set ({len(value)} characters)' if value else 'not set'
        print(f'{name}: {status}')
        
if __name__ == "__main__":
    check()
    
