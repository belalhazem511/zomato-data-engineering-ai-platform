
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    device=-1
)

reviews = [
    "Great eco-friendly packaging. Delivered right on time.",
    "Far too expensive for what you get.",
    "An average experience overall.",
    "The delivery partner was polite and helpful."
]

for review in reviews:
    result = classifier(review)[0]
    print(f"Review: {review}")
    print(f"Sentiment: {result['label']}")
    print(f"Confidence: {result['score']:.2%}")
    print("-" * 40)
