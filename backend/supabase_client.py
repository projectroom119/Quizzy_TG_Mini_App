from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

from typing import Optional

url: Optional[str] = os.getenv("SUPABASE_URL")
key: Optional[str] = os.getenv("SUPABASE_KEY")
if url is None or key is None:
	raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment variables.")
supabase: Client = create_client(url, key)
