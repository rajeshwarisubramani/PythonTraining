from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/call', methods=['GET'])
def call_hello_service():
    try:
        # Call the hello-service
        response = requests.get('http://hello-service:5000/hello')
        # Return the response from the hello-service
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        return jsonify({'error': 'Failed to connect to hello-service', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)