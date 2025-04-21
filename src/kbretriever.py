from kb_ingest import build_retriever, create_weaviate_client
from intent_emotion_router import analyse


#for testing kb after uploading to weaviate
if __name__ == "__main__":
    CLASS_NAME = "CarList"          # or whatever class you ingested
    retriever  = build_retriever(CLASS_NAME)

    while True:
        query = input("\nUser: ")
        if not query.strip():
            break

        intent, emotion = analyse(query)              # ← Phase 3
        # Choose category filter based on intent
        cat = None
        if intent == "TechSupport":
            cat = "Support"
        elif intent == "SalesInquiry":
            cat = "Sales"

        docs = build_retriever(CLASS_NAME, category=cat).invoke(query)

        print(f"\n[Intent:{intent} | Emotion:{emotion} | Cat:{cat}]")
        for d in docs[:2]:
            print("⮡", d.page_content[:120], "…")
