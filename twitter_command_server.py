import os
import tweepy
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_KEY_SECRET = os.environ.get("TWITTER_API_KEY_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

AUTH_TOKEN = os.environ.get("TWITTER_COMMAND_SERVER_AUTH_TOKEN", "abhi21dad")


app = Flask(__name__)


@app.route('/tweet', methods=['POST'])
def post_tweet():
    """
    Listens for a POST request to /tweet.
    The request body must be JSON and contain:
    {
        "text": "The content of the tweet.",
        "token": "YOUR_SUPER_SECRET_TOKEN"
    }
    """
    print("Received a request to /tweet")

   
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    tweet_text = data.get('text')
    received_token = data.get('token')

    if received_token != AUTH_TOKEN:
        print("Authentication failed: Invalid token")
        return jsonify({"error": "Unauthorized"}), 401

    if not tweet_text:
        return jsonify({"error": "Missing 'text' in request body"}), 400

   
    try:
        
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_KEY_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        print(f"Authenticated with Twitter. Attempting to post tweet: '{tweet_text}'")

      
        response = client.create_tweet(text=tweet_text)
        print(f"Successfully posted tweet. Tweet ID: {response.data['id']}")
        
        return jsonify({
            "success": True,
            "message": "Tweet posted successfully!",
            "tweet_id": response.data['id'],
            "tweet_text": response.data['text']
        }), 200

    except Exception as e:
       
        print(f"An error occurred while posting the tweet: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to post tweet.",
            "details": str(e)
        }), 500



@app.route('/')
def index():
    return "<h1>Twitter Command Server is running!</h1><p>Send POST requests to /tweet to post a tweet.</p>"


if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5001, debug=True)
