from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

# Determine the service type from an environment variable
service_type = os.getenv('SERVICE_TYPE', 'hello')

@app.route('/hello', methods=['GET'])
def hello():
    if service_type == 'hello':
        # Return a simple JSON message
        return jsonify({"message": "Hello World"})
    elif service_type == 'caller':
        # Call the upstream hello-service and return its response
        try:
            response = requests.get('http://hello-service:5000/hello')
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Failed to reach hello-service", "details": str(e)}), 500
    else:
        return jsonify({"error": "Invalid service type"}), 400

if __name__ == '__main__':
    # Run the Flask app on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)
