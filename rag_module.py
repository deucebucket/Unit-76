# rag_module.py
# Version 2.1: Smarter Text Splitting
# This module now uses a RecursiveCharacterTextSplitter to more intelligently
# chunk the knowledge base, eliminating warnings and improving performance.

import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
# --- NEW: Import the better text splitter ---
from langchain.text_splitter import RecursiveCharacterTextSplitter

class LongTermMemory:
    def __init__(self, knowledge_dir="knowledge"):
        print("Initializing long-term memory...")

        all_texts = []
        if not os.path.exists(knowledge_dir):
            print(f"Warning: Knowledge directory '{knowledge_dir}' not found.")
            return

        for filename in os.listdir(knowledge_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(knowledge_dir, filename)
                print(f"Ingesting knowledge from: {filepath}")
                with open(filepath, 'r') as f:
                    all_texts.append(f.read())

        if not all_texts:
            print("Warning: No knowledge files found to ingest.")
            return

        raw_text = "\n\n".join(all_texts)

        # --- NEW: Use the smarter RecursiveCharacterTextSplitter ---
        # This will split by paragraph ("\n\n"), then by line ("\n"), then by sentence.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, # We can use a larger, more context-rich chunk size
            chunk_overlap=50,
            length_function=len,
        )
        texts = text_splitter.split_text(raw_text)

        print("Loading embedding model...")
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        print("Embedding model loaded.")

        self.vectorstore = Chroma.from_texts(texts, self.embeddings)
        print("Long-term memory initialized and knowledge base ingested.")

    def retrieve_context(self, query, k=3):
        if not hasattr(self, 'vectorstore'):
            return "No knowledge base loaded."

        print(f"Retrieving context for query: '{query}'")
        docs = self.vectorstore.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in docs])
