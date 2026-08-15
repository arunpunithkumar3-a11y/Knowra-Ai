import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from supabase import Client, create_client

app = FastAPI()

# Replace these with your actual Supabase API credentials
SUPABASE_URL = "https://supabase.co"
SUPABASE_KEY = "your-long-anon-public-key-here"
BUCKET_NAME = "my-bucket"

# Initialize the Supabase cloud client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Read the file data into memory
        file_content = await file.read()

        # Upload directly to the Supabase cloud bucket
        # We use file.filename as the destination path inside the bucket
        response = supabase.storage.from_(BUCKET_NAME).upload(
            path=file.filename,
            file=file_content,
            file_options={"content-type": file.content_type, "x-upsert": "true"},
        )

        # Get the public web URL to view or download the file
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file.filename)

        return {"status": "Success", "filename": file.filename, "cloud_url": public_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
