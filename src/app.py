"""Flask app for Devanagari OCR with dropdown image selection and .txt output."""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict
import base64
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

from src.utils.transliteration import transliterate_word
from src.utils.ocr_engine import get_gemini_ocr
from src.utils.metrics import calculate_wer_cer, get_error_details

# Load environment variables
load_dotenv()

# Configuration
SAMPLE_DIR = Path("data/sampled_images")
OUTPUT_DIR = Path("data/ground_truth_texts")
MAPPING_FILE = Path("data/annotation_mapping.json")
USAGE_FILE = Path("data/api_usage.json")
METRICS_FILE = Path("data/metrics_history.json")

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Create Flask app
app_dir = Path(__file__).parent.parent
app = Flask(__name__, 
            template_folder=str(app_dir / "templates"),
            static_folder=str(app_dir / "static"))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Load or create annotation mapping
def load_mapping() -> Dict:
    """Load annotation mapping (which images are done)."""
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "in_progress": None}

def save_mapping(mapping: Dict):
    """Save annotation mapping."""
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)

# Load or create API usage tracking
def load_usage() -> Dict:
    """Load cumulative API usage statistics."""
    if USAGE_FILE.exists():
        with open(USAGE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "total_requests": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "last_request": None
    }

def save_usage(usage: Dict):
    """Save API usage statistics."""
    with open(USAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(usage, f, indent=2)

def add_usage_record(prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: float):
    """Add a single API usage record to cumulative stats."""
    usage = load_usage()
    usage["total_requests"] += 1
    usage["total_prompt_tokens"] += prompt_tokens
    usage["total_completion_tokens"] += completion_tokens
    usage["total_tokens"] += total_tokens
    usage["total_cost"] = round(usage["total_cost"] + cost, 8)
    usage["last_request"] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
        "timestamp": datetime.now().isoformat()
    }
    save_usage(usage)

# Load or create metrics history
def load_metrics_history() -> Dict:
    """Load metrics history (per-page WER/CER records)."""
    if METRICS_FILE.exists():
        with open(METRICS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "pages": [],
        "cumulative": {
            "total_pages": 0,
            "avg_wer": 0.0,
            "avg_cer": 0.0,
            "avg_word_accuracy": 0.0,
            "avg_char_accuracy": 0.0,
        }
    }

