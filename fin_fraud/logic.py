
client = get_client()
COLLECTION_NAME = "Scam Genome"
TARGET_SIZE = 1024

def analyze_image_risk(image_file):
    """Skip local CLIP inference on free hosting."""
    return {
        "risk_level": "Unknown",
        "probability": 0.0,
        "analysis": (
            "Local image classification is temporarily disabled "
            "to reduce memory usage on free hosting."
        ),
        "source": None
    }