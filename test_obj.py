from supabase import create_client

from src.config import configure

supabase = create_client(configure.SUPABASE_URL, configure.SUPABASE_API_KEY)

with open("README.md", "rb") as f:
    response = supabase.storage.from_(configure.BUCKET_NAME).upload(
        "README.md",
        f,
        {"Content-Type": "text/markdown", "x-upsert": "true"},
    )

    public_url = supabase.storage.from_(configure.BUCKET_NAME).get_public_url(
        "README.md"
    )
    print("[+] Public URL:", public_url)
