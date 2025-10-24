import logging
import json
import functions_framework
from src.main import perform_matchmaking
from src.verify_email import verify_email

# Configure logging for Cloud Functions
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def matchmake(request):
	"""HTTP Cloud Function entry point for matchmaking.
	
	Args:
		request (flask.Request): The request object.
		
	Returns:
		The response text, or any set of values that can be turned into a
		Response object using `make_response`.
	"""
	try:
		logger.info("Starting matchmaking process")

		perform_matchmaking(logger)
		
		# Return results
		result = {
			"status": "success",
		}
		
		logger.info("Matchmaking process completed successfully")
		return json.dumps(result), 200, {'Content-Type': 'application/json'}
		
	except Exception as e:
		logger.error(f"Error in matchmaking process: {str(e)}", exc_info=True)
		error_result = {
			"status": "error",
			"message": str(e)
		}
		return json.dumps(error_result), 500, {'Content-Type': 'application/json'}

@functions_framework.cloud_event
def matchmake_scheduled(cloud_event):
	"""Cloud Event Function entry point for scheduled matchmaking.
	
	This function can be triggered by Cloud Scheduler via Pub/Sub.
	
	Args:
		cloud_event: A CloudEvent object.
	"""
	try:
		logger.info("Starting scheduled matchmaking process")

		perform_matchmaking(logger)
		
		logger.info("Scheduled matchmaking process completed successfully")
	except Exception as e:
		logger.error(f"Error in scheduled matchmaking process: {str(e)}", exc_info=True)
		raise  # Re-raise to mark the function as failed

@functions_framework.http
def verify(request):
	success_redirect = "https://www.aisafety.com/doomr-verified"
	failure_redirect = "https://www.aisafety.com/doomr-failure"
	try:
		if request.method != "GET":
			return "Method not allowed", 405

		person_id = request.args.get('person_id')
		verification_id = request.args.get('verification_id')

		if not person_id:
			logger.error("Error in verifying email: person_id was missing")
			return "", 302, {"Location": failure_redirect}

		if not verification_id:
			logger.error("Error in verifying email: verification_id was missing")
			return "", 302, {"Location": failure_redirect}

		logger.info(f"Start verifying email for {verification_id}")
		verify_email(person_id, verification_id)
		logger.info(f"Done verifying email for {verification_id}")

		return "", 302, {"Location": success_redirect}

	except Exception as e:
		logger.error(f"Error in verifying email: {str(e)}", exc_info=True)
		return "", 302, {"Location": failure_redirect}

# For local testing
if __name__ == "__main__":
	# This allows you to test the function locally
	from flask import Flask, request

	app = Flask(__name__)

	@app.route('/', methods=['POST'])
	def local_test():
		return matchmake(request)

	app.run(debug=True, port=8080)
