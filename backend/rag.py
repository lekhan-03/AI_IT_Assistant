import json
import os
import re
import math
from collections import Counter

class SimpleRAG:
    """
    A lightweight retrieval engine.
    Uses basic token overlap (TF-IDF inspired) to find matches.
    """
    def __init__(self, kb_path: str = "knowledge_base.json"):
        self.kb_path = os.path.join(os.path.dirname(__file__), kb_path)
        self.articles = []
        self._load_kb()

    def _load_kb(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, "r", encoding="utf-8") as f:
                self.articles = json.load(f)
        else:
            self.articles = []

    def search(self, query: str, top_k: int = 2):
        if not self.articles:
            return []
        return self._search_bm25(query, top_k)

    def _tokenize(self, text: str):
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        stop_words = {"the", "is", "at", "which", "on", "in", "a", "an", "and", "or", "to", "for", "of", "with", "it", "this", "my", "i", "have", "but", "can", "t", "s"}
        return [w for w in words if w not in stop_words]

    def _search_bm25(self, query: str, top_k: int):
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        df = Counter()
        doc_tokens = []
        doc_lengths = []
        for article in self.articles:
            text = f"{article.get('title', '')} {article.get('content', '')} {' '.join(article.get('tags', []))}"
            tokens = self._tokenize(text)
            unique_tokens = set(tokens)
            doc_tokens.append((article, tokens))
            doc_lengths.append(len(tokens))
            for token in unique_tokens:
                df[token] += 1

        N = len(self.articles)
        if N == 0:
            return []
            
        avgdl = sum(doc_lengths) / N if N > 0 else 1
        k1 = 1.5
        b = 0.75

        scores = []
        for i, (article, tokens) in enumerate(doc_tokens):
            score = 0.0
            dl = doc_lengths[i]
            tf_dict = Counter(tokens)
            
            for q_token in query_tokens:
                if q_token in tf_dict:
                    # IDF formula
                    idf = math.log((N - df.get(q_token, 0) + 0.5) / (df.get(q_token, 0) + 0.5) + 1.0)
                    tf = tf_dict[q_token]
                    
                    # BM25 formula
                    score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
                    
            if score > 0:
                scores.append((score, article))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [article for score, article in scores][:top_k]
