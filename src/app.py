import io
import base64
import signal
import pytesseract  # type: ignore
from PIL import Image, UnidentifiedImageError
from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import redis
import os

app = Flask(__name__)


def get_client_ip():
    """Get real client IP, handling proxies via X-Forwarded-For"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


# Rate limiting with Redis storage
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
try:
    redis_client = redis.from_url(redis_url)
    redis_client.ping()
    storage_uri = redis_url
except Exception:
    # Fallback to in-memory if Redis is not available
    storage_uri = None

limiter = Limiter(
    app=app,
    key_func=get_client_ip,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=storage_uri
)

# Configuration
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_LANGUAGES = {"rus", "eng", "rus+eng", "eng+rus"}
TIMEOUT_SECONDS = 30


def timeout_handler(signum, frame):
    raise TimeoutError("Image processing timeout")


def process_with_timeout(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT_SECONDS)
        try:
            result = func(*args, **kwargs)
        finally:
            signal.alarm(0)
        return result
    return wrapper


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", title="Home")


@app.route("/results", methods=["POST"])
@limiter.limit("10 per minute")
def result():
    try:
        data = request.form.get("data")
        language = request.form.get("language", "rus")
        
        if not data:
            return "Bad Request: No image data in request", 400

        if "," not in data:
            return "Bad Request: Invalid image data", 400

        # Validate language
        if language not in ALLOWED_LANGUAGES:
            return "Bad Request: Invalid language", 400

        # Decode and validate size
        try:
            image_data = base64.b64decode(data.split(",")[1])
        except Exception:
            return "Bad Request: Invalid base64 data", 400

        if len(image_data) > MAX_IMAGE_SIZE:
            return "Bad Request: Image size exceeds 5MB limit", 400

        # Process image with timeout
        try:
            image = Image.open(io.BytesIO(image_data))
            text = process_image_with_timeout(image, language)
        except TimeoutError:
            return "Bad Request: Image processing timeout", 408

        if not text:
            return "Bad Request: No text found in the image", 400

        text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])

        return text, 200
    except UnidentifiedImageError:
        return "Bad Request: The image is not supported", 400
    except Exception:
        return "Internal Server Error", 500


@process_with_timeout
def process_image_with_timeout(image, language):
    return pytesseract.image_to_string(image, lang=language)