def save_metrics_history(history: Dict):
    """Save metrics history."""
    with open(METRICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_metrics_record(image_name: str, wer: float, cer: float, 
                       word_accuracy: float, char_accuracy: float,
                       ref_word_count: int, hyp_word_count: int,
                       ref_char_count: int, hyp_char_count: int):
    """Add a single page metrics record to history."""
    history = load_metrics_history()
    
    # Check if this page already exists, update it
    existing = None
    for i, page in enumerate(history["pages"]):
        if page["image_name"] == image_name:
            existing = i
            break
    
    record = {
        "image_name": image_name,
        "wer": round(wer, 4),
        "cer": round(cer, 4),
        "word_accuracy": round(word_accuracy, 4),
        "char_accuracy": round(char_accuracy, 4),
        "ref_word_count": ref_word_count,
        "hyp_word_count": hyp_word_count,
        "ref_char_count": ref_char_count,
        "hyp_char_count": hyp_char_count,
        "timestamp": datetime.now().isoformat()
    }
    
    if existing is not None:
        history["pages"][existing] = record
    else:
        history["pages"].append(record)
    
    # Recalculate cumulative stats
    total_pages = len(history["pages"])
    if total_pages > 0:
        avg_wer = sum(p["wer"] for p in history["pages"]) / total_pages
        avg_cer = sum(p["cer"] for p in history["pages"]) / total_pages
        avg_word_acc = sum(p["word_accuracy"] for p in history["pages"]) / total_pages
        avg_char_acc = sum(p["char_accuracy"] for p in history["pages"]) / total_pages
    else:
        avg_wer = avg_cer = avg_word_acc = avg_char_acc = 0.0
    
    history["cumulative"] = {
        "total_pages": total_pages,
        "avg_wer": round(avg_wer, 4),
        "avg_cer": round(avg_cer, 4),
        "avg_word_accuracy": round(avg_word_acc, 4),
        "avg_char_accuracy": round(avg_char_acc, 4),
    }
    
    save_metrics_history(history)
    return history["cumulative"]

def recover_metrics():
    """Recalculate metrics from existing ground truth files and their OCR drafts.
    
    This is useful if metrics were lost or if we want to rebuild history.
    Scans data/ground_truth_texts/ and data/ocr_drafts/ directories.
    """
    history = load_metrics_history()
    recovered = 0
    
    # Check if we have ground truth files
    if not OUTPUT_DIR.exists():
        return {"recovered": 0}
    
    for txt_file in OUTPUT_DIR.glob("*.txt"):
        image_name = txt_file.stem + ".png"
        
        # Check if already in history
        if any(p["image_name"] == image_name for p in history["pages"]):
            continue
        
        # Read ground truth
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                ground_truth = f.read().strip()
        except:
            continue
        
        # Try to find corresponding OCR draft
        ocr_file = OUTPUT_DIR.parent / "ocr_drafts" / txt_file.name
        if not ocr_file.exists():
            continue
        
        try:
            with open(ocr_file, 'r', encoding='utf-8') as f:
                ocr_text = f.read().strip()
        except:
            continue
        
        if ground_truth and ocr_text:
            try:
                details = get_error_details(ground_truth, ocr_text)
                add_metrics_record(
                    image_name,
                    details["wer"],
                    details["cer"],
                    details["word_accuracy"],
                    details["char_accuracy"],
                    details["ref_word_count"],
                    details["hyp_word_count"],
                    details["ref_char_count"],
                    details["hyp_char_count"],
                )
                recovered += 1
            except:
                pass
    
    return {"recovered": recovered}

# Get all available images (not completed)
def get_available_images() -> List[str]:
    """Get list of images that haven't been annotated yet.
    
    Checks both the mapping file and the ground truth files directory.
    This ensures images with saved ground truth files are always excluded,
    even if the mapping file is out of sync.
    """
    mapping = load_mapping()
    completed = set(mapping.get("completed", []))
    
    # Also check ground truth files as backup
    if OUTPUT_DIR.exists():
        for txt_file in OUTPUT_DIR.glob("*.txt"):
            image_name = txt_file.stem + ".png"
            completed.add(image_name)
    
    all_images = []
    if SAMPLE_DIR.exists():
        for f in sorted(SAMPLE_DIR.glob("*.png")):
            if f.name not in completed:
                all_images.append(f.name)
    
    return all_images

# Get image path
def get_image_path(image_name: str) -> Path:
    """Get full path to image."""
    return SAMPLE_DIR / image_name

# Save ground truth as .txt file
def save_ground_truth_txt(image_name: str, text: str) -> Path:
    """Save ground truth text with same name as image but .txt extension."""
    # Convert image_name.png to image_name.txt
    txt_name = Path(image_name).stem + ".txt"
    txt_path = OUTPUT_DIR / txt_name
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return txt_path

# Image to base64
def image_to_base64(image_path: Path) -> str:
    """Convert image to base64 for display."""
    try:
        if not image_path.exists():
            return ""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        print(f"Error converting image: {e}")
        return ""

@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")

@app.route("/api/images", methods=["GET"])
def get_images():
    """Get list of available images for dropdown."""
    try:
        available = get_available_images()
        mapping = load_mapping()
        
        response = jsonify({
            "success": True,
            "images": available,
            "total": len(available),
            "completed": len(mapping.get("completed", []))
        })
        # Prevent browser caching
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Error getting images: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/load_image", methods=["POST"])
def load_image():
    """Load a specific image."""
    data = request.json
    image_name = data.get("image_name")
    
    if not image_name:
        return jsonify({"success": False, "message": "No image specified"})
    
    image_path = get_image_path(image_name)
    if not image_path.exists():
        return jsonify({"success": False, "message": "Image not found"})
    
    # Convert to base64
    image_b64 = image_to_base64(image_path)
    
    # Update mapping
    mapping = load_mapping()
    mapping["in_progress"] = image_name
    save_mapping(mapping)
    
    return jsonify({
        "success": True,
        "image_name": image_name,
        "image_base64": image_b64,
    })

@app.route("/api/generate_ocr", methods=["POST"])
def generate_ocr():
    """Generate OCR for current image."""
    data = request.json
    image_name = data.get("image_name")
    
    if not image_name:
        return jsonify({"success": False, "message": "No image loaded"})
    
    image_path = get_image_path(image_name)
    if not image_path.exists():
        return jsonify({"success": False, "message": "Image not found"})
    
    try:
        # Generate OCR
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return jsonify({
                "success": False,
                "message": "OpenRouter API key not configured"
            })
        
        ocr_result = get_gemini_ocr(str(image_path), api_key=api_key)
        ocr_text = ocr_result["text"]
        
        # Track usage
        add_usage_record(
            ocr_result["prompt_tokens"],
            ocr_result["completion_tokens"],
            ocr_result["total_tokens"],
            ocr_result["estimated_cost"]
        )
        
        return jsonify({
            "success": True,
            "ocr_text": ocr_text,
            "tokens": {
                "prompt": ocr_result["prompt_tokens"],
                "completion": ocr_result["completion_tokens"],
                "total": ocr_result["total_tokens"],
                "cost": ocr_result["estimated_cost"],
            },
            "message": f"OCR generated ({ocr_result['total_tokens']} tokens)"
        })
        
    except Exception as e:
        print(f"Error generating OCR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })

@app.route("/api/save_annotation", methods=["POST"])
def save_annotation():
    """Save ground truth, calculate WER/CER, and mark image as completed."""
    data = request.json
    image_name = data.get("image_name")
    ground_truth = data.get("ground_truth", "")
    ocr_draft = data.get("ocr_draft", "")
    
    if not image_name:
        return jsonify({"success": False, "message": "No image specified"})
    
    try:
        # Save as .txt file
        txt_path = save_ground_truth_txt(image_name, ground_truth)
        
        # Calculate and save WER/CER if OCR draft is available
        metrics = None
        if ocr_draft and ground_truth:
            try:
                details = get_error_details(ground_truth, ocr_draft)
                cumulative = add_metrics_record(
                    image_name,
                    details["wer"],
                    details["cer"],
                    details["word_accuracy"],
                    details["char_accuracy"],
                    details["ref_word_count"],
                    details["hyp_word_count"],
                    details["ref_char_count"],
                    details["hyp_char_count"],
                )
                metrics = {
                    "wer": details["wer"],
                    "cer": details["cer"],
                    "word_accuracy": details["word_accuracy"],
                    "char_accuracy": details["char_accuracy"],
                    "cumulative": cumulative
                }
            except Exception as e:
                print(f"Error calculating metrics: {e}")
        
        # Update mapping
        mapping = load_mapping()
        if image_name not in mapping["completed"]:
            mapping["completed"].append(image_name)
        mapping["in_progress"] = None
        save_mapping(mapping)
        
        # Get remaining images
        available = get_available_images()
        
        return jsonify({
            "success": True,
            "message": "Saved successfully",
            "txt_path": str(txt_path),
            "remaining": len(available),
            "metrics": metrics
        })
        
    except Exception as e:
        print(f"Error saving: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/transliterate", methods=["POST"])
def transliterate():
    """Get transliteration suggestions."""
    data = request.json
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"suggestions": []})
    
    suggestions = transliterate_word(text)
    return jsonify({"suggestions": suggestions[:5]})

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get annotation statistics."""
    try:
        mapping = load_mapping()
        total_images = len(list(SAMPLE_DIR.glob("*.png"))) if SAMPLE_DIR.exists() else 0
        completed = len(mapping.get("completed", []))
        
        response = jsonify({
            "total": total_images,
            "completed": completed,
            "remaining": total_images - completed,
            "progress": (completed / total_images * 100) if total_images > 0 else 0
        })
        # Prevent browser caching
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/usage", methods=["GET"])
def get_usage():
    """Get API usage statistics."""
    try:
        usage = load_usage()
        total_requests = usage["total_requests"]
        
        return jsonify({
            "success": True,
            "total_requests": total_requests,
            "total_prompt_tokens": usage["total_prompt_tokens"],
            "total_completion_tokens": usage["total_completion_tokens"],
            "total_tokens": usage["total_tokens"],
            "total_cost": usage["total_cost"],
            "average_tokens_per_request": round(usage["total_tokens"] / total_requests, 2) if total_requests > 0 else 0,
            "last_request": usage["last_request"]
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/metrics", methods=["POST"])
def get_metrics():
    """Calculate WER/CER between OCR draft and ground truth."""
    data = request.json
    reference = data.get("reference", "").strip()
    hypothesis = data.get("hypothesis", "").strip()
    
    if not reference or not hypothesis:
        return jsonify({
            "success": False,
            "message": "Both reference and hypothesis are required"
        })
    
    try:
        details = get_error_details(reference, hypothesis)
        return jsonify({
            "success": True,
            "wer": details["wer"],
            "cer": details["cer"],
            "word_accuracy": details["word_accuracy"],
            "char_accuracy": details["char_accuracy"],
            "ref_word_count": details["ref_word_count"],
            "hyp_word_count": details["hyp_word_count"],
            "ref_char_count": details["ref_char_count"],
            "hyp_char_count": details["hyp_char_count"],
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/metrics/cumulative", methods=["GET"])
def get_cumulative_metrics():
    """Get cumulative WER/CER metrics across all annotated pages."""
    try:
        history = load_metrics_history()
        return jsonify({
            "success": True,
            "cumulative": history["cumulative"],
            "pages": history["pages"],
            "total_pages": len(history["pages"])
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/metrics/recover", methods=["POST"])
def recover_metrics_endpoint():
    """Recover metrics from existing ground truth files."""
    try:
        result = recover_metrics()
        return jsonify({
            "success": True,
            "recovered": result["recovered"],
            "message": f"Recovered metrics for {result['recovered']} pages"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/sync_mapping", methods=["POST"])
def sync_mapping():
    """Sync mapping file with ground truth files.
    
    Scans the ground truth directory and updates the mapping file
    to mark all images with ground truth files as completed.
    This is useful when the mapping file gets out of sync.
    """
    try:
        mapping = load_mapping()
        synced = 0
        
        if OUTPUT_DIR.exists():
            for txt_file in OUTPUT_DIR.glob("*.txt"):
                image_name = txt_file.stem + ".png"
                if image_name not in mapping["completed"]:
                    mapping["completed"].append(image_name)
                    synced += 1
        
        save_mapping(mapping)
        
        return jsonify({
            "success": True,
            "synced": synced,
            "message": f"Synced {synced} images from ground truth files",
            "total_completed": len(mapping["completed"])
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def main():
    """Main entry point."""
    print("\n>> Devanagari OCR Annotation Tool")
    print(">> Loading sampled images...")
    
    # Count images
    if SAMPLE_DIR.exists():
        count = len(list(SAMPLE_DIR.glob("*.png")))
        print(f">> Found {count} sampled images")
    else:
        print(">> WARNING: No sampled images found!")
        print(">> Run: python sample_images_v2.py")
    
    print(">> Launching at http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=True)

if __name__ == "__main__":
    main()
