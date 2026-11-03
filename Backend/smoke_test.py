import os

from dotenv import load_dotenv

load_dotenv()


def check(name, fn):
    try:
        result = fn()
        print(f"[ok]   {name}: {result}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")


def check_db():
    import psycopg

    url = os.environ["DATABASE_URL"].replace("+psycopg", "")

    with psycopg.connect(url) as conn:
        row = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()

        if row:
            status = "present"
        else:
            status = "MISSING"

        return "connected, vector extension " + status


def check_groq():
    from langchain_groq import ChatGroq

    llm = ChatGroq(model=os.environ["GROQ_SMALL_MODEL"])
    reply = llm.invoke("Reply with the single word: ready")
    return reply.content


def check_gemini():
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model=os.environ["GEMINI_STRONG_MODEL"])
    reply = llm.invoke("Reply with the single word: ready")
    return reply.content


def check_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    emb = HuggingFaceEmbeddings(model_name=os.environ["EMBEDDING_MODEL"])
    vector = emb.embed_query("motor claim")
    return f"vector length {len(vector)} (should be 384)"


def check_tesseract():
    import pytesseract

    return str(pytesseract.get_tesseract_version())


if __name__ == "__main__":
    check("Postgres + pgvector", check_db)
    check("Groq", check_groq)
    check("Gemini", check_gemini)
    check("HF embeddings (first run downloads the model)", check_embeddings)
    check("Tesseract", check_tesseract)

    print("Now open LangSmith -> project ClaimPilot and look for the Groq and Gemini traces.")