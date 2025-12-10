from transformers import pipeline

print("Loading FinBERT... (This will take a minute the first time)")

# 1. Load the "Brain" (FinBERT)
finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")

# 2. Test Sentences
sentences = [
    "Dangote Cement profits skyrocketed this quarter!", 
    "Naira devaluation is hurting banking stocks badly.",
    "The market opens at 9am."
]

# 3. Get Results
print("\n--- RESULTS ---")
results = finbert(sentences)

for text, result in zip(sentences, results):
    print(f"Text: {text}")
    print(f"Sentiment: {result['label']} (Score: {round(result['score'], 2)})")
    print("-" * 30)